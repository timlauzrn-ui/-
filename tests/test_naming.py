"""Sequence numbers and the month reset. No Outlook or Word."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import naming


class NamingTests(unittest.TestCase):
    def test_october_2026_starts_at_2610001(self) -> None:
        self.assertEqual(naming.next_form_code(date(2026, 10, 1), []), "2610001")

    def test_november_2026_starts_at_2611001(self) -> None:
        self.assertEqual(naming.next_form_code(date(2026, 11, 15), []), "2611001")

    def test_sequence_is_highest_plus_one_and_keeps_gaps(self) -> None:
        names = ["2610001.pdf", "2610004.PDF", "notes.txt", "26100012.pdf"]
        self.assertEqual(naming.next_form_code(date(2026, 10, 31), names), "2610005")

    def test_month_reset_ignores_other_prefixes(self) -> None:
        names = ["2610001.pdf", "2610009.pdf", "2610999.pdf"]
        self.assertEqual(naming.next_form_code(date(2026, 11, 1), names), "2611001")

    def test_december_and_january_prefixes(self) -> None:
        self.assertEqual(naming.next_form_code(date(2025, 12, 1), []), "2512001")
        self.assertEqual(naming.next_form_code(date(2027, 1, 1), []), "2701001")

    def test_sequence_stops_at_999(self) -> None:
        with self.assertRaises(naming.SequenceError):
            naming.next_form_code(date(2026, 10, 1), ["2610999.pdf"])

    def test_allocate_reads_only_that_month_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            october = root / "2026" / "10"
            october.mkdir(parents=True)
            (october / "2610001.pdf").write_bytes(b"%PDF")
            (october / "ignore.txt").write_bytes(b"x")
            nested = october / "nested"
            nested.mkdir()
            (nested / "2610099.pdf").write_bytes(b"%PDF")

            dest = naming.allocate_pdf_path(october, date(2026, 10, 8))
            self.assertEqual(dest.name, "2610002.pdf")
            self.assertFalse(dest.exists())

            november = naming.filing_directory(root, date(2026, 11, 1), "%Y", "%m")
            dest_nov = naming.allocate_pdf_path(november, date(2026, 11, 1))
            self.assertEqual(november, root / "2026" / "11")
            self.assertEqual(dest_nov.name, "2611001.pdf")
            self.assertTrue(november.is_dir())
            self.assertFalse(dest_nov.exists())

    def test_received_date_can_choose_the_month(self) -> None:
        fields = {
            "last_working_day": "31/10/2026",
            "received_date": "02/11/2026",
        }
        formats = ["%d/%m/%Y"]
        last_working_day = naming.filing_day(fields, "last_working_day", formats)
        received = naming.filing_day(fields, "received_date", formats)
        self.assertEqual(naming.next_form_code(last_working_day, []), "2610001")
        self.assertEqual(
            naming.next_form_code(received, ["2610008.pdf"]),
            "2611001",
        )

    def test_unknown_filing_field_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            naming.filing_day(
                {"last_working_day": "2026-10-01"},
                "other",
                ["%Y-%m-%d"],
            )


if __name__ == "__main__":
    unittest.main()
