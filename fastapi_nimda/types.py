from pydantic import BaseModel, InstanceOf
from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept
from typing import Type

from .admin import ModelAdmin


class RegisteredResource(BaseModel):
    model: InstanceOf[DeclarativeAttributeIntercept]
    modeladmin: Type[ModelAdmin]  # type: ModelAdmin


class AdminSite(BaseModel):
    index_title: str = ""
    site_header: str = ""
    site_title: str = ""
