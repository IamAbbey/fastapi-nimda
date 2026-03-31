from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import String, inspect, select
from sqlmodel import Field, Relationship, SQLModel, Session, create_engine

from fastapi_nimda import FastAPINimda, ModelAdmin
from fastapi_nimda.types import AdminSite
from fastapi_nimda.widgets import NumberInput, TextInput

BASE_DIR = Path(__file__).resolve().parent
sqlite_file_name = BASE_DIR / "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)



class Region(SQLModel, table=True):
    __tablename__ = "regions"

    code: str = Field(max_length=3, primary_key=True)
    name: str = Field(max_length=40, unique=True)
    countries: list["Country"] = Relationship(back_populates="region")


class Country(SQLModel, table=True):
    __tablename__ = "countries"

    code: str = Field(max_length=2, primary_key=True)
    name: str = Field(max_length=50, unique=True)
    population: int
    is_active: bool = True
    is_featured: bool = False
    is_archived: bool = False
    region_code: str = Field(foreign_key="regions.code")
    region: Region = Relationship(back_populates="countries")


class Team(SQLModel, table=True):
    __tablename__ = "teams"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    city: str
    is_active: bool = True
    heroes: list["Hero"] = Relationship(back_populates="team")


class Hero(SQLModel, table=True):
    __tablename__ = "heroes"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    secret_name: str
    age: int | None = None
    is_active: bool = True
    team_id: int | None = Field(default=None, foreign_key="teams.id")
    team: Team | None = Relationship(back_populates="heroes")


def seed_reference_data() -> None:
    with Session(engine) as session:
        if session.execute(select(Country.code)).first() is not None:
            return

        regions = [
            Region(code="EU", name="Europe"),
            Region(code="NA", name="North America"),
            Region(code="AP", name="Asia Pacific"),
        ]
        session.add_all(regions)

        countries = [
            Country(
                code="FR",
                name="France",
                population=68_000_000,
                is_active=True,
                is_featured=True,
                region_code="EU",
            ),
            Country(
                code="DE",
                name="Germany",
                population=84_000_000,
                is_active=True,
                region_code="EU",
            ),
            Country(
                code="JP",
                name="Japan",
                population=124_000_000,
                is_active=False,
                region_code="AP",
            ),
        ]
        teams = [
            Team(name="Justice League", city="Metropolis", is_active=True),
            Team(name="Birds of Prey", city="Gotham", is_active=True),
        ]
        session.add_all(countries + teams)
        session.commit()

        justice_league = session.execute(
            select(Team).where(Team.name == "Justice League")
        ).scalar_one()
        birds_of_prey = session.execute(
            select(Team).where(Team.name == "Birds of Prey")
        ).scalar_one()
        session.add_all(
            [
                Hero(
                    name="Superman",
                    secret_name="Clark Kent",
                    age=35,
                    is_active=True,
                    team_id=justice_league.id,
                ),
                Hero(
                    name="Black Canary",
                    secret_name="Dinah Lance",
                    age=32,
                    is_active=True,
                    team_id=birds_of_prey.id,
                ),
            ]
        )
        session.commit()




def reset_demo_database() -> None:
    engine.dispose()
    if sqlite_file_name.exists():
        sqlite_file_name.unlink()


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    seed_reference_data()


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
admin_app = FastAPINimda(
    app=app,
    engine=engine,
    site=AdminSite(
        site_header="Nimda SQLModel Demo",
        site_title="Nimda Demo Admin",
        index_title="Demo Administration",
    ),
)


@app.get("/demo/countries/{country_code}/summary")
def country_summary(country_code: str):
    with Session(engine) as session:
        country = session.get(Country, country_code.upper())
        if country is None:
            return JSONResponse(
                status_code=404, content={"detail": "Country not found"}
            )
        return {
            "code": country.code,
            "name": country.name,
            "population": country.population,
            "featured": country.is_featured,
            "region_code": country.region_code,
        }


@app.get("/demo/heroes/{hero_id}/profile")
def hero_profile(hero_id: int):
    with Session(engine) as session:
        hero = session.get(Hero, hero_id)
        if hero is None:
            return JSONResponse(status_code=404, content={"detail": "Hero not found"})
        return {
            "id": hero.id,
            "name": hero.name,
            "secret_name": hero.secret_name,
            "team_id": hero.team_id,
            "active": hero.is_active,
        }


