from fastapi import Request
from typing import Any, Literal, List, Dict
from pydantic import BaseModel, computed_field


class TemplateMessage(BaseModel):
    kind: Literal["info", "success", "error"] = "info"
    message: str

    @computed_field
    @property
    def color(self) -> str:
        if self.kind == "success":
            return "green"
        elif self.kind == "error":
            return "red"
        else:
            return "blue"


def add_template_message(
    request: Request, message: TemplateMessage
) -> List[TemplateMessage]:
    messages = getattr(request.state, "messages", [])
    messages.append(message)
    request.state.messages = messages


def add_template_message_context(request: Request) -> Dict[str, Any]:
    return {"messages": getattr(request.state, "messages", [])}


def add_template_models_context(request: Request) -> Dict[str, Any]:
    _registered: Dict[str, Any] = getattr(request.app, "_registered", {})
    resources = []
    for identity, value in _registered.items():
        resources.append(
            {
                "identity": identity,
                "table_name": value.model.__name__,
            }
        )
    return {"resources": resources}
