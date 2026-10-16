"""Upwork integration via browser automation.

Upwork does not offer a public API for freelancers to search/apply to jobs.
This module uses controlled browser sessions to:
1. Search for CAD/drafting jobs
2. Submit proposals (with user approval)
3. Monitor active contracts for markup files
4. Download markups → feed into redline AI
5. Upload revised deliverables + message client for approval

Requires: Upwork credentials in Secure Vault, user approval per action.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


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


@dataclass
class UpworkContract:
    contract_id: str
    title: str
    client: str
    status: str


# Job search criteria for CAD/drafting work
DEFAULT_SEARCH = {
    "keywords": "AutoCAD drafting architectural plans",
    "categories": ["Engineering & Architecture"],
    "job_types": ["fixed"],  # fixed-price preferred for plan work
}


import re


def parse_budget(budget_str: str) -> Optional[float]:
    """Extract numeric budget from strings like '$500', '$1,200', '$50/hr'."""
    if not budget_str:
        return None
    # Remove commas, find first dollar amount
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
    # Round to nearest $5 for clean numbers
    bid = round(bid / 5) * 5
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


# Browser automation task templates
# These are sent to browser.spawn_task for execution

SEARCH_TASK = """On Upwork (upwork.com), you are logged in as a freelancer.

Search for jobs with these criteria:
- Keywords: {keywords}
- Category: Engineering & Architecture

For the top {limit} results, extract:
- Job title
- Job URL
- Budget/rate
- Posted time
- Number of proposals
- First 200 chars of description
- Required skills

Return as JSON array. Do NOT apply to any jobs."""

APPLY_TASK = """On Upwork (upwork.com), you are logged in as a freelancer.

Go to this job URL: {job_url}

Submit a proposal with:
- Cover letter (provided below)
- Bid amount: {bid_amount}
- Delivery timeline: {timeline}

COVER LETTER:
{cover_letter}

Do NOT submit until all fields are filled. Take a screenshot of the
confirmation page after submitting. Report the proposal URL."""

DOWNLOAD_MARKUPS_TASK = """On Upwork (upwork.com), you are logged in as a freelancer.

Go to the contract messages page: {contract_url}

1. Find all file attachments in the message thread (PDFs, DWGs, images)
2. Download each attachment
3. Report: filename, file type, which message it was in, and the message text

Do NOT send any messages. Only download and report."""

SEND_DELIVERABLE_TASK = """On Upwork (upwork.com), you are logged in as a freelancer.

Go to the contract page: {contract_url}

1. Upload this file as a deliverable: {file_path}
   (Use the contract's "Submit Work" or file upload in messages)
2. Send this message to the client:

[[CLIENT_MESSAGE]]

3. Report confirmation that the file was uploaded and message sent.
Do NOT mark the contract complete unless explicitly instructed."""


def get_search_task(keywords: str, limit: int = 10) -> str:
    return SEARCH_TASK.format(keywords=keywords, limit=limit)


def get_apply_task(job_url: str, cover_letter: str,
                   bid_amount: str, timeline: str) -> str:
    return APPLY_TASK.format(
        job_url=job_url, cover_letter=cover_letter,
        bid_amount=bid_amount, timeline=timeline,
    )


def get_download_task(contract_url: str) -> str:
    return DOWNLOAD_MARKUPS_TASK.format(contract_url=contract_url)


def get_send_task(contract_url: str, file_path: str, message: str) -> str:
    task = SEND_DELIVERABLE_TASK.format(
        contract_url=contract_url, file_path=file_path,
    )
    return task.replace("[[CLIENT_MESSAGE]]", message)
