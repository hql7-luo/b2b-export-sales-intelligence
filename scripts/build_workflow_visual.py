"""Lay out actual current-version UI crops; never recreate application data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
VISUALS = ROOT / "docs" / "visuals"
INK = "#14243A"
MUTED = "#475467"
BLUE = "#2563EB"

STEPS = (
    ("Buyer inquiry", "inquiry", ("English RFQ", "Requirements arrive as free text")),
    ("Structured analysis", "analysis", ("Fields, gaps and risks", "Local rules + an editable reply")),
    ("Customer record", "customer", ("Link or create a customer", "Save the inquiry and product match")),
    ("Quotation", "quotation", ("CNY costs to USD quotation", "Explicit Gross Margin or Markup")),
    ("Follow-up", "followup", ("Linked customer, inquiry and quote", "Next action, priority and due date")),
    ("Sales analytics", "analytics", ("Funnel and lead-quality distribution", "See overdue work and buyer sources")),
)


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    raise RuntimeError("Install Arial or DejaVu Sans to regenerate the visual.")


def build(*, columns: int, filename: str) -> None:
    panel_width, panel_height, gap, margin = 488, 400, 26, 36
    header_height, footer_height = 132, 82
    rows = (len(STEPS) + columns - 1) // columns
    width = margin * 2 + columns * panel_width + (columns - 1) * gap
    height = header_height + rows * panel_height + (rows - 1) * gap + footer_height
    canvas = Image.new("RGB", (width, height), "#F5F7FA")
    draw = ImageDraw.Draw(canvas)
    title = "One linked export-sales workflow"
    draw.text((margin, 28), title, font=font(42 if columns == 3 else 36, bold=True), fill=INK)
    draw.text((margin, 82), "Actual application views · Fictional demonstration data", font=font(25), fill=MUTED)

    for index, (label, name, captions) in enumerate(STEPS):
        x = margin + (index % columns) * (panel_width + gap)
        y = header_height + (index // columns) * (panel_height + gap)
        draw.rounded_rectangle((x, y, x + panel_width, y + panel_height), radius=12, fill="white", outline="#D0D5DD", width=2)
        draw.rounded_rectangle((x + 18, y + 18, x + 69, y + 66), radius=7, fill=BLUE)
        draw.text((x + 28, y + 27), f"{index + 1:02}", font=font(26, bold=True), fill="white")
        draw.text((x + 84, y + 27), label, font=font(29, bold=True), fill=INK)
        with Image.open(VISUALS / "sources" / f"{name}.png") as source:
            preview = ImageOps.contain(source.convert("RGB"), (panel_width - 36, 230), Image.Resampling.LANCZOS)
        preview_x = x + (panel_width - preview.width) // 2
        preview_y = y + 84 + (230 - preview.height) // 2
        canvas.paste(preview, (preview_x, preview_y))
        draw.line((x + 18, y + 325, x + panel_width - 18, y + 325), fill="#EAECF0", width=2)
        draw.text((x + 20, y + 340), captions[0], font=font(24, bold=True), fill=INK)
        draw.text((x + 20, y + 373), captions[1], font=font(22), fill=MUTED)
        # Numbering and arrows show row-major progression without a complex architecture.
        if index % columns != columns - 1:
            cx, cy = x + panel_width + gap // 2, y + 45
            draw.line((cx - 9, cy, cx + 7, cy), fill=BLUE, width=3)
            draw.polygon(((cx + 7, cy), (cx, cy - 6), (cx, cy + 6)), fill=BLUE)

    footer = "SQLite keeps records connected; analytics summarizes the workspace."
    if columns == 3:
        draw.text((margin, height - 48), footer, font=font(24), fill=MUTED)
    else:
        draw.text((margin, height - 63), "SQLite keeps records connected.", font=font(24), fill=MUTED)
        draw.text((margin, height - 32), "Analytics summarizes the workspace.", font=font(24), fill=MUTED)
    canvas.save(VISUALS / filename, optimize=True)


if __name__ == "__main__":
    manifest_path = VISUALS / "capture-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for capture in manifest["captures"]:
        source = VISUALS / capture["file"]
        capture["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        with Image.open(source) as image:
            capture["dimensions"] = list(image.size)
    build(columns=3, filename="sales-workflow.png")
    build(columns=2, filename="sales-workflow-mobile.png")
    manifest["generator"] = "scripts/build_workflow_visual.py (Pillow; only layout, scaling and workflow labels)"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
