start:
    uv run fastapi dev main.py

watch-css:
    cd fastapi_nimda && npx @tailwindcss/cli -i ./static/src/input.css -o ./static/dist/output.css --watch