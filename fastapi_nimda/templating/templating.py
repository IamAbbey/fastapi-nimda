from starlette.templating import Jinja2Templates

from .filter import pretty_name
from ..constants import BASE_DIR

from ..messaging import add_template_message_context, add_template_models_context

templates = Jinja2Templates(
    directory=BASE_DIR / "templates",
    context_processors=[add_template_message_context, add_template_models_context],
)
templates.env.filters["pretty_name"] = pretty_name
