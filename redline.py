"""Redline PDF analyzer - converts reviewer markups to CAD edit instructions."""
import pymupdf
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


# Maps redline PDF page numbers (1-indexed) to CAD layout names.
# This mapping is project-specific; in production it's derived from
# sheet index matching or user confirmation.
PAGE_TO_LAYOUT = {
    8: "07.2 EXISTING & PROPOSED FLOOR PLAN (2)",   # O7.2
    10: "09 FRAMING",                                 # O9.1
    11: "09.2 FRAMING",                               # O9.2
    12: "X 10 DETAILS",                               # Sheet 10
    16: "13 ROOF PLAN",                               # Roof
}


@dataclass
class Markup:
    page: int
    annot_type: str
    rect: tuple  # (x0, y0, x1, y1) in PDF points
    text: str


def extract_markups(pdf_path: str) -> List[Markup]:
    """Extract all annotations from a redline PDF."""
    doc = pymupdf.open(pdf_path)
    markups = []
    for i, page in enumerate(doc):
        for annot in (page.annots() or []):
            info = annot.info
            markups.append(Markup(
                page=i + 1,
                annot_type=annot.type[1],
                rect=tuple(round(v, 1) for v in annot.rect),
                text=info.get("content", "").strip(),
            ))
    doc.close()
    return markups


def _is_crossout(m: Markup) -> bool:
    """Detect diagonal cross-out lines (large Line annotations)."""
    if m.annot_type != "Line":
        return False
    x0, y0, x1, y1 = m.rect
    w, h = abs(x1 - x0), abs(y1 - y0)
    # Large diagonal line = cross-out
    return w > 400 and h > 400


def interpret_markup(m: Markup) -> Optional[Dict[str, Any]]:
    """
    Convert a single markup into a CAD edit instruction.
    Returns None if the markup needs human judgment.
    """
    layout = PAGE_TO_LAYOUT.get(m.page)
    if not layout:
        return None

    text_lower = m.text.lower()

    # --- Text-based instructions ---
    if m.annot_type == "FreeText" and m.text:
        if "remove this plan" in text_lower or "remove sheet" in text_lower:
            if "structural" in text_lower:
                return {
                    "action": "delete_layout",
                    "layout": layout,
                    "reason": m.text,
                    "confidence": "high",
                }
        if "remove the addition" in text_lower:
            return {
                "action": "flag_manual",
                "layout": layout,
                "reason": m.text,
                "note": "Existing/proposed geometry separation requires drafter review",
                "confidence": "medium",
            }
        if "see struc" in text_lower or "refer to struc" in text_lower:
            x0, y0, x1, y1 = m.rect
            return {
                "action": "add_text",
                "layout": layout,
                "text": m.text.upper(),
                "x": (x0 + x1) / 2,  # placeholder - needs PDF→CAD coord mapping
                "y": (y0 + y1) / 2,
                "reason": "Reviewer callout",
                "confidence": "high",
                "needs_coord_mapping": True,
            }
        if "let's discuss" in text_lower or "where is" in text_lower:
            return {
                "action": "flag_manual",
                "layout": layout,
                "reason": m.text,
                "note": "Reviewer wants discussion, not a drafting change",
                "confidence": "high",
            }
        # Generic text annotation → add as callout
        return {
            "action": "add_text",
            "layout": layout,
            "text": m.text.upper(),
            "x": m.rect[0],
            "y": m.rect[1],
            "reason": "Reviewer note",
            "confidence": "low",
            "needs_coord_mapping": True,
        }

    # --- Cross-out lines → mask the area ---
    if _is_crossout(m):
        x0, y0, x1, y1 = m.rect
        return {
            "action": "mask_area",
            "layout": layout,
            "rect": [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)],
            "reason": "Reviewer crossed out this area",
            "confidence": "medium",
            "needs_coord_mapping": True,
        }

    return None


def analyze_redline(pdf_path: str) -> Dict[str, Any]:
    """
    Full pipeline: extract markups → interpret → return proposed edits.
    """
    markups = extract_markups(pdf_path)
    edits = []
    flags = []  # items needing human judgment

    for m in markups:
        result = interpret_markup(m)
        if result:
            if result["action"] == "flag_manual":
                flags.append(result)
            else:
                edits.append(result)

    return {
        "total_markups": len(markups),
        "pages_with_markups": sorted(set(m.page for m in markups)),
        "proposed_edits": edits,
        "needs_human": flags,
        "summary": (
            f"Found {len(markups)} markups. "
            f"Proposed {len(edits)} automated edits. "
            f"{len(flags)} items need human judgment."
        ),
    }
