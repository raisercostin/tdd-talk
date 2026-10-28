"""Export Markdown to matching editable PowerPoint and offline HTML decks.

Install: python -m pip install -r requirements.txt
Run:     python export_tdd.py
         python export_tdd.py --source tdd4.md --output tdd4-talk --section-pages
"""

from __future__ import annotations

import html
import argparse
import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "tdd3.md"
BG, PANEL, FG, MUTED, BLUE = "0F1115", "151922", "E6E6E6", "AAAAAA", "4AA3FF"


@dataclass
class Slide:
    title: str
    section: str
    source: str
    blocks: list[str]
    diagram: bool = False
    stages: list[list[str]] | None = None


def clean(text: str) -> str:
    return re.sub(r"\*\*|~~|`", "", text)


def make_blocks(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    fenced = False
    for line in lines:
        if line.startswith("```"):
            fenced = not fenced
        new_item = bool(re.match(r"^(?:- |\d+\. )", line))
        if not fenced and (not line.strip() or new_item) and current:
            blocks.append("\n".join(current))
            current = []
        if line.strip() or fenced:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def read_slides(source: Path = SOURCE) -> tuple[str, list[Slide]]:
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = lines[0].removeprefix("# ")
    slides = [Slide(title, "Presentation", "\n".join(lines[:4]), [lines[2]])]
    headings: dict[int, str] = {}
    heading = ""
    section = ""
    body: list[str] = []

    def flush() -> None:
        if not any(line.strip() for line in body):
            return
        blocks = make_blocks(body)
        if any("```mermaid" in block for block in blocks):
            slides.append(Slide(heading, section, "\n".join(body), blocks, True))
            return
        chunks: list[list[str]] = [[]]
        size = 0
        for block in blocks:
            cost = len(block) + 65
            if chunks[-1] and (size + cost > 850 or len(chunks[-1]) >= 6):
                chunks.append([])
                size = 0
            chunks[-1].append(block)
            size += cost
        for n, chunk in enumerate(chunks, 1):
            suffix = f" ({n}/{len(chunks)})" if len(chunks) > 1 else ""
            slides.append(Slide(heading + suffix, section, "\n\n".join(chunk), chunk))

    for line in lines[4:]:
        match = re.match(r"^(#{2,4}) (.+)$", line)
        phase = re.match(r"^(RED|GREEN|REFACTOR) - (.+)$", line)
        purposes = line.startswith("Different phases have different purposes:")
        if match or phase or purposes:
            flush()
            body = []
            if match:
                level = len(match[1])
                heading = match[2]
                headings = {k: v for k, v in headings.items() if k < level}
                headings[level] = heading
                section = " / ".join(v for k, v in headings.items() if k < level)
                if not section:
                    section = "Appendix · Study" if heading in ("Study", "Resources", "Ideas") else "Presentation"
            elif phase:
                heading = phase[1]
                section = "4. RED–GREEN–REFACTOR"
                body.append(phase[2])
            else:
                heading = "Different phases have different purposes"
                section = "4. RED–GREEN–REFACTOR"
        else:
            body.append(line)
    flush()
    return title, slides


def read_section_slides(source: Path) -> tuple[str, list[Slide]]:
    """One page per section; +++ progressively reveals content on that page."""
    text = source.read_text(encoding="utf-8")
    # Preparation instructions precede the actual talk and aren't slide content.
    talk = re.search(r"^# TDD Talk\s*$", text, re.M)
    if talk:
        text = text[talk.start():]
    lines = text.splitlines()
    title = lines[0].removeprefix("# ")
    slides: list[Slide] = []
    headings: dict[int, str] = {}
    heading, section, body = title, "Presentation", []
    stages: list[list[str]] = []

    def flush() -> None:
        groups = stages + ([body] if any(line.strip() for line in body) else [])
        groups = [group for group in groups if any(line.strip() for line in group)]
        raw = "\n\n+++\n\n".join("\n".join(group).strip() for group in groups)
        if raw:
            blocks = [make_blocks(group) for group in groups]
            slides.append(Slide(heading, section, raw, [block for group in blocks for block in group], "```mermaid" in raw, blocks))

    for line in lines[1:]:
        match = re.match(r"^(#{2,6}) (.+)$", line)
        if match:
            flush()
            body, stages = [], []
            level = len(match[1])
            heading = title if match[2] == "Content" else match[2]
            headings = {k: v for k, v in headings.items() if k < level}
            section = " / ".join(headings.values()) or "Presentation"
            headings[level] = heading
        elif line.strip() == "+++":
            stages.append(body)
            body = []
        else:
            body.append(line)
    flush()
    return title, slides


IMAGE = re.compile(r"!\[([^]]*)\]\(([^)]+)\)")


def images_and_text(item: Slide, source: Path):
    images = []
    for alt, name in IMAGE.findall(item.source):
        path = source.parent / name
        if not path.is_file() and path.with_suffix(".md").is_file():
            path = path.with_suffix(".md")
        if not path.is_file():
            raise FileNotFoundError(f"Image referenced by {source.name}: {name}")
        with Image.open(path) as im:
            mime = Image.MIME[im.format]
            dimensions = im.size
        images.append((alt, path, mime, dimensions))
    raw = IMAGE.sub("", "\n\n".join(item.blocks))
    stages = [make_blocks(IMAGE.sub("", "\n\n".join(group)).splitlines()) for group in item.stages] if item.stages else None
    return images, Slide(item.title, item.section, raw, make_blocks(raw.splitlines()), item.diagram, stages)


def metadata(slides: list[Slide]):
    match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", slides[0].source)
    date = match[0] if match else ""
    return f"Presenter: Costin Grigore{' · ' + date if date else ''}"


def link_parts(text: str) -> tuple[str, str | None]:
    match = re.search(r"https?://\S+", text)
    if not match:
        return text, None
    url = match[0]
    label = text[:match.start()].strip().removesuffix("-").strip()
    if not label:
        labels = {
            "blog.stevensanderson.com": "Steve Sanderson — Writing Great Unit Tests",
            "www.google.com": "Search: TDD, Where Did It All Go Wrong?",
            "www.reddit.com": "Discussion: Ian Cooper — TDD, Where Did It All Go Wrong?",
            "archive.org": "Kent Beck — Test-Driven Development by Example",
            "dannorth.net": "Dan North",
            "martinfowler.com": "Martin Fowler — Are Harnesses Worth the Cost?",
        }
        label = labels.get(urlparse(url).netloc, url)
    return label, url


def inline(text: str) -> str:
    label, url = link_parts(text)
    if url:
        return f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(label)}</a>'
    value = html.escape(text)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    return re.sub(r"~~(.+?)~~", r"<del>\1</del>", value)


