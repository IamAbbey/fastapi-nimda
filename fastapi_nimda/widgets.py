from __future__ import annotations

from typing import Any

from .templating.templating import templates
import copy


class Widget:
    is_required = False
    label_template_name = "form/widgets/label.html"
    input_type: str | None = None
    template_name: str = ""

    def __init__(self, attrs: dict[str, Any] | None = None):
        self.attrs = {} if attrs is None else attrs.copy()

    @property
    def is_hidden(self):
        return self.input_type == "hidden" if hasattr(self, "input_type") else False

    def render(self, name, value, attrs=None):
        """Render the widget as an HTML string."""
        context = self.get_context(name, value, attrs)
        return self._render(self.template_name, context)

    def render_label(self, name, value, attrs=None):
        """Render the widget label as an HTML string."""
        context = self.get_context(name, value, attrs)
        return self._render(self.label_template_name, context)

    def _render(self, template_name, context):
        return templates.get_template(template_name).render(context)

    def format_value(self, value):
        """
        Return a value as it should appear when rendered in a template.
        """
        if value == "" or value is None:
            return None
        return str(value)

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Build an attribute dictionary."""
        return {**base_attrs, **(extra_attrs or {})}

    def get_context(self, name, value, attrs):
        return {
            "widget": {
                "name": name,
                "is_hidden": self.is_hidden,
                "required": self.is_required,
                "value": self.format_value(value),
                "attrs": self.build_attrs(self.attrs, attrs),
                "template_name": self.template_name,
            },
        }


class Input(Widget):
    """
    Base class for all <input> widgets.
    """

    input_type: str | None = None  # Subclasses must define this.
    template_name = "form/widgets/input.html"
    css_style = "block w-full p-2 text-gray-900 border border-gray-300 rounded-lg bg-gray-50 text-base focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"

    def __init__(self, attrs: dict[str, Any] | None = None):
        if attrs is not None:
            attrs = attrs.copy()
            self.input_type = attrs.pop("type", self.input_type)
            attrs["class"] = attrs.get("class", self.css_style)
        super().__init__(attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["type"] = self.input_type
        context["widget"]["label_template_name"] = (self.label_template_name,)
        return context


class TextInput(Input):
    input_type = "text"
    template_name = "form/widgets/text.html"


class NumberInput(Input):
    input_type = "number"
    template_name = "form/widgets/text.html"


def boolean_check(v):
    return not (v is False or v is None or v == "")


class CheckboxInput(Input):
    input_type = "checkbox"
    template_name = "form/widgets/text.html"
    css_style = "w-4 h-4 border border-gray-300 rounded-sm bg-gray-50 focus:ring-3 focus:ring-blue-300 dark:bg-gray-700 dark:border-gray-600 dark:focus:ring-blue-600 dark:ring-offset-gray-800 dark:focus:ring-offset-gray-800"

    def __init__(self, attrs=None, check_test=None):
        super().__init__(attrs)
        # check_test is a callable that takes a value and returns True
        # if the checkbox should be checked for that value.
        self.check_test = boolean_check if check_test is None else check_test

    def format_value(self, value):
        """Only return the 'value' attribute if value isn't empty."""
        if value is True or value is False or value is None or value == "":
            return
        return str(value)

    def get_context(self, name, value, attrs):
        if self.check_test(value):
            attrs = {**(attrs or {}), "checked": True}
        return super().get_context(name, value, attrs)

    def value_from_datadict(self, data, files, name):
        if name not in data:
            # A missing value means False because HTML form submission does not
            # send results for unselected checkboxes.
            return False
        value = data.get(name)
        # Translate true and false strings to boolean values.
        values = {"true": True, "false": False}
        if isinstance(value, str):
            value = values.get(value.lower(), value)
        return bool(value)

    def value_omitted_from_data(self, data, files, name):
        # HTML checkboxes don't appear in POST data if not checked, so it's
        # never known if the value is actually omitted.
        return False


