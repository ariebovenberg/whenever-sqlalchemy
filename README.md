# whenever-sqlalchemy

SQLAlchemy column types for the [whenever](https://github.com/ariebovenberg/whenever) datetime library.

## Installation

```bash
pip install whenever-sqlalchemy
```

## Type mapping

| whenever type    | SQL type                    |
|------------------|-----------------------------|
| `Instant`        | `TIMESTAMP WITH TIME ZONE`  |
| `PlainDateTime`  | `TIMESTAMP` (no timezone)   |
| `Date`           | `DATE`                      |
| `Time`           | `TIME`                      |

## Usage

### SQLAlchemy 2.x — `Mapped[]` style (recommended)

Register `type_annotation_map` on your `DeclarativeBase` once, then use
`Mapped[Instant]` exactly like you would use `Mapped[datetime]`:

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from whenever import Date, Instant, PlainDateTime, Time
from whenever_sqlalchemy import type_annotation_map

class Base(DeclarativeBase):
    type_annotation_map = type_annotation_map  # merge with your own if needed

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[Instant]
    scheduled: Mapped[PlainDateTime | None]
    date: Mapped[Date | None]
    time: Mapped[Time | None]
```

### SQLAlchemy 1.4 / 2.x — `Column()` style

```python
from sqlalchemy import Column, Integer
from whenever_sqlalchemy import DateType, InstantType, PlainDateTimeType, TimeType

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    timestamp = Column(InstantType)
    scheduled = Column(PlainDateTimeType, nullable=True)
    date = Column(DateType, nullable=True)
    time = Column(TimeType, nullable=True)
```

## Notes

**Nanoseconds** — `whenever` types support nanosecond precision; SQL
`TIMESTAMP` columns store at most microsecond precision. Values are
truncated (not rounded) to microseconds on write, matching `to_stdlib()`.

**`server_default`** — `server_default=func.now()` works as expected: the
server sets the value and SQLAlchemy fetches it back, converting it to the
appropriate `whenever` type.

**Dialect notes**

- **PostgreSQL**: uses `TIMESTAMPTZ` natively; full roundtrip fidelity.
- **SQLite**: stores datetimes as text and drops timezone info. `InstantType`
  reattaches UTC tzinfo on retrieval (the stored value is UTC).
- **MySQL / MariaDB / SQL Server**: similar to SQLite for timezone columns;
  the UTC-reattach workaround covers these too.

## Compatibility

- Python 3.10+
- whenever 0.10+
- SQLAlchemy 1.4+ (`Column()` style); SQLAlchemy 2.0+ (`Mapped[]` style)
