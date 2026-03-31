"""Public package surface for fastapi-nimda."""

from .admin import ModelAdmin
from .app import FastAPINimda

Admin = FastAPINimda
__version__ = "0.1.0"

__all__ = ["FastAPINimda", "Admin", "ModelAdmin", "__version__"]
