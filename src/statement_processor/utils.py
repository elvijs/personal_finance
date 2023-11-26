import datetime
import logging
import unicodedata
from typing import Sequence

LOG = logging.getLogger(__file__)


def parse_float(value: str) -> float:
    return float(normalize(value.replace(",", "")).strip())


def normalize(raw_value: str) -> str:
    try:
        return unicodedata.normalize("NFKD", raw_value).strip()
    except TypeError:
        LOG.debug(f"Could not normalize '{raw_value}', skipping")
        return raw_value


def parse_date(date: str, supported_formats: Sequence[str]) -> datetime.date:
    for potential_format in supported_formats:
        try:
            return datetime.datetime.strptime(date, potential_format).date()
        except ValueError:
            continue

    raise ValueError(
        f"Date {date} does not match any of "
        f"the expected formats: {supported_formats}",
    )
