from dataclasses import dataclass

from fastapi import Depends, Query, Request
from fastapi.params import Path
from fastapi_nimda.admin import ModelAdmin
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .registry import build_model_admin
from .types import RegisteredResource


@dataclass
class ResourceDependency:
    identity: str
    modeladmin: ModelAdmin


def get_model_admin(resource, engine: Engine) -> ModelAdmin:
    return build_model_admin(resource, engine)


def get_resource(
    request: Request, identity: str | None = Path(...)
) -> ResourceDependency | None:
    if identity is None:
        return None

    _resource: RegisteredResource = request.app.register_resource[identity]
    return ResourceDependency(
        identity=identity, modeladmin=get_model_admin(_resource, request.app.engine)
    )


def get_record(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    key: str | None = Path(...),
) -> ResourceDependency | None:
    if resource is None or key is None:
        return None

    with Session(request.app.engine) as session:
        return session.execute(
            resource.modeladmin.get_single_record_query_stmt(key=[key])
        ).scalar_one_or_none()


def get_records(
    request: Request,
    keys: str = Query(),
    resource: ResourceDependency = Depends(get_resource),
) -> ResourceDependency | None:
    if resource is None:
        return None

    with Session(request.app.engine) as session:
        return (
            session.execute(
                resource.modeladmin.get_multi_record_query_stmt(keys=keys.split(","))
            )
            .scalars()
            .all()
        )


def get_resources(request: Request) -> list[ResourceDependency]:
    _resources: dict[str, RegisteredResource] = request.app.register_resource
    return [
        ResourceDependency(
            identity=identity, modeladmin=get_model_admin(resource, request.app.engine)
        )
        for identity, resource in _resources.items()
    ]
