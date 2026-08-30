#!/bin/bash
export SIW_API_BASE="https://show-its-work.vercel.app/api/proxy"
export SIW_API_KEY="dummy-key"
export PYTHONPATH=src
uvicorn web.api:app --port 8533
