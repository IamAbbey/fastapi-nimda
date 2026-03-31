from __future__ import annotations

import typing
from sqlalchemy.orm import DeclarativeBase, selectinload
from sqlalchemy.inspection import inspect
from sqlalchemy.sql.schema import Column
from sqlalchemy.orm.interfaces import RelationshipDirection
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, Float
from sqlalchemy import select, update, delete, insert
from sqlalchemy.sql import func

from fastapi_nimda.widgets import (
    SelectMultiple,
    TextInput,
    Widget,
    NumberInput,
    CheckboxInput,
    Select,
)
from .templating.templating import templates
from .operation import OperationKind
from sqlalchemy.orm.relationships import RelationshipProperty
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy import tuple_
from dataclasses import dataclass

if typing.TYPE_CHECKING:
    from typing import Type, List, Literal, Union, Dict, Iterable, Any, Optional


@dataclass
class ColumnWidget:
    column: Column
    widget: Widget


class ModelAdmin:
    list_display: List[str] = []
    """
    Set list_display to control which fields are displayed on the change list page of the admin.
    If you do not set list_display, the admin site will display a single column that displays the __str__() representation of each object.
    """

    readonly_fields: List[str] = []
    raw_id_fields: List[str] = []
    fields: Union[List[str], Literal["__all__"]] = "__all__"
    exclude: List[str] = []
    widgets: Dict[str, Widget] = {}
    page_size: int = 20
    list_order_by: List[str] = []

    def __init__(self, *, model: Type[DeclarativeBase], engine: Engine) -> None:
        self.engine = engine
        self._model: Type[DeclarativeBase] = model
        self._table_columns: Dict[str, Column] = {}
        self._table_fk_columns: Dict[str, Column] = {}
        self._table_rel_columns: Dict[str, RelationshipProperty] = {}
        self.inspect_model()
        self._validate_attributes()

    def get_page_size(self):
        return self.page_size

    def get_list_display(self):
        return self.list_display

    def get_list_query_count_stmt(self):
        return select(func.count()).select_from(self.model)

    def perform_edit(self, request, obj, form):
        pass

    def get_list_query_stmt(self):
        query = select(self.model)
        if self.get_list_display():
            query = select(
                *[getattr(self.model, field) for field in self.get_list_display()]
            )
        if self.list_order_by:
            return query.order_by(
                *[getattr(self.model, field) for field in self.list_order_by]
            )

        return query.order_by(tuple_(*self.get_primary_key_as_model_column())).limit(
            self.page_size
        )

    def get_primary_key_as_model_column(self):
        primary_key_fields = self.get_model_primary_keys()
        primary_key_as_model_column = [
            getattr(self.model, field) for field in primary_key_fields
        ]
        return primary_key_as_model_column

    def get_update_record_stmt(self, key: List[str]):
        return update(self.model.__table__).where(
            tuple_(*self.get_primary_key_as_model_column()) == key
        )

    def get_delete_record_stmt(self, key: List[str]):
        return delete(self.model.__table__).where(
            tuple_(*self.get_primary_key_as_model_column()) == key
        )

    def get_insert_record_stmt(self):
        return insert(self.model.__table__).returning(
            self.get_primary_key_as_model_column()[0]
        )
        # we using lastrowid as SQLite only added support for RETURNING in version 3.35.0 (March 2021).
        # return insert(self.model.__table__)

    def get_single_record_query_stmt(self, key: List[str]):
        # if len(key) != len(primary_key_fields):
        #     raise ValueError('Querying keys length differs')

        # https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#relationship-loading-techniques
        # print(self._table_rel_columns.items())
        # print([
        #                 getattr(self.model, field)
        #                 for field, item in self._table_rel_columns.items()
        #                 if item.secondary is not None # we do not support many-to-many
        #             ])
        return (
            select(self.model)
            .options(
                selectinload(
                    *[
                        getattr(self.model, field)
                        for field, item in self._table_rel_columns.items()
                        if item.secondary is None  # we do not support many-to-many
                    ]
                )
            )
            .where(tuple_(*self.get_primary_key_as_model_column()) == key)
        )

    def get_multi_record_query_stmt(self, keys: List[str]):
        # if len(key) != len(primary_key_fields):
        #     raise ValueError('Querying keys length differs')

        # https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#relationship-loading-techniques
        # print(self._table_rel_columns.items())
        # print([
        #                 getattr(self.model, field)
        #                 for field, item in self._table_rel_columns.items()
        #                 if item.secondary is not None # we do not support many-to-many
        #             ])
        return (
            select(self.model)
            .options(
                selectinload(
                    *[
                        getattr(self.model, field)
                        for field, item in self._table_rel_columns.items()
                        if item.secondary is None  # we do not support many-to-many
                    ]
                )
            )
            .where(self.get_primary_key_as_model_column()[0].in_(keys))
        )

    @property
    def model(self):
        return self._model

    @property
    def table_columns(self):
        return self._table_columns

    @property
    def table_name(self):
        return self.model.__name__

    @property
    def all_columns(self):
        return {**self._table_columns, **self._table_rel_columns}
        # return {**self._table_columns, **self._table_fk_columns}

    def inspect_model(self):
        mapper = inspect(self.model)
        # print(mapper.column_attrs.keys())
        # print(list(mapper.columns))

        def check_matching_relationship_exist(*, target_column: Column):
            for rel_column in mapper.relationships:
                if rel_column.mapper.tables[0].name == target_column.column.table.name:
                    return True

        # supports only a single column that can reference only one foreign key
        for column in mapper.columns:
            if column.foreign_keys and len(column.foreign_keys) > 1:
                raise ValueError(
                    f"{self.model.__name__} contains unsupported foreignkey column :{column.key}: "
                    f"{column.key} can reference only one foreign key"
                )
            if column.foreign_keys and not column.primary_key:
                # WE SHOULD ABLE TO HAVE foreign_key without relation object defined
                # the relationship object only refers to the python layer and has not to do with the DB
                if not check_matching_relationship_exist(
                    target_column=list(column.foreign_keys)[0]
                ):
                    raise ValueError(
                        f"{self.model.__name__} contains unsupported foreignkey column :{column.key}: "
                        f"{self.model.__name__} needs to define relationship for :{column.key}:"
                    )

            if not column.foreign_keys:
                self._table_columns[column.key] = column

        # columns = [column for column in mapper.columns if not column.foreign_keys]
        # print(mapper.local_table.foreign_keys)
        for column in mapper.columns:
            if column.foreign_keys:
                self._table_fk_columns[column.key] = column
            else:
                self._table_columns[column.key] = column

        for _column in mapper.relationships:
            self._table_rel_columns[_column.key] = _column

    def validate_fields_exist(self, fields: List[str], against: List[str]):
        for field in fields:
            if field not in against:
                raise ValueError(
                    f"{field} is not a column field in associated model ({self.model.__name__})"
                )

    def validate_list_display_like_attributes(self):
        mapper = inspect(self.model)
        for attr in ("list_display", "list_order_by"):
            if not isinstance(getattr(self, attr), (list, tuple)):
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :{attr}: must be sequence e.g list, tuple"
                )
            try:
                self.validate_fields_exist(
                    getattr(self, attr), mapper.column_attrs.keys()
                )
            except ValueError as e:
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :{attr}: {e.args[0]}"
                )

    def validate_field_like_attributes(self):
        all_columns = self.all_columns.keys()
        if self.fields == "__all__":
            self.fields = list(all_columns)

        for attr in ("fields", "readonly_fields", "exclude", "list_order_by"):
            if not isinstance(getattr(self, attr), (list, tuple)):
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :{attr}: must be sequence e.g list, tuple"
                )
            try:
                self.validate_fields_exist(getattr(self, attr), all_columns)
            except ValueError as e:
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :{attr}: {e.args[0]}"
                )

    def _validate_attributes(self):
        self.validate_field_like_attributes()
        self.validate_list_display_like_attributes()
        # if not isinstance(self.exclude, (list, tuple)):
        #     raise ValueError("exclude is not a sequence e.g list, tuple")

    def get_model_admin_fields(self):
        return self.fields

    def can_perform_add(self):
        return len(self.get_model_admin_fields()) > 0

    def get_absolute_url(self):
        return f"/{self._identity}/list/"

    def get_form(
        self,
        *,
        operation: Optional[OperationKind] = OperationKind.VIEW,
        record=None,
    ):
        return AdminForm(
            modeladmin=self,
            widgets=self.get_widgets(),
            engine=self.engine,
            record=record,
            operation=operation,
        )

    def render_form(
        self, operation: Optional[OperationKind] = OperationKind.VIEW, **kwargs
    ):
        record = kwargs.get("record")
        return self.get_form(record=record, operation=operation).render_form(**kwargs)

    def get_widgets(self):
        for name, widget in self.widgets.items():
            if name not in self.fields:
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :widgets: {name} not in fields"
                )

            if not isinstance(widget, Widget):
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :widgets: {name}'s widget is not valid"
                )

        return self.widgets

    def get_model_primary_keys(self) -> Iterable[str]:
        """This method is used to get model primary keys.

        :return: A str.
        """
        return [
            column.key
            for column in self.model.__table__.primary_key
            if not column.foreign_keys
        ]

    def get_auto_increment_column(self) -> Union[Column, None]:
        return self.model.__table__.autoincrement_column

    def get_fields_as_columns(self) -> List[Column]:
        assert isinstance(self.get_model_admin_fields(), (list, tuple))
        columns: List[Column] = []
        # print(self.get_model_admin_fields())
        # exclude = set(self.exclude + kwargs.get('exclude', []))
        for field in self.get_model_admin_fields():
            if field not in self.exclude:
                column = self.all_columns[field]
                if (
                    self.get_auto_increment_column() is not None
                    and self.get_auto_increment_column().key == column.key
                ):
                    continue
                columns.append(column)
        return columns


