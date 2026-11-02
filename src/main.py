"""Poll Outlook for separation mail, file each form, then mail MIS once.

Run on the Windows PC that is signed in to Outlook and has the share mounted:

    python src/main.py --config config.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import tempfile
from pathlib import Path

import extract
import logsheet
import naming
import outlook
import pdfs

logger = logging.getLogger("separation")

_COLUMN_LETTER = re.compile(r"^[A-Za-z]{1,3}$")


class ConfigError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("Invalid config:\n- " + "\n- ".join(problems))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        config = load_config(Path(args.config))
        require_paths(config)
    except (OSError, json.JSONDecodeError, ConfigError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 2

    try:
        pythoncom = _import_pythoncom()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    pythoncom.CoInitialize()
    try:
        return _run(config, dry_run=args.dry_run)
    finally:
        pythoncom.CoUninitialize()


def _run(config: dict, dry_run: bool) -> int:
    try:
        app = outlook.connect()
        messages = outlook.pending_messages(app, config)
    except Exception as exc:
        logger.exception("Could not read Outlook.")
        print(exc, file=sys.stderr)
        return 1

    logger.info("Matched %s unread separation message(s).", len(messages))
    if dry_run:
        for message in messages:
            print(outlook.describe(message))
        return 0
    if not messages:
        logger.info("No unread separation mail.")
        return 0

    filed: list[dict] = []
    failed: list[dict] = []
    word_error = False
    try:
        with extract.WordApp() as word:
            for message in messages:
                subject = outlook.subject_of(message)
                try:
                    result = process_message(message, config, word)
                except Exception as exc:
                    logger.exception("Could not file message: %s", subject)
                    failed.append({"subject": subject, "error": str(exc)})
                    continue
                try:
                    outlook.mark_processed(message, app, config)
                except Exception as exc:
                    result["mark_error"] = str(exc)
                    logger.error(
                        "Filed %s and could not mark the message processed: %s",
                        result["pdf_path"],
                        exc,
                    )
                filed.append(result)
                logger.info("Filed form %s at %s", result["form_no"], result["pdf_path"])
    except Exception as exc:
        word_error = True
        logger.exception("Word stopped the batch.")
        print(exc, file=sys.stderr)

    send_failed = False
    if filed:
        body = outlook.build_summary_body(filed, failed)
        logger.info("Summary:\n%s", body)
        try:
            outlook.send_summary(app, config, body)
        except Exception as exc:
            send_failed = True
            logger.exception("The summary mail could not be sent.")
            print(exc, file=sys.stderr)
    mark_errors = any(row.get("mark_error") for row in filed)
    if failed or mark_errors or send_failed or word_error:
        return 1
    return 0


def process_message(message, config: dict, word: extract.WordApp) -> dict:
    """File one Word attachment. The source message is left unread on failure."""
    with tempfile.TemporaryDirectory(prefix="separation-") as temporary:
        directory = Path(temporary)
        attachment = outlook.save_word_attachment(message, directory)
        document = word.open_readonly(attachment)
        form_pdf = directory / "form.pdf"
        try:
            fields = extract.read_mapped_fields(document, config["word_fields"])
            when = naming.filing_day(
                fields, config["filing_date_field"], config["date_formats"]
            )
            pdfs.export_docx_to_pdf(document, form_pdf)
        finally:
            extract.close_document(document)

        merged = directory / "merged.pdf"
        pdfs.append_checklist(form_pdf, Path(config["checklist_pdf"]), merged)
        month_dir = naming.filing_directory(
            config["share_root"],
            when,
            config["year_folder_format"],
            config["month_folder_format"],
        )
        destination = _place_with_retry(merged, month_dir, when)
        try:
            logsheet.append_log_row(
                Path(config["logsheet_path"]),
                config["logsheet_sheet"],
                config["logsheet_columns"],
                config["logsheet_header_rows"],
                fields,
            )
        except Exception as exc:
            try:
                destination.unlink(missing_ok=True)
            except OSError as cleanup_error:
                raise RuntimeError(
                    f"The logsheet update failed ({exc}) and the PDF could not be removed: {destination}."
                ) from cleanup_error
            raise
        return {
            "staff_name": fields["staff_name"],
            "form_no": fields["form_no"],
            "last_working_day": fields["last_working_day"],
            "pdf_path": str(destination),
        }


def _place_with_retry(merged: Path, month_dir: Path, when) -> Path:
    last_error: Exception | None = None
    for _ in range(5):
        destination = naming.allocate_pdf_path(month_dir, when)
        try:
            pdfs.place_new_pdf(merged, destination)
            return destination
        except FileExistsError as exc:
            last_error = exc
    raise FileExistsError(
        f"Could not reserve a PDF name in {month_dir}."
    ) from last_error


def load_config(path: Path) -> dict:
    """Load config.json and reject empty required placeholders."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError([f"Config file not found: {path}"])
    with path.open(encoding="utf-8-sig") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ConfigError(["The config file must be a JSON object."])
    problems: list[str] = []
    config = {
        "share_root": _required_text(raw, "share_root", problems),
        "logsheet_path": _required_text(raw, "logsheet_path", problems),
        "logsheet_sheet": _optional_text(raw, "logsheet_sheet"),
        "logsheet_header_rows": _optional_header_rows(raw, problems),
        "logsheet_columns": _column_letters(raw.get("logsheet_columns"), problems),
        "checklist_pdf": _required_text(raw, "checklist_pdf", problems),
        "filing_date_field": _filing_field(raw, problems),
        "year_folder_format": _format_text(raw, "year_folder_format", "%Y", problems),
        "month_folder_format": _format_text(raw, "month_folder_format", "%m", problems),
        "date_formats": _date_formats(raw, problems),
        "outlook": _outlook_config(raw.get("outlook"), problems),
        "summary_mail": _summary_config(raw.get("summary_mail"), problems),
        "word_fields": _word_fields(raw.get("word_fields"), problems),
    }
    if problems:
        raise ConfigError(problems)
    return config


