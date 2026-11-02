"""Logsheet append keeps the merged Action Date header. No Excel app."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook, load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import logsheet

HEADERS = [
    "Form No",
    "Department",
    "Staff No",
    "Staff Name",
    "AD Account",
    "Last Working Day",
    "Received Date",
]

VALUES = {
    "form_no": "value-form-no",
    "department": "value-department",
    "staff_no": "value-staff-no",
    "staff_name": "value-staff-name",
    "ad_account": "value-ad-account",
    "last_working_day": "2026-10-31",
    "received_date": "2026-10-01",
}

SECOND = {
    "form_no": "value-form-no-2",
    "department": "value-department-2",
    "staff_no": "value-staff-no-2",
    "staff_name": "value-staff-name-2",
    "ad_account": "value-ad-account-2",
    "last_working_day": "2026-10-30",
    "received_date": "2026-10-02",
}


def _new_logsheet(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Termination Form Logsheet"
    for column, header in enumerate(HEADERS, 1):
        sheet.cell(1, column, header)
    sheet.cell(1, 8, "Action Date")
    sheet.merge_cells("H1:I1")
    sheet.cell(2, 8, "Disable")
    sheet.cell(2, 9, "Delete")
    workbook.save(path)
    workbook.close()


class LogsheetTests(unittest.TestCase):
    def test_append_keeps_action_date_merge_and_leaves_disable_delete_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "logsheet.xlsx"
            _new_logsheet(path)
            columns = {key: "" for key in VALUES}
            first = logsheet.append_log_row(path, "", columns, None, VALUES)
            second = logsheet.append_log_row(path, "", columns, None, SECOND)
            self.assertEqual((first, second), (3, 4))

            workbook = load_workbook(path)
            sheet = workbook.active
            self.assertEqual([str(item) for item in sheet.merged_cells.ranges], ["H1:I1"])
            self.assertEqual(sheet["H1"].value, "Action Date")
            self.assertEqual(sheet["H2"].value, "Disable")
            self.assertEqual(sheet["I2"].value, "Delete")
            self.assertEqual(sheet["A3"].value, "value-form-no")
            self.assertEqual(sheet["G3"].value, "2026-10-01")
            self.assertIsNone(sheet["H3"].value)
            self.assertIsNone(sheet["I3"].value)
            self.assertEqual(sheet["A4"].value, "value-form-no-2")
            self.assertEqual(sheet["E4"].value, "value-ad-account-2")
            self.assertIsNone(sheet["H4"].value)
            self.assertIsNone(sheet["I4"].value)
            self.assertFalse(any(path.parent.glob(".logsheet*.xlsx")))
            workbook.close()

    def test_missing_headers_do_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.xlsx"
            workbook = Workbook()
            workbook.save(path)
            workbook.close()
            with self.assertRaises(logsheet.LogsheetError):
                logsheet.append_log_row(path, "", {}, None, VALUES)
            workbook = load_workbook(path)
            self.assertEqual(workbook.active["A1"].value, None)
            workbook.close()


if __name__ == "__main__":
    unittest.main()
