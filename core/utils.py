from datetime import datetime, date, timedelta
import json
import os
from typing import Any, List, Optional, TypeVar
import uuid
from random import choice
from string import ascii_lowercase, digits
from dateutil.relativedelta import relativedelta


def is_valid_uuid(value):
    try:
        uuid.UUID(value)

        return True
    except ValueError:
        return False


def generate_token() -> str:
    token = "".join(choice(ascii_lowercase + digits) for _ in range(25))
    return token

_TRUE = {"1", "true", "t", "yes", "y", "on"}
_FALSE = {"0", "false", "f", "no", "n", "off"}

def str_to_bool(s: str | None, default: bool = False) -> bool:
    if s is None:
        return default
    v = str(s).strip().lower()
    if v in _TRUE:
        return True
    if v in _FALSE:
        return False
    return default

def getenv_bool(key: str, default: bool = False) -> bool:
    return str_to_bool(os.getenv(key), default)

def getenv_int(key: str, default: int) -> int:
    v = os.getenv(key)
    try:
        return int(v) if v is not None else default
    except Exception:
        return default

def getenv_float(key: str, default: float) -> float:
    v = os.getenv(key)
    try:
        return float(v) if v is not None else default
    except Exception:
        return default


def get_first_day_of_month(date: datetime) -> datetime:
    month_first_day = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return month_first_day


def get_last_day_of_month(date: datetime) -> datetime:
    month_last_day = date.replace(
        hour=23, minute=59, second=59, microsecond=9999
    ) + relativedelta(day=31)
    return month_last_day


def is_list_all_same(x: List[int]) -> bool:
    a = x[0]
    result = True
    for item in x[1:]:
        if item != a:
            result = False
            break
    return result


T = TypeVar("T", str, int)


def diffrence_between_two_list(list_1: List[T], list_2: List[T]) -> List[T]:
    return list(set(list_1) ^ set(list_2))


def int_to_month_id_str(x: int) -> Optional[str]:
    data = {
        1: "Januari",
        2: "Febuari",
        3: "Maret",
        4: "April",
        5: "Mei",
        6: "Juni",
        7: "Juli",
        8: "Agustus",
        9: "September",
        10: "Oktober",
        11: "November",
        12: "Desember",
    }
    return data.get(x, None)


def day_english_to_indonesia(x: str) -> str:
    data = {
        "Monday": "Senin",
        "Tuesday": "Selasa",
        "Wednesday": "Rabu",
        "Thursday": "Kamis",
        "Friday": "Jumat",
        "Saturday": "Sabtu",
        "Sunday": "Minggu",
    }
    return data.get(x, x)


def get_next_friday(x: date) -> date:
    curr = datetime(year=x.year, month=x.month, day=x.day)
    while curr.weekday() != 4:  # Friday
        curr = curr + timedelta(days=1)

    return date(year=curr.year, month=curr.month, day=curr.day)


def str_split_int(x: str, delim: str = ",") -> List[int]:
    x = x.split(delim)
    x = [int(y.strip()) for y in x]
    return x


def list_left_not_in_list_right(left: List[int], right: List[int]) -> List[int]:
    """
    example
    left = [1, 2]
    right = [2, 4]
    return [1]

    left = [1, 2]
    right = [1, 2, 3]
    return []
    """
    return [a for a in left if a not in right]

# def get_token_remember(token: str) -> str:
#     digits = ''.join(str for str in token if str.isdigit())
#     return digits[:30]

def _to_str(v: Any) -> str:
    # Biar rapi kalau yang dikirim dict/list → JSON
    try:
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False)
        return str(v)
    except Exception:
        return str(v)

def safe_format(template: str, /, **data: Any) -> str:
    """
    Ganti placeholder spesifik {key} tanpa pakai str.format/format_map,
    jadi semua kurung kurawal lain tidak tersentuh.
    """
    out = template
    # urutkan key terpanjang dulu supaya kasus nama saling subset tidak bentrok
    for key in sorted(data.keys(), key=len, reverse=True):
        out = out.replace("{"+key+"}", _to_str(data[key]))
    return out