def require_paths(config: dict) -> None:
    """Fail before touching mail when the share, logsheet, or checklist is missing."""
    share = Path(config["share_root"])
    logsheet_path = Path(config["logsheet_path"])
    checklist = Path(config["checklist_pdf"])
    problems = []
    if not share.exists():
        problems.append(f"share_root is not reachable: {share}")
    if not logsheet_path.is_file():
        problems.append(f"logsheet_path is not a file: {logsheet_path}")
    elif logsheet_path.suffix.lower() not in {".xlsx", ".xlsm"}:
        problems.append("logsheet_path must be an .xlsx or .xlsm file.")
    if not checklist.is_file():
        problems.append(f"checklist_pdf is not a file: {checklist}")
    elif checklist.suffix.lower() != ".pdf":
        problems.append("checklist_pdf must be a .pdf file.")
    if problems:
        raise ValueError("\n".join(problems))


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="File Outlook separation mail onto the shared drive and notify MIS."
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config.json (default: config.json in the current directory).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List matching unread mail and do not file, mark, or send anything.",
    )
    return parser.parse_args(argv)


def _import_pythoncom():
    try:
        import pythoncom
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 is required. Run this script on the Windows PC where Outlook is installed."
        ) from exc
    return pythoncom


def _required_text(raw: dict, key: str, problems: list[str]) -> str:
    value = raw.get(key, "")
    if not isinstance(value, str) or not value.strip():
        problems.append(f"Set {key}.")
        return ""
    return value.strip()


def _optional_text(raw: dict, key: str) -> str:
    value = raw.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        return str(value).strip()
    return value.strip()


def _optional_header_rows(raw: dict, problems: list[str]) -> int | None:
    value = raw.get("logsheet_header_rows", "")
    if value == "" or value is None:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        problems.append("logsheet_header_rows must be a positive integer or empty.")
        return None
    if number < 1:
        problems.append("logsheet_header_rows must be a positive integer or empty.")
        return None
    return number


def _column_letters(raw, problems: list[str]) -> dict[str, str]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        problems.append("logsheet_columns must be an object.")
        return {}
    columns = {}
    for key in extract.FIELD_KEYS:
        value = raw.get(key, "")
        if value is None or value == "":
            columns[key] = ""
            continue
        letter = str(value).strip().upper()
        if not _COLUMN_LETTER.match(letter):
            problems.append(f"logsheet_columns.{key} must be a column letter such as A.")
            columns[key] = ""
            continue
        columns[key] = letter
    return columns


def _filing_field(raw: dict, problems: list[str]) -> str:
    value = raw.get("filing_date_field", "last_working_day")
    if not isinstance(value, str) or value.strip() not in ("last_working_day", "received_date"):
        problems.append("filing_date_field must be last_working_day or received_date.")
        return "last_working_day"
    return value.strip()


