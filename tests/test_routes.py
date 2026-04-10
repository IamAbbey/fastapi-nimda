from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from fastapi_nimda import FastAPINimda, ModelAdmin

from .conftest import Base, Country, Hero, HeroAdmin, Region


def test_admin_index_lists_registered_resources(sa_client):
    response = sa_client.get("/admin/")

    assert response.status_code == 200
    assert "Hero" in response.text
    assert "Country" in response.text
    assert "Region" in response.text


def test_list_view_renders_seeded_rows(sa_client, seed_sa_data):
    response = sa_client.get("/admin/heroes/list/")

    assert response.status_code == 200
    assert "Batman" in response.text
    assert "Bruce Wayne" in response.text


def test_add_route_creates_record_and_redirects(sa_client, hero_rows):
    response = sa_client.post(
        "/admin/heroes/add/",
        data={
            "name": "Flash",
            "secret_name": "Barry Allen",
            "is_active": "true",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("/admin/heroes/view/1?n_r=1")
    assert [hero.name for hero in hero_rows()] == ["Flash"]


def test_edit_route_updates_record_and_redirects(sa_client, sa_engine, seed_sa_data):
    response = sa_client.post(
        "/admin/heroes/edit/1",
        data={
            "name": "Batman",
            "secret_name": "Matches Malone",
            "is_active": "true",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("/admin/heroes/view/1?e_r=1")

    with Session(sa_engine) as session:
        hero = session.execute(select(Hero).where(Hero.id == 1)).scalar_one()
        assert hero.secret_name == "Matches Malone"


def test_view_route_accepts_string_path_for_integer_primary_key(
    sa_client, seed_sa_data
):
    response = sa_client.get("/admin/heroes/view/1")

    assert response.status_code == 200
    assert "Batman" in response.text


def test_view_route_renders_success_message_after_create(sa_client, seed_sa_data):
    response = sa_client.get("/admin/heroes/view/1?n_r=1")

    assert response.status_code == 200
    assert "new record created successfully" in response.text
    assert "Batman" in response.text


def test_delete_confirmation_page_renders_selected_record(sa_client, seed_sa_data):
    response = sa_client.get("/admin/heroes/delete/?keys=1")

    assert response.status_code == 200
    assert "Delete record" in response.text
    assert "/admin/heroes/view/1" in response.text


def test_invalid_write_renders_error_and_rolls_back(sa_client, hero_rows):
    first = sa_client.post(
        "/admin/heroes/add/",
        data={
            "name": "Batman",
            "secret_name": "Bruce Wayne",
            "is_active": "true",
        },
        follow_redirects=False,
    )
    assert first.status_code == 303

    duplicate = sa_client.post(
        "/admin/heroes/add/",
        data={
            "name": "Batman",
            "secret_name": "Not Bruce Wayne",
            "is_active": "true",
        },
    )
    assert duplicate.status_code == 200
    assert "Unique constraint failed for: name" in duplicate.text

    second = sa_client.post(
        "/admin/heroes/add/",
        data={
            "name": "Robin",
            "secret_name": "Dick Grayson",
            "is_active": "true",
        },
        follow_redirects=False,
    )
    assert second.status_code == 303
    assert [hero.name for hero in hero_rows()] == ["Batman", "Robin"]


def test_foreign_key_form_submission_saves_relationship(sa_client, sa_engine):
    with Session(sa_engine) as session:
        session.add(Region(code="eu", name="Europe"))
        session.commit()

    response = sa_client.post(
        "/admin/countries/add/",
        data={
            "code": "fr",
            "name": "France",
            "region_code": "eu",
            "region": "eu",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    with Session(sa_engine) as session:
        country = session.execute(
            select(Country).where(Country.code == "fr")
        ).scalar_one()
        assert country.region_code == "eu"


def test_broken_admin_configuration_returns_clear_user_code_error(sa_engine):
    class BrokenParent(Base):
        __tablename__ = "broken_parents"

        id: Mapped[str] = mapped_column(String(10), primary_key=True)
        children: Mapped[list["BrokenChild"]] = relationship(back_populates="parent")

    class BrokenChild(Base):
        __tablename__ = "broken_children"

        id: Mapped[str] = mapped_column(String(10), primary_key=True)
        parent_id: Mapped[str] = mapped_column(ForeignKey("broken_parents.id"))
        parent: Mapped[BrokenParent] = relationship(back_populates="children")

    class BrokenParentAdmin(ModelAdmin):
        list_display = ["id", "children"]

    Base.metadata.create_all(sa_engine)

    app = FastAPI()
    admin = FastAPINimda(app=app, engine=sa_engine)
    identity = admin.register(BrokenParent, BrokenParentAdmin)

    with TestClient(app) as client:
        response = client.get(f"/admin/{identity}/list/")

    assert response.status_code == 400
    assert "Admin configuration error" in response.text
    assert "user-defined admin/model configuration error" in response.text
    assert "BrokenParentAdmin defined at" in response.text
    assert "tests/test_routes.py" in response.text


def test_healthy_admin_pages_render_even_when_another_admin_is_broken(sa_engine):
    class SidebarBrokenParent(Base):
        __tablename__ = "sidebar_broken_parents"

        id: Mapped[str] = mapped_column(String(10), primary_key=True)
        children: Mapped[list["SidebarBrokenChild"]] = relationship(
            back_populates="parent"
        )

    class SidebarBrokenChild(Base):
        __tablename__ = "sidebar_broken_children"

        id: Mapped[str] = mapped_column(String(10), primary_key=True)
        parent_id: Mapped[str] = mapped_column(ForeignKey("sidebar_broken_parents.id"))
        parent: Mapped[SidebarBrokenParent] = relationship(back_populates="children")

    class BrokenParentAdmin(ModelAdmin):
        list_display = ["id", "children"]

    Base.metadata.create_all(sa_engine)

    with Session(sa_engine) as session:
        session.add(Hero(name="Batman", secret_name="Bruce Wayne", is_active=True))
        session.commit()

    app = FastAPI()
    admin = FastAPINimda(app=app, engine=sa_engine)
    admin.register(Hero, HeroAdmin)
    admin.register(SidebarBrokenParent, BrokenParentAdmin)

    with TestClient(app) as client:
        response = client.get("/admin/heroes/list/")

    assert response.status_code == 200
    assert "Batman" in response.text