class AdminForm:
    def __init__(
        self,
        modeladmin: ModelAdmin,
        widgets: Dict[str, Widget],
        engine: Engine,
        record: Any,
        operation: OperationKind,
    ):
        if not isinstance(modeladmin, ModelAdmin):
            raise ValueError(f"{modeladmin} not an instance of {ModelAdmin.__name__}")
        self.modeladmin: ModelAdmin = modeladmin
        self.widgets = widgets
        self.engine = engine
        self.record = record
        self.operation = operation

    def field_is_readonly(self, column_name: str, is_pk: bool):
        return (
            self.operation == OperationKind.VIEW
            or column_name in self.modeladmin.readonly_fields
            or (
                self.operation != OperationKind.ADD
                and is_pk
                and self.record is not None
            )  # if record is None then we are in the add view not  edit
        )

    @staticmethod
    def _get_record_value(record, name):
        try:
            return getattr(record, name)
        except AttributeError:
            if isinstance(record, dict):
                return record.get(name)

    def get_columns_widget(self, columns: List[Column]) -> Dict[str, ColumnWidget]:
        widget_map: Dict[str, ColumnWidget] = {}
        primary_keys = self.modeladmin.get_model_primary_keys()
        for column in columns:
            column_name = column.key
            is_pk = column_name in primary_keys

            if isinstance(column, Column):
                attrs = {
                    **(
                        {"value": self._get_record_value(self.record, column_name)}
                        if self.record
                        else {}
                    ),
                    "readonly": self.field_is_readonly(
                        column_name=column_name, is_pk=is_pk
                    ),
                    "required": not column.nullable or column.default is not None,
                }
                if isinstance(column.type, String):
                    widget = TextInput(attrs)
                elif isinstance(column.type, (Integer, Float)):
                    widget = NumberInput(attrs)
                elif isinstance(column.type, Boolean):
                    widget = CheckboxInput(attrs)
                else:
                    widget = TextInput(attrs)
            elif isinstance(column, RelationshipProperty):
                from .helpers import get_any_model_primary_keys, getattrs

                field_type = column.direction
                column_name = column.key
                if column.secondary is not None:
                    continue
                c_model_pk = get_any_model_primary_keys(column.mapper.class_)[0]

                attrs = {
                    **{
                        **(
                            {
                                "value": str(
                                    getattrs(
                                        self._get_record_value(
                                            self.record, column_name
                                        ),
                                        c_model_pk,
                                        None,
                                    )
                                )
                            }
                            if self.record
                            else {}
                        ),
                        "readonly": self.operation == OperationKind.VIEW,
                    },
                    **{},
                }
                if (
                    field_type == RelationshipDirection.MANYTOONE
                    or field_type == RelationshipDirection.MANYTOMANY
                ):
                    if (
                        self.operation == OperationKind.VIEW
                        or column_name in self.modeladmin.raw_id_fields
                    ):
                        widget = TextInput(attrs)
                    else:
                        with Session(self.engine) as session:
                            queryset = (
                                session.execute(select(column.mapper.class_))
                                .scalars()
                                .all()
                            )

                            choices = [
                                (getattrs(qs, c_model_pk, None), str(qs))
                                for qs in queryset
                            ]
                            # print(choices)
                            if field_type == RelationshipDirection.MANYTOMANY:
                                widget = SelectMultiple(
                                    choices=choices,
                                    attrs=attrs,
                                )
                            else:
                                widget = Select(
                                    choices=choices,
                                    attrs=attrs,
                                )
                elif field_type == RelationshipDirection.ONETOMANY:  # reverse lookups
                    widget = None

            if widget:
                widget_map[column.key] = ColumnWidget(widget=widget, column=column)

        return widget_map

    def get_render_widgets(self):
        columns = self.modeladmin.get_fields_as_columns()
        field_widgets = self.get_columns_widget(columns)

        for name, widget in self.widgets.items():
            if name not in self.fields:
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :widgets: {name} not in fields"
                )

            if not isinstance(widget, Widget):
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :widgets: {name}'s widget is not valid"
                )

            if name in field_widgets.keys():
                field_widgets[name].widget = widget

        return field_widgets

    def render_form(self, **kwargs):
        exclude = kwargs.get("exclude", [])
        return templates.get_template("form/div.html").render(
            {
                "fields": {
                    name: {
                        "label": column_widget.widget.render_label(
                            name=name, value=None
                        ),
                        "field": column_widget.widget.render(
                            name=name, value=column_widget.widget.attrs.get("value")
                        ),
                        "error": name in kwargs.get("error_fields", []),
                    }
                    for name, column_widget in self.get_render_widgets().items()
                    if name not in exclude
                }
            }
        )

    def validate_form(self, **kwargs):
        exclude = kwargs.get("exclude", [])
        form_body = kwargs.get("form_body", {})
        response = {}
        for name, column_widget in self.get_render_widgets().items():
            if name not in exclude:
                _destination_col = name
                column = column_widget.column
                if isinstance(column, RelationshipProperty):
                    _destination_col = next(iter(column.local_columns)).key
                response[_destination_col] = column_widget.widget.format_value(
                    form_body.get(name)
                )
        return response
