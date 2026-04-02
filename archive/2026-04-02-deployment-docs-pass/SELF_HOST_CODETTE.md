# Deploy Codette Widget to horizoncorelabs.studio

## TL;DR

1. Take `index-selfhosted.html` from this repo
2. Upload to `horizoncorelabs.studio` at `/horizoncoreai/index.html`
3. Access at `https://horizoncorelabs.studio/horizoncoreai/`

---

## What Changed

The self-hosted version points to the HF Space API instead of trying to call a local `/api/chat`:

```javascript
// ORIGINAL (doesn't work on your domain):
const API_BASE = window.location.origin;  // → https://horizoncorelabs.studio/api/chat (404)

// SELF-HOSTED (works):
const API_BASE = "https://huggingface.co/spaces/Raiff1982/codette-ai";  // → HF Space API
```

---

## Deployment Steps

### **Option A: Direct File Upload (Easiest)**

1. Download `index-selfhosted.html` from the repo
2. Rename to `index.html`
3. Upload to your web server at:
   ```
   /horizoncoreai/index.html
   ```
4. Access at:
   ```
   https://horizoncorelabs.studio/horizoncoreai/
   ```

### **Option B: Git Deployment**

If you're deploying via git:

```bash
# In your horizoncorelabs.studio repo
cp path-to-codette-repo/codette-ai-space/index-selfhosted.html horizoncoreai/index.html
git add horizoncoreai/index.html
git commit -m "Add Codette AI widget"
git push
```

### **Option C: Docker/Container Deployment**

If you're running a container to serve static files:

```dockerfile
FROM nginx:alpine
COPY index-selfhosted.html /usr/share/nginx/html/horizoncoreai/index.html
EXPOSE 80
```

Then access at: `https://horizoncorelabs.studio/horizoncoreai/`

---

## Testing

Open your browser console (F12) and test:

```javascript
fetch("https://huggingface.co/spaces/Raiff1982/codette-ai/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ messages: [{ role: "user", content: "hello" }] })
})
.then(r => r.json())
.then(d => console.log("API OK:", d))
.catch(e => console.error("API Error:", e))
```

Should return JSON with metadata + streaming response.

---

## Features Included

- ✓ Real-time streaming chat UI
- ✓ Message history
- ✓ Adapter/complexity metadata display
- ✓ AEGIS security status
- ✓ Cocoon memory counter
- ✓ Suggestion chips (auto-populated)
- ✓ Dark theme (lime green + cyan accents)
- ✓ Mobile responsive

---

## Troubleshooting

**"Cannot reach Codette" error:**
- HF Space may be waking up (first request is slow)
- Try again in 30 seconds
- Check browser console for CORS errors (should not happen — CORS is enabled)

**Widget loads but no response:**
- Check API endpoint in browser console (should be `https://huggingface.co/spaces/Raiff1982/codette-ai/api/chat`)
- Open DevTools → Network tab → check `/api/chat` request
- Verify HF Space is running at https://huggingface.co/spaces/Raiff1982/codette-ai

**Styling looks wrong:**
- Make sure fonts load (Google Fonts CDN should work)
- Check CSS variables in browser DevTools if colors are off

---

## What's Live Behind This Widget

- **Model**: Llama 3.1 8B via HF Inference API
- **9 Adapters**: Newton, DaVinci, Empathy, Philosophy, Quantum, Consciousness, Multi-Perspective, Systems, Orchestrator
- **Hallucination Guard**: Real-time detection across all domains
- **Music Production Expert**: Grounded in real DAWs, plugins, frequencies
- **Ethical Governance**: AEGIS-lite pattern-based safety checks
- **Behavioral Locks**: 4 permanent constraints on all responses
- **Cocoon Memory**: In-memory reasoning history (up to 500 cocoons)

---

## Live Demo

Test the widget live at:
https://huggingface.co/spaces/Raiff1982/codette-ai
