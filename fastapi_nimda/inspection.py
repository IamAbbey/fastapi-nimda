from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.inspection import inspect
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm.interfaces import RelationshipDirection
from sqlalchemy.orm.relationships import RelationshipProperty
from sqlalchemy.sql.schema import Column

from .errors import UnsupportedPrimaryKeyError


@dataclass
class ModelInspection:
    table_columns: dict[str, Column]
    table_fk_columns: dict[str, Column]
    table_rel_columns: dict[str, RelationshipProperty]
    primary_key_columns: list[Column]
    supported_form_fields: list[str]
    unsupported_relation_fields: dict[str, str]
    readonly_relation_fields: dict[str, str]

    @property
    def all_columns(self):
        return {
            **self.table_columns,
            **self.table_fk_columns,
            **self.table_rel_columns,
        }


def inspect_model(model: type[DeclarativeBase]) -> ModelInspection:
    mapper = inspect(model)
    table_columns: dict[str, Column] = {}
    table_fk_columns: dict[str, Column] = {}
    table_rel_columns: dict[str, RelationshipProperty] = {}
    unsupported_relation_fields: dict[str, str] = {}
    readonly_relation_fields: dict[str, str] = {}
    primary_key_columns = list(model.__table__.primary_key.columns)
    supported_form_fields: list[str] = []
    relationship_backed_fk_fields: set[str] = set()

    if len(primary_key_columns) != 1:
        raise UnsupportedPrimaryKeyError(
            f"{model.__name__} uses {len(primary_key_columns)} primary-key columns. "
            "fastapi-nimda currently supports only a single-column primary key."
        )

    def check_matching_relationship_exist(*, target_column: Column):
        for rel_column in mapper.relationships:
            if rel_column.mapper.tables[0].name == target_column.column.table.name:
                return True
        return False

    for column in mapper.columns:
        if column.foreign_keys and len(column.foreign_keys) > 1:
            raise ValueError(
                f"{model.__name__} contains unsupported foreignkey column :{column.key}: "
                f"{column.key} can reference only one foreign key"
            )
        if column.foreign_keys and not column.primary_key:
            if not check_matching_relationship_exist(
                target_column=list(column.foreign_keys)[0]
            ):
                raise ValueError(
                    f"{model.__name__} contains unsupported foreignkey column :{column.key}: "
                    f"{model.__name__} needs to define relationship for :{column.key}:"
                )

    for column in mapper.columns:
        if column.foreign_keys:
            table_fk_columns[column.key] = column
        else:
            table_columns[column.key] = column
        supported_form_fields.append(column.key)

    for column in mapper.relationships:
        table_rel_columns[column.key] = column
        if column.secondary is not None:
            unsupported_relation_fields[column.key] = (
                "many-to-many relationships are not supported in admin forms yet"
            )
            continue
        if column.uselist:
            unsupported_relation_fields[column.key] = (
                "one-to-many collections are not supported as admin form fields"
            )
            continue
        if column.direction == RelationshipDirection.ONETOMANY:
            readonly_relation_fields[column.key] = (
                "reverse one-to-one relationships are read-only and cannot be used as admin form fields"
            )
            continue
        relationship_backed_fk_fields.update(
            local_column.key for local_column in column.local_columns
        )
        supported_form_fields.append(column.key)

    supported_form_fields = [
        field_name
        for field_name in supported_form_fields
        if field_name not in relationship_backed_fk_fields
        or field_name in table_columns
        or field_name in primary_key_columns
    ]

    return ModelInspection(
        table_columns=table_columns,
        table_fk_columns=table_fk_columns,
        table_rel_columns=table_rel_columns,
        primary_key_columns=primary_key_columns,
        supported_form_fields=supported_form_fields,
        unsupported_relation_fields=unsupported_relation_fields,
        readonly_relation_fields=readonly_relation_fields,
    )


def get_model_primary_keys(model) -> list[str]:
    return [column.key for column in model.__table__.primary_key]
