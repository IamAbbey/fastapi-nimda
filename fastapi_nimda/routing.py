from fastapi import APIRouter, Depends
from fastapi import Request, Path, status, Body, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_nimda.depends import (
    get_resource,
    get_resources,
    get_record,
    get_records,
    ResourceDependency,
)
from .helpers import (
    normalize_sqlachemy_error,
)
from .operation import OperationKind
from .templating.templating import templates
from .messaging import add_template_message, TemplateMessage
from typing import Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import DatabaseError

# from sqlmodel import Field, Session, SQLModel, create_engine, select
router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="admin_index")
def index(
    request: Request,
    resources: List[ResourceDependency] = Depends(get_resources),
) -> Any:
    """
    Admin index.
    """
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "resources": [
                {
                    "identity": resource.identity,
                    "table_name": resource.modeladmin.table_name,
                }
                for resource in resources
            ]
        },
    )


@router.get("/{identity}/list/", response_class=HTMLResponse, name="admin_list")
def list(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    identity: str = Path(...),
    skip: int = 0,
) -> Any:
    """
    Retrieve countries.
    """
    modeladmin = resource.modeladmin
    with Session(request.app.engine) as session:
        statement = modeladmin.get_list_query_stmt()
        count_statement = modeladmin.get_list_query_count_stmt()
        if skip > 0:
            statement = statement.offset(skip)
        if modeladmin.get_list_display():
            queryset = session.execute(statement).all()
        else:
            queryset = session.execute(statement).scalars().all()
        count = session.execute(count_statement).scalar_one()
        page_size = modeladmin.get_page_size()
        return templates.TemplateResponse(
            request=request,
            name="list.html",
            context={
                "table_name": modeladmin.table_name,
                "modeladmin": modeladmin,
                "identity": identity,
                "data": queryset,
                "list_display": modeladmin.get_list_display(),
                "can_perform_add": modeladmin.can_perform_add(),
                "pk": modeladmin.get_model_primary_keys()[0],
                "count": count,
                "paginator": {
                    "range": {"start": skip + 1, "end": len(queryset) + skip},
                    "page_size": page_size,
                    "has_next": count > (len(queryset) + skip),
                    "has_prev": skip > 0,
                    "next": skip + page_size,
                    "prev": skip,
                },
            },
        )


@router.get("/{identity}/add/", response_class=HTMLResponse, name="admin_add")
def add(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    identity: str = Path(...),
) -> Any:
    """
    Add new record.
    """
    modeladmin = resource.modeladmin
    return templates.TemplateResponse(
        request=request,
        name="add.html",
        context={
            "form": modeladmin.render_form(operation=OperationKind.ADD),
            "table_name": modeladmin.table_name,
            "identity": identity,
        },
    )


