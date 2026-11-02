"""Append one Termination Form Logsheet row without touching merged headers."""

from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.utils import column_index_from_string

from extract import FIELD_KEYS

HEADER_LABELS = {
    "form no": "form_no",
    "form number": "form_no",
    "department": "department",
    "staff no": "staff_no",
    "staff number": "staff_no",
    "staff name": "staff_name",
    "ad account": "ad_account",
    "last working day": "last_working_day",
    "received date": "received_date",
    "disable": "disable",
    "delete": "delete",
}


logger = logging.getLogger("separation")


class LogsheetError(Exception):
    """The logsheet row could not be appended."""


def append_log_row(
    workbook_path: Path,
    sheet_name: str,
    configured_columns: dict[str, str],
    header_rows: int | None,
    values: dict[str, str],
) -> int:
    """Append the seven form values. Disable and Delete stay blank.

    Returns the 1-based row that was written. The Action Date merge is left
    as it was. The workbook is saved by replacing the file only after the
    in-memory sheet still has the same merged ranges.
    """
    path = Path(workbook_path)
    keep_vba = path.suffix.lower() == ".xlsm"
    workbook = load_workbook(path, keep_vba=keep_vba)
    try:
        sheet = _select_sheet(workbook, sheet_name)
        row = append_log_row_to_sheet(sheet, configured_columns, header_rows, values)
        _save_replace(workbook, path)
        return row
    finally:
        try:
            workbook.close()
        except Exception:
            logger.warning("Could not close the logsheet.", exc_info=True)


def append_log_row_to_sheet(sheet, configured_columns, header_rows, values) -> int:
    """Write one data row onto an open worksheet. Does not save."""
    columns, header_depth = resolve_columns(sheet, configured_columns, header_rows)
    row = _next_data_row(sheet, columns, header_depth)
    before = _merge_snapshot(sheet)
    for key in FIELD_KEYS:
        if key not in values:
            raise LogsheetError(f"Missing logsheet value for {key}.")
        column = columns[key]
        cell = sheet.cell(row, column)
        if isinstance(cell, MergedCell):
            raise LogsheetError(
                f"The cell for {key} on row {row} is inside a merged range. "
                "Write data on the row below the Action Date header."
            )
        cell.value = values[key]
    after = _merge_snapshot(sheet)
    if before != after:
        raise LogsheetError("Appending a row changed merged cells. The logsheet was not saved.")
    return row


def resolve_columns(sheet, configured_columns, header_rows: int | None):
    """Map field names to column indexes and return the header depth."""
    found = _find_headers(sheet)
    columns: dict[str, int] = {}
    missing: list[str] = []
    for key in FIELD_KEYS:
        letter = ""
        if configured_columns:
            letter = str(configured_columns.get(key) or "").strip()
        if letter:
            columns[key] = column_index_from_string(letter)
        elif key in found:
            columns[key] = found[key][1]
        else:
            missing.append(key)
    if missing:
        raise LogsheetError(
            "The logsheet is missing headers for: "
            + ", ".join(missing)
            + ". Set logsheet_columns to the column letters, or use the header names "
            "Form No, Department, Staff No, Staff Name, AD Account, Last Working Day, "
            "and Received Date."
        )
    if header_rows:
        depth = int(header_rows)
    else:
        depths = [found[key][0] for key in FIELD_KEYS if key in found]
        depths.extend(pos[0] for name, pos in found.items() if name in ("disable", "delete"))
        if not depths:
            raise LogsheetError(
                "Could not find a header row. Set logsheet_header_rows."
            )
        depth = max(depths)
    return columns, depth


def _select_sheet(workbook, sheet_name: str):
    if sheet_name:
        if sheet_name not in workbook.sheetnames:
            raise LogsheetError(
                f"logsheet_sheet {sheet_name!r} is not in the workbook. "
                f"Sheets: {', '.join(workbook.sheetnames)}."
            )
        return workbook[sheet_name]
    sheet = workbook.active
    if sheet is None:
        raise LogsheetError("The logsheet workbook has no active sheet.")
    return sheet


def _normalize_header(value: object) -> str:
    text = str(value or "").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text.strip(".:")


def _find_headers(sheet) -> dict[str, tuple[int, int]]:
    found: dict[str, tuple[int, int]] = {}
    max_row = min(sheet.max_row or 1, 30)
    max_col = min(sheet.max_column or 1, 30)
    for row in sheet.iter_rows(min_row=1, max_row=max_row, max_col=max_col):
        for cell in row:
            if isinstance(cell, MergedCell):
                continue
            key = HEADER_LABELS.get(_normalize_header(cell.value))
            if key and key not in found:
                found[key] = (cell.row, cell.column)
    return found


def _blank(value: object) -> bool:
    return value is None or str(value).strip() == ""


def _next_data_row(sheet, columns: dict[str, int], header_depth: int) -> int:
    last_used = header_depth
    tracked = set(columns.values())
    max_col = max(tracked)
    max_row = sheet.max_row or header_depth
    for row in sheet.iter_rows(min_row=header_depth + 1, max_row=max_row, max_col=max_col):
        if any(cell.column in tracked and not _blank(cell.value) for cell in row):
            last_used = row[0].row
    return last_used + 1


def _merge_snapshot(sheet) -> list[str]:
    return sorted(str(item) for item in sheet.merged_cells.ranges)


def _save_replace(workbook, path: Path) -> None:
    """Save to a temp file beside the workbook, then replace it."""
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}.",
        suffix=path.suffix,
        dir=path.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        workbook.save(temporary)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
