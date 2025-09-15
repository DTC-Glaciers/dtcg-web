# DTCG WebUI
Browser frontend for DTCG API.

## Installation

Clone this repository then navigate to its root folder:

```bash
git clone https://github.com/DTC-Glaciers/dtcg-web.git  # via http
git clone git@github.com:DTC-Glaciers/dtcg-web.git  # via SSH

cd dtcg-web
```

### Docker (recommended)

Build the docker image and run the container:

```bash
docker build -t dtcg_web_312 .
docker run -d --name dtcg_l2_dashboard -p 8000:8000 dtcg_web_312
```

The default port is set to 8000 in the Dockerfile, but this can be changed manually.

### Local environment

The easiest way to install locally is with pip:
```bash
pip install -e .[oggm]
```
This will also install a DTCG-compatible fork of OGGM and its dependencies.

For conda environments first install OGGM's dependencies, and then run:
```bash
conda install -f requirements.yml
```

Once installed, navigate to ``src/dtcgweb`` and run:
```bash
fastapi dev main.py --reload
uvicorn main::app --reload  # if you prefer
```

## View the dashboard

Open your browser to [http://127.0.0.1:8000/app](http://127.0.0.1:8000/app).
If you changed the port number (e.g. in the Dockerfile), then point the URL to that port instead.
