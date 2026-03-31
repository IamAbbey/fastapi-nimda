from __future__ import annotations

from fastapi_nimda.operation import OperationKind
from fastapi_nimda.forms import AdminForm
from fastapi_nimda.widgets import TextInput, Widget

from .conftest import Country, CountryAdmin, Hero, HeroAdmin


def test_form_renders_foreign_key_select(sa_engine):
    modeladmin = CountryAdmin(model=Country, engine=sa_engine)

    form_html = modeladmin.render_form(operation=OperationKind.ADD)

    assert 'name="region"' in form_html
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
            "region_code": "eu",
            "region": "eu",
        }
    )

    assert validated["region_code"] == "eu"
    assert validated["code"] == "fr"


def test_custom_widget_override_is_applied(sa_engine):
    class OverrideHeroAdmin(HeroAdmin):
        widgets = {"name": TextInput(attrs={"class": "custom-name-input"})}

    form_html = OverrideHeroAdmin(model=Hero, engine=sa_engine).render_form()

    assert "custom-name-input" in form_html


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
