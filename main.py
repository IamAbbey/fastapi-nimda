from fastapi import FastAPI
from fastapi_nimda.admin import ModelAdmin
from fastapi_nimda.app import FastAPINimda
from typing import Union, List

from sqlmodel import Field, SQLModel


from sqlmodel import create_engine
from sqlmodel import Relationship

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)


class CountryLanguageLink(SQLModel, table=True):
    __tablename__ = "country_link_languages"

    country_code: Union[str, None] = Field(
        default=None, foreign_key="countries.code", primary_key=True
    )
    language_code: Union[str, None] = Field(
        default=None, foreign_key="languages.code", primary_key=True
    )


class RegionBase(SQLModel):
    code: str = Field(max_length=3, primary_key=True)
    name: str = Field(max_length=9)


# Database model, database table inferred from class name
class Region(RegionBase, table=True):
    __tablename__ = "regions"

    countries: List["Country"] = Relationship(
        back_populates="region", cascade_delete=True
    )


class LanguageBase(SQLModel):
    code: str = Field(max_length=3, primary_key=True)
    name: str = Field(max_length=25)


class Language(LanguageBase, table=True):
    __tablename__ = "languages"

    countries: List["Country"] = Relationship(
        back_populates="languages", link_model=CountryLanguageLink
    )


class CountryBase(SQLModel):
    code: str = Field(max_length=2, primary_key=True)
    name: str = Field(max_length=50)
    population: int


class FavoriteCountryUpdate(SQLModel):
    is_favorite: bool


class Country(CountryBase, table=True):
    __tablename__ = "countries"

    region_code: str = Field(foreign_key="regions.code")
    region: Region = Relationship(back_populates="countries")
    languages: List["Language"] = Relationship(
        back_populates="countries", link_model=CountryLanguageLink
    )


class Hero(SQLModel, table=True):
    id: Union[int, None] = Field(default=None, primary_key=True)
    name: str
    secret_name: str
    age: Union[int, None] = None


# class Hero(SQLModel, table=True):
#     id: int = Field(default=None, primary_key=True)
#     name: str
#     secret_name: str
#     data: List[str] = Field(default_factory=list, sa_column=Column(ARRAY(Integer)))
#     age: int = Field(default=None, nullable=True)
#     is_love: bool


# class Base(DeclarativeBase):
#     pass


# class User(Base):
#     __tablename__ = "user_account"
#     id: Mapped[int] = mapped_column(primary_key=True)
#     name: Mapped[str] = mapped_column(String(30))
#     fullname: Mapped[Optional[str]]
#     addresses: Mapped[List["Address"]] = relationship(
#         back_populates="user", cascade="all, delete-orphan"
#     )

#     def __repr__(self) -> str:
#         return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"


# class Address(Base):
#     __tablename__ = "address"
#     id: Mapped[int] = mapped_column(primary_key=True)
#     email_address: Mapped[str]
#     data: Mapped[List[str]] = mapped_column(ARRAY(Integer))
#     user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))
#     user: Mapped["User"] = relationship(back_populates="addresses")

#     def __repr__(self) -> str:
#         return f"Address(id={self.id!r}, email_address={self.email_address!r})"


app = FastAPI()
admin_app = FastAPINimda(app=app, engine=engine)


class LanguageAdmin(ModelAdmin):
    # list_display = ["name", 'code']
    pass


class CountryAdmin(ModelAdmin):
    list_display = ["code", "name", "population", "region_code"]
    page_size = 50


class RegionAdmin(ModelAdmin):
    list_display = ["code", "name"]
    list_order_by = ["name"]


class HeroAdmin(ModelAdmin):
    pass


# class CountryLanguageLinkAdmin(ModelAdmin):
#     pass


# admin_app.register(CountryLanguageLink, CountryLanguageLinkAdmin)
admin_app.register(Region, RegionAdmin)
admin_app.register(Country, CountryAdmin)
admin_app.register(Language, LanguageAdmin)
admin_app.register(Hero, HeroAdmin)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    create_db_and_tables()
