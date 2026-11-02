"""Config placeholders and the MIS summary text. No Outlook or Word."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import extract
import main
import outlook

ROOT = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    def test_example_config_has_empty_placeholders(self) -> None:
        raw = (ROOT / "config.example.json").read_text(encoding="utf-8")
        data = json.loads(raw)
        self.assertEqual(data["share_root"], "")
        self.assertEqual(data["logsheet_path"], "")
        self.assertEqual(data["checklist_pdf"], "")
        self.assertEqual(data["outlook"]["mailbox"], "")
        self.assertEqual(data["outlook"]["folder_path"], "")
        self.assertEqual(data["outlook"]["subject_contains"], "")
        self.assertEqual(data["summary_mail"]["to"], [])
        for spec in data["word_fields"].values():
            self.assertEqual(spec["kind"], "")
            self.assertEqual(spec["tag"], "")
            self.assertEqual(spec["title"], "")
        self.assertNotIn("@", raw)
        self.assertNotIn("\\\\", raw)
        with self.assertRaises(main.ConfigError):
            main.load_config(ROOT / "config.example.json")

    def test_filled_config_normalizes_word_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(_filled_config()), encoding="utf-8")
            config = main.load_config(path)
        self.assertEqual(config["filing_date_field"], "received_date")
        self.assertEqual(config["word_fields"]["form_no"]["tag"], "form-no-tag")
        self.assertEqual(config["word_fields"]["department"]["table"], 1)
        self.assertEqual(config["word_fields"]["department"]["row"], 2)
        self.assertEqual(config["word_fields"]["department"]["column"], 3)
        self.assertEqual(config["summary_mail"]["to"], ["MIS list"])
        self.assertEqual(config["logsheet_columns"]["form_no"], "B")

    def test_require_paths_checks_the_share_files(self) -> None:
        config = _filled_config()
        with self.assertRaises(ValueError):
            main.require_paths(config)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logsheet = root / "log.xlsx"
            checklist = root / "check.pdf"
            logsheet.write_bytes(b"")
            checklist.write_bytes(b"")
            config["share_root"] = str(root)
            config["logsheet_path"] = str(logsheet)
            config["checklist_pdf"] = str(checklist)
            main.require_paths(config)

    def test_clean_word_text_strips_cell_markers(self) -> None:
        self.assertEqual(extract.clean_word_text("name-token\r\x07"), "name-token")
        self.assertEqual(extract.clean_word_text("a\xa0b"), "a b")

    def test_summary_lists_name_form_day_and_path(self) -> None:
        body = outlook.build_summary_body(
            [
                {
                    "staff_name": "value-staff-name",
                    "form_no": "value-form-no",
                    "last_working_day": "2026-10-31",
                    "pdf_path": "SHARE/2026/10/2610001.pdf",
                }
            ],
            [{"subject": "separation mail", "error": "missing attachment"}],
        )
        self.assertIn("value-staff-name", body)
        self.assertIn("value-form-no", body)
        self.assertIn("2026-10-31", body)
        self.assertIn("SHARE/2026/10/2610001.pdf", body)
        self.assertIn("Not filed", body)
        self.assertIn("missing attachment", body)


def _filled_config() -> dict:
    word_fields = {}
    for key in extract.FIELD_KEYS:
        if key == "department":
            word_fields[key] = {
                "kind": "table_cell",
                "tag": "",
                "title": "",
                "table": "1",
                "row": "2",
                "column": "3",
            }
        else:
            word_fields[key] = {
                "kind": "content_control",
                "tag": f"{key.replace('_', '-')}-tag",
                "title": "",
                "table": "",
                "row": "",
                "column": "",
            }
    return {
        "share_root": "SHARE",
        "logsheet_path": "SHARE/log.xlsx",
        "logsheet_sheet": "",
        "logsheet_header_rows": "",
        "logsheet_columns": {
            "form_no": "b",
            "department": "",
            "staff_no": "",
            "staff_name": "",
            "ad_account": "",
            "last_working_day": "",
            "received_date": "",
        },
        "checklist_pdf": "SHARE/check.pdf",
        "filing_date_field": "received_date",
        "year_folder_format": "%Y",
        "month_folder_format": "%m",
        "date_formats": ["%Y-%m-%d", "%d/%m/%Y"],
        "outlook": {
            "mailbox": "",
            "folder_path": "Inbox\\Separation",
            "subject_contains": "",
            "processed_folder": "",
            "processed_category": "SeparationFiled",
        },
        "summary_mail": {
            "to": ["MIS list"],
            "cc": [],
            "subject": "Separation forms filed",
        },
        "word_fields": word_fields,
    }


if __name__ == "__main__":
    unittest.main()