def _format_text(raw: dict, key: str, default: str, problems: list[str]) -> str:
    value = raw.get(key, default)
    if not isinstance(value, str) or not value.strip():
        problems.append(f"Set {key}.")
        return default
    return value.strip()


def _date_formats(raw: dict, problems: list[str]) -> list[str]:
    value = raw.get("date_formats")
    if not isinstance(value, list) or not value:
        problems.append("date_formats must be a non-empty list of strptime patterns.")
        return []
    formats = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            problems.append("date_formats must contain only non-empty strings.")
            return []
        formats.append(item.strip())
    return formats


def _outlook_config(raw, problems: list[str]) -> dict:
    if not isinstance(raw, dict):
        problems.append("outlook must be an object.")
        raw = {}
    folder_path = str(raw.get("folder_path") or "").strip()
    subject = str(raw.get("subject_contains") or "").strip()
    parts = [part for part in re.split(r"[\\/]+", folder_path) if part]
    inbox_path = not parts or parts[-1].casefold() == "inbox"
    if inbox_path and not subject:
        problems.append(
            "Set outlook.folder_path to a dedicated folder, or set outlook.subject_contains "
            "so Inbox mail is filtered."
        )
    category = raw.get("processed_category", "SeparationFiled")
    if category is None:
        category = ""
    if not isinstance(category, str):
        problems.append("outlook.processed_category must be a string.")
        category = ""
    return {
        "mailbox": str(raw.get("mailbox") or "").strip(),
        "folder_path": folder_path,
        "subject_contains": subject,
        "processed_folder": str(raw.get("processed_folder") or "").strip(),
        "processed_category": category.strip(),
    }


def _summary_config(raw, problems: list[str]) -> dict:
    if not isinstance(raw, dict):
        problems.append("summary_mail must be an object.")
        raw = {}
    recipients = _address_list(raw.get("to"), "summary_mail.to", problems, required=True)
    copies = _address_list(raw.get("cc"), "summary_mail.cc", problems, required=False)
    subject = raw.get("subject", "Separation forms filed")
    if subject is None:
        subject = ""
    if not isinstance(subject, str):
        problems.append("summary_mail.subject must be a string.")
        subject = "Separation forms filed"
    return {"to": recipients, "cc": copies, "subject": subject.strip()}


def _address_list(value, label: str, problems: list[str], required: bool) -> list[str]:
    if value is None:
        value = []
    if isinstance(value, str):
        value = [value] if value.strip() else []
    if not isinstance(value, list):
        problems.append(f"{label} must be a list of recipients.")
        return []
    addresses = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            problems.append(f"{label} must contain only non-empty strings.")
            return []
        addresses.append(item.strip())
    if required and not addresses:
        problems.append(f"Set {label} to the MIS distribution list.")
    return addresses


def _word_fields(raw, problems: list[str]) -> dict:
    if not isinstance(raw, dict):
        problems.append("word_fields must be an object.")
        return {}
    fields = {}
    for key in extract.FIELD_KEYS:
        spec = raw.get(key)
        if not isinstance(spec, dict):
            problems.append(f"Set word_fields.{key}.")
            continue
        kind = str(spec.get("kind") or "").strip()
        if kind == "content_control":
            tag = str(spec.get("tag") or "").strip()
            title = str(spec.get("title") or "").strip()
            if not tag and not title:
                problems.append(f"Set word_fields.{key}.tag or word_fields.{key}.title.")
            fields[key] = {"kind": kind, "tag": tag, "title": title}
        elif kind == "table_cell":
            try:
                fields[key] = {
                    "kind": kind,
                    "table": _positive_int(spec.get("table"), f"word_fields.{key}.table"),
                    "row": _positive_int(spec.get("row"), f"word_fields.{key}.row"),
                    "column": _positive_int(spec.get("column"), f"word_fields.{key}.column"),
                }
            except ValueError as exc:
                problems.append(str(exc))
        else:
            problems.append(
                f"Set word_fields.{key}.kind to content_control or table_cell."
            )
    return fields


def _positive_int(value, label: str) -> int:
    if isinstance(value, bool) or value == "" or value is None:
        raise ValueError(f"{label} must be a positive integer.")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive integer.") from exc
    if number < 1:
        raise ValueError(f"{label} must be a positive integer.")
    return number


if __name__ == "__main__":
    raise SystemExit(main())
