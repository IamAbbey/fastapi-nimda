from operator import attrgetter
from typing import Any, List, Iterable
from sqlalchemy.exc import SQLAlchemyError
import re


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


def normalize_sqlachemy_error(table_name: str, exc: SQLAlchemyError) -> List[str]:
    message = exc._message()

    split = message.split(f"{table_name.lower()}")
    if len(split) >= 2:
        return [s[2:] for s in split[1:]]
    return []


def get_any_model_primary_keys(model) -> Iterable[str]:
    """This method is used to get model primary keys.

    :return: A str.
    """
    return [
        column.key for column in model.__table__.primary_key if not column.foreign_keys
    ]
