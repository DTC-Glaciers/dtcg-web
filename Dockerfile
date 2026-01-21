FROM python:3.12
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# COPY --from=ghcr.io/astral-sh/uv:python3.12-trixie-slim /uv /uvx /bin/

ENV UV_NO_DEV=1
WORKDIR /app/


COPY ./requirements.txt /app/requirements.txt
COPY ./pyproject.toml /app/pyproject.toml
COPY ./README.md /app/README.md
COPY ./LICENSE /app/LICENSE
COPY ./src/dtcgweb /app/dtcgweb/
COPY ./src/dtcgweb/static/ /app/static/

RUN uv sync --no-dev --group oggm
# RUN uv pip install --upgrade -e .[oggm]

WORKDIR /app/dtcgweb/
CMD ["/app/.venv/bin/fastapi", "run", "app.py", "--port", "8080"]

# CMD ["fastapi", "run", "app.py", "--proxy-headers", "--port", "8080"]
# CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--port", "80", "--host", "0.0.0.0"]