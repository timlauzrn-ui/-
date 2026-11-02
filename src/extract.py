"""Read mapped fields from a Word attachment via Word COM."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("separation")

# wdAlertsNone, wdDoNotSaveChanges, msoAutomationSecurityForceDisable
WD_ALERTS_NONE = 0
WD_DO_NOT_SAVE_CHANGES = 0
MSO_AUTOMATION_SECURITY_FORCE_DISABLE = 3

FIELD_KEYS = (
    "form_no",
    "department",
    "staff_no",
    "staff_name",
    "ad_account",
    "last_working_day",
    "received_date",
)

_PLACEHOLDERS = {
    "click or tap here to enter text.",
    "click here to enter text.",
    "enter text.",
    "[enter text]",
}


class FieldReadError(Exception):
    """A configured Word field could not be read."""


def clean_word_text(value: object) -> str:
    """Drop Word cell markers and collapse whitespace."""
    if value is None:
        return ""
    text = str(value)
    text = (
        text.replace("\xa0", " ")
        .replace("\x07", " ")
        .replace("\r", " ")
        .replace("\x0b", " ")
    )
    return re.sub(r"\s+", " ", text).strip()


class WordApp:
    """Word session that quits only when this script started Word."""

    def __init__(self) -> None:
        self.app = None
        self.started = False
        self._previous_alerts = None
        self._previous_security = None

    def __enter__(self) -> "WordApp":
        try:
            import win32com.client
        except ImportError as exc:
            raise RuntimeError(
                "pywin32 is required. Run this script on the Windows PC where Word is installed."
            ) from exc
        try:
            self.app = win32com.client.GetActiveObject("Word.Application")
            self.started = False
        except Exception:
            self.app = win32com.client.Dispatch("Word.Application")
            self.started = True
            self.app.Visible = False
        try:
            self._previous_alerts = self.app.DisplayAlerts
        except Exception:
            self._previous_alerts = None
        self.app.DisplayAlerts = WD_ALERTS_NONE
        try:
            self._previous_security = self.app.AutomationSecurity
            self.app.AutomationSecurity = MSO_AUTOMATION_SECURITY_FORCE_DISABLE
        except Exception:
            self._previous_security = None
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self.app is None:
            return False
        if self.started:
            try:
                self.app.Quit()
            except Exception:
                logger.warning("Word did not quit.", exc_info=True)
            return False
        try:
            if self._previous_alerts is not None:
                self.app.DisplayAlerts = self._previous_alerts
            if self._previous_security is not None:
                self.app.AutomationSecurity = self._previous_security
        except Exception:
            logger.warning("Word settings could not be restored.", exc_info=True)
        return False

    def open_readonly(self, path):
        # ConfirmConversions=False, ReadOnly=True, AddToRecentFiles=False
        return self.app.Documents.Open(str(path), False, True, False)


def close_document(document) -> None:
    """Close without saving. A close failure is logged and swallowed."""
    try:
        document.Saved = True
    except Exception:
        pass
    try:
        document.Close(WD_DO_NOT_SAVE_CHANGES)
    except Exception:
        logger.warning("Word did not close the document.", exc_info=True)


def read_mapped_fields(document, field_map: dict) -> dict[str, str]:
    """Read the seven form fields from content controls or table cells."""
    values: dict[str, str] = {}
    for key in FIELD_KEYS:
        spec = field_map[key]
        text = _read_one(document, key, spec)
        if not text or text.casefold() in _PLACEHOLDERS:
            raise FieldReadError(f"word_fields.{key} is blank in the document.")
        values[key] = text
    return values


def _read_one(document, key: str, spec: dict) -> str:
    kind = spec["kind"]
    if kind == "content_control":
        return _read_content_control(document, key, spec)
    if kind == "table_cell":
        return _read_table_cell(document, key, spec)
    raise FieldReadError(
        f"word_fields.{key}.kind must be content_control or table_cell."
    )


def _read_content_control(document, key: str, spec: dict) -> str:
    tag = spec.get("tag") or ""
    title = spec.get("title") or ""
    if tag:
        found = document.SelectContentControlsByTag(tag)
        _expect_one(found, key, "tag")
        if found.Count == 1:
            return clean_word_text(found.Item(1).Range.Text)
    if title:
        found = document.SelectContentControlsByTitle(title)
        _expect_one(found, key, "title")
        if found.Count == 1:
            return clean_word_text(found.Item(1).Range.Text)
    raise FieldReadError(f"No content control matched word_fields.{key}.")


def _expect_one(found, key: str, how: str) -> None:
    count = int(found.Count)
    if count > 1:
        raise FieldReadError(
            f"word_fields.{key} matched {count} content controls by {how}."
        )


def _read_table_cell(document, key: str, spec: dict) -> str:
    try:
        table = document.Tables(spec["table"])
        cell = table.Cell(spec["row"], spec["column"])
        return clean_word_text(cell.Range.Text)
    except FieldReadError:
        raise
    except Exception as exc:
        raise FieldReadError(
            f"Could not read word_fields.{key} from table {spec['table']}, "
            f"row {spec['row']}, column {spec['column']}."
        ) from exc
