# 🚀 CAD AI Editor - Launch Checklist

## ✅ Done (code is ready)
- [x] Full app built and tested (16 API routes)
- [x] Git repo initialized, committed, ready to push
- [x] Dockerfile for production deployment
- [x] Domain options researched

## 📋 Your action items (only you can do these)

### 1. Push to GitHub (~5 min)
```bash
# On your computer (or I can guide you):
gh auth login
gh repo create cad-ai-editor --public --source=~/workspace/cad-ai-app --push
```

### 2. Buy a domain (~$12/yr)
Potentially available (verified via RDAP 2026-10-16):
- **redlinerobot.com** — memorable, on-brand
- **airelinecad.com** — "AI redline CAD"
- **planrevise.com** — clear what it does

Buy at: Cloudflare Registrar (cheapest, no markup) or Namecheap

### 3. Create Stripe account (~15 min)
1. Go to stripe.com → Sign up
2. Complete business verification (EIN, bank account)
3. Dashboard → Products → Create two products:
   - **"10 Revisions"** — $29.00, one-time payment
   - **"Pro Monthly"** — $99.00/month, recurring subscription
4. Copy the Price IDs → set as env vars:
   - `STRIPE_PRICE_PAY_PER=price_...`
   - `STRIPE_PRICE_PRO=price_...`
5. Developers → API keys → copy Secret Key → `STRIPE_SECRET_KEY=sk_live_...`
6. Developers → Webhooks → Add endpoint: `https://yourdomain.com/api/webhook/stripe`
   → copy Signing Secret → `STRIPE_WEBHOOK_SECRET=whsec_...`

### 4. Deploy (~20 min)
**Easiest: Railway**
1. railway.app → sign up → New Project → Deploy from GitHub
2. Select your `cad-ai-editor` repo
3. Add env vars (from step 3 + your domain):
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`
   - `STRIPE_PRICE_PAY_PER`
   - `STRIPE_PRICE_PRO`
   - `APP_URL=https://yourdomain.com`
4. Railway gives you a URL → point your domain to it
5. Done!

### 5. ODA Converter in Docker (before launch)
The Dockerfile needs the ODA .deb added. Two options:
- **Easy**: Download ODAFileConverter .deb from opendesign.com, place in project root,
  uncomment the lines in Dockerfile
- **Alternative**: Contact ODA about redistribution licensing for commercial use

## 💰 Costs
| Item | Cost |
|------|------|
| Domain | ~$12/year |
| Railway hosting | $5/month |
| Stripe fees | 2.9% + $0.30 per transaction |
| **Total to launch** | **~$17 + Stripe fees** |

## ⚠️ Legal note
ODA File Converter is free for use but check their license terms for
redistribution in a commercial product. You may need to have users
download it themselves, or contact ODA for OEM licensing.
