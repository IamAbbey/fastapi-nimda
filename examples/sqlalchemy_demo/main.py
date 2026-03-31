from pathlib import Path

from fastapi import FastAPI
from fastapi_nimda import FastAPINimda, ModelAdmin
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, sessionmaker
from sqlalchemy.orm import relationship

BASE_DIR = Path(__file__).resolve().parent
sqlite_file_name = BASE_DIR / "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, index=True)
    # room_id: Mapped[int] = mapped_column(ForeignKey("room.id"))
    room: Mapped[list["Room"]] = relationship(
        "Room",
        primaryjoin="Room.id == Item.id",
        foreign_keys="Room.id",
    )


class Room(Base):
    __tablename__ = "room"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    items: Mapped[list["Item"]] = relationship(lazy="selectin")


Base.metadata.create_all(bind=engine)

app = FastAPI()


admin_app = FastAPINimda(app=app, engine=engine)


class ItemAdmin(ModelAdmin):
    pass


class RoomAdmin(ModelAdmin):
    pass


admin_app.register(Item, ItemAdmin)
admin_app.register(Room, RoomAdmin)
