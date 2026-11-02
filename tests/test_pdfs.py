"""Checklist pages are appended after the form. No Word."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pdfs


def _blank(path: Path, width: float, height: float) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
    with path.open("wb") as handle:
        writer.write(handle)


class PdfTests(unittest.TestCase):
    def test_checklist_follows_the_form(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            form = root / "form.pdf"
            checklist = root / "checklist.pdf"
            destination = root / "merged.pdf"
            _blank(form, 111, 111)
            _blank(checklist, 222, 333)
            pdfs.append_checklist(form, checklist, destination)
            reader = PdfReader(str(destination))
            self.assertEqual(len(reader.pages), 2)
            self.assertAlmostEqual(float(reader.pages[0].mediabox.width), 111)
            self.assertAlmostEqual(float(reader.pages[1].mediabox.width), 222)
            self.assertAlmostEqual(float(reader.pages[1].mediabox.height), 333)

    def test_place_new_pdf_does_not_replace_an_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.pdf"
            _blank(source, 100, 100)
            destination = root / "2610001.pdf"
            pdfs.place_new_pdf(source, destination)
            with self.assertRaises(FileExistsError):
                pdfs.place_new_pdf(source, destination)
            reader = PdfReader(str(destination))
            self.assertEqual(len(reader.pages), 1)


if __name__ == "__main__":
    unittest.main()
