# Codette Widget Embed Code for horizoncorelabs.studio

## Option 1: Direct iframe Embed (Recommended)

Add this to your horizoncorelabs.studio page HTML:

```html
<!-- Codette Widget Embed -->
<iframe
  src="https://huggingface.co/spaces/Raiff1982/codette-ai"
  style="width: 100%; max-width: 740px; height: 640px; border: none; border-radius: 20px; margin: 20px auto; display: block;"
  title="Codette AI"
  allow="microphone; camera"
></iframe>
```

This embeds the full HF Space widget directly.

---

## Option 2: Full Page Redirect

If you want `/horizoncoreai/` to show the Codette widget, redirect to the HF Space:

```nginx
# In your nginx config (if applicable):
location /horizoncoreai/ {
  return 301 https://huggingface.co/spaces/Raiff1982/codette-ai;
}
```

Or in your web server config (Apache, etc.):

```apache
Redirect /horizoncoreai/ https://huggingface.co/spaces/Raiff1982/codette-ai
```

---

## Option 3: Proxy Setup

If you want to serve from your own domain (`/horizoncoreai/`), set up a reverse proxy:

**Nginx:**
```nginx
location /horizoncoreai/ {
  proxy_pass https://huggingface.co/spaces/Raiff1982/codette-ai/;
  proxy_set_header Host huggingface.co;
  proxy_set_header X-Forwarded-For $remote_addr;
  proxy_set_header X-Forwarded-Proto https;
}
```

**Apache:**
```apache
ProxyPreserveHost On
ProxyPass /horizoncoreai/ https://huggingface.co/spaces/Raiff1982/codette-ai/
ProxyPassReverse /horizoncoreai/ https://huggingface.co/spaces/Raiff1982/codette-ai/
```

---

## Option 4: Custom Widget Host (If You Hosted index.html Before)

If you want to serve the widget from your own domain while hitting the HF Space API:

1. Host the `index.html` on horizoncorelabs.studio at `/horizoncoreai/`
2. Update the API endpoint in index.html to point to HF Space:

```javascript
// In index.html, change this line:
const apiBase = "/api/chat";

// To:
const apiBase = "https://huggingface.co/spaces/Raiff1982/codette-ai/api/chat";
```

---

## Direct HF Space URL

If none of the above work, users can access Codette directly at:

```
https://huggingface.co/spaces/Raiff1982/codette-ai
```

---

## Testing

To verify it's working, test the API endpoint:

```bash
curl -X POST https://huggingface.co/spaces/Raiff1982/codette-ai/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello Codette"}
    ]
  }'
```

Should return a streaming JSON response starting with metadata.
