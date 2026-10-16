# CAD AI Editor - Sellable App MVP

## What it does
Upload a DWG → AI converts to DXF → apply AI-generated CAD edits from redline markups → download revised file.

## Architecture
- **Backend**: FastAPI (Python) - DWG→DXF conversion, ezdxf editing engine
- **Frontend**: Mobile-friendly web app (no app store needed, runs in browser)
- **AI Engine**: Redline markup interpretation → CAD edit instructions

## Project Structure
```
cad-ai-app/
├── backend/
│   ├── main.py          # FastAPI app
│   ├── converter.py     # DWG→DXF via ODA
│   ├── editor.py        # ezdxf edit engine
│   ├── redline.py       # PDF markup → edit instructions
│   └── requirements.txt
├── frontend/
│   └── index.html       # Mobile web UI
├── uploads/             # User uploads
└── outputs/             # Processed files
```

## API Endpoints (planned)
- POST /upload - upload DWG + redline PDF
- GET /layouts/{job_id} - list layouts in file
- POST /analyze - AI reads redlines, returns proposed edits
- POST /apply - apply approved edits, return revised DXF
- GET /download/{job_id} - download result

## MVP Status (2026-10-16)
✅ WORKING:
- FastAPI backend (upload, list layouts, apply edits, download)
- Mobile-friendly web frontend (no app store needed)
- ezdxf editing engine (add text/lines, mask areas, delete sheets)
- End-to-end tested: upload DXF → list 15 layouts → apply edits → download

⚠️ NEEDS BEFORE SELLING:
- DWG→DXF conversion on server (currently manual via ODA)
- User auth + payments (Stripe)
- Redline PDF → auto-edit AI (currently manual edit specification)
- Production hosting (needs a server, not localhost)
- Error handling, file size limits, job cleanup

## To run locally
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8099
# Open http://localhost:8099 in browser
```

## Redline AI Update (2026-10-16)
✅ NEW - `backend/redline.py`:
- Extracts PDF annotations (FreeText, Line, Polygon, etc.) with positions
- Maps redline pages → CAD layouts
- Interprets markups into edit instructions:
  - "remove this plan/sheet" → delete_layout (high confidence)
  - "SEE STRUC" / "REFER TO STRUC" → add_text callout (high confidence)
  - "let's discuss" / "where is" → flag for human (not auto-applied)
  - "remove the addition" → flag for human (needs drafter judgment)
  - Cross-out lines → mask_area (medium confidence)
- Tested on Pabaraju redlines: 47 markups → 18 proposed edits + 3 human flags

✅ NEW - `POST /api/analyze/{job_id}` endpoint
✅ NEW - Frontend: redline upload → AI analysis → approve individual edits or bulk-approve high-confidence

## How the AI works
1. User uploads DWG/DXF + redline PDF
2. AI extracts all reviewer annotations with positions
3. AI proposes CAD edits with confidence levels
4. User approves edits (individually or bulk)
5. Approved edits applied → download revised DXF

## Production Update (2026-10-16)
✅ DWG AUTO-CONVERSION (`backend/converter.py`):
- Upload endpoint now auto-converts DWG→DXF via ODA File Converter
- Runs headless via xvfb, outputs ACAD2018 DXF
- Falls back gracefully with clear error if ODA not installed

✅ USER ACCOUNTS + STRIPE (`backend/auth.py`, `backend/billing.py`):
- Register/login with session tokens (SQLite, 3 free credits)
- Credit system: 1 credit per revision, pro/unlimited bypass
- Stripe Checkout for upgrades ($29/10 revisions, $99/mo pro)
- Webhook handler auto-upgrades plan + adds credits on payment
- Plans defined in auth.py PLANS dict

✅ HOSTING (`Dockerfile`, `DEPLOY.md`):
- Production Docker image (Ubuntu 22.04 + Python + Qt + xvfb + gunicorn)
- Deploy guides for Railway ($5/mo), DigitalOcean ($6/mo), Hetzner ($4/mo)
- Pre-launch checklist: ODA .deb, Stripe products, webhook URL, SSL, PostgreSQL

## API routes (16 total)
- POST /api/register, POST /api/login, GET /api/me
- POST /api/checkout/{plan}, POST /api/webhook/stripe
- POST /api/upload (auto-converts DWG), GET /api/layouts/{job_id}
- POST /api/analyze/{job_id} (redline AI), POST /api/apply (uses 1 credit)
- GET /api/download/{job_id}, GET /api/health

## Upwork Integration (2026-10-16)
✅ NEW - `backend/upwork.py` + 4 API endpoints + frontend tab

**Why browser automation**: Upwork has no public API for freelancers to
search/apply to jobs. All Upwork actions go through controlled browser
sessions with user approval per action.

**Workflow**:
1. **Find jobs** → `POST /api/upwork/search-task` generates a browser task
   → run in logged-in Upwork session → returns job listings as JSON
2. **Apply** → `POST /api/upwork/proposal` generates tailored cover letter
   + browser task to submit → user reviews → approves → submitted
3. **Get markups** → `POST /api/upwork/download-task/{contract_id}` generates
   browser task → downloads attachments from contract messages
   → feed into `/api/analyze` for AI redline processing
4. **Deliver** → `POST /api/upwork/send-deliverable` generates browser task
   → uploads revised DXF + sends approval message to client

**Full loop**: Upwork job → download markups → AI edits CAD → send back
for client approval — all from the app.
