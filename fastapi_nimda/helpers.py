from __future__ import annotations

import re
from operator import attrgetter
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from .errors import DatabaseErrorSummary


def getattrs(obj: Any, attrs: str, default=None) -> Any:
    """Get attributes from an object.

    :param obj: An object.
    :param attrs: A string of attributes separated by dots.
    :param default: A default value to return if an attribute is not found.
    :return: The value of the last attribute.
    """
    try:
        return attrgetter(attrs)(obj)
    except (TypeError, AttributeError):
        return default


def normalize_sqlachemy_error_params(exc: SQLAlchemyError) -> dict:
    """
    Why ??

    SQLAlchemy sometimes gives tuples
    SQLAlchemy sits on top of the DBAPI (sqlite3, psycopg2, mysqlclient, etc.).

    Some DBAPIs only support positional binds (? placeholders in SQLite, %s in MySQL).

    In those cases, SQLAlchemy must hand the DBAPI a tuple, not a dict.

    That's why you're seeing e.params as a tuple with SQLite.

    """
    params = exc.params
    stmt = exc.statement or ""

    # Already dict (Postgres, etc.)
    if isinstance(params, dict):
        return params

    # Tuple → parse from statement
    if isinstance(params, (list, tuple)) and "INSERT INTO" in stmt:
        match = re.search(r"\((.*?)\)", stmt)
        if match:
            cols = [c.strip() for c in match.group(1).split(",")]
            return dict(zip(cols, params))

    return {}


def summarize_sqlalchemy_error(
    table_name: str, exc: SQLAlchemyError
) -> DatabaseErrorSummary:
    raw_message = str(getattr(exc, "orig", exc))
    field_names: list[str] = []
    normalized_table = table_name.lower()

    def strip_table_prefix(values: list[str]) -> list[str]:
        names: list[str] = []
        for value in values:
            if "." in value:
                maybe_table, maybe_field = value.split(".", 1)
                if maybe_table.lower() == normalized_table:
                    names.append(maybe_field)
                    continue
            names.append(value)
        return names

    unique_match = re.search(
        r"UNIQUE constraint failed: (?P<fields>.+)$", raw_message, re.IGNORECASE
    )
    if unique_match:
        field_names = strip_table_prefix(
            [field.strip() for field in unique_match.group("fields").split(",")]
        )
        return DatabaseErrorSummary(
            message=f"Unique constraint failed for: {', '.join(field_names)}",
            field_names=field_names,
        )

    not_null_match = re.search(
        r"NOT NULL constraint failed: (?P<field>.+)$", raw_message, re.IGNORECASE
    )
    if not_null_match:
        field_names = strip_table_prefix([not_null_match.group("field").strip()])
        return DatabaseErrorSummary(
            message=f"Required field missing: {field_names[0]}",
            field_names=field_names,
        )

    if re.search(r"FOREIGN KEY constraint failed", raw_message, re.IGNORECASE):
        return DatabaseErrorSummary(
            message="Foreign key constraint failed. Choose an existing related record.",
            field_names=[],
        )

    check_match = re.search(
        r"CHECK constraint failed: (?P<constraint>.+)$", raw_message, re.IGNORECASE
    )
    if check_match:
        return DatabaseErrorSummary(
            message=f"Check constraint failed: {check_match.group('constraint').strip()}",
            field_names=[],
        )

    return DatabaseErrorSummary(
        message="The database rejected the submitted values.",
        field_names=[],
    )


def normalize_sqlachemy_error(table_name: str, exc: SQLAlchemyError) -> list[str]:
    return summarize_sqlalchemy_error(table_name, exc).field_names


def get_sqlalchemy_error_message(table_name: str, exc: SQLAlchemyError) -> str:
    return summarize_sqlalchemy_error(table_name, exc).message


def get_missing_table_name(exc: SQLAlchemyError) -> str | None:
    match = re.search(r"no such table: ([^\s]+)", str(exc), re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def is_missing_table_error(exc: SQLAlchemyError) -> bool:
    return get_missing_table_name(exc) is not None


def get_any_model_primary_keys(model) -> list[str]:
    """This method is used to get model primary keys.

    :return: A str.
    """
    return [column.key for column in model.__table__.primary_key]
