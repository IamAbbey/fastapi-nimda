# fastapi-nimda

`fastapi-nimda` is a lightweight admin interface for FastAPI applications backed by SQLAlchemy or SQLModel models.

It mounts a server-rendered admin site under `/admin` and generates basic CRUD pages from registered ORM models.

## Python Requirement

`fastapi-nimda` now targets Python 3.10 and newer.

The codebase uses Python 3.10+ syntax intentionally, including `|` unions and built-in generic types such as `list[str]`.

## Public API

The intended top-level package surface is:

- `FastAPINimda`: the canonical admin application object
- `Admin`: compatibility alias for `FastAPINimda`
- `ModelAdmin`: per-model admin configuration base class

## Naming Policy

The canonical application class name is `FastAPINimda`.

`Admin` is currently kept as a compatibility alias, but the project should treat `FastAPINimda` as the stable documented name going forward. New examples and documentation should prefer `FastAPINimda`.

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
- SQLAlchemy declarative models as the primary ORM target
- SQLModel table models as a first-class supported integration on top of SQLAlchemy
- server-rendered HTML admin pages
- basic CRUD flows:
  - list
  - add
  - view
  - edit
  - delete
- class-based model configuration through `ModelAdmin`
- simple relationship-aware forms for supported foreign-key patterns

## ORM Support Policy

The framework is built on SQLAlchemy inspection and query primitives.

That means:

- SQLAlchemy declarative models are the core support target
- SQLModel table models are considered supported when they map cleanly to the same SQLAlchemy model/relationship patterns
- support is defined by ORM shape compatibility, not by brand name alone

If a SQLModel construct produces a model shape that the current SQLAlchemy inspection logic does not support, that case should be treated as unsupported until implemented explicitly.

## Current Limitations

The project is still in an early stage. Current limitations include:

- sparse formal documentation beyond this README
- limited automated test coverage
- only single-column primary keys are supported
- file uploads are not supported
- many-to-many editing is explicitly unsupported
- foreign-key handling is conservative and rejects some valid ORM shapes
- error normalization is still database-specific in places
- the project currently assumes SQLite behavior in some flows, especially around `RETURNING`

## Unsupported or Not Yet Stable

The following should currently be treated as unsupported or not yet stable:

- composite primary keys
- file upload fields in admin forms
- full many-to-many editing workflows
- one-to-many collection fields in admin forms
- complex foreign-key arrangements, including one column targeting multiple foreign keys
- ORM shapes that do not define the expected relationship objects alongside foreign keys
- database backends that do not behave like the currently assumed SQLAlchemy and SQLite path
- production-grade extension guarantees around hooks, permissions, and customization APIs

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
uv run fastapi dev examples/sqlmodel_demo/main.py
uv run fastapi dev examples/sqlalchemy_demo/main.py
npx @tailwindcss/cli -i ./fastapi_nimda/static/src/input.css -o ./fastapi_nimda/static/lib/output.css --watch
```

These are development-time commands for the current repository layout and may change as the project is restructured.

## Repository Layout

The repository is now organized with:

- library code under `fastapi_nimda/`
- runnable examples under `examples/`
- architecture and support notes under `docs/`
- archived scratch artifacts under `archive/`