def block_html(block: str) -> str:
    fenced = re.fullmatch(r"```([^\n]*)\n(.*?)\n?```", block.strip(), re.S)
    if fenced:
        return f'<pre class="source-code"><code class="language-{html.escape(fenced[1], quote=True)}">{html.escape(fenced[2])}</code></pre>'
    lines = block.splitlines()
    main = re.match(r"^(- |\d+\. )(.*)$", lines[0])
    quote = lines[0].startswith("> ")
    if not main and not quote:
        nested_at = next((i for i, line in enumerate(lines) if re.match(r"^\s+- ", line)), None)
        if nested_at is not None:
            import textwrap
            lead = block_html("\n".join(lines[:nested_at]))
            children = make_blocks(textwrap.dedent("\n".join(lines[nested_at:])).splitlines())
            return lead + "".join(block_html(child) for child in children)
    if main:
        numbered = main[1] != "- "
        tag = "ol" if numbered else "ul"
        start = f' start="{main[1].split(".")[0]}"' if numbered else ""
        def children_html(children: list[str]) -> str:
            if not children:
                return ""
            level = len(children[0]) - len(children[0].lstrip())
            parts = ["<ul>"]
            i = 0
            while i < len(children):
                line = children[i]
                i += 1
                nested_lines = []
                while i < len(children) and len(children[i]) - len(children[i].lstrip()) > level:
                    nested_lines.append(children[i])
                    i += 1
                parts.append(f"<li>{inline(re.sub(r'^\s*- ', '', line))}{children_html(nested_lines)}</li>")
            return "".join(parts) + "</ul>"

        nested = children_html([line for line in lines[1:] if line.strip()])
        return f'<{tag}{start}><li>{inline(main[2])}{nested}</li></{tag}>'
    if quote:
        return f'<blockquote>{inline(block.removeprefix("> "))}</blockquote>'
    return f'<p>{inline(block).replace(chr(10), "<br>")}</p>'