class RegionAdmin(ModelAdmin):
    list_display = ["code", "name"]
    list_order_by = ["name"]
    search_fields = ["code", "name"]
    sortable_fields = ["code", "name"]
    label = "Region"
    plural_label = "Regions"
    navigation_group = "Reference Data"
    icon = "map"
    field_help_texts = {
        "code": "Keep region codes short and stable because countries reference them.",
    }

    # The demo keeps regions as reference data, so destructive actions stay disabled.
    def has_delete_permission(self, request, record=None) -> bool:
        return False


class CountryAdmin(ModelAdmin):
    list_display = ["code", "name", "population", "is_active", "region_code"]
    list_order_by = ["name"]
    search_fields = ["code", "name"]
    list_filter = ["is_active", "region_code"]
    sortable_fields = ["code", "name", "population"]
    actions = {
        "feature": "Mark selected as featured",
        "archive": "Archive selected",
    }
    label = "Country"
    plural_label = "Countries"
    navigation_group = "Reference Data"
    icon = "globe"
    field_labels = {
        "code": "ISO code",
        "region_code": "Region",
    }
    field_help_texts = {
        "code": "The pre-save hook uppercases new country codes automatically.",
        "population": "Use a whole-number estimate for the admin demo.",
        "region": "Rendered as a relationship dropdown because this is a supported foreign key.",
    }
    formfield_overrides = {
        String: TextInput(attrs={"placeholder": "Enter a value"}),
    }
    widgets = {
        "population": NumberInput(attrs={"min": "0", "step": "1"}),
    }

    # The list query hook keeps archived rows out of the normal admin workflow.
    def get_list_query(self, statement, *, request=None):
        return statement.where(Country.is_archived.is_(False))

    def before_create(self, request, values):
        values["code"] = values["code"].upper()
        values["name"] = values["name"].strip()
        return values

    def before_update(self, request, record, values):
        values["code"] = values["code"].upper()
        values["name"] = values["name"].strip()
        return values

    def after_create(self, request, record) -> None:
        request.app.state.last_saved_country = record.code

    def after_update(self, request, record) -> None:
        request.app.state.last_saved_country = record.code

    def handle_action_feature(self, request, session, records):
        for record in records:
            record.is_featured = True
        return f"{len(records)} countries marked as featured"

    def handle_action_archive(self, request, session, records):
        for record in records:
            record.is_archived = True
        return f"{len(records)} countries archived"

    def get_object_actions(self, request, record):
        return [
            {
                "label": "JSON summary",
                "url": f"/demo/countries/{record.code}/summary",
                "color": "emerald",
            }
        ]

    def has_delete_permission(self, request, record=None) -> bool:
        return False


class TeamAdmin(ModelAdmin):
    list_display = ["id", "name", "city", "is_active"]
    search_fields = ["name", "city"]
    list_filter = ["is_active"]
    sortable_fields = ["id", "name", "city"]
    label = "Team"
    plural_label = "Teams"
    navigation_group = "Hero Ops"
    icon = "shield"


class HeroAdmin(ModelAdmin):
    list_display = ["id", "name", "secret_name", "is_active", "team_id"]
    search_fields = ["name", "secret_name"]
    list_filter = ["is_active", "team_id"]
    sortable_fields = ["id", "name", "age"]
    actions = {"activate": "Activate selected heroes"}
    label = "Hero"
    plural_label = "Heroes"
    navigation_group = "Hero Ops"
    icon = "bolt"
    field_help_texts = {
        "team": "The list view shows the related team inline next to the foreign key value.",
    }

    def handle_action_activate(self, request, session, records):
        for record in records:
            record.is_active = True
        return f"{len(records)} heroes activated"

    def get_object_actions(self, request, record):
        return [
            {
                "label": "Hero profile JSON",
                "url": f"/demo/heroes/{record.id}/profile",
                "color": "emerald",
            }
        ]


admin_app.register(Region, RegionAdmin)
admin_app.register(Country, CountryAdmin)
admin_app.register(Team, TeamAdmin)
admin_app.register(Hero, HeroAdmin)


if __name__ == "__main__":
    create_db_and_tables()
