# DTCG WebUI
Browser frontend for DTCG API.

## Installation

The easiest way:
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
