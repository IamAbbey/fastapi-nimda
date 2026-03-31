# Configurations

This document covers the main configuration points exposed by `ModelAdmin` and the built-in widget layer.

## Core Admin Options

These attributes are defined on `ModelAdmin` subclasses.

### Resource identity and labels

- `slug`: explicit resource slug used in URLs instead of the inferred model name
- `label`: singular display label
- `plural_label`: plural display label
- `navigation_group`: sidebar grouping label, defaults to `"Models"`
- `icon`: optional icon name rendered in the UI

### List page options

- `list_display`: fields shown in the table
- `list_order_by`: default ordering
- `page_size`: number of rows per page, defaults to `20`
- `search_fields`: searchable model columns
- `list_filter`: filterable model columns
- `sortable_fields`: columns allowed for interactive sorting

Notes:

- `list_display` may include relationship fields
- `search_fields`, `list_filter`, and `sortable_fields` are validated against real column fields
- if `sortable_fields` is empty, nimda derives a default based on `list_display` or the primary key

### Form options

- `fields`: fields included in add and edit forms, defaults to `"__all__"`
- `exclude`: fields removed from form rendering
- `readonly_fields`: fields rendered read-only
- `raw_id_fields`: relationship fields rendered as raw text inputs instead of selects
- `field_labels`: per-field UI labels
- `field_help_texts`: per-field help text shown in forms
- `widgets`: per-field widget instances
- `formfield_overrides`: type-based widget defaults

Notes:

- auto-increment primary keys are omitted from generated forms
- primary keys are read-only on edit and view pages
- unsupported relationship shapes raise explicit errors during admin setup or form generation

## Hooks

`ModelAdmin` exposes hooks for query shaping, validation, persistence, and permissions.

### Query and lifecycle hooks

- `get_list_query(statement, *, request=None)`: modify the base list query
- `before_create(request, values)`: mutate values before insert
- `after_create(request, record)`: run after insert
- `before_update(request, record, values)`: mutate values before update
- `after_update(request, record)`: run after update

### Permission hooks

- `has_module_permission(request)`
- `has_list_permission(request)`
- `has_view_permission(request, record=None)`
- `has_add_permission(request)`
- `has_edit_permission(request, record=None)`
- `has_delete_permission(request, record=None)`
- `has_action_permission(request, action_name)`

All permission hooks default to allowing access.

### Action hooks

- `actions`: a mapping of action name to label
- `handle_action_<name>(request, session, records)`: handler for each declared bulk action
- `get_object_actions(request, record)`: returns per-row or per-record UI actions

Example:

```python
class CountryAdmin(ModelAdmin):
    actions = {
        "archive": "Archive selected",
    }

    def handle_action_archive(self, request, session, records):
        for record in records:
            record.is_archived = True
        return f"{len(records)} countries archived"
```

## Widgets

Built-in widgets currently include:

- `TextInput`
- `NumberInput`
- `CheckboxInput`
- `Select`
- `SelectMultiple`

All widgets inherit from `Widget`.

## Per-Field Widget Configuration

Use `widgets` when you want to control a specific field directly.

```python
from fastapi_nimda.widgets import NumberInput


class CountryAdmin(ModelAdmin):
    widgets = {
        "population": NumberInput(attrs={"min": "0", "step": "1"}),
    }
```

The `widgets` mapping must contain widget instances, not classes.

## Type-Based Widget Overrides

Use `formfield_overrides` when you want the same widget policy for all columns of a given SQLAlchemy type.

```python
from sqlalchemy import String
from fastapi_nimda.widgets import TextInput


class CountryAdmin(ModelAdmin):
    formfield_overrides = {
        String: TextInput(attrs={"placeholder": "Enter a value"}),
    }
```

Each value can be either:

- a widget instance
- a `Widget` subclass

## Default Widget Mapping

If you do not configure a widget explicitly, the form layer currently maps fields like this:

- `String` columns -> `TextInput`
- `Integer` and `Float` columns -> `NumberInput`
- `Boolean` columns -> `CheckboxInput`
- supported many-to-one relationships -> `Select`
- relationships listed in `raw_id_fields` -> `TextInput`

View pages render relationship values read-only.

## Relationship Support Notes

Current form generation is intentionally conservative.

Supported:

- basic scalar columns
- supported many-to-one relationships

Not supported:

- file inputs
- many-to-many form editing
- one-to-many collection fields
- more complex relationship shapes that the inspection layer rejects

## Practical Example

```python
from sqlalchemy import String

from fastapi_nimda import ModelAdmin
from fastapi_nimda.widgets import NumberInput, TextInput


class HeroAdmin(ModelAdmin):
    list_display = ["id", "name", "secret_name", "team_id"]
    search_fields = ["name", "secret_name"]
    list_filter = ["team_id"]
    sortable_fields = ["id", "name"]
    field_labels = {"secret_name": "Alias"}
    field_help_texts = {"team": "Choose the related team."}
    raw_id_fields = ["team"]
    widgets = {
        "age": NumberInput(attrs={"min": "0"}),
    }
    formfield_overrides = {
        String: TextInput(attrs={"data-override": "yes"}),
    }
```

Use `raw_id_fields` carefully: it trades dropdown convenience for direct primary-key entry.
