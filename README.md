# DTCG WebUI
Browser frontend for DTCG API.

## Installation

### Docker (recommended)

Build the docker image and run the container:

```
docker build -t dtcg_web_312
docker run -d --name dtcg_l2_dashboard -p 8000:8000 dtcg_web_312
```

The default port is set to 8000 in the Dockerfile, but this can be changed manually.

### Local environment

The easiest way is to install via :
```
pip install -e .[oggm]
```
This will also install a DTCG-compatible fork of OGGM and its dependencies.

For conda environments first install OGGM's dependencies, and then run:
```
conda install -f requirements.yml
```

## Run locally

Once installed, navigate to ``src/dtcgweb`` and run:
```
fastapi dev main.py --reload
uvicorn main::app --reload  # if you prefer
```

## View the dashboard

Open your browser to [http://127.0.0.1:8000/app](http://127.0.0.1:8000/app).
If you changed the port number (e.g. in the Dockerfile), then point the URL to that port instead.