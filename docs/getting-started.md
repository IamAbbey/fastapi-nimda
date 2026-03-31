# Getting Started

`fastapi-nimda` mounts a server-rendered admin application into an existing FastAPI app.

The normal integration flow is:

1. create your FastAPI application
2. create a SQLAlchemy engine
3. construct `FastAPINimda(app=app, engine=engine)`
4. define `ModelAdmin` subclasses for the models you want to expose
5. register those models with the admin app

## Requirements

- Python 3.10 or newer
- FastAPI
- SQLAlchemy or SQLModel models
- a SQLAlchemy engine

## Minimal Setup

```python
from fastapi import FastAPI
from sqlmodel import Field, SQLModel, create_engine

from fastapi_nimda import FastAPINimda, ModelAdmin


engine = create_engine("sqlite:///database.db")


class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    secret_name: str


class HeroAdmin(ModelAdmin):
    list_display = ["id", "name", "secret_name"]


app = FastAPI()
admin = FastAPINimda(app=app, engine=engine)
admin.register(Hero, HeroAdmin)
```

After registration, the admin interface is mounted at `/admin`.

## Site Branding

You can customize the site header and page titles by passing an `AdminSite` object:

```python
from fastapi_nimda.types import AdminSite


admin = FastAPINimda(
    app=app,
    engine=engine,
    site=AdminSite(
        site_header="Nimda Demo",
        site_title="Nimda Admin",
        index_title="Administration",
    ),
)
```

## Local Development

This repository already includes runnable examples:

```bash
uv run fastapi dev examples/sqlmodel_demo/main.py
uv run fastapi dev examples/sqlalchemy_demo/main.py
```

## Current Limits

Before integrating deeply, keep these current limits in mind:

- only single-column primary keys are supported
- file uploads are not supported
- many-to-many editing is not supported
- one-to-many collection fields are not supported in forms
- some behavior is still SQLite-oriented

See `docs/limitations.md` for the current support boundary.
