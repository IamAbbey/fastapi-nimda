from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Path, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi_nimda.depends import (
    ResourceDependency,
    get_record,
    get_records,
    get_resource,
    get_resources,
)

from .errors import PermissionDeniedError
from .helpers import get_sqlalchemy_error_message, normalize_sqlachemy_error
from .messaging import TemplateMessage, add_template_message
from .operation import OperationKind
from .services import create_record, update_record
from .templating.templating import templates

router = APIRouter()


def _ensure_permission(allowed: bool, message: str) -> None:
    if not allowed:
        raise PermissionDeniedError(message)


def _build_list_query_context(
    request: Request, modeladmin
) -> tuple[str | None, str | None, str, dict[str, str]]:
    search_term = request.query_params.get("q")
    sort = request.query_params.get("sort")
    direction = request.query_params.get("direction", "asc").lower()
    if direction not in {"asc", "desc"}:
        direction = "asc"
    filters = {
        field: request.query_params.get(f"filter__{field}", "")
        for field in modeladmin.get_list_filter_fields()
    }
    return search_term, sort, direction, filters


def _base_list_query_url(request: Request, **changes) -> str:
    params = {
        key: value
        for key, value in request.query_params.items()
        if key != "skip" and value not in ("", None)
    }
    for key, value in changes.items():
        if value in ("", None):
            params.pop(key, None)
        else:
            params[key] = str(value)
    query = urlencode(params)
    base = str(request.url_for("admin_list", identity=request.path_params["identity"]))
    return f"{base}?{query}" if query else base


@router.get("/", response_class=HTMLResponse, name="admin_index")
def index(
    request: Request,
    resources: list[ResourceDependency] = Depends(get_resources),
) -> Any:
    visible_resources = [
        {
            "identity": resource.identity,
            "table_name": resource.modeladmin.table_name,
            "label": resource.modeladmin.get_label(),
            "plural_label": resource.modeladmin.get_plural_label(),
            "group": resource.modeladmin.get_navigation_group(),
            "icon": resource.modeladmin.get_navigation_icon(),
            "can_add": resource.modeladmin.has_add_permission(request),
        }
        for resource in resources
        if resource.modeladmin.has_module_permission(request)
    ]
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"resources": visible_resources},
    )


@router.get("/{identity}/list/", response_class=HTMLResponse, name="admin_list")
def list_records(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    identity: str = Path(...),
    skip: int = 0,
) -> Any:
    modeladmin = resource.modeladmin
    _ensure_permission(
        modeladmin.has_list_permission(request),
        f"{modeladmin.get_label()}: list view is not permitted",
    )
    action_message = request.query_params.get("a_m")
    action_kind = request.query_params.get("a_k", "success")
    if action_message:
        add_template_message(
            request=request,
            message=TemplateMessage(kind=action_kind, message=action_message),
        )
    search_term, sort, direction, filters = _build_list_query_context(
        request, modeladmin
    )

    with Session(request.app.engine) as session:
        statement = modeladmin.get_list_query_stmt(
            request=request,
            search=search_term,
            filters=filters,
            sort=sort,
            direction=direction,
        )
        count_statement = modeladmin.get_list_query_count_stmt(
            request=request,
            search=search_term,
            filters=filters,
            sort=sort,
            direction=direction,
        )
        if skip > 0:
            statement = statement.offset(skip)
        queryset = session.execute(statement).scalars().all()
        count = session.execute(count_statement).scalar_one()
        page_size = modeladmin.get_page_size()
        columns = modeladmin.get_list_display() or [modeladmin.get_primary_key_name()]
        header_columns = []
        sortable_fields = set(modeladmin.get_sortable_fields())
        for field in columns:
            is_sortable = field in sortable_fields
            next_direction = (
                "desc"
                if is_sortable and sort == field and direction == "asc"
                else "asc"
            )
            header_columns.append(
                {
                    "name": field,
                    "label": modeladmin.get_field_label(field),
                    "sortable": is_sortable,
                    "sort_direction": direction if sort == field else None,
                    "sort_url": _base_list_query_url(
                        request,
                        sort=field if is_sortable else None,
                        direction=next_direction if is_sortable else None,
                    ),
                }
            )

        pagination = {
            "range": {
                "start": skip + 1 if queryset else 0,
                "end": len(queryset) + skip,
            },
            "page_size": page_size,
            "has_next": count > (len(queryset) + skip),
            "has_prev": skip > 0,
            "next_url": _base_list_query_url(request, skip=skip + page_size),
            "prev_url": _base_list_query_url(request, skip=max(skip - page_size, 0)),
        }

        return templates.TemplateResponse(
            request=request,
            name="list.html",
            context={
                "table_name": modeladmin.table_name,
                "label": modeladmin.get_label(),
                "plural_label": modeladmin.get_plural_label(),
                "modeladmin": modeladmin,
                "identity": identity,
                "data": queryset,
                "columns": header_columns,
                "can_perform_add": modeladmin.can_perform_add(request),
                "can_delete": modeladmin.has_delete_permission(request),
                "pk": modeladmin.get_primary_key_name(),
                "count": count,
                "paginator": pagination,
                "search_term": search_term or "",
                "active_filters": filters,
                "available_filters": modeladmin.get_list_filter_options(session),
                "bulk_actions": modeladmin.get_bulk_actions(request),
                "empty_state_message": (
                    "No records matched the current search or filters."
                    if search_term or any(filters.values())
                    else "No records exist yet. Create the first one to get started."
                ),
            },
        )


