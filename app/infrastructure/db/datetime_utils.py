"""Normalización de fechas leídas desde la base de datos.

SQLite (usado en desarrollo local) descarta la zona horaria al persistir,
por lo que los valores vuelven como naive. Postgres con `timestamptz` los
devuelve con zona. Se asume UTC cuando falta para que la API sea consistente.
"""

from datetime import UTC, datetime


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
