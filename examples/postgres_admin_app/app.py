from contextlib import asynccontextmanager
import os
from typing import Optional

from fastapi import FastAPI
from sqlalchemy import Boolean, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from sqlmodel import Field, Relationship, SQLModel

from fastapi_nimda import FastAPINimda, ModelAdmin


DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    heroes: Mapped[list["Hero"]] = relationship(back_populates="team")


class Hero(Base):
    __tablename__ = "heroes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    secret_name: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    team: Mapped[Team | None] = relationship(back_populates="heroes")


class SourceInputBase(SQLModel):
    source_url: str | None = Field(default=None, max_length=500)
    file_path: str | None = Field(default=None, max_length=500)


class SourceInput(SourceInputBase, table=True):
    __tablename__ = "source_inputs"

    id: int | None = Field(default=None, primary_key=True)
    lyrics_slides: list["LyricsSlide"] = Relationship(back_populates="source_input")
    task_status: Optional["SourceInputTaskStatus"] = Relationship(
        back_populates="source_input",
        sa_relationship_kwargs={"uselist": False},
    )


class LyricsSlide(SQLModel, table=True):
    __tablename__ = "lyrics_slides"

    id: int | None = Field(default=None, primary_key=True)
    source_input_id: int | None = Field(default=None, foreign_key="source_inputs.id")
    title: str = Field(max_length=255)
    source_input: SourceInput | None = Relationship(back_populates="lyrics_slides")


class SourceInputTaskStatus(SQLModel, table=True):
    __tablename__ = "source_input_task_statuses"

    id: int | None = Field(default=None, primary_key=True)
    source_input_id: int = Field(foreign_key="source_inputs.id", unique=True)
    status: str = Field(max_length=64)
    source_input: SourceInput | None = Relationship(back_populates="task_status")


def create_schema_and_seed() -> None:
    Base.metadata.create_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if session.execute(select(Hero.id)).first() is not None:
            hero_seeded = True
        else:
            hero_seeded = False

        if not hero_seeded:
            team = Team(name="Justice League")
            session.add(team)
            session.flush()
            session.add(
                Hero(
                    name="Batman",
                    secret_name="Bruce Wayne",
                    is_active=True,
                    team_id=team.id,
                )
            )

        if session.execute(select(SourceInput.id)).first() is None:
            source_input = SourceInput(
                source_url="https://example.com/video",
                file_path="/tmp/example.mp4",
            )
            session.add(source_input)
            session.flush()
            session.add(
                LyricsSlide(
                    source_input_id=source_input.id,
                    title="Verse 1",
                )
            )
            session.add(
                SourceInputTaskStatus(
                    source_input_id=source_input.id,
                    status="queued",
                )
            )

        session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_schema_and_seed()
    yield


class HeroAdmin(ModelAdmin):
    list_display = ["id", "name", "secret_name", "team_id"]


class TeamAdmin(ModelAdmin):
    list_display = ["id", "name"]


class SourceInputAdmin(ModelAdmin):
    list_display = ["id", "source_url", "file_path", "task_status"]


app = FastAPI(lifespan=lifespan)
admin = FastAPINimda(app=app, engine=engine)
admin.register(Hero, HeroAdmin)
admin.register(Team, TeamAdmin)
admin.register(SourceInput, SourceInputAdmin)
