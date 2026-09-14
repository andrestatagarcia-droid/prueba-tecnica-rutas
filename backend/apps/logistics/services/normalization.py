import json
import math
import re
import unicodedata
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo


BOGOTA_TZ = ZoneInfo("America/Bogota")


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if value.__class__.__name__ in {"NAType", "NaTType"}:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def normalize_spaces(value: Any) -> str | None:
    if is_missing(value):
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def normalize_comparison_text(value: Any) -> str:
    text = normalize_spaces(value) or ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(character for character in text if unicodedata.category(character) != "Mn")
    return text.casefold()


def normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_comparison_text(value))


def get_alias(mapping: Mapping[str, Any], candidates: Sequence[str]) -> tuple[bool, Any, str | None]:
    actual_keys = {normalize_key(key): key for key in mapping}
    for candidate in candidates:
        actual_key = actual_keys.get(normalize_key(candidate))
        if actual_key is not None:
            return True, mapping[actual_key], actual_key
    return False, None, None


def to_integer(value: Any) -> int | None:
    if is_missing(value) or isinstance(value, bool):
        return None
    try:
        decimal_value = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None
    if not decimal_value.is_finite() or decimal_value != decimal_value.to_integral_value():
        return None
    return int(decimal_value)


def to_decimal(value: Any) -> Decimal | None:
    if is_missing(value) or isinstance(value, bool):
        return None
    try:
        decimal_value = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None
    return decimal_value if decimal_value.is_finite() else None


def to_datetime(value: Any) -> datetime | None:
    if is_missing(value):
        return None

    parsed: datetime
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif hasattr(value, "to_pydatetime"):
        parsed = value.to_pydatetime()
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        parsed = datetime(1899, 12, 30) + timedelta(days=float(value))
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=BOGOTA_TZ)
    return parsed.astimezone(BOGOTA_TZ)


def parse_json_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if is_missing(value):
        return None
    try:
        parsed = json.loads(str(value))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def json_safe(value: Any) -> Any:
    if is_missing(value):
        return None
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except (TypeError, ValueError):
            pass
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)