FENCE = re.compile(r"```([^\n]*)\n(.*?)\n?```", re.S)


def separate_code(item: Slide):
    code = []
    text_stages = []
    for stage, blocks in enumerate(item.stages or [item.blocks]):
        raw = "\n\n".join(blocks)
        for language, content in FENCE.findall(raw):
            if language.strip() != "mermaid":
                code.append((stage, language.strip(), content))
        raw = FENCE.sub("", raw)
        text_stages.append(make_blocks(raw.splitlines()))
    text_blocks = [block for group in text_stages for block in group]
    return code, Slide(item.title, item.section, "\n\n".join(text_blocks), text_blocks, False, text_stages)


# Shared coordinates: native PowerPoint shapes and offline SVG use the same graph.
NODES = {
    "1": (480, 45, "Unit 1"),
    "1.1": (100, 205, "Unit 1.1"),
    "1.2": (350, 205, "Unit 1.2"),
    "1.3": (600, 205, "Unit 1.3"),
    "1.4": (850, 205, "Unit 1.4"),
    "1.3.1": (460, 370, "Unit 1.3.1"),
    "1.3.2": (730, 370, "Unit 1.3.2"),
    "1.3.2b": (730, 520, "Unit 1.3.2b"),
}
EDGES = [("1", child) for child in ("1.1", "1.2", "1.3", "1.4")] + [("1.3", "1.3.1"), ("1.3", "1.3.2"), ("1.3.2", "1.3.2b")]


def diagram_svg() -> str:
    parts = ['<svg viewBox="0 0 1050 600" role="img" aria-label="Unit 1 decomposes into units 1.1, 1.2, 1.3 and 1.4. Unit 1.3 has two children. Unit 1.3.2 is replaced by Unit 1.3.2b.">', '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#4aa3ff"/></marker></defs>']
    for parent, child in EDGES:
        x1, y1, _ = NODES[parent]
        x2, y2, _ = NODES[child]
        dash = ' stroke-dasharray="8 6"' if child == "1.3.2b" else ""
        parts.append(f'<line x1="{x1}" y1="{y1 + 28}" x2="{x2}" y2="{y2 - 28}" stroke="#4aa3ff" stroke-width="2" marker-end="url(#arrow)"{dash}/>')
    for key, (x, y, label) in NODES.items():
        parts.append(f'<rect x="{x-93}" y="{y-28}" width="186" height="56" rx="4" fill="#151922" stroke="#4aa3ff"/>')
        decoration = ' text-decoration="line-through"' if key == "1.3.2" else ""
        parts.append(f'<text x="{x}" y="{y+8}" text-anchor="middle" fill="#e6e6e6" font-family="Arial, sans-serif" font-size="23"{decoration}>{label}</text>')
    return "".join(parts) + "</svg>"


def textbox(slide, x, y, width, height, text, size=22, color=FG, bold=False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.03)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, line in enumerate(text.splitlines()):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = "Arial"
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = RGBColor.from_string(color)
    return box


