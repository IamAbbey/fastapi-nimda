start:
    uv run fastapi dev examples/sqlmodel_demo/main.py

start-sqlalchemy:
    uv run fastapi dev examples/sqlalchemy_demo/main.py

watch-css:
    npx @tailwindcss/cli -i ./fastapi_nimda/static/src/input.css -o ./fastapi_nimda/static/dist/output.css --watch

lint:
    uvx mypy .
    uvx ruff check .
    uvx ruff format . --check