@router.post("/{identity}/add/", name="admin_add_post")
async def add_post(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    identity: str = Path(...),
) -> Any:
    """
    POST add record.
    """
    modeladmin = resource.modeladmin
    form_body = {}
    with Session(request.app.engine) as session:
        statement = modeladmin.get_insert_record_stmt()
        async with request.form() as form:
            for _key, value in form.items():
                if isinstance(value, UploadFile):
                    raise ValueError("File Upload not supported yet")
                form_body[_key] = value
        validated_form = modeladmin.get_form().validate_form(form_body=form_body)
        statement = statement.values(validated_form)
        try:
            result = session.execute(statement)
            new_record_key = result.scalar_one()
            session.commit()

            add_template_message(
                request=request,
                message=TemplateMessage(
                    kind="success",
                    message=f"{resource.modeladmin.table_name}: new record created successfully",
                ),
            )
            # 303 tells the client: “I accepted your POST, now go GET this other URL.”
            return RedirectResponse(
                request.url_for(
                    "admin_view",
                    identity=identity,
                    key=new_record_key,
                ).replace_query_params(
                    n_r=1,
                ),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        except DatabaseError as exc:
            add_template_message(
                request=request,
                message=TemplateMessage(
                    kind="error", message=f"Error: {exc._message()}"
                ),
            )
            return templates.TemplateResponse(
                request=request,
                name="add.html",
                context={
                    "form": modeladmin.render_form(
                        record=validated_form,
                        operation=OperationKind.ADD,
                        error_fields=normalize_sqlachemy_error(
                            modeladmin.table_name, exc
                        ),
                    ),
                    "table_name": modeladmin.table_name,
                    "identity": identity,
                },
            )


@router.get("/{identity}/edit/{key}", response_class=HTMLResponse, name="admin_edit")
def edit(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    record: ResourceDependency = Depends(get_record),
    identity: str = Path(...),
) -> Any:
    """
    Edit record.
    """
    modeladmin = resource.modeladmin
    return templates.TemplateResponse(
        request=request,
        name="edit.html",
        context={
            "form": modeladmin.render_form(record=record, operation=OperationKind.EDIT),
            "table_name": modeladmin.table_name,
            "identity": identity,
            "record": record,
            "pk": modeladmin.get_model_primary_keys()[0],
        },
    )


@router.post("/{identity}/edit/{key}", name="admin_edit_post")
async def edit_post(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    record: ResourceDependency = Depends(get_record),
    identity: str = Path(...),
    key: str = Path(...),
    input: str = Body(...),
) -> Any:
    """
    POST edit record.
    """
    modeladmin = resource.modeladmin
    form_body = {}
    with Session(request.app.engine) as session:
        statement = modeladmin.get_update_record_stmt(key=[key])
        async with request.form() as form:
            for _key, value in form.items():
                if isinstance(value, UploadFile):
                    raise ValueError("File Upload not supported yet")
                form_body[_key] = value

        validated_form = modeladmin.get_form().validate_form(form_body=form_body)
        statement = statement.values(validated_form)
        session.execute(statement)
        session.commit()
    add_template_message(
        request=request,
        message=TemplateMessage(
            message=f"{resource.modeladmin.table_name}: {key} updated successfully"
        ),
    )
    # 303 tells the client: “I accepted your POST, now go GET this other URL.”
    return RedirectResponse(
        request.url_for("admin_view", identity=identity, key=key).replace_query_params(
            e_r=1,
        ),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/{identity}/view/{key}", response_class=HTMLResponse, name="admin_view")
def view(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    record: ResourceDependency = Depends(get_record),
    identity: str = Path(...),
    n_r: Optional[bool] = None,
    e_r: Optional[bool] = None,
) -> Any:
    """
    View record.
    """
    modeladmin = resource.modeladmin
    if record is None:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"code": "404", "message": "Page not found"},
        )

    if n_r:
        add_template_message(
            request=request,
            message=TemplateMessage(
                kind="success",
                message=f"{resource.modeladmin.table_name}: new record created successfully",
            ),
        )
    elif e_r:
        add_template_message(
            request=request,
            message=TemplateMessage(
                kind="success",
                message=f"{resource.modeladmin.table_name}: record updated successfully",
            ),
        )

    return templates.TemplateResponse(
        request=request,
        name="view.html",
        context={
            "form": modeladmin.render_form(record=record, operation=OperationKind.VIEW),
            "table_name": modeladmin.table_name,
            "identity": identity,
            "record": record,
            "pk": modeladmin.get_model_primary_keys()[0],
        },
    )


@router.get("/{identity}/delete/", response_class=HTMLResponse, name="admin_delete")
def delete(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    records: ResourceDependency = Depends(get_records),
    identity: str = Path(...),
) -> Any:
    """
    Delete record.
    """
    modeladmin = resource.modeladmin
    return templates.TemplateResponse(
        request=request,
        name="delete.html",
        context={
            "table_name": modeladmin.table_name,
            "identity": identity,
            "records": records,
            "pk": modeladmin.get_model_primary_keys()[0],
        },
    )