def body_lines(item: Slide):
    for block in item.blocks:
        for j, line in enumerate(block.splitlines()):
            match = re.match(r"^(\s*)(- |\d+\. )(.*)$", line)
            raw = match[3] if match else line.removeprefix("> ")
            label, url = link_parts(clean(raw))
            indent = "  " * (len(match[1]) // 2) if match else ""
            prefix = indent + ("• " if match and match[2] == "- " else match[2] if match else "")
            yield prefix + label, url, raw, j


def body_height(item: Slide, size: int, width: float, compact=False) -> float:
    try:
        font = ImageFont.truetype("arial.ttf", size * 4)
    except OSError:
        font = ImageFont.load_default(size=size * 4)
    height = 0
    for text, _, _, j in body_lines(item):
        wrapped, current = 1, ""
        for word in text.split():
            proposed = f"{current} {word}".strip()
            if current and font.getlength(proposed) > width * 288:
                wrapped += 1
                current = word
            else:
                current = proposed
        height += wrapped * size * (1.12 if compact else 1.25) + ((.5 if j == 0 else 0) if compact else (12 if j == 0 else 7))
    return height / 72


def body_font_size(item: Slide, width=11.54, height_inches=4.45, minimum=18, compact=False) -> int:
    # Fit the complete revealed state, rather than just the initial content.
    for size in range(24, minimum - 1, -1):
        if body_height(item, size, width, compact) <= height_inches:
            return size
    raise ValueError(f"Slide needs to be split further: {item.title}")


def add_reveal_animations(slide, targets: dict[int, list[int]]) -> None:
    """Native PowerPoint entrance builds: one click reveals an entire stage."""
    if not targets:
        return
    next_id = 3
    builds = []
    for step, shape_ids in sorted(targets.items()):
        wrapper_id, parallel_id, click_id = next_id, next_id + 1, next_id + 2
        next_id += 3
        effects = []
        for shape_id in shape_ids:
            effects.append(f'''<p:set><p:cBhvr><p:cTn id="{next_id}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn><p:tgtEl><p:spTgt spid="{shape_id}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>''')
            next_id += 1
        builds.append(f'''<p:par><p:cTn id="{wrapper_id}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst><p:par><p:cTn id="{parallel_id}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst><p:par><p:cTn id="{click_id}" presetID="1" presetClass="entr" presetSubtype="0" fill="hold" nodeType="clickEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>{''.join(effects)}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>''')
    timing = f'''<p:timing {nsdecls('p')}><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>{''.join(builds)}</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>'''
    slide._element.append(parse_xml(timing))


def export_ppt(title: str, slides: list[Slide], output: Path = ROOT / "tdd-presentation.pptx", source: Path = SOURCE) -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    prs.core_properties.title = title
    prs.core_properties.subject = f"TDD presentation exported from {source.name}"
    prs.core_properties.author = "Costin Grigore"
    for index, item in enumerate(slides):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string(BG)
        textbox(slide, .7, .3, 11.9, .4, item.section, 12, MUTED)
        textbox(slide, .7, .85, 11.9, 1.05, item.title, 34, bold=True)
        reveal_targets: dict[int, list[int]] = {}
        if item.diagram:
            _, prose = separate_code(item)
            has_prose = bool(prose.blocks)
            if has_prose:
                size = body_font_size(prose, 3.74, 4.5, 12)
                textbox(slide, .85, 2.05, 3.8, 4.65, "\n".join(text for text, _, _, _ in body_lines(prose)), size)
            ox = 4.8 if has_prose else .8
            sx, sy = (7.7 if has_prose else 11.5) / 1050, 4.65 / 600
            for parent, child in EDGES:
                x1, y1, _ = NODES[parent]
                x2, y2, _ = NODES[child]
                edge = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(ox + x1*sx), Inches(2 + (y1+28)*sy), Inches(ox + x2*sx), Inches(2 + (y2-28)*sy))
                edge.line.color.rgb = RGBColor.from_string(BLUE)
                edge.line.width = Pt(1.5)
                arrow = OxmlElement("a:tailEnd")
                arrow.set("type", "triangle")
                edge.line._get_or_add_ln().append(arrow)
                if child == "1.3.2b":
                    edge.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            for key, (x, y, label) in NODES.items():
                shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(ox+(x-93)*sx), Inches(2+(y-28)*sy), Inches(186*sx), Inches(56*sy))
                shape.fill.solid()
                shape.fill.fore_color.rgb = RGBColor.from_string(PANEL)
                shape.line.color.rgb = RGBColor.from_string(BLUE)
                shape.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
                p = shape.text_frame.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                p.text = label
                p.font.name = "Arial"
                p.font.size = Pt(12 if has_prose else 17)
                p.font.color.rgb = RGBColor.from_string(FG)
                if key == "1.3.2":
                    for run in p.runs:
                        run._r.get_or_add_rPr().set("strike", "sngStrike")
        else:
            images, text_item = images_and_text(item, source)
            code, text_item = separate_code(text_item)
            compact = bool(code) or bool(images and item.stages and len(item.stages) > 1)
            comparison_blocks = [block for block in text_item.blocks if block.startswith(("- Human", "- AI"))]
            comparison = len(comparison_blocks) == 2
            regions = [(text_item, .85, 11.6)]
            if code:
                regions = [(text_item, .85, 5.7)]
                for stage, language, content in code:
                    # Preserve Java indentation in a separate editable code panel.
                    for font_size in range(14, 7, -1):
                        font = ImageFont.truetype("consola.ttf", font_size * 4)
                        if max(font.getlength(line) for line in content.splitlines()) <= 5.8 * 288 and len(content.splitlines()) * font_size * 1.1 <= 4.5 * 72:
                            break
                    box = textbox(slide, 6.7, 2.05, 5.8, 4.65, content, font_size)
                    for p in box.text_frame.paragraphs:
                        p.font.name = "Consolas"
                        p.line_spacing = 1.05
                        p.space_before = p.space_after = Pt(0)
                    if stage:
                        reveal_targets.setdefault(stage, []).append(box.shape_id)
            elif comparison:
                prefix = [block for block in text_item.blocks if block not in comparison_blocks]
                regions = []
                if prefix:
                    regions.append((Slide(item.title, item.section, "\n\n".join(prefix), prefix, stages=[prefix]), .85, 3.1))
                for n, block in enumerate(comparison_blocks):
                    stage = next((i for i, group in enumerate(text_item.stages or []) if block in group), 0)
                    groups = [[] for _ in range(stage)] + [[block]]
                    regions.append((Slide(item.title, item.section, block, [block], stages=groups), 4.15+n*4.15 if prefix else .85+n*6, 4.0 if prefix else 5.6))
            elif images:
                regions = [(text_item, 4.4, 8.0)]
                for n, (alt, path, mime, (iw, ih)) in enumerate(images):
                    scale = min(3.2 / iw, 4.5 / len(images) / ih)
                    pic = slide.shapes.add_picture(str(path), Inches(.85), Inches(2.05+n*4.5/len(images)), width=Inches(iw*scale), height=Inches(ih*scale))
                    pic._element.nvPicPr.cNvPr.set("descr", alt)
            for text_item, x, width in regions:
                size = body_font_size(text_item, width-.06, 4.5 if compact else 4.45, 9 if compact else 12, compact)
                y = 2.05
                for stage, blocks in enumerate(text_item.stages or [text_item.blocks]):
                    if not blocks:
                        continue
                    stage_item = Slide(item.title, item.section, "\n\n".join(blocks), blocks)
                    height = body_height(stage_item, size, width-.06, compact) + .04
                    box = textbox(slide, x, y, width, height, "", 23)
                    y += height
                    if stage:
                        reveal_targets.setdefault(stage, []).append(box.shape_id)
                    tf = box.text_frame
                    first = True
                    for text, url, raw, j in body_lines(stage_item):
                        p = tf.paragraphs[0] if first else tf.add_paragraph()
                        first = False
                        p.text = text
                        p.font.name = "Arial"
                        p.font.size = Pt(size)
                        p.font.color.rgb = RGBColor.from_string(BLUE if url else FG)
                        p.line_spacing = 1.05 if compact else 1.2
                        p.space_before = Pt((.5 if j == 0 else 0) if compact else (9 if j == 0 else 4))
                        p.space_after = Pt(0 if compact else 3)
                        if "~~" in raw:
                            for run in p.runs:
                                run._r.get_or_add_rPr().set("strike", "sngStrike")
                        if url:
                            p.runs[0].hyperlink.address = url
        textbox(slide, .7, 7.0, 10.5, .3, title, 10, MUTED)
        textbox(slide, 11.6, 7.0, 1.0, .3, f"{index+1} / {len(slides)}", 10, MUTED)
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(7.45), int(prs.slide_width*(index+1)/len(slides)), Inches(.05))
        bar.fill.solid()
        bar.fill.fore_color.rgb = RGBColor.from_string(BLUE)
        bar.line.fill.background()
        add_reveal_animations(slide, reveal_targets)
        slide.notes_slide.notes_text_frame.text = f"Source: {source.name}\n\n{item.source}"
    prs.save(output)


