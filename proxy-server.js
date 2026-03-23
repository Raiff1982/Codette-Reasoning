/**
 * Reverse Proxy for Codette HF Space
 * Strips X-Frame-Options header to allow embedding
 * Deploy to Railway.app or Fly.io for free
 */

const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.json({ limit: '10mb' }));

const HF_SPACE_URL = 'https://huggingface.co/spaces/Raiff1982/codette-ai';

// Proxy all requests to HF Space, strip X-Frame-Options
app.all('*', async (req, res) => {
  try {
    const targetUrl = HF_SPACE_URL + req.originalUrl;

    const response = await axios({
      method: req.method,
      url: targetUrl,
      headers: {
        ...req.headers,
        host: 'huggingface.co',
      },
      data: req.body,
      validateStatus: () => true, // Accept all status codes
      responseType: 'stream',
      maxRedirects: 5,
    });

    // Copy response headers, but remove X-Frame-Options
    Object.entries(response.headers).forEach(([key, value]) => {
      if (key.toLowerCase() !== 'x-frame-options') {
        res.setHeader(key, value);
      }
    });

    // Add CORS headers for safety
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    res.status(response.status);
    response.data.pipe(res);
  } catch (err) {
    console.error('Proxy error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Proxy running on port ${PORT}`));
