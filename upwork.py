"""Upwork manual-assist tools.

Upwork's Terms of Use prohibit automated access (robots, scrapers, or any
technology other than their interface) without written permission. This module
therefore does NOT automate Upwork. It provides in-app drafting assistance:

1. Bid calculator (30% below client budget, rounded to nearest $5)
2. Cover letter generator tailored to the job
3. Step-by-step manual checklists for searching, applying, downloading
   markups, and sending deliverables — all done by the user in their own
   browser.

No credentials are stored. No browser automation is performed.
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class UpworkJob:
    job_id: str
    title: str
    description: str
    budget: str
    posted: str
    proposals: str
    url: str
    skills: List[str]


# Job search criteria for CAD/drafting work
DEFAULT_SEARCH = {
    "keywords": "AutoCAD drafting architectural plans",
    "categories": ["Engineering & Architecture"],
    "job_types": ["fixed"],  # fixed-price preferred for plan work
}


def parse_budget(budget_str: str) -> Optional[float]:
    """Extract numeric budget from strings like '$500', '$1,200', '$50/hr'."""
    if not budget_str:
        return None
    clean = budget_str.replace(",", "")
    match = re.search(r'\$?(\d+(?:\.\d{2})?)', clean)
    if match:
        return float(match.group(1))
    return None


def calculate_bid(budget_str: str, discount_pct: float = 30.0) -> Optional[str]:
    """
    Calculate bid at discount_pct below the client's budget.
    Returns formatted string like '$350' or None if budget unparseable.
    """
    budget = parse_budget(budget_str)
    if budget is None:
        return None
    bid = budget * (1 - discount_pct / 100)
    bid = round(bid / 5) * 5  # round to nearest $5
    return f"${int(bid)}"


def build_proposal(job: UpworkJob, freelancer_profile: Dict[str, str]) -> str:
    """Generate a tailored proposal for a CAD job."""
    return f"""Hi,

I'm {freelancer_profile.get('name', 'a drafting professional')} specializing in architectural CAD work.

For your project "{job.title}", I can deliver:
- Permit-ready plan sets (floor plans, elevations, sections, details)
- Quick turnaround with revision rounds included
- Direct communication throughout

{freelancer_profile.get('bio_extra', '')}

Recent relevant work: ADUs, patio covers, home additions, and full house plans — all permitted through California jurisdictions.

I'd welcome the chance to discuss your project. Let me know if you'd like to see samples.

Best,
{freelancer_profile.get('name', '')}
{freelancer_profile.get('phone', '')}
{freelancer_profile.get('website', '')}"""


# Manual checklists — the user performs these steps in their own browser.
# No automation; Upwork's ToS requires human interaction via their interface.

SEARCH_CHECKLIST = """Find CAD jobs on Upwork manually:

1. Go to upwork.com → Find Work → search: "{keywords}"
2. Filter: Category = Engineering & Architecture, Job type = Fixed-price
3. For each promising job, note: title, URL, budget, posted time,
   proposal count, and required skills
4. Paste the job details into the Proposal Drafting tab here to generate
   your cover letter and bid."""


APPLY_CHECKLIST = """Submit your proposal on Upwork manually:

1. Open the job posting in your browser
2. Click "Submit a Proposal"
3. Paste the cover letter below into the proposal field
4. Enter your bid amount: {bid_amount}
5. Set your delivery timeline: {timeline}
6. Review and submit

COVER LETTER (copy everything below this line):
{cover_letter}"""


DOWNLOAD_CHECKLIST = """Download client markups from Upwork manually:

1. Open your contract messages page in your browser
2. Find all file attachments in the thread (PDFs, DWGs, images)
3. Download each attachment to your computer
4. Upload the markup PDF here via the Analyze tab for AI redline processing"""


SEND_CHECKLIST = """Send your deliverable on Upwork manually:

1. Open your contract page in your browser
2. Upload the revised file: {file_name}
   (Use "Submit Work" or attach in messages)
3. Paste this message to the client:

{message}

4. Send. Do NOT mark the contract complete unless the client approves."""


def get_search_checklist(keywords: str) -> str:
    return SEARCH_CHECKLIST.format(keywords=keywords)


def get_apply_checklist(cover_letter: str, bid_amount: str,
                        timeline: str) -> str:
    return APPLY_CHECKLIST.format(
        cover_letter=cover_letter, bid_amount=bid_amount, timeline=timeline)


def get_download_checklist() -> str:
    return DOWNLOAD_CHECKLIST


def get_send_checklist(file_name: str, message: str) -> str:
    return SEND_CHECKLIST.format(file_name=file_name, message=message)