def export_html(title: str, slides: list[Slide], output: Path = ROOT / "tdd-presentation.html", source: Path = SOURCE) -> None:
    # Retain the reference deck's layout, colors, typography and interaction model.
    reference = (ROOT / "2026-07-01--tdd" / "tdd-present1.html").read_text(encoding="utf-8")
    css = re.search(r"<style>(.*?)</style>", reference, re.S)[1]
    extra_css = """
  * { box-sizing: border-box; }
  #sidebar { flex: 0 0 260px; }
  #sidebar[hidden] { display: none; }
  #main { min-width: 0; min-height: 0; }
  #content { min-height: 0; }
  #nav { display: grid; }
  button.slide-link { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; text-align: left; border: 0; border-bottom: 1px solid #222733; background: transparent; }
  .slide-link-title { min-width: 0; overflow-wrap: anywhere; }
  .slide-link-page { flex: 0 0 auto; margin-left: auto; color: #aaa; font-variant-numeric: tabular-nums; text-align: right; }
  button.slide-link:hover { background: #1f2633; }
  button.active-link { background: #27324a; }
  .slide { max-width: 1100px; width: 100%; margin-inline: auto; font-size: clamp(20px, 1.9vw, 26px); line-height: 1.35; overflow-wrap: anywhere; }
  .slide h2 { font-size: clamp(30px, 3.2vw, 44px); line-height: 1.15; margin: 12px 0 22px; }
  .slide ul, .slide ol { padding-left: 1.4em; margin-block: .3em; }
  .slide li > ul { color: #c4cad5; }
  .slide > ul > li > ul, .slide > ol > li > ul { font-size: .86em; }
  .slide p { margin-block: .6em; }
  .slide blockquote { border-left: 3px solid #4aa3ff; margin: 1em 0; padding-left: 1em; }
  .slide svg { display: block; max-height: calc(100dvh - 330px); width: 100%; min-height: 180px; }
  .media-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2.2fr); gap: 28px; align-items: start; }
  .media-layout img { max-width: 100%; max-height: 48vh; object-fit: contain; background: white; }
  .media-layout .slide-text { font-size: .78em; }
  .comparison { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 32px; font-size: .8em; }
  .comparison > div > ul > li { list-style: none; font-weight: bold; }
  .comparison li li { font-weight: normal; }
  .dense { font-size: .85em; }
  .source-code { font-family: Consolas, monospace; font-size: 14px; line-height: 1.45; white-space: pre; overflow-x: auto; padding: 16px; background: #0b0d12; border-left: 3px solid #4aa3ff; }
  .diagram-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); gap: 24px; align-items: start; }
  .reveal[hidden] { display: none !important; }
  .staged-comparison { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); gap: 28px; }
  .staged-comparison > .reveal:first-child { font-size: .85em; }
  a { color: #4aa3ff; }
  .tag { font-size: 12px; }
  #presentation-toolbar { display: flex; align-items: center; background: #121621; border-top: 1px solid #2a2f3a; }
  #view-controls { display: flex; gap: 6px; padding: 10px; padding-right: 0; flex-shrink: 0; }
  #view-controls button { font-size: 12px; padding: 6px 7px; }
  #controls { flex: 1; min-width: 0; align-items: center; gap: 12px; border-top: 0; }
  body.chrome-hidden #header, body.chrome-hidden #controls { display: none; }
  body.chrome-hidden #presentation-toolbar { position: fixed; bottom: 10px; left: 10px; z-index: 10; background: transparent; border: 0; }
  body.chrome-hidden #view-controls { padding: 0; }
  #counter { flex: 1; min-width: 0; text-align: center; font-size: 13px; color: #aaa; }
  button:disabled { opacity: .4; cursor: default; }
  button:focus-visible, a:focus-visible { outline: 2px solid #4aa3ff; outline-offset: 3px; }
  @media (max-width: 760px) {
    body { height: 100dvh; }
    #sidebar { flex-basis: 150px; width: 150px; }
    button.slide-link { font-size: 11px; padding: 9px 8px; }
    #content { padding: 20px 16px; }
    #header h1 { font-size: 14px; }
    #controls { gap: 6px; }
    #presentation-toolbar { flex-wrap: wrap; }
    #controls { flex-basis: 100%; }
    #controls button { font-size: 12px; padding: 6px 7px; }
    #counter { font-size: 11px; }
    .slide { font-size: 18px; }
    .slide h2 { font-size: 28px; }
    .media-layout, .comparison, .staged-comparison, .diagram-layout { grid-template-columns: minmax(0, 1fr); }
  }
  @media (prefers-reduced-motion: reduce) { .slide { animation: none; } }
  @media print {
    body { display: block; height: auto; overflow: visible; background: white; color: black; }
    #sidebar, #header, #controls, #presentation-toolbar { display: none; }
    #main, #content { display: block; overflow: visible; padding: 0; }
    .slide { display: block !important; break-after: page; padding: 20px; font-size: 20px; animation: none; }
    .slide:last-child { break-after: auto; }
    .tag, a, .slide li > ul { color: inherit; }
    .slide svg { max-height: none; }
    .reveal[hidden] { display: block !important; }
    @page { size: landscape; margin: 12mm; }
  }
"""
    def stage_html(item, blocks):
        part = Slide(item.title, item.section, "\n\n".join(blocks), blocks)
        has_diagram = "```mermaid" in part.source
        if has_diagram:
            raw = FENCE.sub(lambda m: "" if m[1].strip() == "mermaid" else m[0], part.source)
            part = Slide(item.title, item.section, raw, make_blocks(raw.splitlines()))
        images, text_item = images_and_text(part, source)
        body = "".join(block_html(block) for block in text_item.blocks)
        comparison = len(text_item.blocks) == 2 and text_item.blocks[0].startswith("- Human") and text_item.blocks[1].startswith("- AI")
        if comparison:
            body = '<div class="comparison">' + ''.join(f'<div>{block_html(block)}</div>' for block in text_item.blocks) + '</div>'
        elif len(part.source) > 700:
            body = f'<div class="dense">{body}</div>'
        if images:
            pictures = ''.join(f'<img src="data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}" alt="{html.escape(alt, quote=True)}">' for alt, path, mime, dimensions in images)
            body = f'<div class="media-layout"><div>{pictures}</div><div class="slide-text">{body}</div></div>'
        if has_diagram:
            body = f'<div class="diagram-layout"><div>{body}</div>{diagram_svg()}</div>' if part.source.strip() else diagram_svg()
        return body

    sections = []
    for i, item in enumerate(slides):
        groups = item.stages or [item.blocks]
        body = ''.join(f'<div class="reveal" data-reveal="{step}"{(" hidden" if step else "")}>{stage_html(item, blocks)}</div>' for step, blocks in enumerate(groups))
        if len(groups) > 1 and any(block.startswith("- Human") for block in item.blocks):
            body = f'<div class="staged-comparison">{body}</div>'
        sections.append(f'<section class="slide" id="slide-{i+1}" aria-labelledby="title-{i+1}" hidden><div class="tag">{html.escape(item.section)}</div><h2 id="title-{i+1}">{html.escape(item.title)}</h2>{body}</section>')
    titles = json.dumps([item.title for item in slides], ensure_ascii=False).replace("<", "\\u003c")
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>{css}{extra_css}</style>
</head>
<body>
<aside id="sidebar" aria-label="Slides"><h2>Slides</h2><nav id="nav" aria-label="Slide navigation"></nav></aside>
<main id="main">
  <header id="header"><h1>{html.escape(title)}</h1><small>{html.escape(metadata(slides))}</small><div id="progressBar" role="progressbar" aria-label="Presentation progress" aria-valuemin="1" aria-valuemax="{len(slides)}"><div id="progress"></div></div></header>
  <div id="content">{''.join(sections)}</div>
  <div id="presentation-toolbar">
    <div id="view-controls" role="group" aria-label="Presentation view">
      <button id="toggle-outline" type="button" aria-controls="sidebar" aria-expanded="true">Hide outline</button>
      <button id="toggle-chrome" type="button" aria-controls="header controls" aria-expanded="true">Hide header/footer</button>
    </div>
    <footer id="controls"><button id="prev" type="button">⬅ Prev</button><span id="counter" aria-live="polite"></span><button id="next" type="button">Next ➡</button></footer>
  </div>
