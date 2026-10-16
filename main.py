"""CAD AI Editor - FastAPI backend."""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import shutil
import uuid

from editor import CADEditor
from redline import analyze_redline
from converter import dwg_to_dxf
from upwork import build_proposal, get_search_task, get_apply_task, get_download_task, get_send_task, DEFAULT_SEARCH
from auth import init_db, register, login, get_user_by_token, use_credit
from billing import create_checkout_session, handle_webhook, is_configured
from auth import PLANS
from fastapi import Request, Header

app = FastAPI(title="CAD AI Editor", version="0.1.0")

BASE = Path(__file__).parent.parent
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

# In-memory job store (use Redis/DB in production)
jobs: dict = {}


# Initialize database
init_db()


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def get_current_user(authorization: str = Header(None)):
    """Extract user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    user = get_user_by_token(authorization[7:])
    if not user:
        raise HTTPException(401, "Invalid or expired session")
    return user


@app.post("/api/register")
async def api_register(req: RegisterRequest):
    try:
        user = register(req.email, req.password)
    except ValueError as e:
        raise HTTPException(400, str(e))
    token = login(req.email, req.password)
    return {"token": token, "user": user}


@app.post("/api/login")
async def api_login(req: LoginRequest):
    token = login(req.email, req.password)
    if not token:
        raise HTTPException(401, "Invalid email or password")
    user = get_user_by_token(token)
    return {"token": token, "user": {
        "email": user["email"], "plan": user["plan"],
        "credits": user["credits"],
    }}


@app.get("/api/me")
async def api_me(authorization: str = Header(None)):
    user = get_current_user(authorization)
    return {"email": user["email"], "plan": user["plan"],
            "credits": user["credits"]}


@app.post("/api/checkout/{plan}")
async def api_checkout(plan: str, authorization: str = Header(None)):
    """Create Stripe checkout session for plan upgrade."""
    if not is_configured():
        raise HTTPException(500, "Billing not configured")
    if plan not in PLANS or plan == "free":
        raise HTTPException(400, "Invalid plan")
    user = get_current_user(authorization)
    base = os.environ.get("APP_URL", "http://localhost:8099")
    url = create_checkout_session(
        user["id"], user["email"], plan,
        f"{base}/success", f"{base}/pricing",
    )
    return {"checkout_url": url}


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe payment webhooks."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        result = handle_webhook(payload, sig)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if result:
        from auth import upgrade_plan
        upgrade_plan(result["user_id"], result["plan"],
                     result.get("stripe_customer_id"))
        # Add credits for pay-per plan
        if result["plan"] == "pay_per":
            import sqlite3
            from auth import DB_PATH
            db = sqlite3.connect(str(DB_PATH))
            db.execute(
                "UPDATE users SET credits = credits + 10 WHERE id = ?",
                (result["user_id"],))
            db.commit()
            db.close()
    return {"received": True}


class EditRequest(BaseModel):
    job_id: str
    edits: list


@app.post("/api/upload")
async def upload_dwg(file: UploadFile = File(...)):
    """Upload a DWG or DXF file. DWG auto-converts to DXF. Returns job_id."""
    if not file.filename.lower().endswith((".dwg", ".dxf")):
        raise HTTPException(400, "Only .dwg and .dxf files accepted")
    job_id = uuid.uuid4().hex[:8]
    dest = UPLOADS / f"{job_id}_{file.filename}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Auto-convert DWG → DXF
    try:
        dxf_path = dwg_to_dxf(str(dest), str(UPLOADS / job_id))
    except RuntimeError as e:
        raise HTTPException(500, f"DWG conversion failed: {e}")

    jobs[job_id] = {
        "original": dxf_path,
        "original_upload": str(dest),
        "filename": file.filename,
    }
    return {"job_id": job_id, "filename": file.filename,
            "converted": dxf_path != str(dest)}


@app.get("/api/layouts/{job_id}")
async def get_layouts(job_id: str):
    """List layouts in the uploaded file."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    editor = CADEditor(job["original"])
    return {"layouts": editor.list_layouts()}


