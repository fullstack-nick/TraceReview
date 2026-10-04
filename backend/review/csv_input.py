"""Strict input interpretation. Original bytes are never rewritten."""
import csv
import io
import math
import re
from decimal import Decimal, InvalidOperation
from .calculation import analyze_trace
from .exceptions import DomainError

PARSER_VERSION = "csv-time-signal-v1"
MAX_FILE_BYTES = 262144
COLUMNS = ["time_min", "signal_au"]
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
csv.field_size_limit(128)


def fail(message, line, column=None, code="invalid_csv"):
    prefix = f"Line {line}" + (f", {column}" if column else "")
    raise DomainError(f"{prefix}: {message}", code, location={"line": line, "column": column})


def parse_csv(source: bytes):
    if len(source) > MAX_FILE_BYTES:
        raise DomainError("File exceeds 256 KiB.", "upload_too_large", 413)
    try:
        content = source.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise DomainError("Save the file as UTF-8 CSV.", "invalid_encoding") from exc
    if re.search(r"\r(?!\n)", content):
        raise DomainError("Use LF or CRLF line endings.", "invalid_csv")
    reader = csv.reader(io.StringIO(content, newline=""), strict=True)
    points = []
    try:
        if next(reader, None) != COLUMNS:
            fail("expected the columns time_min,signal_au in that order.", 1)
        while True:
            line = reader.line_num + 1
            row = next(reader, None)
            if row is None:
                break
            if reader.line_num != line:
                fail("multiline fields are not supported.", line)
            if len(row) != 2:
                fail("expected exactly two values; blank rows are not allowed.", line)
            if len(points) >= 2000:
                fail("maximum 2,000 data points exceeded.", line, code="too_many_points")
            values = []
            for column, cell in zip(COLUMNS, row):
                token = cell.strip(" \t")
                if len(cell) > 128 or not NUMBER.fullmatch(token):
                    fail("enter a decimal number (use a period, with no missing values).", line, column)
                try:
                    value = float(token)
                    nonzero_underflow = value == 0 and Decimal(token) != 0
                except (ValueError, OverflowError, InvalidOperation):
                    fail("value exceeds the supported numerical range.", line, column)
                if not math.isfinite(value) or nonzero_underflow:
                    fail("value exceeds the supported numerical range.", line, column)
                values.append(value)
            if values[1] < 0:
                fail("signal must be nonnegative and already prepared.", line, "signal_au")
            if points and values[0] <= points[-1][0]:
                fail(f"must be greater than the previous time ({points[-1][0]:g}).", line, "time_min")
            points.append(values)
    except csv.Error as exc:
        fail("malformed CSV or a field longer than 128 characters.", max(reader.line_num, 1))
    if len(points) < 2:
        fail("at least two data points are required.", max(reader.line_num + 1, 2))
    result = analyze_trace(points, points[0][0], points[-1][0])
    return points, result
