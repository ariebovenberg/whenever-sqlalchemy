import datetime as stdlib_datetime
from typing import Optional

import pytest

from whenever import Date, Instant, PlainDateTime, Time

from sqlalchemy import Column, Integer, create_engine, func
from sqlalchemy.orm import Session, declarative_base

from whenever_sqlalchemy import (
    DateType,
    InstantType,
    PlainDateTimeType,
    TimeType,
    type_annotation_map as whenever_type_annotation_map,
)

_UTC = stdlib_datetime.timezone.utc


# ── Unit tests (no database) ─────────────────────────────────────────────────


class TestInstantType:
    def test_bind_none(self):
        assert InstantType().process_bind_param(None, None) is None

    def test_result_none(self):
        assert InstantType().process_result_value(None, None) is None

    def test_bind(self):
        instant = Instant.from_utc(2024, 6, 15, 12, 30, 0)
        result = InstantType().process_bind_param(instant, None)
        assert result == stdlib_datetime.datetime(
            2024, 6, 15, 12, 30, tzinfo=_UTC
        )

    def test_result_aware(self):
        dt = stdlib_datetime.datetime(2024, 6, 15, 12, 30, tzinfo=_UTC)
        result = InstantType().process_result_value(dt, None)
        assert result == Instant.from_utc(2024, 6, 15, 12, 30)

    def test_result_naive_treated_as_utc(self):
        # SQLite (and MySQL) drop tzinfo on retrieval; the stored value was
        # UTC so we reattach UTC tzinfo.
        dt = stdlib_datetime.datetime(2024, 6, 15, 12, 30)
        result = InstantType().process_result_value(dt, None)
        assert result == Instant.from_utc(2024, 6, 15, 12, 30)

    def test_roundtrip(self):
        instant = Instant.from_utc(2024, 6, 15, 12, 30, 45)
        t = InstantType()
        assert (
            t.process_result_value(t.process_bind_param(instant, None), None)
            == instant
        )

    def test_nanoseconds_truncated_to_microseconds(self):
        # 500 ns < 1 µs, so it is truncated away
        instant = Instant.from_utc(2024, 1, 1, nanosecond=1_500)
        t = InstantType()
        result = t.process_result_value(
            t.process_bind_param(instant, None), None
        )
        assert result == Instant.from_utc(2024, 1, 1, nanosecond=1_000)


class TestPlainDateTimeType:
    def test_bind_none(self):
        assert PlainDateTimeType().process_bind_param(None, None) is None

    def test_result_none(self):
        assert PlainDateTimeType().process_result_value(None, None) is None

    def test_bind(self):
        pdt = PlainDateTime(2024, 6, 15, 12, 30, 0)
        result = PlainDateTimeType().process_bind_param(pdt, None)
        assert result == stdlib_datetime.datetime(2024, 6, 15, 12, 30, 0)
        assert result.tzinfo is None

    def test_result(self):
        dt = stdlib_datetime.datetime(2024, 6, 15, 12, 30, 0)
        result = PlainDateTimeType().process_result_value(dt, None)
        assert result == PlainDateTime(2024, 6, 15, 12, 30, 0)

    def test_roundtrip(self):
        pdt = PlainDateTime(2024, 6, 15, 12, 30, 45)
        t = PlainDateTimeType()
        assert (
            t.process_result_value(t.process_bind_param(pdt, None), None)
            == pdt
        )

    def test_nanoseconds_truncated_to_microseconds(self):
        pdt = PlainDateTime(2024, 1, 1, nanosecond=1_500)
        t = PlainDateTimeType()
        result = t.process_result_value(t.process_bind_param(pdt, None), None)
        assert result == PlainDateTime(2024, 1, 1, nanosecond=1_000)


