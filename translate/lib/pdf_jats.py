"""Heuristic PDF → JATS for short research PDFs (e.g. OpenAI tech reports).

Uses PyMuPDF text extraction. Section numbers on their own line (``1`` / ``3.1``)
followed by a title line are mapped to ``<sec>``. Figures and tables become
``<fig>`` / plain ``<p>`` blocks. Good enough for digest → translate; not a
general PDF parser.
"""

from __future__ import annotations

import html
import re
from pathlib import Path  # noqa: TC003 — used at runtime in write_pdf_bundle
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

import pymupdf

XLINK_NS = "http://www.w3.org/1999/xlink"
register_namespace("xlink", XLINK_NS)

# Top-level / subsection numbers only (rejects table scores like 83.3).
SEC_NUM_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})?)\s*$")
FIG_CAP_RE = re.compile(r"^(Figure|Fig\.?)\s+(\d+)\s*:\s*(.*)$", re.IGNORECASE)
TABLE_CAP_RE = re.compile(r"^Table\s+(\d+)\s*:\s*(.*)$", re.IGNORECASE)
REF_RE = re.compile(r"^\[(\d+)\]\s+(.*)$")
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w.-]+\.\w+$")
AFFIL_SKIP = frozenset({"openai", "google", "microsoft", "facebook", "deepmind"})


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def _normalize_pdf_text(text: str) -> str:
    # PDF often uses compatibility ligatures / soft hyphens.
    return (
        text.replace("\ufb01", "fi")
        .replace("\ufb02", "fl")
        .replace("\u00ad", "")
        .replace("ﬁ", "fi")
        .replace("ﬂ", "fl")
    )


def extract_text_lines(pdf: bytes) -> list[str]:
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    lines: list[str] = []
    for page in doc:
        for raw in page.get_text("text").splitlines():
            line = _normalize_pdf_text(raw).strip()
            if line:
                lines.append(line)
    return lines


def extract_images(pdf: bytes, out_dir: Path) -> list[str]:
    """Write unique raster images as figN.png (page order). Return basenames."""
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    out_dir.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    n = 0
    seen: set[int] = set()
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in seen:
                continue
            seen.add(xref)
            pix = pymupdf.Pixmap(doc, xref)
            if pix.n - pix.alpha > 3:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            if pix.width < 80 or pix.height < 80:
                continue
            n += 1
            name = f"fig{n}.png"
            pix.save(str(out_dir / name))
            names.append(name)
    return names


def _parse_front(lines: list[str]) -> tuple[str, str, int]:
    """Return title, abstract text, index of first body line."""
    title_parts: list[str] = []
    i = 0
    while i < len(lines):
        low = lines[i].lower()
        if low == "abstract":
            break
        if EMAIL_RE.match(lines[i]) or low in AFFIL_SKIP:
            i += 1
            continue
        # Author lines: Title Case short names without ending period of sentences
        if title_parts and (
            (lines[i][0].isupper() and len(lines[i].split()) <= 4 and "@" not in lines[i])
            or low in AFFIL_SKIP
        ):
            # stop collecting title once we hit author block; keep scanning to Abstract
            i += 1
            continue
        can_title = (not title_parts or (len(title_parts) < 3 and len(lines[i].split()) <= 8)) and (
            i < 6 and not EMAIL_RE.match(lines[i]) and low not in AFFIL_SKIP and "@" not in lines[i]
        )
        if can_title:
            words = lines[i].split()
            # Person-name lines after the first title fragment are authors, not title.
            if i > 0 and 1 <= len(words) <= 3 and all(w[0].isupper() for w in words if w):
                i += 1
                continue
            title_parts.append(lines[i])
        i += 1
    if i >= len(lines) or lines[i].lower() != "abstract":
        raise ValueError("PDF: Abstract heading not found")
    i += 1
    abs_parts: list[str] = []
    while i < len(lines):
        if SEC_NUM_RE.match(lines[i]) and i + 1 < len(lines):
            break
        abs_parts.append(lines[i])
        i += 1
    title = " ".join(title_parts).strip()
    if not title:
        raise ValueError("PDF: could not detect title")
    abstract = " ".join(abs_parts).strip()
    if not abstract:
        raise ValueError("PDF: empty abstract")
    return title, abstract, i