@router.post("/{identity}/actions/", name="admin_action_post")
async def action_post(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    identity: str = Path(...),
) -> Any:
    modeladmin = resource.modeladmin
    async with request.form() as form:
        action_name = str(form.get("action", "")).strip()
        keys = [key for key in str(form.get("keys", "")).split(",") if key]

    if not action_name:
        add_template_message(
            request=request,
            message=TemplateMessage(kind="error", message="Choose an action first."),
        )
        return RedirectResponse(
            request.url_for("admin_list", identity=identity),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if action_name == "delete":
        _ensure_permission(
            modeladmin.has_delete_permission(request),
            f"{modeladmin.get_label()}: delete is not permitted",
        )
        return RedirectResponse(
            request.url_for("admin_delete", identity=identity).include_query_params(
                keys=",".join(keys)
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    _ensure_permission(
        modeladmin.has_action_permission(request, action_name),
        f"{modeladmin.get_label()}: action '{action_name}' is not permitted",
    )
    with Session(request.app.engine) as session:
        records = (
            session.execute(modeladmin.get_multi_record_query_stmt(keys=keys))
            .scalars()
            .all()
        )
        message = modeladmin.run_action(action_name, request, session, records)
        session.commit()

    add_template_message(
        request=request,
        message=TemplateMessage(kind="success", message=message),
    )
    return RedirectResponse(
        request.url_for("admin_list", identity=identity).include_query_params(
            a_m=message,
            a_k="success",
        ),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/{identity}/add/", response_class=HTMLResponse, name="admin_add")
def add(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    identity: str = Path(...),
) -> Any:
    modeladmin = resource.modeladmin
    _ensure_permission(
        modeladmin.has_add_permission(request),
        f"{modeladmin.get_label()}: add view is not permitted",
    )
    return templates.TemplateResponse(
        request=request,
        name="add.html",
        context={
            "form": modeladmin.render_form(operation=OperationKind.ADD),
            "table_name": modeladmin.table_name,
            "label": modeladmin.get_label(),
            "identity": identity,
        },
    )


@router.post("/{identity}/add/", name="admin_add_post")
async def add_post(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    identity: str = Path(...),
) -> Any:
    modeladmin = resource.modeladmin
    _ensure_permission(
        modeladmin.has_add_permission(request),
        f"{modeladmin.get_label()}: creating records is not permitted",
    )
    database_table_name = modeladmin.model.__table__.name
    result = await create_record(request, modeladmin)
    if result.succeeded:
        add_template_message(
            request=request,
            message=TemplateMessage(
                kind="success",
                message=f"{resource.modeladmin.table_name}: new record created successfully",
            ),
        )
        return RedirectResponse(
            request.url_for(
                "admin_view",
                identity=identity,
                key=result.new_record_key,
            ).replace_query_params(n_r=1),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if isinstance(result.error, SQLAlchemyError):
        message = get_sqlalchemy_error_message(database_table_name, result.error)
        error_fields = normalize_sqlachemy_error(database_table_name, result.error)
    else:
        message = str(result.error)
        error_fields = []
    add_template_message(
        request=request,
        message=TemplateMessage(kind="error", message=message),
    )
    return templates.TemplateResponse(
        request=request,
        name="add.html",
        context={
            "form": modeladmin.render_form(
                record=result.validated_form,
                operation=OperationKind.ADD,
                error_fields=error_fields,
            ),
            "error_message": message,
            "error_fields": error_fields,
            "table_name": modeladmin.table_name,
            "label": modeladmin.get_label(),
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
    modeladmin = resource.modeladmin
    _ensure_permission(
        modeladmin.has_edit_permission(request, record),
        f"{modeladmin.get_label()}: edit view is not permitted",
    )
    return templates.TemplateResponse(
        request=request,
        name="edit.html",
        context={
            "form": modeladmin.render_form(record=record, operation=OperationKind.EDIT),
            "table_name": modeladmin.table_name,
            "label": modeladmin.get_label(),
            "identity": identity,
            "record": record,
            "pk": modeladmin.get_primary_key_name(),
        },
    )


@router.post("/{identity}/edit/{key}", name="admin_edit_post")
async def edit_post(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    record: ResourceDependency = Depends(get_record),
    identity: str = Path(...),
    key: str = Path(...),
) -> Any:
    modeladmin = resource.modeladmin
    _ensure_permission(
        modeladmin.has_edit_permission(request, record),
        f"{modeladmin.get_label()}: updating records is not permitted",
    )
    database_table_name = modeladmin.model.__table__.name
    result = await update_record(request, modeladmin, key)
    if not result.succeeded:
        if isinstance(result.error, SQLAlchemyError):
            message = get_sqlalchemy_error_message(database_table_name, result.error)
            error_fields = normalize_sqlachemy_error(database_table_name, result.error)
        else:
            message = str(result.error)
            error_fields = []
        add_template_message(
            request=request,
            message=TemplateMessage(kind="error", message=message),
        )
        return templates.TemplateResponse(
            request=request,
            name="edit.html",
            context={
                "form": modeladmin.render_form(
                    record=result.validated_form,
                    operation=OperationKind.EDIT,
                    error_fields=error_fields,
                ),
                "error_message": message,
                "error_fields": error_fields,
                "table_name": modeladmin.table_name,
                "label": modeladmin.get_label(),
                "identity": identity,
                "record": record,
                "pk": modeladmin.get_primary_key_name(),
            },
        )
    add_template_message(
        request=request,
        message=TemplateMessage(
            message=f"{resource.modeladmin.table_name}: {key} updated successfully"
        ),
    )
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
    n_r: bool | None = None,
    e_r: bool | None = None,
) -> Any:
    modeladmin = resource.modeladmin
    _ensure_permission(
        modeladmin.has_view_permission(request, record),
        f"{modeladmin.get_label()}: viewing records is not permitted",
    )
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
            "label": modeladmin.get_label(),
            "identity": identity,
            "record": record,
            "pk": modeladmin.get_primary_key_name(),
            "custom_object_actions": modeladmin.get_object_actions(request, record),
            "can_edit": modeladmin.has_edit_permission(request, record),
            "can_delete": modeladmin.has_delete_permission(request, record),
        },
    )


@router.get("/{identity}/delete/", response_class=HTMLResponse, name="admin_delete")
def delete(
    request: Request,
    resource: ResourceDependency = Depends(get_resource),
    records: ResourceDependency = Depends(get_records),
    identity: str = Path(...),
) -> Any:
    modeladmin = resource.modeladmin
    _ensure_permission(
        modeladmin.has_delete_permission(request),
        f"{modeladmin.get_label()}: delete view is not permitted",
    )
    return templates.TemplateResponse(
        request=request,
        name="delete.html",
        context={
            "table_name": modeladmin.table_name,
            "label": modeladmin.get_label(),
            "identity": identity,
            "records": records,
            "pk": modeladmin.get_primary_key_name(),
        },
    )