@app.post("/api/apply")
async def apply_edits(req: EditRequest, authorization: str = Header(None)):
    """Apply AI-generated edits. Consumes 1 credit. Returns download URL."""
    # Credit check (skip if no auth header = dev mode)
    if authorization:
        user = get_current_user(authorization)
        if not use_credit(user["id"]):
            raise HTTPException(402, "No credits left. Upgrade your plan.")
    job = jobs.get(req.job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    editor = CADEditor(job["original"])
    results = editor.apply_edits(req.edits)
    out_name = f"{req.job_id}_revised.dxf"
    out_path = OUTPUTS / out_name
    editor.save(str(out_path))
    return {
        "job_id": req.job_id,
        "results": results,
        "download_url": f"/api/download/{req.job_id}",
    }


@app.post("/api/analyze/{job_id}")
async def analyze(job_id: str, file: UploadFile = File(...)):
    """Upload a redline PDF. Returns AI-proposed CAD edits."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF redlines accepted")
    pdf_path = UPLOADS / f"{job_id}_redline.pdf"
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    result = analyze_redline(str(pdf_path))
    job["analysis"] = result
    return result


@app.get("/api/download/{job_id}")
async def download(job_id: str):
    out_path = OUTPUTS / f"{job_id}_revised.dxf"
    if not out_path.exists():
        raise HTTPException(404, "No output yet - apply edits first")
    return FileResponse(str(out_path), filename=f"revised_{job_id}.dxf")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ============ Upwork Integration ============

class UpworkSearchRequest(BaseModel):
    keywords: str = DEFAULT_SEARCH["keywords"]
    limit: int = 10


@app.post("/api/upwork/search-task")
async def upwork_search_task(req: UpworkSearchRequest,
                             authorization: str = Header(None)):
    """Generate a browser task to search Upwork for jobs.
    Returns the task prompt - execute via browser session."""
    get_current_user(authorization) if authorization else None
    return {
        "task": get_search_task(req.keywords, req.limit),
        "note": "Execute this in a logged-in Upwork browser session. "
                "Results come back as JSON for the next step.",
    }


class UpworkProposalRequest(BaseModel):
    job_id: str
    job_title: str
    job_url: str
    budget: str = ""  # client's listed budget, e.g. "$500"
    bid_amount: str = ""  # manual override; auto-calculated if empty
    timeline: str = "3-5 business days"


@app.post("/api/upwork/proposal")
async def upwork_proposal(req: UpworkProposalRequest,
                          authorization: str = Header(None)):
    """Generate a tailored proposal + browser task to submit it.
    Bid auto-calculates to 30% below client's budget unless overridden."""
    user = get_current_user(authorization) if authorization else {}
    from upwork import UpworkJob, calculate_bid
    from upwork import build_proposal as _build_proposal

    # Auto-bid: 30% below offer
    bid = req.bid_amount
    auto_bid = False
    if not bid and req.budget:
        bid = calculate_bid(req.budget, 30.0)
        auto_bid = True
    if not bid:
        bid = "TBD"

    job = UpworkJob(
        job_id=req.job_id, title=req.job_title, description="",
        budget=req.budget, posted="", proposals="", url=req.job_url,
        skills=[],
    )
    profile = {
        "name": "Sam Campbell",
        "phone": "(916) 741-9721",
        "website": "yardhousedrafting.com",
        "bio_extra": "Licensed drafting professional, 100+ permitted projects.",
    }
    cover_letter = _build_proposal(job, profile)
    return {
        "cover_letter": cover_letter,
        "bid_amount": bid,
        "auto_bid": auto_bid,
        "discount": "30% below listed budget" if auto_bid else None,
        "browser_task": get_apply_task(
            req.job_url, cover_letter, bid, req.timeline),
        "note": "Review the cover letter, then execute the browser task "
                "to submit. Requires your approval per proposal.",
    }


@app.post("/api/upwork/download-task/{contract_id}")
async def upwork_download_task(contract_id: str,
                               contract_url: str = "",
                               authorization: str = Header(None)):
    """Generate browser task to download markups from a contract."""
    get_current_user(authorization) if authorization else None
    url = contract_url or f"https://www.upwork.com/ab/contracts/{contract_id}"
    return {
        "task": get_download_task(url),
        "note": "Downloaded files can be fed directly into /api/analyze "
                "for AI redline processing.",
    }


class UpworkSendRequest(BaseModel):
    contract_id: str
    contract_url: str = ""
    file_job_id: str  # job_id of the revised CAD file
    message: str


@app.post("/api/upwork/send-deliverable")
async def upwork_send_deliverable(req: UpworkSendRequest,
                                  authorization: str = Header(None)):
    """Generate browser task to upload deliverable + message client."""
    get_current_user(authorization) if authorization else None
    out_path = OUTPUTS / f"{req.file_job_id}_revised.dxf"
    if not out_path.exists():
        raise HTTPException(404, "Revised file not found. Apply edits first.")
    url = req.contract_url or \
        f"https://www.upwork.com/ab/contracts/{req.contract_id}"
    return {
        "task": get_send_task(url, str(out_path), req.message),
        "file": str(out_path),
        "note": "Execute in logged-in Upwork browser session. "
                "Requires your approval before sending to client.",
    }


# Serve frontend
app.mount("/", StaticFiles(directory=str(BASE / "frontend"), html=True), name="static")
