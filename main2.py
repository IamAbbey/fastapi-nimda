from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from typing import List
from fastapi_nimda.admin import ModelAdmin
from fastapi_nimda.app import FastAPINimda
from sqlalchemy.orm import relationship


sqlite_file_name = "database_test.db"
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
    room: Mapped[List["Room"]] = relationship(
        "Room",
        primaryjoin="Room.id == Item.id",
        foreign_keys="Room.id",
    )


class Room(Base):
    __tablename__ = "room"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    items: Mapped[List["Item"]] = relationship(lazy="selectin")


Base.metadata.create_all(bind=engine)

app = FastAPI()


admin_app = FastAPINimda(app=app, engine=engine)


class ItemAdmin(ModelAdmin):
    pass


class RoomAdmin(ModelAdmin):
    pass


admin_app.register(Item, ItemAdmin)
admin_app.register(Room, RoomAdmin)