def _looks_like_section_title(num: str, title_line: str) -> bool:
    """True when ``num`` + ``title_line`` is a real section, not a page/table score."""
    major = int(num.split(".", 1)[0])
    if major > 12 or not re.search(r"[A-Za-z]", title_line):
        return False
    if REF_RE.match(title_line) or title_line[0].isdigit():
        return False
    if re.match(r"^(Table|Figure|Fig\.?)\b", title_line, re.IGNORECASE):
        return False
    if re.search(r"\[\d+\]", title_line):
        return False
    # Top-level: short Title-Case headings (not mid-sentence page breaks).
    if "." not in num:
        if not title_line[0].isupper() or "," in title_line:
            return False
        if len(title_line.split()) > 6:
            return False
    return True


def _better_join(lines: list[str]) -> list[str]:
    """Line-wrap aware join for body paragraphs."""
    paras: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if not buf:
            return
        text = buf[0]
        for line in buf[1:]:
            text = text[:-1] + line if text.endswith("-") else f"{text} {line}"
        paras.append(text.strip())
        buf = []

    for line in lines:
        if re.fullmatch(r"\d{1,2}", line):
            continue
        if not buf:
            buf = [line]
            continue
        prev = buf[-1]
        # Likely new paragraph: previous ends with .!? and current starts with uppercase
        # and previous line was "short" (end of visual line near margin is unreliable).
        if prev.endswith((".", "?", "!")) and line[0].isupper() and len(prev) < 70:
            flush()
            buf = [line]
        else:
            buf.append(line)
    flush()
    return paras