class TestDateType:
    def test_bind_none(self):
        assert DateType().process_bind_param(None, None) is None

    def test_result_none(self):
        assert DateType().process_result_value(None, None) is None

    def test_bind(self):
        d = Date(2024, 6, 15)
        result = DateType().process_bind_param(d, None)
        assert result == stdlib_datetime.date(2024, 6, 15)

    def test_result(self):
        d = stdlib_datetime.date(2024, 6, 15)
        result = DateType().process_result_value(d, None)
        assert result == Date(2024, 6, 15)

    def test_roundtrip(self):
        d = Date(2024, 6, 15)
        t = DateType()
        assert t.process_result_value(t.process_bind_param(d, None), None) == d


class TestTimeType:
    def test_bind_none(self):
        assert TimeType().process_bind_param(None, None) is None

    def test_result_none(self):
        assert TimeType().process_result_value(None, None) is None

    def test_bind(self):
        t = Time(12, 30, 45)
        result = TimeType().process_bind_param(t, None)
        assert result == stdlib_datetime.time(12, 30, 45)

    def test_result(self):
        t = stdlib_datetime.time(12, 30, 45)
        result = TimeType().process_result_value(t, None)
        assert result == Time(12, 30, 45)

    def test_roundtrip(self):
        t = Time(12, 30, 45)
        typ = TimeType()
        assert (
            typ.process_result_value(typ.process_bind_param(t, None), None)
            == t
        )

    def test_nanoseconds_truncated_to_microseconds(self):
        t = Time(12, 30, 45, nanosecond=1_500)
        typ = TimeType()
        result = typ.process_result_value(
            typ.process_bind_param(t, None), None
        )
        assert result == Time(12, 30, 45, nanosecond=1_000)


# ── Integration tests (SQLite in-memory, full ORM roundtrip) ─────────────────
#
# Two model definitions cover the two supported SQLAlchemy usage styles:
#   - SA1.4 / SA2 Core style: explicit Column() declarations
#   - SA2 Mapped[] style: type-annotated attributes with type_annotation_map

# ── SA1.4-compatible Core style ──────────────────────────────────────────────

_CoreBase = declarative_base()


class _CoreModel(_CoreBase):
    __tablename__ = "core_model"
    id = Column(Integer, primary_key=True, autoincrement=True)
    instant = Column(InstantType, nullable=True)
    plain_dt = Column(PlainDateTimeType, nullable=True)
    date = Column(DateType, nullable=True)
    time = Column(TimeType, nullable=True)


class _ServerDefaultModel(_CoreBase):
    __tablename__ = "server_default_model"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # server_default bypasses process_bind_param;
    # process_result_value still runs
    instant = Column(InstantType, server_default=func.current_timestamp())
    plain_dt = Column(
        PlainDateTimeType, server_default=func.current_timestamp()
    )


@pytest.fixture
def core_session():
    engine = create_engine("sqlite:///:memory:")
    _CoreBase.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    _CoreBase.metadata.drop_all(engine)
    engine.dispose()


class TestSQLiteRoundtrip:
    def test_instant(self, core_session):
        value = Instant.from_utc(2024, 6, 15, 12, 30, 45)
        core_session.add(_CoreModel(instant=value))
        core_session.commit()
        core_session.expire_all()
        result = core_session.query(_CoreModel).one()
        assert result.instant == value

    def test_plain_datetime(self, core_session):
        value = PlainDateTime(2024, 6, 15, 12, 30, 45)
        core_session.add(_CoreModel(plain_dt=value))
        core_session.commit()
        core_session.expire_all()
        result = core_session.query(_CoreModel).one()
        assert result.plain_dt == value

    def test_date(self, core_session):
        value = Date(2024, 6, 15)
        core_session.add(_CoreModel(date=value))
        core_session.commit()
        core_session.expire_all()
        result = core_session.query(_CoreModel).one()
        assert result.date == value

    def test_time(self, core_session):
        value = Time(12, 30, 45)
        core_session.add(_CoreModel(time=value))
        core_session.commit()
        core_session.expire_all()
        result = core_session.query(_CoreModel).one()
        assert result.time == value

    def test_null_values(self, core_session):
        core_session.add(_CoreModel())
        core_session.commit()
        core_session.expire_all()
        result = core_session.query(_CoreModel).one()
        assert result.instant is None
        assert result.plain_dt is None
        assert result.date is None
        assert result.time is None

    def test_all_types_together(self, core_session):
        instant = Instant.from_utc(2024, 6, 15, 12, 30, 45)
        plain_dt = PlainDateTime(2023, 12, 31, 23, 59, 59)
        date = Date(2024, 1, 1)
        time = Time(8, 0, 0)
        core_session.add(
            _CoreModel(
                instant=instant, plain_dt=plain_dt, date=date, time=time
            )
        )
        core_session.commit()
        core_session.expire_all()
        result = core_session.query(_CoreModel).one()
        assert result.instant == instant
        assert result.plain_dt == plain_dt
        assert result.date == date
        assert result.time == time

    def test_server_default_instant(self, core_session):
        # The DB sets the value; process_result_value must convert it back.
        # SQLite's current_timestamp() returns a naive string; InstantType
        # reattaches UTC, so the result must be a valid Instant.
        core_session.add(_ServerDefaultModel())
        core_session.commit()
        core_session.expire_all()
        result = core_session.query(_ServerDefaultModel).one()
        assert isinstance(result.instant, Instant)

    def test_server_default_plain_datetime(self, core_session):
        core_session.add(_ServerDefaultModel())
        core_session.commit()
        core_session.expire_all()
        result = core_session.query(_ServerDefaultModel).one()
        assert isinstance(result.plain_dt, PlainDateTime)


