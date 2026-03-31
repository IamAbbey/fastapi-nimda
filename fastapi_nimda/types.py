from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept

    from .admin import ModelAdmin


@dataclass
class RegisteredResource:
    identity: str
    model: type["DeclarativeAttributeIntercept"]
    modeladmin: type["ModelAdmin"]


@dataclass
class AdminSite:
    index_title: str = ""
    site_header: str = ""
    site_title: str = ""
