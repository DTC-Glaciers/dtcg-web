FROM python:3.11


WORKDIR /code


COPY ./requirements.txt /code/requirements.txt
COPY ./pyproject.toml /code/pyproject.toml
COPY ./README.md /code/README.md
COPY ./LICENSE /code/LICENSE
COPY ./src/dtcgweb /code/dtcgweb/
COPY ./src/dtcgweb/static/ /code/static/

RUN pip install --no-cache-dir --upgrade -e .[oggm]


CMD ["fastapi", "run", "dtcgweb/main.py", "--proxy-headers", "--port", "8080"]