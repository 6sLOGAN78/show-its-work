# `web/` - Web Server & Frontend UI

This directory contains the FastAPI server and the static frontend for the application.

## Structure
- `api.py`: A lightweight FastAPI wrapper around the core intelligence engine. It routes `POST /api/investigate` calls to the engine and serves static files.
- `static/`: Contains the HTML, CSS, and Vanilla JavaScript (`app.js`) for the interactive user interface. This is what renders the insights, the LLM memo, and the evidence/hypothesis graphs.
