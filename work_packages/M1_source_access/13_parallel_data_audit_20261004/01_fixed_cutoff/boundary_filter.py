"""Proposed publication-date boundary helper. Does not alter any source data.

Use only a source publication date or timestamp. Never pass collection, CMS,
modification, retrieval, or report time as a substitute. For timestamps the
proposed day convention is UTC; existing GOV.UK local-day rows require review.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timezone


START = date(1988, 1, 1)
END = date(2026, 9, 21)


@dataclass(frozen=True)
class BoundaryResult:
    status: str  # included, outside, uncertain, missing, invalid
    earliest: date | None
    latest: date | None
    reason: str


def classify_publication(value: str | None, precision: str) -> BoundaryResult:
    """Classify an evidenced publication date without inventing missing parts.

    precision: day, month, year, timestamp, or unknown. Month/year values are
    intervals. A partial-precision value crossing a boundary stays uncertain.
    A timestamp must carry a timezone offset and is converted to a UTC day.
    """
    if not value or precision == "unknown":
        return BoundaryResult("missing", None, None, "publication date unresolved")
    try:
        if precision == "day":
            first = last = date.fromisoformat(value)
        elif precision == "month":
            if len(value) != 7:
                raise ValueError("month must be YYYY-MM")
            year, month = map(int, value.split("-"))
            first = date(year, month, 1)
            last = date(year, month, calendar.monthrange(year, month)[1])
        elif precision == "year":
            if len(value) != 4:
                raise ValueError("year must be YYYY")
            year = int(value)
            first, last = date(year, 1, 1), date(year, 12, 31)
        elif precision == "timestamp":
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError("timestamp has no timezone")
            first = last = parsed.astimezone(timezone.utc).date()
        else:
            raise ValueError("unsupported precision")
    except (ValueError, TypeError) as exc:
        return BoundaryResult("invalid", None, None, str(exc))
    if START <= first and last <= END:
        return BoundaryResult("included", first, last, "entire publication-date interval inside scope")
    if last < START or first > END:
        return BoundaryResult("outside", first, last, "entire publication-date interval outside scope")
    return BoundaryResult("uncertain", first, last, "date precision overlaps a scope boundary")


if __name__ == "__main__":
    checks = [
        ("1988-01-01", "day", "included"),
        ("2026-09-21", "day", "included"),
        ("2026-09-22", "day", "outside"),
        ("1987-12-31", "day", "outside"),
        (None, "unknown", "missing"),
        ("2026-09", "month", "uncertain"),
        ("2026", "year", "uncertain"),
        ("2026-08", "month", "included"),
        ("2026-09-22T00:30:00+01:00", "timestamp", "included"),
        ("2026-09-21T23:30:00-01:00", "timestamp", "outside"),
        ("2026-09-21T23:30:00", "timestamp", "invalid"),
    ]
    for value, precision, expected in checks:
        actual = classify_publication(value, precision).status
        assert actual == expected, (value, precision, expected, actual)
    print(f"{len(checks)} boundary examples passed")
