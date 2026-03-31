# Example

The main runnable example in this repository is `examples/sqlmodel_demo/main.py`.

It demonstrates:

- mounting the admin app into FastAPI
- configuring site branding
- registering multiple models
- search, sorting, and filtering
- custom labels and help text
- custom widgets and form field overrides
- bulk actions and object-level actions

## Run The Example

```bash
uv run fastapi dev examples/sqlmodel_demo/main.py
```

Then open:

- `http://127.0.0.1:8000/admin/`

## Condensed Example

```python
from fastapi import FastAPI
from sqlmodel import Field, Relationship, SQLModel, create_engine

from fastapi_nimda import FastAPINimda, ModelAdmin
from fastapi_nimda.types import AdminSite
from fastapi_nimda.widgets import NumberInput


engine = create_engine("sqlite:///database.db")


class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    heroes: list["Hero"] = Relationship(back_populates="team")


class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    secret_name: str
    age: int | None = None
    is_active: bool = True
    team_id: int | None = Field(default=None, foreign_key="team.id")
    team: Team | None = Relationship(back_populates="heroes")


class HeroAdmin(ModelAdmin):
    list_display = ["id", "name", "secret_name", "is_active", "team_id"]
    search_fields = ["name", "secret_name"]
    list_filter = ["is_active", "team_id"]
    sortable_fields = ["id", "name", "age"]
    field_help_texts = {
        "team": "Rendered as a relationship dropdown for a supported foreign key."
    }
    widgets = {
        "age": NumberInput(attrs={"min": "0", "step": "1"}),
    }


app = FastAPI()
admin = FastAPINimda(
    app=app,
    engine=engine,
    site=AdminSite(
        site_header="Nimda Demo",
        site_title="Nimda Admin",
        index_title="Demo Administration",
    ),
)
admin.register(Hero, HeroAdmin)
```

## What To Look At In The Full Demo

`examples/sqlmodel_demo/main.py` contains examples of:

- `navigation_group` and `icon` for sidebar organization
- `field_labels` and `field_help_texts`
- `formfield_overrides` for type-based widget defaults
- `widgets` for per-field widget control
- `before_create` and `before_update` hooks
- custom bulk actions with `actions` plus `handle_action_<name>()`
- row-level actions returned from `get_object_actions()`
