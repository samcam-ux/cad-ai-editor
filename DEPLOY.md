# CAD AI Editor - Deployment Guide

## Option A: Railway (easiest, ~$5/mo)
1. Push this folder to GitHub
2. Go to railway.app → New Project → Deploy from GitHub
3. Add env vars: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `APP_URL`
4. Railway auto-detects Dockerfile and deploys
5. Done — you get a public URL

## Option B: DigitalOcean Droplet ($6/mo)
```bash
# On a fresh Ubuntu 22.04 droplet:
git clone <your-repo>
cd cad-ai-app
docker build -t cad-ai-editor .
docker run -d -p 80:8099 \
  -e STRIPE_SECRET_KEY=sk_live_... \
  -e STRIPE_WEBHOOK_SECRET=whsec_... \
  -e APP_URL=https://yourdomain.com \
  --restart always \
  cad-ai-editor
```

## Option C: Hetzner ($4/mo)
Same as DigitalOcean — cheaper.

## Before going live:
- [ ] Get ODA File Converter .deb and add to Dockerfile
- [ ] Create Stripe products matching PLANS in auth.py
  - "10 Revisions" — $29 one-time → Price ID → STRIPE_PRICE_PAY_PER
  - "Pro Monthly" — $99/month → Price ID → STRIPE_PRICE_PRO
- [ ] Set Stripe webhook URL to https://yourdomain.com/api/webhook/stripe
- [ ] Add domain + SSL (Railway does this automatically)
- [ ] Replace SQLite with PostgreSQL for production (Railway/DigitalOcean offer managed DBs)

## Pricing suggestion
- Free: 3 revisions (trial)
- Pay-per: $29 for 10 revisions
- Pro: $99/month unlimited

## Costs to run
- Hosting: $4-6/month
- Stripe: 2.9% + $0.30 per transaction
- Domain: ~$12/year
