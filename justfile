start:
    uv run fastapi dev examples/sqlmodel_demo/main.py

start-sqlalchemy:
    uv run fastapi dev examples/sqlalchemy_demo/main.py

watch-css:
    npx @tailwindcss/cli -i ./fastapi_nimda/static/src/input.css -o ./fastapi_nimda/static/lib/output.css --watch

lint:
    env UV_CACHE_DIR=.uv-cache UV_TOOL_DIR=.uv-tools uvx mypy fastapi_nimda
    env UV_CACHE_DIR=.uv-cache UV_TOOL_DIR=.uv-tools uvx ruff check .
    env UV_CACHE_DIR=.uv-cache UV_TOOL_DIR=.uv-tools uvx ruff format . --check

test:
    uv run pytest