# ── SA2 Mapped[] style ───────────────────────────────────────────────────────

try:
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

    class _MappedBase(DeclarativeBase):
        type_annotation_map = whenever_type_annotation_map

    class _MappedModel(_MappedBase):
        __tablename__ = "mapped_model"
        id: Mapped[int] = mapped_column(
            Integer, primary_key=True, autoincrement=True
        )
        instant: Mapped[Optional[Instant]]
        plain_dt: Mapped[Optional[PlainDateTime]]
        date: Mapped[Optional[Date]]
        time: Mapped[Optional[Time]]

    _SA2_AVAILABLE = True
except ImportError:
    _SA2_AVAILABLE = False


@pytest.fixture
def mapped_session():
    if not _SA2_AVAILABLE:
        pytest.skip("SQLAlchemy 2.x required for Mapped[] style")
    engine = create_engine("sqlite:///:memory:")
    _MappedBase.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    _MappedBase.metadata.drop_all(engine)
    engine.dispose()


@pytest.mark.skipif(not _SA2_AVAILABLE, reason="SQLAlchemy 2.x required")
class TestMappedAnnotations:
    """Verify Mapped[WheneverType] works identically to Mapped[datetime]."""

    def test_instant(self, mapped_session):
        value = Instant.from_utc(2024, 6, 15, 12, 30, 45)
        mapped_session.add(_MappedModel(instant=value))
        mapped_session.commit()
        mapped_session.expire_all()
        result = mapped_session.query(_MappedModel).one()
        assert result.instant == value

    def test_plain_datetime(self, mapped_session):
        value = PlainDateTime(2024, 6, 15, 12, 30, 45)
        mapped_session.add(_MappedModel(plain_dt=value))
        mapped_session.commit()
        mapped_session.expire_all()
        result = mapped_session.query(_MappedModel).one()
        assert result.plain_dt == value

    def test_date(self, mapped_session):
        value = Date(2024, 6, 15)
        mapped_session.add(_MappedModel(date=value))
        mapped_session.commit()
        mapped_session.expire_all()
        result = mapped_session.query(_MappedModel).one()
        assert result.date == value

    def test_time(self, mapped_session):
        value = Time(12, 30, 45)
        mapped_session.add(_MappedModel(time=value))
        mapped_session.commit()
        mapped_session.expire_all()
        result = mapped_session.query(_MappedModel).one()
        assert result.time == value

    def test_nullable(self, mapped_session):
        mapped_session.add(_MappedModel())
        mapped_session.commit()
        mapped_session.expire_all()
        result = mapped_session.query(_MappedModel).one()
        assert result.instant is None
        assert result.plain_dt is None
        assert result.date is None
        assert result.time is None
