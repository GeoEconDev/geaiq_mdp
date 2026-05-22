import re
from datetime import datetime
from dateutil.relativedelta import relativedelta


patterns = [
    (r"^(?P<year>\d{4})$", "%Y", relativedelta(years=1)),  # YYYY
    (
        r"^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})$",
        r"%Y%m%d",
        relativedelta(days=1),
    ),  # YYYYMMDD
    (
        r"^(?P<year>\d{4})(?P<month>\d{2})$",
        r"%Y%m",
        relativedelta(months=1),
    ),  # YYYYMM
    (
        r"^(?P<day>\d{2})-(?P<month>\d{2})-(?P<year>\d{4})$",
        r"%Y-%m-%d",
        relativedelta(days=1),
    ),  # DD-MM-YYYY
    (
        r"^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})$",
        r"%Y/%m/%d",
        relativedelta(days=1),
    ),  # YYYY/MM/DD
]


def parse_period(date_str):
    # Recorrer cada patrón
    for pattern, date_format, delta in patterns:
        match = re.match(pattern, date_str)
        if match:
            period_begin = datetime.strptime(date_str, date_format).date()
            return period_begin, period_begin + delta

    raise ValueError(f"Formato de fecha no reconocido: {date_str}")
