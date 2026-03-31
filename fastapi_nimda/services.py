from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from .errors import UnsupportedFileUploadError


@dataclass
class WriteResult:
    validated_form: dict[str, Any]
    error: Exception | None = None
    new_record_key: Any | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


async def extract_form_body(request: Request) -> dict[str, Any]:
    form_body = {}
    async with request.form() as form:
        for key, value in form.items():
            if isinstance(value, StarletteUploadFile):
                raise UnsupportedFileUploadError(
                    f"File uploads are not supported yet. Remove the uploaded value for '{key}'."
                )
            form_body[key] = value
    return form_body


async def create_record(request: Request, modeladmin) -> WriteResult:
    validated_form: dict[str, Any] = {}
    try:
        form_body = await extract_form_body(request)
        validated_form = modeladmin.get_form().validate_form(form_body=form_body)
        validated_form = modeladmin.before_create(request, validated_form)
        statement = modeladmin.get_insert_record_stmt().values(validated_form)
        with Session(request.app.engine) as session:
            try:
                result = session.execute(statement)
                new_record_key = result.scalar_one()
                created_record = session.execute(
                    modeladmin.get_single_record_query_stmt(key=[new_record_key])
                ).scalar_one()
                modeladmin.after_create(request, created_record)
                session.commit()
                return WriteResult(
                    validated_form=validated_form,
                    new_record_key=new_record_key,
                )
            except SQLAlchemyError as exc:
                session.rollback()
                return WriteResult(validated_form=validated_form, error=exc)
    except SQLAlchemyError as exc:
        return WriteResult(validated_form=validated_form, error=exc)
    except Exception as exc:
        return WriteResult(validated_form=validated_form, error=exc)


async def update_record(request: Request, modeladmin, key) -> WriteResult:
    validated_form: dict[str, Any] = {}
    try:
        form_body = await extract_form_body(request)
        with Session(request.app.engine) as session:
            try:
                existing_record = session.execute(
                    modeladmin.get_single_record_query_stmt(key=[key])
                ).scalar_one_or_none()
                validated_form = modeladmin.get_form().validate_form(
                    form_body=form_body
                )
                validated_form = modeladmin.before_update(
                    request,
                    existing_record,
                    validated_form,
                )
                statement = modeladmin.get_update_record_stmt(key=[key]).values(
                    validated_form
                )
                session.execute(statement)
                updated_record = session.execute(
                    modeladmin.get_single_record_query_stmt(key=[key])
                ).scalar_one()
                modeladmin.after_update(request, updated_record)
                session.commit()
                return WriteResult(validated_form=validated_form)
            except SQLAlchemyError as exc:
                session.rollback()
                return WriteResult(validated_form=validated_form, error=exc)
    except SQLAlchemyError as exc:
        return WriteResult(validated_form=validated_form, error=exc)
    except Exception as exc:
        return WriteResult(validated_form=validated_form, error=exc)
