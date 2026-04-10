from fastapi import FastAPI

from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from starlette.types import ASGIApp

from fastapi_nimda.types import AdminSite

from .constants import BASE_DIR
from .errors import FastAPINimdaError, PermissionDeniedError
from .helpers import get_missing_table_name, is_missing_table_error
from .registry import AdminRegistry
from .routing import router
from .templating.templating import templates
from fastapi.staticfiles import StaticFiles


def app_requirement_checks(engine: Engine):
    if engine.dialect.name != "sqlite":
        return

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
    def __init__(self, *, app: ASGIApp, engine: Engine, site: AdminSite | None = None):
        super().__init__()

        app_requirement_checks(engine)

        self.registry = AdminRegistry()
        self.models: list[object] = []

        app.mount("/admin", self)
        self.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
        self.include_router(router)

        self.engine = engine
        self.site: AdminSite = site or AdminSite()
        self.add_exception_handler(SQLAlchemyError, self._handle_sqlalchemy_error)
        self.add_exception_handler(FastAPINimdaError, self._handle_admin_error)

    @property
    def register_resource(self):
        return self.registry.as_dict()

    def register(self, model, modeladmin):
        return self.registry.register(model, modeladmin)

    async def _handle_sqlalchemy_error(self, request, exc: SQLAlchemyError):
        if is_missing_table_error(exc):
            table_name = get_missing_table_name(exc)
            return templates.TemplateResponse(
                request=request,
                name="404.html",
                context={
                    "code": "500",
                    "message": "Database schema is not initialized",
                    "description": (
                        f"The admin tried to access the table '{table_name}', but it does not exist yet. "
                        "Create or migrate your database schema before using this admin view."
                    ),
                },
                status_code=500,
            )

        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "code": "500",
                "message": "Database error",
                "description": "The admin encountered a database error while processing this request.",
            },
            status_code=500,
        )

    async def _handle_admin_error(self, request, exc: FastAPINimdaError):
        status_code = 403 if isinstance(exc, PermissionDeniedError) else 400
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "code": str(status_code),
                "message": "Admin request could not be processed",
                "description": str(exc),
            },
            status_code=status_code,
        )
