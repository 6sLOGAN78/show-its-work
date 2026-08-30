# `gemini-proxy/` - (Deprecated) Node.js Proxy

**Note: This directory is deprecated.**
Initially, this project required a separate Node.js server to act as a secure proxy for the Gemini API. 

However, since the main Python FastAPI backend is now securely deployed on Vercel (see `vercel.json`), the Python backend communicates directly with the Gemini API. This `gemini-proxy` folder is kept for historical reference but is no longer needed to run the application.
