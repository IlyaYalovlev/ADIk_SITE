from datetime import datetime
from decimal import Decimal


def decimal_to_float(data):
    """
    Преобразует значения Decimal в float для сериализации.
    """
    if isinstance(data, dict):
        return {k: decimal_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [decimal_to_float(v) for v in data]
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data