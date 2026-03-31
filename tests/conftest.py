from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Boolean, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from sqlmodel import Field, SQLModel

from fastapi_nimda import FastAPINimda, ModelAdmin


class Base(DeclarativeBase):
    pass


class Hero(Base):
    __tablename__ = "heroes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    secret_name: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Region(Base):
    __tablename__ = "regions"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    countries: Mapped[list["Country"]] = relationship(back_populates="region")


class Country(Base):
    __tablename__ = "countries"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    region_code: Mapped[str] = mapped_column(ForeignKey("regions.code"))
    region: Mapped[Region] = relationship(back_populates="countries")


class Team(SQLModel, table=True):
    __tablename__ = "teams"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)


class TeamHero(SQLModel, table=True):
    __tablename__ = "team_heroes"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    team_id: int | None = Field(default=None)


class HeroAdmin(ModelAdmin):
    list_display = ["id", "name", "secret_name"]


class RegionAdmin(ModelAdmin):
    list_display = ["code", "name"]


class CountryAdmin(ModelAdmin):
    list_display = ["code", "name", "region_code"]


class TeamAdmin(ModelAdmin):
    list_display = ["id", "name"]


class TeamHeroAdmin(ModelAdmin):
    list_display = ["id", "name", "team_id"]


@pytest.fixture
def sa_engine(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'sa.db'}")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def sqlmodel_engine(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'sqlmodel.db'}")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def sa_admin_app(sa_engine):
    app = FastAPI()
    admin = FastAPINimda(app=app, engine=sa_engine)
    admin.register(Hero, HeroAdmin)
    admin.register(Region, RegionAdmin)
    admin.register(Country, CountryAdmin)
    return app, admin


@pytest.fixture
def sqlmodel_admin_app(sqlmodel_engine):
    app = FastAPI()
    admin = FastAPINimda(app=app, engine=sqlmodel_engine)
    admin.register(Team, TeamAdmin)
    admin.register(TeamHero, TeamHeroAdmin)
    return app, admin


@pytest.fixture
def sa_client(sa_admin_app):
    app, _ = sa_admin_app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sqlmodel_client(sqlmodel_admin_app):
    app, _ = sqlmodel_admin_app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def seed_sa_data(sa_engine):
    with Session(sa_engine) as session:
        region = Region(code="eu", name="Europe")
        hero = Hero(name="Batman", secret_name="Bruce Wayne", is_active=True)
        country = Country(code="fr", name="France", region=region)
        session.add_all([region, hero, country])
        session.commit()
        return {
            "region": region,
            "hero": hero,
            "country": country,
        }


@pytest.fixture
def seed_sqlmodel_data(sqlmodel_engine):
    with Session(sqlmodel_engine) as session:
        team = Team(name="Justice League")
        session.add(team)
        session.commit()
        session.refresh(team)
        hero = TeamHero(name="Superman", team_id=team.id)
        session.add(hero)
        session.commit()
        session.refresh(hero)
        return {
            "team": team,
            "hero": hero,
        }


@pytest.fixture
def hero_rows(sa_engine):
    def _rows():
        with Session(sa_engine) as session:
            return session.execute(select(Hero).order_by(Hero.id)).scalars().all()

    return _rows
