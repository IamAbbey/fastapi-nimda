from fastapi import FastAPI
from typing import Optional, Type, Dict
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept
from fastapi_nimda.admin import ModelAdmin
from fastapi_nimda.types import AdminSite, RegisteredResource
from .routing import router
from fastapi.staticfiles import StaticFiles
from .constants import BASE_DIR
from starlette.types import ASGIApp
from sqlalchemy.engine import Engine


def app_requirement_checks():
    import sqlite3
    import sys

    MIN_VERSION = (3, 35, 0)  # RETURNING support was added in 3.35.0

    current = tuple(map(int, sqlite3.sqlite_version.split(".")))

    if current < MIN_VERSION:
        sys.exit(
            f"SQLite {MIN_VERSION} or newer is required, "
            f"but you have {sqlite3.sqlite_version}"
        )


class FastAPINimda(FastAPI):
    def __init__(
        self, *, app: ASGIApp, engine: Engine, site: Optional[AdminSite] = None
    ):
        super().__init__()

        app_requirement_checks()

        self._registered: Dict[str, RegisteredResource] = {}
        self.models = []

        app.mount("/admin", self)
        self.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
        self.include_router(router)

        self.engine = engine

    @property
    def register_resource(self) -> Dict[str, RegisteredResource]:
        return self._registered

    def register(self, model: Type[DeclarativeBase], modeladmin: Type[ModelAdmin]):
        if not issubclass(modeladmin, ModelAdmin):
            raise ValueError(
                f"{modeladmin} needs to be a subclass of {ModelAdmin.__name__}"
            )

        if not isinstance(model, DeclarativeAttributeIntercept):
            raise ValueError(f"{model.__name__} needs to be has an SQLAlchemy table")

        self._registered[f"{len(self._registered) + 1}"] = RegisteredResource(
            model=model, modeladmin=modeladmin
        )
