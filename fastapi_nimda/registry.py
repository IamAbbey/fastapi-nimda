from __future__ import annotations

import re

from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept

from .admin import ModelAdmin
from .types import RegisteredResource


class AdminRegistry:
    def __init__(self):
        self._registered: dict[str, RegisteredResource] = {}

    def register(
        self, model: type[DeclarativeBase], modeladmin: type[ModelAdmin]
    ) -> str:
        if not issubclass(modeladmin, ModelAdmin):
            raise ValueError(
                f"{modeladmin} needs to be a subclass of {ModelAdmin.__name__}"
            )

        if not isinstance(model, DeclarativeAttributeIntercept):
            raise ValueError(f"{model.__name__} needs to be has an SQLAlchemy table")

        identity = self._build_identity(model, modeladmin)
        if identity in self._registered:
            raise ValueError(
                f"{modeladmin.__name__} Error: duplicate admin slug '{identity}'"
            )
        self._registered[identity] = RegisteredResource(
            identity=identity, model=model, modeladmin=modeladmin
        )
        return identity

    def get(self, identity: str) -> RegisteredResource:
        return self._registered[identity]

    def items(self):
        return self._registered.items()

    def as_dict(self) -> dict[str, RegisteredResource]:
        return self._registered

    def _build_identity(
        self, model: type[DeclarativeBase], modeladmin: type[ModelAdmin]
    ) -> str:
        explicit_slug = getattr(modeladmin, "slug", None)
        if explicit_slug:
            return self._slugify(explicit_slug)

        table_name = getattr(getattr(model, "__table__", None), "name", None)
        if table_name:
            return self._slugify(table_name)

        return self._slugify(model.__name__)

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        if not slug:
            raise ValueError("Admin resource slug cannot be empty")
        return slug


def build_model_admin(resource: RegisteredResource, engine: Engine) -> ModelAdmin:
    modeladmin = resource.modeladmin(model=resource.model, engine=engine)
    modeladmin._identity = resource.identity
    return modeladmin