def pdf_to_jats(pdf: bytes, *, image_names: list[str] | None = None) -> str:
    """Convert PDF bytes to a JATS ``<article>`` XML string."""
    lines = extract_text_lines(pdf)
    title, abstract, i = _parse_front(lines)

    root = Element("article", {"article-type": "research-article"})
    front = SubElement(root, "front")
    meta = SubElement(front, "article-meta")
    tg = SubElement(meta, "title-group")
    SubElement(tg, "article-title").text = title
    abs_el = SubElement(meta, "abstract", {"id": "abstract"})
    SubElement(abs_el, "p").text = abstract

    body = SubElement(root, "body")
    back = SubElement(root, "back")
    ref_list = SubElement(back, "ref-list")
    SubElement(ref_list, "title").text = "References"

    # section stack: list of (level, element)
    stack: list[tuple[int, Element]] = [(1, body)]
    para_buf: list[str] = []
    fig_imgs = list(image_names or [])
    fig_img_i = 0
    in_refs = False
    pid = 0
    sid = 0
    fid = 0
    rid = 0

    def flush_paras(parent: Element) -> None:
        nonlocal pid, para_buf
        for text in _better_join(para_buf):
            pid += 1
            SubElement(parent, "p", {"id": f"p{pid}"}).text = text
        para_buf = []

    def current_parent() -> Element:
        return stack[-1][1]

    while i < len(lines):
        line = lines[i]

        # Lone digits are page numbers unless the next line is a section title.
        if re.fullmatch(r"\d{1,2}", line):
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if not (nxt and _looks_like_section_title(line, nxt)):
                i += 1
                continue

        mref = REF_RE.match(line)
        if mref and (in_refs or int(mref.group(1)) == 1):
            flush_paras(current_parent())
            in_refs = True
            # collect continuation lines
            num, rest = mref.group(1), mref.group(2)
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if REF_RE.match(nxt) or SEC_NUM_RE.match(nxt):
                    break
                if re.fullmatch(r"\d{1,2}", nxt):
                    i += 1
                    continue
                rest = f"{rest} {nxt}"
                i += 1
            rid += 1
            ref = SubElement(ref_list, "ref", {"id": f"bib{rid}"})
            SubElement(ref, "label").text = num
            SubElement(ref, "mixed-citation").text = f"[{num}] {rest.strip()}"
            continue

        if in_refs:
            i += 1
            continue

        mfig = FIG_CAP_RE.match(line)
        if mfig:
            flush_paras(current_parent())
            cap = mfig.group(3)
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if (
                    SEC_NUM_RE.match(nxt)
                    or FIG_CAP_RE.match(nxt)
                    or TABLE_CAP_RE.match(nxt)
                    or REF_RE.match(nxt)
                ):
                    break
                if re.fullmatch(r"\d{1,2}", nxt):
                    i += 1
                    continue
                # stop if looks like body paragraph start after short caption wrap
                if cap and nxt[0].isupper() and len(nxt) > 60 and cap.endswith((".", ")", ";")):
                    break
                cap = f"{cap} {nxt}".strip()
                i += 1
                if cap.endswith("."):
                    break
            fid += 1
            fig = SubElement(current_parent(), "fig", {"id": f"fig{fid}"})
            SubElement(fig, "label").text = f"Fig. {mfig.group(2)}"
            cap_el = SubElement(fig, "caption")
            SubElement(cap_el, "p").text = cap.strip()
            # Attach next unused extracted images (often left/right panels).
            for _ in range(2):
                if fig_img_i < len(fig_imgs):
                    g = SubElement(fig, "graphic")
                    g.set(f"{{{XLINK_NS}}}href", fig_imgs[fig_img_i])
                    fig_img_i += 1
            continue

        mtab = TABLE_CAP_RE.match(line)
        if mtab:
            flush_paras(current_parent())
            cap = mtab.group(2)
            i += 1
            # Consume wrapped caption only (table body is lossy in text extraction).
            while i < len(lines):
                nxt = lines[i]
                if (
                    SEC_NUM_RE.match(nxt)
                    or FIG_CAP_RE.match(nxt)
                    or TABLE_CAP_RE.match(nxt)
                    or REF_RE.match(nxt)
                ):
                    break
                if re.fullmatch(r"\d{1,2}", nxt):
                    i += 1
                    continue
                if nxt[0].isupper() and len(nxt) > 50 and cap.endswith((".", "art", "art.")):
                    break
                # stop at likely table header junk / next section prose
                if re.match(r"^(Method|Dataset|Test|Dev|Results)\b", nxt):
                    break
                cap = f"{cap} {nxt}".strip()
                i += 1
                if len(cap) > 200:
                    break
            pid += 1
            SubElement(
                current_parent(), "p", {"id": f"p{pid}"}
            ).text = f"[Table {mtab.group(1)}] {cap.strip()}"
            continue

        msec = SEC_NUM_RE.match(line)
        if msec and i + 1 < len(lines) and not REF_RE.match(lines[i + 1]):
            num = msec.group(1)
            title_line = lines[i + 1]
            if _looks_like_section_title(num, title_line):
                flush_paras(current_parent())
                level = num.count(".") + 2  # 1 -> h2, 1.1 -> h3
                while stack and stack[-1][0] >= level:
                    stack.pop()
                parent = stack[-1][1]
                sid += 1
                sec = SubElement(parent, "sec", {"id": f"sec{sid}"})
                SubElement(sec, "title").text = f"{num} {title_line}"
                stack.append((level, sec))
                i += 2
                continue

        para_buf.append(line)
        i += 1

    flush_paras(current_parent())
    return tostring(root, encoding="unicode")


def write_pdf_bundle(pdf: bytes, source_xml: Path, assets_dir: Path) -> list[str]:
    """Extract images to assets_dir and write source.xml. Return image basenames."""
    names = extract_images(pdf, assets_dir)
    xml = pdf_to_jats(pdf, image_names=names)
    source_xml.parent.mkdir(parents=True, exist_ok=True)
    tmp = source_xml.with_suffix(".xml.tmp")
    tmp.write_text(xml, encoding="utf-8")
    tmp.replace(source_xml)
    return names
