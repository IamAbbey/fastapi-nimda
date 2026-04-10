from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.orm.interfaces import RelationshipDirection
from sqlalchemy.orm.relationships import RelationshipProperty
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Boolean, Float, Integer, String

from .errors import UnsupportedRelationshipError
from .helpers import get_any_model_primary_keys, getattrs
from .operation import OperationKind
from .templating.templating import templates
from .widgets import (
    CheckboxInput,
    NumberInput,
    Select,
    SelectMultiple,
    TextInput,
    Widget,
)


@dataclass
class ColumnWidget:
    column: Column
    widget: Widget


class AdminForm:
    def __init__(
        self,
        modeladmin,
        widgets: dict[str, Widget],
        engine: Engine,
        record: Any,
        operation: OperationKind,
    ):
        from .admin import ModelAdmin

        if not isinstance(modeladmin, ModelAdmin):
            raise ValueError(f"{modeladmin} not an instance of {ModelAdmin.__name__}")
        self.modeladmin = modeladmin
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
            )
        )

    @staticmethod
    def _get_record_value(record, name):
        try:
            return getattr(record, name)
        except AttributeError:
            if isinstance(record, dict):
                return record.get(name)

    def get_columns_widget(self, columns: list[Column]) -> dict[str, ColumnWidget]:
        widget_map: dict[str, ColumnWidget] = {}
        primary_keys = self.modeladmin.get_model_primary_keys()
        for column in columns:
            column_name = column.key
            is_pk = column_name in primary_keys

            widget = None
            if isinstance(column, Column):
                override_widget = self.modeladmin.get_formfield_override_widget(column)
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
                if override_widget is not None:
                    override_widget.attrs = override_widget.build_attrs(
                        override_widget.attrs,
                        attrs,
                    )
                    widget = override_widget
                elif isinstance(column.type, String):
                    widget = TextInput(attrs)
                elif isinstance(column.type, (Integer, Float)):
                    widget = NumberInput(attrs)
                elif isinstance(column.type, Boolean):
                    widget = CheckboxInput(attrs)
                else:
                    widget = TextInput(attrs)
            elif isinstance(column, RelationshipProperty):
                field_type = column.direction
                column_name = column.key
                if column.secondary is not None:
                    raise UnsupportedRelationshipError(
                        f"{self.modeladmin.__class__.__name__} Error: {column_name} is unsupported because "
                        "many-to-many relationships are not supported in admin forms yet"
                    )
                c_model_pk = get_any_model_primary_keys(column.mapper.class_)[0]

                attrs = {
                    **(
                        {
                            "value": str(
                                getattrs(
                                    self._get_record_value(self.record, column_name),
                                    c_model_pk,
                                    None,
                                )
                            )
                        }
                        if self.record
                        else {}
                    ),
                    "readonly": self.operation == OperationKind.VIEW,
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
                            (getattrs(qs, c_model_pk, None), str(qs)) for qs in queryset
                        ]
                        if field_type == RelationshipDirection.MANYTOMANY:
                            widget = SelectMultiple(choices=choices, attrs=attrs)
                        else:
                            widget = Select(choices=choices, attrs=attrs)
                elif field_type == RelationshipDirection.ONETOMANY:
                    raise UnsupportedRelationshipError(
                        f"{self.modeladmin.__class__.__name__} Error: {column_name} is unsupported because "
                        "one-to-many collections are not supported as admin form fields"
                    )

            if widget:
                widget_map[column.key] = ColumnWidget(widget=widget, column=column)

        return widget_map

    def get_render_widgets(self):
        columns = self.modeladmin.get_fields_as_columns()
        field_widgets = self.get_columns_widget(columns)

        for name, widget in self.widgets.items():
            if name not in self.modeladmin.fields:
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
                        "name": name,
                        "label_text": self.modeladmin.get_field_label(name),
                        "label": column_widget.widget.render_label(
                            name=self.modeladmin.get_field_label(name), value=None
                        ),
                        "field": column_widget.widget.render(
                            name=name, value=column_widget.widget.attrs.get("value")
                        ),
                        "help_text": self.modeladmin.get_field_help_text(name),
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
                destination_col = name
                column = column_widget.column
                if isinstance(column, RelationshipProperty):
                    destination_col = next(iter(column.local_columns)).key
                raw_value = form_body.get(name)
                value_from_data = getattr(
                    column_widget.widget,
                    "value_from_datadict",
                    None,
                )
                if callable(value_from_data):
                    raw_value = value_from_data(form_body, None, name)
                if getattr(column_widget.widget, "input_type", None) == "checkbox":
                    normalized_value = raw_value
                else:
                    normalized_value = column_widget.widget.format_value(raw_value)
                if (
                    getattr(column_widget.widget, "input_type", None) == "select"
                    and not getattr(
                        column_widget.widget, "allow_multiple_selected", False
                    )
                    and isinstance(normalized_value, list)
                ):
                    normalized_value = normalized_value[0] if normalized_value else None
                response[destination_col] = self.modeladmin.normalize_field_value(
                    destination_col, normalized_value
                )
        return response
