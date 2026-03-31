# fastapi-nimda

`fastapi-nimda` is a lightweight admin interface for FastAPI applications backed by SQLAlchemy or SQLModel models.

It mounts a server-rendered admin site under `/admin` and generates basic CRUD pages from registered ORM models.

## Public API

The intended top-level package surface is:

- `FastAPINimda`: the admin application object
- `Admin`: compatibility alias for `FastAPINimda`
- `ModelAdmin`: per-model admin configuration base class

## Quickstart

```python
from fastapi import FastAPI
from sqlmodel import SQLModel, Field, create_engine

from fastapi_nimda import FastAPINimda, ModelAdmin


engine = create_engine("sqlite:///database.db")


class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    secret_name: str


app = FastAPI()
admin = FastAPINimda(app=app, engine=engine)


class HeroAdmin(ModelAdmin):
    list_display = ["id", "name", "secret_name"]


admin.register(Hero, HeroAdmin)
```

After registration, the admin site is mounted at `/admin`.

## Integration Model

The expected setup flow is:

1. create your FastAPI app
2. create a SQLAlchemy engine
3. construct `FastAPINimda(app=app, engine=engine)`
4. subclass `ModelAdmin` for each model you want to expose
5. register models with `admin.register(Model, ModelAdminSubclass)`

## Supported Today

The current implementation is aimed at:

- FastAPI applications
- SQLAlchemy declarative models
- SQLModel table models
- server-rendered HTML admin pages
- basic CRUD flows:
  - list
  - add
  - view
  - edit
  - delete
- class-based model configuration through `ModelAdmin`
- simple relationship-aware forms for supported foreign-key patterns

## Current Limitations

The project is still in an early stage. Current limitations include:

- sparse formal documentation beyond this README
- limited automated test coverage
- file uploads are not supported
- many-to-many editing is not fully supported
- foreign-key handling is conservative and rejects some valid ORM shapes
- error normalization is still database-specific in places
- the project currently assumes SQLite behavior in some flows, especially around `RETURNING`

## Project Status

This is currently a prototype-quality library with a usable core, not a finished production package.

The architecture is already coherent, but the next priorities are:

- stabilizing the public API
- improving package structure
- adding tests
- documenting supported and unsupported patterns clearly

## Development Notes

Useful local commands currently present in the repository:

```bash
uv run fastapi dev main.py
npx @tailwindcss/cli -i ./fastapi_nimda/static/src/input.css -o ./fastapi_nimda/static/dist/output.css --watch
```

These are development-time commands for the current repository layout and may change as the project is restructured.
