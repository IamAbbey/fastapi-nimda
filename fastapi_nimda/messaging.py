from fastapi import Request
from typing import Any, Literal
from pydantic import BaseModel

from .errors import FastAPINimdaError


class TemplateMessage(BaseModel):
    kind: Literal["info", "success", "error"] = "info"
    message: str

    def color(self) -> str:
        if self.kind == "success":
            return "green"
        if self.kind == "error":
            return "red"
        return "blue"


def add_template_message(
    request: Request, message: TemplateMessage
) -> list[TemplateMessage]:
    messages = getattr(request.state, "messages", [])
    messages.append(message)
    request.state.messages = messages
    return messages


def add_template_message_context(request: Request) -> dict[str, Any]:
    return {"messages": getattr(request.state, "messages", [])}


def add_template_models_context(request: Request) -> dict[str, Any]:
    from .registry import build_model_admin

    registered: dict[str, Any] = getattr(request.app, "register_resource", {})
    resources = []
    broken_resources = []
    for identity, value in registered.items():
        try:
            modeladmin = build_model_admin(value, request.app.engine)
        except FastAPINimdaError as exc:
            broken_resources.append(
                {
                    "identity": identity,
                    "table_name": value.model.__name__,
                    "admin_class": value.modeladmin.__name__,
                    "error": str(exc),
                }
            )
            continue
        if not modeladmin.has_module_permission(request):
            continue
        resources.append(
            {
                "identity": identity,
                "table_name": value.model.__name__,
                "label": modeladmin.get_label(),
                "plural_label": modeladmin.get_plural_label(),
                "group": modeladmin.get_navigation_group(),
                "icon": modeladmin.get_navigation_icon(),
                "url": f"/admin/{identity}/list/",
            }
        )
    site = getattr(request.app, "site", None)
    return {
        "resources": resources,
        "broken_resources": broken_resources,
        "site_header": getattr(site, "site_header", "") or "fastapi-nimda",
        "site_title": getattr(site, "site_title", "") or "Admin",
        "index_title": getattr(site, "index_title", "") or "Site administration",
    }