class ChoiceWidget(Widget):
    allow_multiple_selected = False
    input_type: str | None = None
    template_name: str = ""
    option_template_name: str | None = None
    add_id_index = True
    checked_attribute = {"checked": True}
    option_inherits_attrs = True
    css_style = "w-full text-base text-gray-900 border border-gray-300 rounded-lg bg-gray-50 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"

    def __init__(
        self,
        attrs: dict[str, Any] | None = None,
        choices: tuple[Any, ...] | list[Any] = (),
    ):
        if attrs is not None:
            attrs = attrs.copy()
            attrs["class"] = attrs.get("class", self.css_style)
        super().__init__(attrs)
        self.choices = choices

    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        obj.attrs = self.attrs.copy()
        obj.choices = copy.copy(self.choices)
        memo[id(self)] = obj
        return obj

    def options(self, name, value, attrs=None):
        """Yield a flat list of options for this widget."""
        for group in self.opt(name, value, attrs):
            yield from group[1]

    def opt(self, name, value, attrs=None):
        """Return a list of options for this widget."""
        options = []
        has_selected = False
        for index, (option_value, option_label) in enumerate(self.choices):
            if option_value is None:
                option_value = ""

            choices = [(option_value, option_label)]

            for _value, _label in choices:
                selected = (not has_selected or self.allow_multiple_selected) and str(
                    _value
                ) in value
                has_selected |= selected
                options.append(
                    self.create_option(
                        name,
                        _value,
                        _label,
                        selected,
                        index,
                        attrs=attrs,
                    )
                )
        return options

    def create_option(self, name, value, label, selected, index, attrs=None):
        index = str(index)
        option_attrs = (
            self.build_attrs(self.attrs, attrs) if self.option_inherits_attrs else {}
        )
        if selected:
            option_attrs.update(self.checked_attribute)
        if "id" in option_attrs:
            option_attrs["id"] = self.id_for_label(option_attrs["id"], index)
        return {
            "name": name,
            "value": value,
            "label": label,
            "selected": selected,
            "index": index,
            "attrs": option_attrs,
            "type": self.input_type,
            "template_name": self.option_template_name,
            "wrap_label": True,
        }

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["options"] = self.opt(name, context["widget"]["value"], attrs)
        return context

    def id_for_label(self, id_, index="0"):
        """
        Use an incremented id for each option where the main widget
        references the zero index.
        """
        if id_ and self.add_id_index:
            id_ = "%s_%s" % (id_, index)
        return id_

    def value_from_datadict(self, data, files, name):
        getter = data.get
        if self.allow_multiple_selected:
            try:
                getter = data.getlist
            except AttributeError:
                pass
        return getter(name)

    def format_value(self, value):
        """Return selected values as a list."""
        if value is None and self.allow_multiple_selected:
            return []
        if not isinstance(value, (tuple, list)):
            value = [value]
        return [str(v) if v is not None else "" for v in value]

    @property
    def choices(self):
        return self._choices

    @choices.setter
    def choices(self, value):
        self._choices = value


class Select(ChoiceWidget):
    input_type = "select"
    template_name = "form/widgets/select.html"
    option_template_name = "form/widgets/select_option.html"
    add_id_index = False
    checked_attribute = {"selected": True}
    option_inherits_attrs = False

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.allow_multiple_selected:
            context["widget"]["attrs"]["multiple"] = True
        return context

    def format_value(self, value):
        if value is None:
            return []
        if isinstance(value, (tuple, list)):
            return [str(v) if v is not None else "" for v in value]
        return [str(value)]

    @staticmethod
    def _choice_has_empty_value(choice):
        """Return True if the choice's value is empty string or None."""
        value, _ = choice
        return value is None or value == ""

    def use_required_attribute(self, initial):
        """
        Don't render 'required' if the first <option> has a value, as that's
        invalid HTML.
        """
        use_required_attribute = super().use_required_attribute(initial)
        # 'required' is always okay for <select multiple>.
        if self.allow_multiple_selected:
            return use_required_attribute

        first_choice = next(iter(self.choices), None)
        return (
            use_required_attribute
            and first_choice is not None
            and self._choice_has_empty_value(first_choice)
        )


class SelectMultiple(Select):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        try:
            getter = data.getlist
        except AttributeError:
            getter = data.get
        return getter(name)

    def value_omitted_from_data(self, data, files, name):
        # An unselected <select multiple> doesn't appear in POST data, so it's
        # never known if the value is actually omitted.
        return False
