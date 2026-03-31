from __future__ import annotations

from sqlalchemy import delete, distinct, insert, or_, select, tuple_, update
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func


class ModelQueryBuilder:
    def __init__(self, modeladmin):
        self.modeladmin = modeladmin

    @property
    def model(self):
        return self.modeladmin.model

    def get_primary_key_as_model_column(self):
        primary_key_fields = self.modeladmin.get_model_primary_keys()
        return [getattr(self.model, field) for field in primary_key_fields]

    def get_distinct_values_stmt(self, field_name: str):
        return select(distinct(getattr(self.model, field_name))).order_by(
            getattr(self.model, field_name)
        )

    def _get_filtered_list_stmt(
        self,
        *,
        request=None,
        search: str | None = None,
        filters: dict[str, str] | None = None,
        sort: str | None = None,
        direction: str = "asc",
    ):
        query = select(self.model)
        selectinload_columns = self.get_selectinload_columns()
        if selectinload_columns:
            query = query.options(
                *[selectinload(column) for column in selectinload_columns]
            )

        query = self.modeladmin.get_list_query(query, request=request)

        if search:
            predicates = []
            for field in self.modeladmin.get_search_fields():
                predicates.append(getattr(self.model, field).ilike(f"%{search}%"))
            if predicates:
                query = query.where(or_(*predicates))

        for field_name, raw_value in (filters or {}).items():
            if raw_value in ("", None):
                continue
            column = getattr(self.model, field_name)
            python_type = self.modeladmin.get_column_python_type(field_name)
            normalized_value: object = raw_value
            if python_type is bool:
                normalized_value = str(raw_value).lower() == "true"
            elif python_type is int:
                normalized_value = int(raw_value)
            elif python_type is float:
                normalized_value = float(raw_value)
            query = query.where(column == normalized_value)

        sortable_fields = set(self.modeladmin.get_sortable_fields())
        if sort and sort in sortable_fields:
            sort_column = getattr(self.model, sort)
            query = query.order_by(
                sort_column.desc() if direction == "desc" else sort_column.asc()
            )
        elif self.modeladmin.list_order_by:
            query = query.order_by(
                *[getattr(self.model, field) for field in self.modeladmin.list_order_by]
            )
        else:
            query = query.order_by(tuple_(*self.get_primary_key_as_model_column()))

        return query

    def get_list_query_count_stmt(self, **kwargs):
        statement = self._get_filtered_list_stmt(**kwargs).order_by(None)
        return select(func.count()).select_from(statement.subquery())

    def get_list_query_stmt(self, **kwargs):
        return self._get_filtered_list_stmt(**kwargs).limit(self.modeladmin.page_size)

    def get_update_record_stmt(self, key: list[str]):
        return update(self.model.__table__).where(
            tuple_(*self.get_primary_key_as_model_column()) == key
        )

    def get_delete_record_stmt(self, key: list[str]):
        return delete(self.model.__table__).where(
            tuple_(*self.get_primary_key_as_model_column()) == key
        )

    def get_insert_record_stmt(self):
        return insert(self.model.__table__).returning(
            self.get_primary_key_as_model_column()[0]
        )

    def get_selectinload_columns(self):
        return [
            getattr(self.model, field)
            for field, item in self.modeladmin.table_rel_columns.items()
            if item.secondary is None
        ]

    def get_single_record_query_stmt(self, key: list[str]):
        statement = select(self.model)
        selectinload_columns = self.get_selectinload_columns()
        if selectinload_columns:
            statement = statement.options(
                *[selectinload(column) for column in selectinload_columns]
            )
        return statement.where(tuple_(*self.get_primary_key_as_model_column()) == key)

    def get_multi_record_query_stmt(self, keys: list[str]):
        statement = select(self.model)
        selectinload_columns = self.get_selectinload_columns()
        if selectinload_columns:
            statement = statement.options(
                *[selectinload(column) for column in selectinload_columns]
            )
        return statement.where(self.get_primary_key_as_model_column()[0].in_(keys))
