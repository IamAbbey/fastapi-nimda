from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .conftest import Country, Hero, Region


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
