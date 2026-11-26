#!/usr/bin/env python3
"""Convert a Yiant BIFF .xls worksheet into a private working CSV."""
import argparse
import csv
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import xlrd


def convert(source, destination, sheet_name=None):
    with xlrd.open_workbook(source, on_demand=True) as book:
        if sheet_name is None:
            visible = [s for s in book.sheets() if s.visibility == 0]
            if len(visible) != 1:
                raise ValueError("Select the product worksheet with --sheet")
            sheet = visible[0]
        else:
            sheet = book.sheet_by_name(sheet_name)
        if not sheet.nrows:
            raise ValueError("The selected worksheet is empty")
        headers = sheet.row_values(0)
        if not all(isinstance(h, str) and h and h == h.strip() for h in headers):
            raise ValueError("The header row must contain field names")
        if len(headers) != len(set(headers)):
            raise ValueError("The header row has duplicate names")
        link_col = headers.index("link") if "link" in headers else None
        private_columns = {i for i, h in enumerate(headers) if h in ("SANDBASE_API_KEY", "IMGBB_API_KEY")}
        destination.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", newline="", encoding="utf-8", dir=destination.parent) as tmp:
            writer = csv.writer(tmp)
            writer.writerow(headers)
            for r in range(1, sheet.nrows):
                values = sheet.row_values(r)
                for c, cell in enumerate(sheet.row(r)):
                    if cell.ctype == xlrd.XL_CELL_ERROR:
                        raise ValueError(f"Worksheet error at row {r + 1}, column {c + 1}")
                    if c in private_columns and cell.ctype not in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK, xlrd.XL_CELL_TEXT):
                        raise ValueError(f"Enter the key as text in row {r + 1}, column {c + 1}")
                hyperlink = sheet.hyperlink_map.get((r, link_col))
                if hyperlink and hyperlink.url_or_path:
                    target = hyperlink.url_or_path
                    displayed = str(values[link_col]).strip()
                    if displayed.startswith(("http://", "https://")) and displayed != target:
                        raise ValueError(f"Displayed link and hyperlink target differ in row {r + 1}")
                    values[link_col] = target
                writer.writerow(values)
            tmp.flush()
            os.link(tmp.name, destination)
    return sheet.nrows - 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--sheet", help="Worksheet name for a multi-sheet workbook")
    args = parser.parse_args()
    try:
        count = convert(args.source, args.destination, args.sheet)
    except (OSError, ValueError, xlrd.XLRDError) as exc:
        parser.exit(2, f"Cannot convert workbook: {exc}\n")
    print(f"Converted {count} data rows to a private working CSV.")
