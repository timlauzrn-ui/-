"""Export the Word form to PDF and append the checklist."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from pypdf import PdfReader, PdfWriter

# wdExportFormatPDF
WD_EXPORT_FORMAT_PDF = 17


class PdfError(Exception):
    """The form PDF could not be built."""


def export_docx_to_pdf(document, pdf_path: Path) -> None:
    """Ask the open Word document to export a PDF."""
    document.ExportAsFixedFormat(str(pdf_path), WD_EXPORT_FORMAT_PDF)
    path = Path(pdf_path)
    if not path.is_file() or path.stat().st_size == 0:
        raise PdfError(f"Word did not create a PDF at {path}.")


def append_checklist(form_pdf: Path, checklist_pdf: Path, destination: Path) -> None:
    """Write a new PDF with the form pages followed by the checklist pages."""
    writer = PdfWriter()
    for source in (Path(form_pdf), Path(checklist_pdf)):
        reader = PdfReader(str(source))
        if reader.is_encrypted:
            raise PdfError(f"Cannot append an encrypted PDF: {source}.")
        if len(reader.pages) == 0:
            raise PdfError(f"PDF has no pages: {source}.")
        for page in reader.pages:
            writer.add_page(page)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        writer.write(handle)


def place_new_pdf(source: Path, destination: Path) -> None:
    """Create `destination` only when that file is not already there."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        descriptor = os.open(destination, flags)
    except FileExistsError as exc:
        raise FileExistsError(f"PDF already exists: {destination}.") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle, Path(source).open("rb") as incoming:
            shutil.copyfileobj(incoming, handle)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
