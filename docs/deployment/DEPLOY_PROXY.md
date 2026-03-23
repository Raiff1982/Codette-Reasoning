# Deploy Codette Proxy to Railway (FREE)

## Why You Need This

HuggingFace blocks iframe embedding with `X-Frame-Options: deny`. This proxy server:
- ✅ Strips the blocking header
- ✅ Relays requests to HF Space
- ✅ Allows iframe embedding on horizoncorelabs.studio

---

## Step 1: Deploy to Railway (2 minutes)

1. Go to **https://railway.app** and sign up (with GitHub)
2. Click **"Create New Project"** → **"Deploy from GitHub Repo"**
3. Connect your `codette-clean` repo (or this branch)
4. Railway auto-detects `package.json` and deploys

**Your proxy URL will look like:**
```
https://codette-proxy-xxxxxx.railway.app
```

(Railway generates a random subdomain)

---

## Step 2: Update horizoncorelabs.studio Embed

Replace your embed code with:

```html
<iframe
  src="https://YOUR-RAILWAY-URL/spaces/Raiff1982/codette-ai"
  style="width: 100%; max-width: 740px; height: 640px; border: none; border-radius: 20px; margin: 20px auto; display: block;"
  title="Codette AI"
></iframe>
```

Replace `YOUR-RAILWAY-URL` with your actual Railway domain (without `https://`).

---

## Step 3: Test

1. Reload horizoncorelabs.studio
2. Codette widget should now load in the iframe
3. Test sending a message

---

## Alternative: Fly.io (Also Free)

If Railway doesn't work:

1. Install Fly CLI: `npm install -g @fly/cli`
2. In `codette-clean` folder: `fly launch`
3. `fly deploy`
4. Get your URL: `fly status`

Update the embed code with your Fly URL.

---

## How the Proxy Works

```
horizoncorelabs.studio
  ↓ (iframe request)
Railway Proxy (YOUR-RAILWAY-URL)
  ↓ (proxies request, strips X-Frame-Options)
HuggingFace Space (HF_SPACE_URL)
  ↓ (returns response without blocking header)
horizoncorelabs.studio
  ↓ (iframe renders successfully)
```

---

## If You Need a Custom Domain

You can add a custom domain to Railway:

1. In Railway dashboard, go to **Settings** → **Domains**
2. Add `api.horizoncorelabs.studio` or similar
3. Update your embed code to use that domain

Then horizoncorelabs.studio will proxy through its own subdomain instead of Railway's.

---

## Next Steps

1. Deploy to Railway (takes ~60 seconds)
2. Copy your Railway URL
3. Update embed code on Squarespace
4. Reload and test

Let me know when you've deployed!
