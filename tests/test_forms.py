from __future__ import annotations

from fastapi_nimda.operation import OperationKind
from fastapi_nimda.forms import AdminForm
from fastapi_nimda.widgets import TextInput, Widget

from .conftest import Country, CountryAdmin, Hero, HeroAdmin


def test_form_renders_foreign_key_select(sa_engine):
    modeladmin = CountryAdmin(model=Country, engine=sa_engine)

    form_html = modeladmin.render_form(operation=OperationKind.ADD)

    assert 'name="region"' in form_html
    assert 'name="region_code"' not in form_html
    assert "<select" in form_html


def test_form_validation_maps_relationship_value_to_foreign_key(sa_engine):
    modeladmin = CountryAdmin(model=Country, engine=sa_engine)
    form = AdminForm(
        modeladmin=modeladmin,
        widgets=modeladmin.get_widgets(),
        engine=sa_engine,
        record=None,
        operation=OperationKind.ADD,
    )

    validated = form.validate_form(
        form_body={
            "code": "fr",
            "name": "France",
            "region": "eu",
        }
    )

    assert validated["region_code"] == "eu"
    assert validated["code"] == "fr"


def test_form_validation_coerces_integer_fields(sqlmodel_engine):
    from .conftest import TeamHero, TeamHeroAdmin

    modeladmin = TeamHeroAdmin(model=TeamHero, engine=sqlmodel_engine)
    form = AdminForm(
        modeladmin=modeladmin,
        widgets=modeladmin.get_widgets(),
        engine=sqlmodel_engine,
        record=None,
        operation=OperationKind.ADD,
    )

    validated = form.validate_form(
        form_body={
            "name": "Superman",
            "team_id": "1",
        }
    )

    assert validated["team_id"] == 1


def test_custom_widget_override_is_applied(sa_engine):
    class OverrideHeroAdmin(HeroAdmin):
        widgets = {"name": TextInput(attrs={"class": "custom-name-input"})}

    form_html = OverrideHeroAdmin(model=Hero, engine=sa_engine).render_form()

    assert "custom-name-input" in form_html


def test_boolean_field_checkbox_renders_with_visible_checkbox_classes(sa_engine):
    modeladmin = HeroAdmin(model=Hero, engine=sa_engine)

    add_form_html = modeladmin.render_form(operation=OperationKind.ADD)
    edit_form_html = modeladmin.render_form(
        operation=OperationKind.EDIT,
        record={
            "id": 1,
            "name": "Batman",
            "secret_name": "Bruce Wayne",
            "is_active": True,
        },
    )

    assert 'name="is_active"' in add_form_html
    assert 'class="h-4 w-4 rounded border border-gray-300 bg-white text-blue-600 focus:ring-2 focus:ring-blue-500"' in add_form_html
    assert 'name="is_active"' in edit_form_html
    assert "checked" in edit_form_html


def test_file_widget_is_rejected(sa_engine):
    class FileInputWidget(Widget):
        input_type = "file"
        template_name = "form/widgets/text.html"

    class InvalidHeroAdmin(HeroAdmin):
        widgets = {"name": FileInputWidget()}

    modeladmin = InvalidHeroAdmin(model=Hero, engine=sa_engine)

    try:
        modeladmin.get_form()
    except ValueError as exc:
        assert "file uploads are not supported yet" in str(exc)
    else:
        raise AssertionError("expected a file widget configuration error")
