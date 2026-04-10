from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from sqlalchemy.engine import Engine
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.orm.interfaces import RelationshipDirection
from sqlalchemy.orm.relationships import RelationshipProperty
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import String

from .errors import UnknownAdminActionError, UnsupportedRelationshipError
from .forms import AdminForm
from .inspection import get_model_primary_keys, inspect_model
from .operation import OperationKind
from .queries import ModelQueryBuilder
from .widgets import Widget


class ModelAdmin:
    list_display: list[str] = []
    readonly_fields: list[str] = []
    raw_id_fields: list[str] = []
    fields: list[str] | Literal["__all__"] = "__all__"
    exclude: list[str] = []
    widgets: dict[str, Widget] = {}
    formfield_overrides: dict[type, Widget | type[Widget]] = {}
    field_labels: dict[str, str] = {}
    field_help_texts: dict[str, str] = {}
    page_size: int = 20
    list_order_by: list[str] = []
    search_fields: list[str] = []
    list_filter: list[str] = []
    sortable_fields: list[str] = []
    actions: dict[str, str] = {}
    slug: str | None = None
    label: str | None = None
    plural_label: str | None = None
    navigation_group: str = "Models"
    icon: str | None = None

    def __init__(self, *, model: type[DeclarativeBase], engine: Engine) -> None:
        self.engine = engine
        self._model: type[DeclarativeBase] = model
        self._identity: str | None = None
        inspection = inspect_model(model)
        self._table_columns = inspection.table_columns
        self._table_fk_columns = inspection.table_fk_columns
        self._table_rel_columns = inspection.table_rel_columns
        self._supported_form_fields = inspection.supported_form_fields
        self._unsupported_relation_fields = inspection.unsupported_relation_fields
        self._readonly_relation_fields = inspection.readonly_relation_fields
        self._query_builder = ModelQueryBuilder(self)
        self._validate_attributes()

    def get_page_size(self):
        return self.page_size

    def get_list_display(self):
        return self.list_display

    def get_list_query_count_stmt(self, **kwargs):
        return self._query_builder.get_list_query_count_stmt(**kwargs)

    def get_list_query_stmt(self, **kwargs):
        return self._query_builder.get_list_query_stmt(**kwargs)

    def get_primary_key_as_model_column(self):
        return self._query_builder.get_primary_key_as_model_column()

    def get_update_record_stmt(self, key: list[str]):
        return self._query_builder.get_update_record_stmt(key)

    def get_delete_record_stmt(self, key: list[str]):
        return self._query_builder.get_delete_record_stmt(key)

    def get_insert_record_stmt(self):
        return self._query_builder.get_insert_record_stmt()

    def get_single_record_query_stmt(self, key: list[str]):
        return self._query_builder.get_single_record_query_stmt(key)

    def get_multi_record_query_stmt(self, keys: list[str]):
        return self._query_builder.get_multi_record_query_stmt(keys)

    @property
    def model(self):
        return self._model

    @property
    def table_columns(self):
        return self._table_columns

    @property
    def table_fk_columns(self):
        return self._table_fk_columns

    @property
    def table_rel_columns(self):
        return self._table_rel_columns

    @property
    def table_name(self):
        return self.model.__name__

    @property
    def all_columns(self):
        return {
            **self._table_columns,
            **self._table_fk_columns,
            **self._table_rel_columns,
        }

    @property
    def unsupported_relation_fields(self):
        return self._unsupported_relation_fields

    @property
    def readonly_relation_fields(self):
        return self._readonly_relation_fields

    def validate_fields_exist(self, fields: list[str], against):
        for field in fields:
            if field not in against:
                raise ValueError(
                    f"{field} is not a column field in associated model ({self.model.__name__})"
                )

    def validate_list_display_like_attributes(self):
        for attr in ("list_display",):
            if not isinstance(getattr(self, attr), (list, tuple)):
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :{attr}: must be sequence e.g list, tuple"
                )
            try:
                self.validate_fields_exist(getattr(self, attr), self.all_columns.keys())
            except ValueError as e:
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :{attr}: {e.args[0]}"
                )

        mapper = inspect(self.model)
        if not isinstance(self.list_order_by, (list, tuple)):
            raise ValueError(
                f"{self.__class__.__name__} Error: Invalid attribute :list_order_by: must be sequence e.g list, tuple"
            )
        try:
            self.validate_fields_exist(self.list_order_by, mapper.column_attrs.keys())
        except ValueError as e:
            raise ValueError(
                f"{self.__class__.__name__} Error: Invalid attribute :list_order_by: {e.args[0]}"
            )

    def validate_field_like_attributes(self):
        all_columns = self.all_columns.keys()
        column_fields = {**self.table_columns, **self.table_fk_columns}.keys()
        if self.fields == "__all__":
            self.fields = list(self._supported_form_fields)

        for attr in ("fields", "readonly_fields", "exclude"):
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

        for attr in ("search_fields", "list_filter", "sortable_fields"):
            if not isinstance(getattr(self, attr), (list, tuple)):
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :{attr}: must be sequence e.g list, tuple"
                )
        try:
            self.validate_fields_exist(list(self.search_fields), column_fields)
            self.validate_fields_exist(list(self.list_filter), column_fields)
            self.validate_fields_exist(list(self.sortable_fields), column_fields)
        except ValueError as e:
            raise ValueError(
                f"{self.__class__.__name__} Error: Invalid attribute configuration: {e.args[0]}"
            )

        if not isinstance(self.actions, dict):
            raise ValueError(
                f"{self.__class__.__name__} Error: Invalid attribute :actions: must be a dict"
            )
        if not isinstance(self.field_labels, dict) or not isinstance(
            self.field_help_texts, dict
        ):
            raise ValueError(
                f"{self.__class__.__name__} Error: field label/help text configuration must be dict-like"
            )
        if not isinstance(self.formfield_overrides, dict):
            raise ValueError(
                f"{self.__class__.__name__} Error: Invalid attribute :formfield_overrides: must be a dict"
            )

    def validate_supported_field_usage(self):
        for attr in ("fields", "readonly_fields", "raw_id_fields", "list_display"):
            for field in getattr(self, attr):
                if field in self.unsupported_relation_fields:
                    raise UnsupportedRelationshipError(
                        f"{self.__class__.__name__} Error: Invalid attribute :{attr}: "
                        f"{field} is unsupported because {self.unsupported_relation_fields[field]}"
                    )
        for attr in ("fields", "raw_id_fields"):
            for field in getattr(self, attr):
                if field in self.readonly_relation_fields:
                    raise UnsupportedRelationshipError(
                        f"{self.__class__.__name__} Error: Invalid attribute :{attr}: "
                        f"{field} is unsupported because {self.readonly_relation_fields[field]}"
                    )

    def validate_actions(self):
        for name, label in self.actions.items():
            if not isinstance(name, str) or not isinstance(label, str) or not label:
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :actions: every action needs a non-empty string name and label"
                )
            if not hasattr(self, f"handle_action_{name}"):
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :actions: missing handler handle_action_{name}"
                )

    def _validate_attributes(self):
        self.validate_field_like_attributes()
        self.validate_list_display_like_attributes()
        self.validate_supported_field_usage()
        self.validate_actions()

    def get_model_admin_fields(self):
        return self.fields

    def get_label(self) -> str:
        return self.label or self.table_name

    def get_plural_label(self) -> str:
        return self.plural_label or self.get_label()

    def get_navigation_group(self) -> str:
        return self.navigation_group or "Models"

    def get_navigation_icon(self) -> str | None:
        return self.icon

    def can_perform_add(self, request=None):
        return len(self.get_model_admin_fields()) > 0 and self.has_add_permission(
            request
        )

    def get_absolute_url(self):
        return f"/{self._identity}/list/"

    def get_field_label(self, name: str) -> str:
        return self.field_labels.get(name, name.replace("_", " ").capitalize())

    def get_field_help_text(self, name: str) -> str | None:
        return self.field_help_texts.get(name)

    def get_default_search_fields(self) -> list[str]:
        return [
            name
            for name, column in {**self.table_columns, **self.table_fk_columns}.items()
            if isinstance(column.type, String)
        ]

    def get_search_fields(self) -> list[str]:
        return list(self.search_fields or self.get_default_search_fields())

    def get_list_filter_fields(self) -> list[str]:
        return list(self.list_filter)

    def get_sortable_fields(self) -> list[str]:
        if self.sortable_fields:
            return list(self.sortable_fields)
        if self.list_display:
            return [
                field
                for field in self.list_display
                if field in self.table_columns or field in self.table_fk_columns
            ]
        return self.get_model_primary_keys()

    def get_list_query(self, statement, *, request=None):
        return statement

    def before_create(self, request, values: dict[str, Any]) -> dict[str, Any]:
        return values

    def after_create(self, request, record) -> None:
        return None

    def before_update(self, request, record, values: dict[str, Any]) -> dict[str, Any]:
        return values

    def after_update(self, request, record) -> None:
        return None

    def has_module_permission(self, request) -> bool:
        return True

    def has_list_permission(self, request) -> bool:
        return self.has_module_permission(request)

    def has_view_permission(self, request, record=None) -> bool:
        return self.has_module_permission(request)

    def has_add_permission(self, request) -> bool:
        return self.has_module_permission(request)

    def has_edit_permission(self, request, record=None) -> bool:
        return self.has_module_permission(request)

    def has_delete_permission(self, request, record=None) -> bool:
        return self.has_module_permission(request)

    def has_action_permission(self, request, action_name: str) -> bool:
        return self.has_module_permission(request)

    def get_object_actions(self, request, record) -> list[dict[str, str]]:
        return []

    def get_bulk_actions(self, request=None) -> list[dict[str, str]]:
        if request is not None and not self.has_delete_permission(request):
            delete_actions: list[dict[str, str]] = []
        else:
            delete_actions = [{"name": "delete", "label": "Delete selected"}]
        custom_actions = [
            {"name": name, "label": label}
            for name, label in self.actions.items()
            if request is None or self.has_action_permission(request, name)
        ]
        return [*delete_actions, *custom_actions]

    def run_action(
        self, name: str, request, session: Session, records: list[Any]
    ) -> str:
        if name not in self.actions:
            raise UnknownAdminActionError(
                f"{self.get_label()}: unknown bulk action '{name}'"
            )
        if not self.has_action_permission(request, name):
            raise UnknownAdminActionError(
                f"{self.get_label()}: action '{name}' is not available"
            )
        handler = getattr(self, f"handle_action_{name}")
        result = handler(request, session, records)
        return (
            result
            or f"{self.get_plural_label()}: action '{self.actions[name]}' completed"
        )

    def get_form(
        self,
        *,
        operation: OperationKind = OperationKind.VIEW,
        record=None,
    ):
        return AdminForm(
            modeladmin=self,
            widgets=self.get_widgets(),
            engine=self.engine,
            record=record,
            operation=operation,
        )

    def render_form(self, operation: OperationKind = OperationKind.VIEW, **kwargs):
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
            if getattr(widget, "input_type", None) == "file":
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid attribute :widgets: "
                    f"{name} cannot use a file input because file uploads are not supported yet"
                )

        return self.widgets

    def get_formfield_override_widget(self, column: Column) -> Widget | None:
        for column_type, widget_or_type in self.formfield_overrides.items():
            if isinstance(column.type, column_type):
                if isinstance(widget_or_type, Widget):
                    return deepcopy(widget_or_type)
                if isinstance(widget_or_type, type) and issubclass(
                    widget_or_type, Widget
                ):
                    return widget_or_type()
                raise ValueError(
                    f"{self.__class__.__name__} Error: Invalid formfield override for {column.key}"
                )
        return None

    def get_model_primary_keys(self) -> list[str]:
        return get_model_primary_keys(self.model)

    def get_primary_key_name(self) -> str:
        primary_keys = list(self.get_model_primary_keys())
        return primary_keys[0]

    def get_auto_increment_column(self) -> Column | None:
        return self.model.__table__.autoincrement_column

    def get_fields_as_columns(self) -> list[Column | RelationshipProperty]:
        assert isinstance(self.get_model_admin_fields(), (list, tuple))
        columns: list[Column | RelationshipProperty] = []
        auto_increment_column = self.get_auto_increment_column()
        for field in self.get_model_admin_fields():
            if field not in self.exclude:
                column = self.all_columns[field]
                if isinstance(column, RelationshipProperty):
                    if column.secondary is not None:
                        raise UnsupportedRelationshipError(
                            f"{self.__class__.__name__} Error: {field} is unsupported because "
                            "many-to-many relationships are not supported in admin forms yet"
                        )
                    if column.uselist:
                        raise UnsupportedRelationshipError(
                            f"{self.__class__.__name__} Error: {field} is unsupported because "
                            "one-to-many collections are not supported as admin form fields"
                        )
                    if column.direction == RelationshipDirection.ONETOMANY:
                        raise UnsupportedRelationshipError(
                            f"{self.__class__.__name__} Error: {field} is unsupported because "
                            "reverse one-to-one relationships are read-only and cannot be used as admin form fields"
                        )
                    columns.append(column)
                    continue
                if (
                    auto_increment_column is not None
                    and auto_increment_column.key == column.key
                ):
                    continue
                columns.append(column)
        return columns

    def get_record_label(self, record) -> str:
        for field_name in (
            "name",
            "title",
            "label",
            "code",
            self.get_primary_key_name(),
        ):
            if hasattr(record, field_name):
                value = getattr(record, field_name)
                if value not in (None, ""):
                    return str(value)
        return str(record)

    def get_list_display_value(self, record, field: str) -> Any:
        if field in self.table_rel_columns:
            related = getattr(record, field, None)
            return "" if related is None else self.get_record_label(related)

        value = getattr(record, field, None)
        if field in self.table_fk_columns:
            for rel_name, relationship in self.table_rel_columns.items():
                if relationship.direction != RelationshipDirection.MANYTOONE:
                    continue
                local_column_names = {
                    column.key for column in relationship.local_columns
                }
                if field in local_column_names:
                    related = getattr(record, rel_name, None)
                    if related is not None:
                        related_label = self.get_record_label(related)
                        return f"{related_label} ({value})"
        return value

    def get_column_python_type(self, field: str):
        column_type = self.all_columns[field].type
        try:
            return column_type.python_type
        except (AttributeError, NotImplementedError):
            return None

    def normalize_field_value(self, field: str, value: Any) -> Any:
        if value in ("", None):
            return None
        if isinstance(value, list):
            return [self.normalize_field_value(field, item) for item in value]

        python_type = self.get_column_python_type(field)
        if python_type is None or isinstance(value, python_type):
            return value
        if python_type is bool:
            if isinstance(value, str):
                return value.lower() == "true"
            return bool(value)
        return python_type(value)

    def normalize_primary_key_value(self, value: Any) -> Any:
        return self.normalize_field_value(self.get_primary_key_name(), value)

    def normalize_primary_key_values(self, values: list[Any]) -> list[Any]:
        return [self.normalize_primary_key_value(value) for value in values]

    def get_list_filter_options(self, session: Session) -> list[dict[str, Any]]:
        filter_options: list[dict[str, Any]] = []
        for field in self.get_list_filter_fields():
            getattr(self.model, field)
            options: list[dict[str, str]] = []
            if self.get_column_python_type(field) is bool:
                options = [
                    {"value": "true", "label": "Yes"},
                    {"value": "false", "label": "No"},
                ]
            else:
                values = [
                    value
                    for value in session.execute(
                        self._query_builder.get_distinct_values_stmt(field)
                    )
                    .scalars()
                    .all()
                    if value not in (None, "")
                ]
                options = [
                    {"value": str(value), "label": str(value)} for value in values
                ]
            filter_options.append(
                {
                    "name": field,
                    "label": self.get_field_label(field),
                    "options": options,
                }
            )
        return filter_options
