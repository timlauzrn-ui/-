"""Filing codes and the year/month folder they belong to.

October 2026 starts at 2610001. November 2026 starts at 2611001.
The first four digits are the year and month (YYMM). The last three are a
sequence taken from the highest matching PDF in that month folder, plus one.
The sequence returns to 001 each month.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path, PurePath
from typing import Iterable


class SequenceError(ValueError):
    """The month folder has no unused three-digit sequence left."""


def month_prefix(when: date) -> str:
    """Return the YYMM prefix for a calendar month."""
    return f"{when.year % 100:02d}{when.month:02d}"


def sequence_in_name(name: str, prefix: str) -> int | None:
    """Return the 1-999 sequence if `name` is a YYMMNNN.pdf for this month."""
    path = PurePath(name)
    if path.suffix.lower() != ".pdf":
        return None
    stem = path.stem
    if len(stem) != 7 or not stem.isdigit() or not stem.startswith(prefix):
        return None
    return int(stem[4:])


def next_form_code(when: date, existing_names: Iterable[str]) -> str:
    """Return the next YYMMNNN code given the file names already in the folder."""
    prefix = month_prefix(when)
    highest = 0
    for name in existing_names:
        sequence = sequence_in_name(name, prefix)
        if sequence is not None and sequence > highest:
            highest = sequence
    nxt = highest + 1
    if nxt > 999:
        raise SequenceError(
            f"No sequence number left for {prefix} (001-999 are already used)."
        )
    return f"{prefix}{nxt:03d}"


def filing_directory(
    share_root: str | Path,
    when: date,
    year_format: str = "%Y",
    month_format: str = "%m",
) -> Path:
    """Return {share}/{Year}/{Month} for the filing date."""
    return Path(share_root) / when.strftime(year_format) / when.strftime(month_format)


def allocate_pdf_path(month_dir: Path, when: date) -> Path:
    """Create the month folder if needed and return the next PDF path.

    The PDF file itself is not created here, so a later failure does not
    consume the number.
    """
    month_dir.mkdir(parents=True, exist_ok=True)
    names = [entry.name for entry in month_dir.iterdir() if entry.is_file()]
    code = next_form_code(when, names)
    return month_dir / f"{code}.pdf"


def parse_date(value: object, formats: Iterable[str]) -> date:
    """Parse a form date with the configured formats."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("The filing date is empty.")
    format_list = list(formats)
    for fmt in format_list:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not parse date {text!r} with date_formats {format_list}.")


def filing_day(fields: dict[str, str], field_name: str, formats: Iterable[str]) -> date:
    """Pick Last Working Day or Received Date, then parse it."""
    if field_name not in ("last_working_day", "received_date"):
        raise ValueError(
            "filing_date_field must be last_working_day or received_date."
        )
    return parse_date(fields[field_name], formats)
