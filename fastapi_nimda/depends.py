from typing import List, Optional, Dict
from fastapi import Depends, Request
from fastapi.params import Path
from dataclasses import dataclass
from fastapi_nimda.admin import ModelAdmin
from .types import RegisteredResource
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from fastapi import Query


@dataclass
class ResourceDependency:
    identity: str
    modeladmin: ModelAdmin


def get_model_admin(resource, engine: Engine) -> ModelAdmin:
    return resource.modeladmin(model=resource.model, engine=engine)


def get_resource(
    request: Request, identity: Optional[str] = Path(...)
) -> ResourceDependency:
    if identity is None:
        return

    _resource: RegisteredResource = request.app.register_resource[identity]
    return ResourceDependency(
        identity=identity, modeladmin=get_model_admin(_resource, request.app.engine)
    )


def get_record(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    key: Optional[str] = Path(...),
) -> ResourceDependency:
    if resource is None:
        return

    with Session(request.app.engine) as session:
        return session.execute(
            resource.modeladmin.get_single_record_query_stmt(key=[key])
        ).scalar_one_or_none()


def get_records(
    request: Request,
    keys: str = Query(),
    resource: ResourceDependency = Depends(get_resource),
) -> ResourceDependency:
    if resource is None:
        return

    with Session(request.app.engine) as session:
        return (
            session.execute(
                resource.modeladmin.get_multi_record_query_stmt(keys=keys.split(","))
            )
            .scalars()
            .all()
        )


def get_resources(request: Request) -> List[ResourceDependency]:
    _resources: Dict[str, RegisteredResource] = request.app.register_resource
    return [
        ResourceDependency(
            identity=identity, modeladmin=get_model_admin(resource, request.app.engine)
        )
        for identity, resource in _resources.items()
    ]
