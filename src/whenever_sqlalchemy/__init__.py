"""SQLAlchemy column types for ``whenever``."""

from __future__ import annotations

import datetime as _stdlib

import sqlalchemy as _sa
from sqlalchemy.types import TypeDecorator
from whenever import Date, Instant, PlainDateTime, Time

_UTC = _stdlib.timezone.utc


class InstantType(TypeDecorator):  # type: ignore[type-arg]
    """SQLAlchemy column type for :class:`~whenever.Instant`.

    Stored as ``TIMESTAMP WITH TIME ZONE`` (``TIMESTAMPTZ`` on PostgreSQL).
    Nanoseconds are truncated to microseconds on storage.

    On databases that do not preserve timezone information (e.g. SQLite),
    the stored UTC value is returned correctly.
    """

    impl = _sa.DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: Instant | None, dialect: object
    ) -> _stdlib.datetime | None:
        if value is None:
            return None
        return value.to_stdlib()

    def process_result_value(
        self, value: _stdlib.datetime | None, dialect: object
    ) -> Instant | None:
        if value is None:
            return None
        # SQLite (and other backends without native tz support) returns naive
        # datetimes for TIMESTAMP WITH TIME ZONE columns. We stored UTC, so
        # we can safely attach UTC tzinfo on retrieval.
        if value.tzinfo is None:
            value = value.replace(tzinfo=_UTC)
        return Instant(value)


class PlainDateTimeType(TypeDecorator):  # type: ignore[type-arg]
    """SQLAlchemy column type for :class:`~whenever.PlainDateTime`.

    Stored as ``TIMESTAMP`` (without timezone).
    Nanoseconds are truncated to microseconds on storage.
    """

    impl = _sa.DateTime(timezone=False)
    cache_ok = True

    def process_bind_param(
        self, value: PlainDateTime | None, dialect: object
    ) -> _stdlib.datetime | None:
        if value is None:
            return None
        return value.to_stdlib()

    def process_result_value(
        self, value: _stdlib.datetime | None, dialect: object
    ) -> PlainDateTime | None:
        if value is None:
            return None
        return PlainDateTime(value)


class DateType(TypeDecorator):  # type: ignore[type-arg]
    """SQLAlchemy column type for :class:`~whenever.Date`.

    Stored as ``DATE``.
    """

    impl = _sa.Date()
    cache_ok = True

    def process_bind_param(
        self, value: Date | None, dialect: object
    ) -> _stdlib.date | None:
        if value is None:
            return None
        return value.to_stdlib()

    def process_result_value(
        self, value: _stdlib.date | None, dialect: object
    ) -> Date | None:
        if value is None:
            return None
        return Date(value)


class TimeType(TypeDecorator):  # type: ignore[type-arg]
    """SQLAlchemy column type for :class:`~whenever.Time`.

    Stored as ``TIME``.
    Nanoseconds are truncated to microseconds on storage.
    """

    impl = _sa.Time()
    cache_ok = True

    def process_bind_param(
        self, value: Time | None, dialect: object
    ) -> _stdlib.time | None:
        if value is None:
            return None
        return value.to_stdlib()

    def process_result_value(
        self, value: _stdlib.time | None, dialect: object
    ) -> Time | None:
        if value is None:
            return None
        return Time(value)


type_annotation_map = {
    Instant: InstantType(),
    PlainDateTime: PlainDateTimeType(),
    Date: DateType(),
    Time: TimeType(),
}