</main>
<script>
const titles = {titles};
const slides = [...document.querySelectorAll('.slide')];
const stages = slides.map(slide => [...slide.querySelectorAll('[data-reveal]')]);
const revealed = slides.map(() => 0);
const nav = document.getElementById('nav');
const sidebar = document.getElementById('sidebar');
const outlineButton = document.getElementById('toggle-outline');
const chromeButton = document.getElementById('toggle-chrome');
outlineButton.addEventListener('click', () => {{
  sidebar.hidden = !sidebar.hidden;
  outlineButton.textContent = sidebar.hidden ? 'Show outline' : 'Hide outline';
  outlineButton.setAttribute('aria-expanded', String(!sidebar.hidden));
}});
chromeButton.addEventListener('click', () => {{
  const hidden = document.body.classList.toggle('chrome-hidden');
  chromeButton.textContent = hidden ? 'Show header/footer' : 'Hide header/footer';
  chromeButton.setAttribute('aria-expanded', String(!hidden));
}});
let index = 0;
titles.forEach((title, i) => {{
  const button = document.createElement('button');
  button.type = 'button'; button.className = 'slide-link';
  const titleLabel = document.createElement('span');
  titleLabel.className = 'slide-link-title'; titleLabel.textContent = title;
  const pageLabel = document.createElement('span');
  pageLabel.className = 'slide-link-page'; pageLabel.textContent = i + 1;
  button.append(titleLabel, pageLabel);
  button.setAttribute('aria-label', `${{title}}, page ${{i + 1}}`);
  button.addEventListener('click', () => go(i));
  nav.appendChild(button);
}});
const links = [...nav.children];
function render() {{
  slides.forEach((slide, i) => {{ slide.hidden = i !== index; slide.classList.toggle('active', i === index); }});
  stages.forEach((groups, i) => groups.forEach((group, step) => {{ group.hidden = step > revealed[i]; }}));
  links.forEach((link, i) => {{
    link.classList.toggle('active-link', i === index);
    if (i === index) link.setAttribute('aria-current', 'step'); else link.removeAttribute('aria-current');
  }});
  const steps = stages[index].length;
  document.getElementById('counter').textContent = `${{index + 1}} / ${{slides.length}}${{steps > 1 ? ` · Step ${{revealed[index] + 1}} / ${{steps}}` : ''}}`;
  document.getElementById('progress').style.width = `${{(index + 1) / slides.length * 100}}%`;
  document.getElementById('progressBar').setAttribute('aria-valuenow', index + 1);
  document.getElementById('prev').disabled = index === 0 && revealed[index] === 0;
  document.getElementById('next').disabled = index === slides.length - 1 && revealed[index] === steps - 1;
  links[index].scrollIntoView({{ block: 'nearest' }});
}}
function go(i, step = 0) {{
  const previous = index;
  index = Math.max(0, Math.min(slides.length - 1, i));
  revealed[index] = Math.max(0, Math.min(stages[index].length - 1, step));
  const suffix = revealed[index] ? `-step-${{revealed[index] + 1}}` : '';
  history.replaceState(null, '', `#slide-${{index + 1}}${{suffix}}`);
  render();
  if (previous !== index || revealed[index] === 0) document.getElementById('content').scrollTop = 0;
  else stages[index][revealed[index]].scrollIntoView({{ block: 'nearest' }});
}}
function next() {{
  if (revealed[index] < stages[index].length - 1) go(index, revealed[index] + 1);
  else if (index < slides.length - 1) go(index + 1);
}}
function prev() {{
  if (revealed[index] > 0) go(index, revealed[index] - 1);
  else if (index > 0) go(index - 1, stages[index - 1].length - 1);
}}
function readHash() {{
  const match = /^#slide-(\\d+)(?:-step-(\\d+))?$/.exec(location.hash);
  index = match ? Math.max(0, Math.min(slides.length - 1, Number(match[1]) - 1)) : 0;
  revealed[index] = match ? Math.max(0, Math.min(stages[index].length - 1, Number(match[2] || 1) - 1)) : 0;
  render();
}}
document.getElementById('prev').addEventListener('click', prev);
document.getElementById('next').addEventListener('click', next);
document.addEventListener('keydown', event => {{
  if (event.altKey || event.ctrlKey || event.metaKey || /INPUT|TEXTAREA|SELECT/.test(event.target.tagName)) return;
  if (['ArrowRight', 'PageDown'].includes(event.key)) {{ event.preventDefault(); next(); }}
  if (['ArrowLeft', 'PageUp'].includes(event.key)) {{ event.preventDefault(); prev(); }}
  if (event.key === 'Home') {{ event.preventDefault(); go(0); }}
  if (event.key === 'End') {{ event.preventDefault(); go(slides.length - 1, stages[slides.length - 1].length - 1); }}
}});
window.addEventListener('hashchange', readHash);
readHash();
</script>
</body>
</html>
"""
    output.write_text(page, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=ROOT / "tdd-presentation", help="Output basename without extension")
    parser.add_argument("--section-pages", action="store_true", help="One page per section, with +++ reveal steps within the page")
    args = parser.parse_args()
    deck_title, deck_slides = read_section_slides(args.source) if args.section_pages else read_slides(args.source)
    export_ppt(deck_title, deck_slides, args.output.with_suffix(".pptx"), args.source)
    export_html(deck_title, deck_slides, args.output.with_suffix(".html"), args.source)
    print(f"Exported {len(deck_slides)} slides to {args.output}.pptx and {args.output}.html")
