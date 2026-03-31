from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import String, select
from sqlalchemy.orm import Session

from fastapi_nimda import FastAPINimda, ModelAdmin
from fastapi_nimda.widgets import TextInput

from .conftest import Country, Hero, Region


def test_list_search_sort_filter_and_inline_foreign_key_display(sa_engine):
    class SearchableHeroAdmin(ModelAdmin):
        list_display = ["id", "name", "secret_name", "is_active"]
        list_filter = ["is_active"]

    class RelatedCountryAdmin(ModelAdmin):
        list_display = ["code", "name", "region_code"]

    app = FastAPI()
    admin = FastAPINimda(app=app, engine=sa_engine)
    admin.register(Hero, SearchableHeroAdmin)
    admin.register(Region, ModelAdmin)
    admin.register(Country, RelatedCountryAdmin)

    with Session(sa_engine) as session:
        session.add_all(
            [
                Hero(name="Batman", secret_name="Bruce Wayne", is_active=True),
                Hero(name="Robin", secret_name="Dick Grayson", is_active=False),
                Region(code="eu", name="Europe"),
            ]
        )
        session.flush()
        session.add(Country(code="fr", name="France", region_code="eu"))
        session.commit()

    with TestClient(app) as client:
        search_response = client.get("/admin/heroes/list/?q=Bruce")
        assert search_response.status_code == 200
        assert "Batman" in search_response.text
        assert "Robin" not in search_response.text

        sort_response = client.get("/admin/heroes/list/?sort=name&direction=desc")
        assert sort_response.status_code == 200
        assert sort_response.text.index("Robin") < sort_response.text.index("Batman")

        filter_response = client.get("/admin/heroes/list/?filter__is_active=false")
        assert filter_response.status_code == 200
        assert "Robin" in filter_response.text
        assert "Batman" not in filter_response.text

        country_response = client.get("/admin/countries/list/")
        assert country_response.status_code == 200
        assert "Europe (eu)" in country_response.text


def test_customization_hooks_and_navigation_metadata(sa_engine):
    class HookedHeroAdmin(ModelAdmin):
        list_display = ["id", "name", "secret_name", "is_active"]
        actions = {"deactivate": "Deactivate selected"}
        label = "Hero roster"
        plural_label = "Hero roster"
        navigation_group = "Security"
        icon = "shield"
        field_labels = {"secret_name": "Alias"}
        field_help_texts = {"secret_name": "Used for private identities."}
        formfield_overrides = {String: TextInput(attrs={"data-override": "yes"})}

        def get_list_query(self, statement, *, request=None):
            return statement.where(Hero.name != "Hidden")

        def before_create(self, request, values):
            values["name"] = values["name"].title()
            return values

        def after_create(self, request, record):
            request.app.state.last_created_name = record.name

        def get_object_actions(self, request, record):
            return [
                {"label": "Inspect", "url": f"/inspect/{record.id}", "color": "emerald"}
            ]

        def handle_action_deactivate(self, request, session, records):
            for record in records:
                record.is_active = False
            return "Heroes deactivated"

    app = FastAPI()
    admin = FastAPINimda(app=app, engine=sa_engine)
    admin.register(Hero, HookedHeroAdmin)

    with Session(sa_engine) as session:
        session.add_all(
            [
                Hero(name="Hidden", secret_name="Nope", is_active=True),
                Hero(name="Visible", secret_name="Shown", is_active=True),
                Hero(name="Second", secret_name="Shown Too", is_active=True),
            ]
        )
        session.commit()

    with TestClient(app) as client:
        home_response = client.get("/admin/")
        assert home_response.status_code == 200
        assert "Hero roster" in home_response.text
        assert "Security" in home_response.text
        assert "shield" in home_response.text

        add_response = client.get("/admin/heroes/add/")
        assert add_response.status_code == 200
        assert "Alias" in add_response.text
        assert "Used for private identities." in add_response.text
        assert 'data-override="yes"' in add_response.text

        create_response = client.post(
            "/admin/heroes/add/",
            data={
                "name": "superman",
                "secret_name": "Clark Kent",
                "is_active": "true",
            },
            follow_redirects=False,
        )
        assert create_response.status_code == 303
        assert admin.state.last_created_name == "Superman"

        list_response = client.get("/admin/heroes/list/")
        assert list_response.status_code == 200
        assert "Visible" in list_response.text
        assert "Hidden" not in list_response.text

        view_response = client.get("/admin/heroes/view/2")
        assert view_response.status_code == 200
        assert "Inspect" in view_response.text

        action_response = client.post(
            "/admin/heroes/actions/",
            data={"action": "deactivate", "keys": "2,3"},
            follow_redirects=True,
        )
        assert action_response.status_code == 200
        assert "Heroes deactivated" in action_response.text

    with Session(sa_engine) as session:
        inactive_names = (
            session.execute(
                select(Hero.name).where(Hero.is_active.is_(False)).order_by(Hero.id)
            )
            .scalars()
            .all()
        )
        assert inactive_names == ["Visible", "Second"]


def test_permission_hooks_hide_add_and_block_add_post(sa_engine):
    class RestrictedHeroAdmin(ModelAdmin):
        list_display = ["id", "name", "secret_name"]

        def has_add_permission(self, request):
            return False

    app = FastAPI()
    admin = FastAPINimda(app=app, engine=sa_engine)
    admin.register(Hero, RestrictedHeroAdmin)

    with TestClient(app) as client:
        list_response = client.get("/admin/heroes/list/")
        assert list_response.status_code == 200
        assert "/admin/heroes/add/" not in list_response.text

        add_response = client.get("/admin/heroes/add/")
        assert add_response.status_code == 403
