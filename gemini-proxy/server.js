require('dotenv').config();
const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
// Fallback to node-fetch if global fetch is unavailable (Node < 18)
const fetch = global.fetch || require('node-fetch');

const app = express();

// Allow the local CLI / web UI (and a deployed frontend) to call this proxy.
app.use(cors());
app.use(express.json({ limit: '1mb' }));
app.use((err, req, res, next) => {
  if (err instanceof SyntaxError && err.status === 400 && 'body' in err) {
    return res.status(400).json({ error: 'Malformed JSON payload.' });
  }
  next();
});

// Trust the Vercel reverse proxy so rate limiting sees the real client IP.
app.set('trust proxy', 1);

// Abuse guard: cap requests per IP.
const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 60 * 60 * 1000,
  max: parseInt(process.env.RATE_LIMIT_MAX) || 20,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests, please try again later.' }
});
app.use(limiter);

// OPTIONAL shared-secret gate. If PROXY_ACCESS_KEY is set, callers must send it as the
// Bearer token; if it is NOT set, the proxy stays open (zero-config demo mode). Set it
// before exposing a public deployment so only your app can spend your Gemini quota.
const ACCESS_KEY = process.env.PROXY_ACCESS_KEY;
function requireAccess(req, res, next) {
  if (!ACCESS_KEY) return next();
  const token = (req.headers.authorization || '').replace(/^Bearer\s+/i, '');
  if (token !== ACCESS_KEY) return res.status(401).json({ error: 'Invalid proxy access key.' });
  next();
}

// Health check — also reports whether the upstream key is configured (never the key itself).
app.get('/health', (req, res) =>
  res.status(200).json({ status: 'ok', gemini_key_configured: !!process.env.GEMINI_API_KEY }));

// OpenAI-compatible endpoint: forwards to Gemini's OpenAI-compat surface, injecting the
// server-side key so clients never need one.
app.post('/v1/chat/completions', requireAccess, async (req, res) => {
  const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
  if (!GEMINI_API_KEY) {
    console.error('CRITICAL: GEMINI_API_KEY is not set in the environment.');
    return res.status(500).json({ error: 'Server misconfiguration: upstream API key missing.' });
  }

  const upstreamUrl = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions';
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), parseInt(process.env.UPSTREAM_TIMEOUT_MS) || 30000);
  try {
    const upstream = await fetch(upstreamUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${GEMINI_API_KEY}` },
      body: JSON.stringify(req.body),
      signal: controller.signal
    });
    const data = await upstream.json();
    return res.status(upstream.status).json(data);
  } catch (error) {
    if (error.name === 'AbortError') {
      return res.status(504).json({ error: 'Upstream timed out.' });
    }
    console.error('Proxy error:', error.message);
    return res.status(502).json({ error: 'Bad gateway fetching from Gemini.' });
  } finally {
    clearTimeout(timeout);
  }
});

// Export for Vercel serverless.
module.exports = app;

// Only listen when run directly (not when imported by Vercel).
if (require.main === module) {
  const PORT = process.env.PORT || 3000;
  app.listen(PORT, () => console.log(`Gemini proxy running locally on port ${PORT}`));
}
