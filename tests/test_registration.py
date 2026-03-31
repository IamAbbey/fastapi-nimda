from __future__ import annotations

import pytest
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_nimda.admin import ModelAdmin
from fastapi_nimda.errors import UnsupportedPrimaryKeyError
from fastapi_nimda.registry import build_model_admin
from fastapi_nimda.types import RegisteredResource

from .conftest import Base, Hero


def test_duplicate_slug_is_rejected(sa_engine):
    class FirstHeroAdmin(ModelAdmin):
        slug = "people"

    class SecondHeroAdmin(ModelAdmin):
        slug = "people"

    from fastapi_nimda.registry import AdminRegistry

    registry = AdminRegistry()
    registry.register(Hero, FirstHeroAdmin)

    with pytest.raises(ValueError, match="duplicate admin slug 'people'"):
        registry.register(Hero, SecondHeroAdmin)


def test_invalid_list_display_field_is_rejected(sa_engine):
    class InvalidHeroAdmin(ModelAdmin):
        list_display = ["missing"]

    with pytest.raises(ValueError, match="Invalid attribute :list_display"):
        InvalidHeroAdmin(model=Hero, engine=sa_engine)


def test_composite_primary_key_is_rejected(sa_engine):
    class CompositeThing(Base):
        __tablename__ = "composite_things"

        left_id: Mapped[str] = mapped_column(String(10), primary_key=True)
        right_id: Mapped[str] = mapped_column(String(10), primary_key=True)

    class CompositeThingAdmin(ModelAdmin):
        pass

    with pytest.raises(
        UnsupportedPrimaryKeyError, match="supports only a single-column primary key"
    ):
        CompositeThingAdmin(model=CompositeThing, engine=sa_engine)


def test_build_model_admin_sets_registered_identity(sa_engine):
    class HeroAdminWithSlug(ModelAdmin):
        slug = "heroes-custom"

    resource = RegisteredResource(
        identity="heroes-custom",
        model=Hero,
        modeladmin=HeroAdminWithSlug,
    )

    modeladmin = build_model_admin(resource, sa_engine)

    assert modeladmin.get_absolute_url() == "/heroes-custom/list/"
