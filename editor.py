"""Core CAD editing engine - ezdxf based."""
import ezdxf
from ezdxf import colors
from ezdxf.enums import TextEntityAlignment
from pathlib import Path
from typing import List, Dict, Any
import uuid


class CADEditor:
    """AI-driven CAD editor. Applies structured edit instructions to DXF files."""
    
    def __init__(self, dxf_path: str):
        self.doc = ezdxf.readfile(dxf_path)
        self.dxf_path = dxf_path
        self.job_id = uuid.uuid4().hex[:8]
        self._ensure_ai_layer()
    
    def _ensure_ai_layer(self):
        if "AI-REVISIONS" not in self.doc.layers:
            self.doc.layers.add("AI-REVISIONS", color=colors.RED)
    
    def list_layouts(self) -> List[Dict[str, Any]]:
        """Return all paper space layouts with entity counts."""
        result = []
        for layout in self.doc.layouts:
            if layout.name == "Model":
                continue
            entities = list(layout)
            result.append({
                "name": layout.name,
                "entity_count": len(entities),
            })
        return result
    
    def list_layers(self) -> List[str]:
        return [l.dxf.name for l in self.doc.layouts and self.doc.layers]
    
    def add_text(self, layout_name: str, text: str, x: float, y: float,
                 height: float = 1.5) -> Dict[str, Any]:
        """Add a text callout to a layout."""
        layout = self.doc.layouts.get(layout_name)
        t = layout.add_text(text, height=height,
                            dxfattribs={"layer": "AI-REVISIONS"})
        t.set_placement((x, y), align=TextEntityAlignment.LEFT)
        return {"type": "text", "text": text, "x": x, "y": y}
    
    def add_line(self, layout_name: str, x1: float, y1: float,
                 x2: float, y2: float) -> Dict[str, Any]:
        """Draw a line on a layout."""
        layout = self.doc.layouts.get(layout_name)
        layout.add_line((x1, y1), (x2, y2),
                        dxfattribs={"layer": "AI-REVISIONS"})
        return {"type": "line", "from": [x1, y1], "to": [x2, y2]}
    
    def delete_layout(self, layout_name: str) -> Dict[str, Any]:
        """Remove an entire layout (sheet)."""
        self.doc.layouts.delete(layout_name)
        return {"type": "delete_layout", "layout": layout_name}
    
    def mask_area(self, layout_name: str, x0: float, y0: float,
                  x1: float, y1: float) -> Dict[str, Any]:
        """Cover an area with a white solid hatch (non-destructive removal)."""
        layout = self.doc.layouts.get(layout_name)
        hatch = layout.add_hatch(dxfattribs={"layer": "AI-REVISIONS"})
        hatch.set_solid_fill(color=7)
        hatch.paths.add_polyline_path(
            [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], is_closed=True)
        return {"type": "mask", "layout": layout_name,
                "rect": [x0, y0, x1, y1]}
    
    def apply_edits(self, edits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply a batch of edit instructions. Returns results."""
        results = []
        for edit in edits:
            action = edit.get("action")
            try:
                if action == "add_text":
                    r = self.add_text(edit["layout"], edit["text"],
                                      edit["x"], edit["y"],
                                      edit.get("height", 1.5))
                elif action == "add_line":
                    r = self.add_line(edit["layout"], *edit["from"], *edit["to"])
                elif action == "delete_layout":
                    r = self.delete_layout(edit["layout"])
                elif action == "mask_area":
                    r = self.mask_area(edit["layout"], *edit["rect"])
                else:
                    r = {"error": f"Unknown action: {action}"}
                r["status"] = "ok"
            except Exception as e:
                r = {"status": "error", "error": str(e), "action": action}
            results.append(r)
        return results
    
    def save(self, output_path: str):
        self.doc.saveas(output_path)
        return output_path
