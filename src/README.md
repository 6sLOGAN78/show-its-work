# `src/show_its_work/` - Core Engine

This directory contains the Python backend logic and core Intelligence Engine for the "Show Its Work" application.

## Structure
- `agents/`: Contains the specific persona agents, such as the `narrative.py` agent which generates the LLM-powered causal memos, and the `skeptic.py` agent which tries to disprove hypotheses before they reach the user.
- `llm/`: Contains the `client.py` wrapper which communicates with the Gemini API (via the OpenAI-compatible endpoint).
- `engine.py`: The orchestrator that coordinates hypothesis generation, metric evaluation, telemetry, and final memo generation.
- `telemetry.py` / `memory.py`: Tracks causal telemetry, LLM token costs, latency, and episodic memory of the queries evaluated.
