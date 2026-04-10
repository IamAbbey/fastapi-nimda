from __future__ import annotations

import io
import subprocess
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Session
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlmodel import Field, SQLModel, create_engine

from fastapi_nimda import FastAPINimda
from fastapi_nimda.admin import ModelAdmin
from fastapi_nimda.errors import UnsupportedRelationshipError
from fastapi_nimda.inspection import inspect_model

from .conftest import Base


def test_many_to_many_field_is_explicitly_rejected(sa_engine):
    membership = Table(
        "membership_links",
        Base.metadata,
        Column("team_id", ForeignKey("m2m_teams.id"), primary_key=True),
        Column("member_id", ForeignKey("m2m_members.id"), primary_key=True),
    )

    class Member(Base):
        __tablename__ = "m2m_members"

        id: Mapped[str] = mapped_column(String(10), primary_key=True)
        name: Mapped[str] = mapped_column(String(50))
        teams: Mapped[list["Team"]] = relationship(
            secondary=membership,
            back_populates="members",
        )

    class Team(Base):
        __tablename__ = "m2m_teams"

        id: Mapped[str] = mapped_column(String(10), primary_key=True)
        name: Mapped[str] = mapped_column(String(50))
        members: Mapped[list[Member]] = relationship(
            secondary=membership,
            back_populates="teams",
        )

    class TeamAdmin(ModelAdmin):
        fields = ["name", "members"]

    with pytest.raises(
        UnsupportedRelationshipError,
        match="many-to-many relationships are not supported in admin forms yet",
    ):
        TeamAdmin(model=Team, engine=sa_engine)


def test_one_to_many_field_is_explicitly_rejected(sa_engine):
    class Parent(Base):
        __tablename__ = "parents"

        id: Mapped[str] = mapped_column(String(10), primary_key=True)
        children: Mapped[list["Child"]] = relationship(back_populates="parent")

    class Child(Base):
        __tablename__ = "children"

        id: Mapped[str] = mapped_column(String(10), primary_key=True)
        parent_id: Mapped[str] = mapped_column(ForeignKey("parents.id"))
        parent: Mapped[Parent] = relationship(back_populates="children")

    class ParentAdmin(ModelAdmin):
        fields = ["id", "children"]

    with pytest.raises(
        UnsupportedRelationshipError,
        match="one-to-many collections are not supported as admin form fields",
    ):
        ParentAdmin(model=Parent, engine=sa_engine)


def test_scalar_reverse_one_to_one_is_allowed_in_list_display_but_not_form_fields(
    tmp_path,
):
    class SourceInput(Base):
        __tablename__ = "source_inputs"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
        file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
        task_status: Mapped["SourceInputTaskStatus | None"] = relationship(
            back_populates="source_input",
            uselist=False,
        )

    class SourceInputTaskStatus(Base):
        __tablename__ = "source_input_task_statuses"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        status: Mapped[str] = mapped_column(String(50), default="pending")
        source_input_id: Mapped[int] = mapped_column(
            ForeignKey("source_inputs.id"), unique=True
        )
        source_input: Mapped[SourceInput] = relationship(back_populates="task_status")

    class SourceInputAdmin(ModelAdmin):
        list_display = ["id", "source_url", "task_status"]

    engine = create_engine(f"sqlite:///{tmp_path / 'scalar-one-to-one.db'}")
    Base.metadata.create_all(engine)

    inspection = inspect_model(SourceInput)
    assert "task_status" not in inspection.supported_form_fields
    assert "task_status" in inspection.readonly_relation_fields

    modeladmin = SourceInputAdmin(model=SourceInput, engine=engine)
    assert "task_status" not in modeladmin.get_model_admin_fields()

    with Session(engine) as session:
        source_input = SourceInput(
            source_url="https://example.com/song",
            file_path="/tmp/song.txt",
        )
        session.add(source_input)
        session.commit()
        session.refresh(source_input)
        session.add(
            SourceInputTaskStatus(
                status="ready",
                source_input_id=source_input.id,
            )
        )
        session.commit()

    app = FastAPI()
    admin = FastAPINimda(app=app, engine=engine)
    identity = admin.register(SourceInput, SourceInputAdmin)

    with TestClient(app) as client:
        list_response = client.get(f"/admin/{identity}/list/")
        view_response = client.get(f"/admin/{identity}/view/1")

    assert list_response.status_code == 200
    assert "ready" in list_response.text
    assert view_response.status_code == 200
    assert "https://example.com/song" in view_response.text


def test_file_upload_request_is_rejected_with_clear_message(sa_client):
    response = sa_client.post(
        "/admin/heroes/add/",
        data={"secret_name": "Clark Kent", "is_active": "true"},
        files={"name": ("hero.txt", io.BytesIO(b"Superman"), "text/plain")},
    )

    assert response.status_code == 200
    assert "File uploads are not supported yet" in response.text


def test_sqlmodel_support_smoke_route(sqlmodel_client, seed_sqlmodel_data):
    response = sqlmodel_client.get("/admin/teams/list/")

    assert response.status_code == 200
    assert "Justice League" in response.text


def test_sqlmodel_string_list_filter_options_do_not_crash(tmp_path):
    class SqlModelFilterRecord(SQLModel, table=True):
        __tablename__ = "sqlmodel_filter_records"

        id: int | None = Field(default=None, primary_key=True)
        title: str
        category: str
        is_active: bool = True

    class SqlModelFilterAdmin(ModelAdmin):
        list_display = ["id", "title", "category", "is_active"]
        list_filter = ["category", "is_active"]

    engine = create_engine(f"sqlite:///{tmp_path / 'sqlmodel-filters.db'}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                SqlModelFilterRecord(
                    title="France",
                    category="Europe",
                    is_active=True,
                ),
                SqlModelFilterRecord(
                    title="Japan",
                    category="Asia",
                    is_active=False,
                ),
            ]
        )
        session.commit()

    app = FastAPI()
    admin = FastAPINimda(app=app, engine=engine)
    identity = admin.register(SqlModelFilterRecord, SqlModelFilterAdmin)

    with TestClient(app) as client:
        response = client.get(f"/admin/{identity}/list/")

    assert response.status_code == 200
    assert "Europe" in response.text
    assert "Yes" in response.text


def test_sqlmodel_example_relationships_configure():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from sqlalchemy.inspection import inspect; "
                "from examples.sqlmodel_demo.main import Region; "
                "assert list(inspect(Region).relationships.keys()) == ['countries']"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
