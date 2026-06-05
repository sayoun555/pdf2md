#!/usr/bin/env python3
"""전자책 PDF를 로컬/오프라인에서 Markdown(.md)으로 변환한다.

- 본문: pymupdf4llm 으로 폰트 크기 기반 헤더/표/문단 구조화
- 가독성: 반복 머리말·꼬리말 / 쪽번호 / 줄끝 하이픈 / 합자 / 과도한 빈 줄 정리
- 이미지: 폴더 추출(상대경로 참조) 또는 base64 인라인 임베딩
- 목차(TOC): 마크다운 헤더(우선) 또는 PDF 내장 북마크로 클릭 가능한 목차 생성
- OCR: 스캔본(이미지 PDF)을 Tesseract로 텍스트화 (--ocr)
- 분할: 챕터별 .md 파일로 나누기 (--split)
- 점검: 표/수식/이미지 품질 리포트

실행 시점에는 인터넷이 전혀 필요 없다. (OCR만 Tesseract 별도 설치 필요)

예)
    python pdf2md.py book.pdf                      # output/book.md + output/images/
    python pdf2md.py book.pdf --embed-images       # 단일 파일(.md)로 완결
    python pdf2md.py book.pdf --split              # 챕터별 파일로 분할
    python pdf2md.py scan.pdf --ocr --lang kor+eng # 스캔본 OCR
    python pdf2md.py book.pdf --report             # 품질 리포트 파일 생성
    python pdf2md.py book.pdf --raw                # 가독성 후처리 끔
"""
from __future__ import annotations

import argparse
import base64
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

try:
    import fitz  # PyMuPDF
    import pymupdf4llm
except ImportError as e:  # 친절한 안내
    sys.exit(
        f"의존성이 없습니다 ({e.name}). 먼저 설치하세요:\n"
        "    python3 -m venv .venv && source .venv/bin/activate\n"
        "    pip install -r requirements.txt"
    )

# 단독 실행파일(PyInstaller)로 묶였을 때, 동봉된 OCR 언어데이터를 쓰도록 설정한다.
# 덕분에 Tesseract를 따로 설치하지 않아도 OCR 품질로 변환된다.
if getattr(sys, "frozen", False):
    _bundled = os.path.join(getattr(sys, "_MEIPASS", ""), "tessdata")
    if os.path.isdir(_bundled):
        os.environ.setdefault("TESSDATA_PREFIX", _bundled)

# 합자(ligature) → 일반 문자. 검색/복사/가독성 개선.
LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
}


# ---------------------------------------------------------------- 가독성 후처리

def normalize_unicode(s: str) -> str:
    """합자/특수 공백/소프트하이픈 정리 + NFC 정규화."""
    for k, v in LIGATURES.items():
        s = s.replace(k, v)
    s = s.replace("­", "")   # soft hyphen 제거
    s = s.replace(" ", " ")  # nbsp → 일반 공백
    s = s.replace("​", "")   # zero-width space 제거
    return unicodedata.normalize("NFC", s)


def dehyphenate(s: str) -> str:
    """줄 끝에서 하이픈으로 잘린 영어 단어를 다시 붙인다. informa-\\ntion → information."""
    return re.sub(r"([A-Za-z])-[ \t]*\n[ \t]*([a-z])", r"\1\2", s)


def collapse_blanks(s: str) -> str:
    """줄 끝 공백 제거 + 3줄 이상 연속 빈 줄을 1줄로."""
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip() + "\n"


def strip_page_numbers(s: str) -> str:
    """본문 중간에 홀로 떠 있는 쪽번호 줄(예: '12', '- 12 -')을 제거."""
    return re.sub(r"(?m)^[ \t]*[-–—]?[ \t]*\d{1,4}[ \t]*[-–—]?[ \t]*$\n?", "", s)


def _furniture_key(line: str) -> str:
    """반복 머리말/꼬리말 비교용 키. 숫자(쪽번호)는 #으로 치환해 같은 것으로 묶음."""
    return re.sub(r"\d+", "#", line.strip())


def detect_furniture(chunks: list, top: int = 2, bot: int = 2) -> set:
    """여러 페이지의 상/하단에 반복되는 머리말·꼬리말 줄을 찾아낸다."""
    npages = len(chunks)
    counter: Counter = Counter()
    for ch in chunks:
        lines = [l for l in ch["text"].splitlines()
                 if l.strip() and not l.lstrip().startswith('<a id="page-')]
        for l in set(lines[:top] + lines[-bot:]):
            if l.lstrip().startswith(("#", "![")):
                continue  # 진짜 헤더·이미지 참조는 보호
            key = _furniture_key(l)
            if 0 < len(key) <= 60:
                counter[key] += 1
    threshold = max(3, int(npages * 0.3))  # 전체 페이지의 30% 이상 반복 시 furniture
    return {k for k, c in counter.items() if c >= threshold}


def strip_furniture(text: str, furniture: set, top: int = 2, bot: int = 2) -> str:
    """페이지 상/하단의 반복 머리말·꼬리말 줄만 제거(본문 한가운데는 건드리지 않음)."""
    lines = text.splitlines()
    non_empty = [i for i, l in enumerate(lines)
                 if l.strip() and not l.lstrip().startswith('<a id="page-')]
    edge = set(non_empty[:top] + non_empty[-bot:])
    out = []
    for i, l in enumerate(lines):
        if i in edge and not l.lstrip().startswith(("#", "![")) and _furniture_key(l) in furniture:
            continue
        out.append(l)
    return "\n".join(out)


def clean_markdown(chunks: list) -> str:
    """페이지 단위 청크를 가독성 좋은 하나의 마크다운으로 합친다."""
    furniture = detect_furniture(chunks) if len(chunks) >= 4 else set()
    parts = []
    for ch in chunks:
        t = ch["text"]
        if furniture:
            t = strip_furniture(t, furniture)
        parts.append(normalize_unicode(t).strip())
    md = "\n\n".join(p for p in parts if p)
    md = dehyphenate(md)
    md = strip_page_numbers(md)
    return collapse_blanks(md)


# ----------------------------------------------------------------------- OCR

def ocr_pages(doc, lang: str, dpi: int = 300) -> list:
    """스캔본 PDF를 Tesseract로 페이지별 OCR → 청크 목록."""
    tessdata = os.environ.get("TESSDATA_PREFIX")
    out = []
    for i, page in enumerate(doc):
        try:
            tp = page.get_textpage_ocr(language=lang, dpi=dpi, full=True, tessdata=tessdata)
        except Exception as e:  # Tesseract 미설치/tessdata 경로 문제
            sys.exit(
                "OCR 실패 — Tesseract가 필요합니다:\n"
                "    brew install tesseract tesseract-lang\n"
                "    export TESSDATA_PREFIX=\"$(brew --prefix)/share/tessdata\"\n"
                f"원인: {e}"
            )
        out.append({"text": f'<a id="page-{i + 1}"></a>\n\n' + page.get_text("text", textpage=tp)})
        print(f"OCR {i + 1}/{doc.page_count}", file=sys.stderr)
    return out


# ------------------------------------------------------------------ 이미지 추출

def extract_page_images(doc, page, page_index: int, img_dir: Path, embed: bool, seen: dict) -> list:
    """페이지의 래스터 이미지를 직접 추출해 마크다운 참조를 만든다.

    pymupdf4llm은 OCR 가능 빌드에서 이미지를 글자로 OCR해버려 그림이 누락되므로
    PyMuPDF(get_images + extract_image)로 직접 뽑아 확실히 보존한다.
    같은 이미지(xref)는 한 번만 저장하고 재참조한다(반복 로고 중복 방지).
    """
    refs = []
    page_area = page.rect.width * page.rect.height
    for info in page.get_images(full=True):
        xref = info[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        if rects and page_area > 0:
            cover = max(r.width * r.height for r in rects) / page_area
            if cover >= 0.8:
                continue  # 페이지 전체를 덮는 스캔 이미지는 '그림'이 아님 → 제외
        try:
            d = doc.extract_image(xref)
        except Exception:
            continue
        if d.get("width", 0) < 32 or d.get("height", 0) < 32:
            continue  # 아이콘/장식 등 초소형 이미지 제외
        ext = d["ext"]
        if embed:
            b64 = base64.b64encode(d["image"]).decode()
            refs.append(f"![figure](data:image/{ext};base64,{b64})")
        else:
            if xref not in seen:
                name = f"p{page_index + 1:03d}-{len(seen) + 1}.{ext}"
                seen[xref] = name
                img_dir.mkdir(parents=True, exist_ok=True)
                (img_dir / name).write_bytes(d["image"])
            refs.append(f"![figure](images/{seen[xref]})")
    return refs


# ---------------------------------------------------------------------- 목차(TOC)

def slugify(title: str) -> str:
    """GitHub 스타일 앵커 슬러그. 한글/영문/숫자 유지, 나머지는 하이픈."""
    s = title.strip().lower()
    s = re.sub(r"[^\w\s가-힣-]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s.strip("-")


def build_toc(md: str, bookmarks: list) -> str:
    """클릭 가능한 목차 블록 생성.

    1순위: 충실한 PDF 내장 북마크 → 페이지 앵커(#page-N)로 링크. 책의 실제 구조라 가장 정확.
    2순위: md 본문 헤더(#/##/###) — 앵커가 실제 존재해 링크가 확실히 동작.
    """
    if bookmarks and len(bookmarks) >= 5:
        lines = ["# 목차", ""]
        for level, title, page in bookmarks:
            t = title.strip()
            if t:
                lines.append("  " * max(0, level - 1) + f"- [{t}](#page-{page})")
        return "\n".join(lines)

    headers = []
    for line in md.splitlines():
        m = re.match(r"^(#{1,3})\s+(.*\S)\s*$", line)
        if m:
            headers.append((len(m.group(1)) - 1, m.group(2)))

    lines = ["# 목차", ""]
    if len(headers) >= 2:
        seen: dict = {}
        for depth, title in headers:
            slug = slugify(title)
            if slug in seen:  # 중복 헤더는 -1, -2 ... (GitHub 규칙)
                seen[slug] += 1
                slug = f"{slug}-{seen[slug]}"
            else:
                seen[slug] = 0
            lines.append("  " * depth + f"- [{title}](#{slug})")
    elif bookmarks:
        for level, title, page in bookmarks:
            lines.append("  " * (level - 1) + f"- {title} _(p.{page})_")
    else:
        return ""
    return "\n".join(lines)


def restructure_with_bookmarks(md: str, bookmarks: list) -> str:
    """스캔본처럼 자동 헤더가 과다할 때, 가짜 헤더를 평문으로 내리고
    신뢰할 수 있는 PDF 북마크를 페이지 앵커 위치에 진짜 헤더로 재삽입한다.

    (`#include`/`#define` 등 C 전처리기는 '#' 뒤에 공백이 없어 영향받지 않는다.)
    """
    md = re.sub(r"(?m)^#{1,6}[ \t]+", "", md)  # 자동 헤더 → 평문

    by_page: dict = {}
    for level, title, page in bookmarks:
        if title.strip():
            by_page.setdefault(page, []).append((level, title.strip()))

    def repl(m):
        heads = by_page.get(int(m.group(1)), [])
        ins = "".join(f'\n\n{"#" * min(level + 1, 6)} {t}' for level, t in heads)
        return m.group(0) + ins

    return re.sub(r'(?m)^<a id="page-(\d+)"></a>', repl, md)


def _norm(s: str, digits: bool = True) -> str:
    return re.sub(r"[^A-Za-z0-9]" if digits else r"[^A-Za-z]", "", s).upper()

_RUN_HEADER = [
    re.compile(r"^\s*\d{1,4}\s+[A-Z][A-Z0-9 .,'\"&/\-—]+$"),   # "6 A TUTORIAL INTRODUCTION"
    re.compile(r"^[A-Z][A-Z0-9 .,'\"&/\-—]+\s+\d{1,4}\s*$"),   # "GETTING STARTED   7"
    re.compile(r"^CHAPTER\s*\d+\s*$", re.I),                    # "CHAPTER1"
    re.compile(r"^SECTION\s+[A-Za-z0-9]+\.[A-Za-z0-9]+\s*$", re.I),  # "SECTION l.1"
]


def strip_scan_noise(md: str, bookmarks: list) -> str:
    """스캔본 OCR 잔여 노이즈 제거 — 북마크 제목을 기준으로:
    (1) 본문에 중복 인쇄된 장/절 제목 줄 제거  (2) 페이지 가장자리 러닝헤더/풋터 제거.
    """
    exact, nod = set(), set()
    for _lvl, title, _pg in bookmarks:
        t = title.strip()
        if not t:
            continue
        exact.add(_norm(t))
        nod.add(_norm(t, digits=False))
        tail = re.sub(r"^(CHAPTER\s+\d+\s*[:.]?\s*|[A-Za-z]?\d+(\.\d+)*\s+)", "", t)  # 설명부만
        nod.add(_norm(tail, digits=False))

    def clean_block(seg: str) -> str:
        lines = seg.split("\n")
        content = [i for i, l in enumerate(lines)
                   if l.strip() and not l.lstrip().startswith(("#", "![", "<a"))]
        edge = set(content[:3]) | set(content[-2:])
        keep = []
        for i, l in enumerate(lines):
            s = l.strip()
            if s and not l.lstrip().startswith(("#", "![", "<a")):
                if len(s) <= 60 and _norm(s) in exact:
                    continue  # 중복 인쇄된 제목
                if i in edge and (any(p.match(s) for p in _RUN_HEADER)
                                  or (len(_norm(s, False)) >= 5 and _norm(s, False) in nod)):
                    continue  # 러닝헤더/풋터
            keep.append(l)
        return "\n".join(keep)

    parts = re.split(r'(?m)^(<a id="page-\d+"></a>)$', md)
    return "".join(p if p.startswith('<a id="page-') else clean_block(p) for p in parts)


# ------------------------------------------------------------------ 챕터 분할

def safe_filename(title: str, maxlen: int = 40) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', "", title).strip()
    s = re.sub(r"\s+", "-", s)
    s = s[:maxlen].strip("-")
    return s or "section"


def split_chapters(md: str) -> list | None:
    """가장 높은 헤더 레벨을 기준으로 (제목, 본문) 섹션 목록으로 분할."""
    levels = [len(m.group(1)) for m in re.finditer(r"(?m)^(#{1,6})\s", md)]
    if not levels:
        return None
    lvl = min(levels)
    pat = re.compile(rf"(?m)^#{{{lvl}}}\s+(.*\S)\s*$")
    matches = list(pat.finditer(md))
    if len(matches) < 2:
        return None

    sections = []
    if matches[0].start() > 0:
        pre = md[: matches[0].start()].strip()
        if pre:
            sections.append(("서문", pre))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        sections.append((m.group(1).strip(), md[m.start():end].strip()))
    return sections


def write_split(base: Path, md: str, doc_title: str) -> int | None:
    sections = split_chapters(md)
    if not sections:
        return None
    index = [f"# {doc_title or base.name}", "", "## 목차", ""]
    for i, (title, body) in enumerate(sections):
        fname = f"{i:02d}-{safe_filename(title)}.md"
        (base / fname).write_text(body.rstrip() + "\n", encoding="utf-8")
        index.append(f"- [{title}]({fname})")
    (base / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return len(sections)


# ------------------------------------------------------------------ 품질 점검

_MATH = set("∑∫√≤≥≈≠±×÷∞∂∇∈∉⊂⊆∪∩→←↔⇒⇔αβγδεθλμνπρστφψωΣΠΩ")


def quality_report(md: str) -> dict:
    lines = md.splitlines()
    headings = sum(1 for l in lines if re.match(r"^#{1,6}\s", l))
    images = len(re.findall(r"!\[[^\]]*\]\(", md))

    tables, bad_tables, bad_lines = 0, 0, []
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|"):
            start, block = i, []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                block.append(lines[i])
                i += 1
            if len(block) >= 2:
                tables += 1
                cols = [l.count("|") for l in block]
                if len(set(cols)) > 1:
                    bad_tables += 1
                    bad_lines.append(start + 1)
        else:
            i += 1

    formula_lines = [
        n + 1 for n, l in enumerate(lines) if sum(c in _MATH for c in l) >= 2
    ]
    return {
        "headings": headings,
        "images": images,
        "tables": tables,
        "bad_tables": bad_tables,
        "bad_table_lines": bad_lines,
        "formula_lines": formula_lines,
    }


def print_report(r: dict) -> None:
    print(
        f"📊 점검: 헤더 {r['headings']} · 표 {r['tables']}(의심 {r['bad_tables']}) "
        f"· 이미지 {r['images']} · 수식의심 {len(r['formula_lines'])}줄"
    )
    if r["bad_tables"]:
        print(f"   ⚠️ 열 수가 안 맞는 표 {r['bad_tables']}개 (md 줄 {r['bad_table_lines'][:10]}) — 수동 확인 권장", file=sys.stderr)
    if r["formula_lines"]:
        print("   ⚠️ 수식 의심 줄 존재 — 깨지면 이미지(옵션 A/B)로 보존 권장", file=sys.stderr)


def write_report_file(path: Path, r: dict) -> None:
    lines = [
        "# 변환 품질 리포트", "",
        f"- 헤더: {r['headings']}",
        f"- 이미지: {r['images']}",
        f"- 표: {r['tables']} (열 수 불일치 의심 {r['bad_tables']})",
        f"- 수식 의심 줄: {len(r['formula_lines'])}",
        "",
    ]
    if r["bad_table_lines"]:
        lines += ["## 점검 필요 — 표 (md 줄 번호)", "", *[f"- L{n}" for n in r["bad_table_lines"]], ""]
    if r["formula_lines"]:
        lines += ["## 점검 필요 — 수식 의심 (md 줄 번호)", "", *[f"- L{n}" for n in r["formula_lines"][:50]], ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ HTML 출력

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: light dark; }}
body {{ max-width: 820px; margin: 2rem auto; padding: 0 1.1rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif;
  line-height: 1.75; color: #222; word-break: keep-all; }}
h1,h2,h3,h4,h5,h6 {{ line-height: 1.3; margin-top: 1.7em; }}
h1 {{ border-bottom: 2px solid #ddd; padding-bottom: .3em; }}
h2 {{ border-bottom: 1px solid #eee; padding-bottom: .2em; }}
a {{ color: #0066cc; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
img {{ max-width: 100%; height: auto; display: block; margin: 1.2em auto; }}
pre {{ background: #f5f5f5; padding: 1em; overflow-x: auto; border-radius: 6px; }}
code {{ background: #f0f0f0; padding: .1em .35em; border-radius: 3px;
  font-family: "SF Mono", Menlo, Consolas, monospace; font-size: .9em; }}
pre code {{ background: none; padding: 0; }}
table {{ border-collapse: collapse; margin: 1em 0; }}
th,td {{ border: 1px solid #ccc; padding: .4em .7em; }}
blockquote {{ border-left: 4px solid #ddd; margin: 1em 0; padding-left: 1em; color: #666; }}
@media (prefers-color-scheme: dark) {{
  body {{ color: #ddd; background: #1a1a1a; }}
  pre, code {{ background: #2a2a2a; }} a {{ color: #5aa3ff; }}
  h1,h2 {{ border-color: #333; }} blockquote {{ color: #999; border-color: #444; }}
}}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def md_to_html(md_text: str, title: str) -> str:
    """정리된 마크다운을 자체완결 HTML 한 파일로 변환(이미지·스타일 내장)."""
    try:
        import markdown
    except ImportError:
        sys.exit("HTML 출력에는 markdown 패키지가 필요합니다:  pip install markdown")
    import html as _html
    body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )
    return HTML_TEMPLATE.format(title=_html.escape(title or "전자책"), body=body)


# ----------------------------------------------------------------------- 변환 본체

def convert(pdf_path, out_path, embed=False, images=True, toc=True, clean=True,
            ocr=False, lang="kor+eng", split=False, report=False) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base = (out_path.parent / out_path.stem) if split else out_path.parent
    base.mkdir(parents=True, exist_ok=True)
    img_dir = base / "images"

    doc = fitz.open(pdf_path)

    if ocr:
        chunks = ocr_pages(doc, lang)
    else:
        sample = "".join(doc[i].get_text() for i in range(min(3, doc.page_count)))
        if not sample.strip():
            print(
                "⚠️  텍스트가 추출되지 않습니다. 스캔본일 수 있어요. → `--ocr` 옵션을 써보세요.",
                file=sys.stderr,
            )
        raw = pymupdf4llm.to_markdown(doc, page_chunks=True, show_progress=True)
        chunks, seen = [], {}
        for idx, ch in enumerate(raw):
            text = ch["text"]
            # pymupdf4llm이 비면(이미지 페이지로 오판 등) 임베디드 텍스트 레이어로 폴백.
            # 이 덕분에 '텍스트 레이어 있는 스캔본'은 OCR(Tesseract) 없이도 변환된다.
            if idx < doc.page_count and len(text.strip()) < 20:
                native = doc[idx].get_text("text")
                if len(native.strip()) > 20:
                    text = native
            if images and idx < doc.page_count:
                refs = extract_page_images(doc, doc[idx], idx, img_dir, embed, seen)
                if refs:
                    text = text.rstrip() + "\n\n" + "\n\n".join(refs) + "\n"
            chunks.append({"text": f'<a id="page-{idx + 1}"></a>\n\n' + text})

    md = clean_markdown(chunks) if clean else "\n\n".join(c["text"].strip() for c in chunks)

    # 스캔본 보정: 북마크가 충실한데 자동 헤더가 과다하면 북마크 구조로 재구성
    bookmarks = doc.get_toc()
    if clean and bookmarks and len(bookmarks) >= 5:
        auto = len(re.findall(r"(?m)^#{1,6}[ \t]", md))
        # 자동 헤더가 너무 많거나(OCR 과다검출) 너무 적으면(텍스트레이어 폴백) 북마크 구조 사용
        if auto > 1.5 * len(bookmarks) or auto < 0.5 * len(bookmarks):
            md = restructure_with_bookmarks(md, bookmarks)
            md = collapse_blanks(strip_scan_noise(md, bookmarks))
            print(f"ℹ️  스캔본 감지: 자동 헤더 {auto}개 → 북마크 {len(bookmarks)}개 구조 재구성 + 노이즈 정리", file=sys.stderr)

    title = ((doc.metadata or {}).get("title") or "").strip()
    head = f"# {title}\n\n" if 0 < len(title) < 100 else ""

    r = quality_report(md)

    if split:
        n = write_split(base, md, title)
        if n is None:
            print("⚠️ 분할할 헤더를 못 찾아 단일 파일로 저장합니다.", file=sys.stderr)
            split = False
        else:
            print(f"✅ 분할 완료 → {base}/  (index.md + 챕터 {n}개)")

    if not split:
        block = build_toc(md, bookmarks) if toc else ""
        body = (head + block + "\n\n---\n\n" + md) if block else (head + md)
        out_path.write_text(body, encoding="utf-8")
        where = "(.md 단일 파일)" if embed else (f"(이미지: {img_dir}/)" if images else "(텍스트만)")
        tag = " · ".join(filter(None, ["OCR" if ocr else "", "가독성 정리" if clean else "", "목차" if block else ""])) or "원본"
        print(f"✅ 변환 완료 → {out_path}  {where}  [{tag}]")

    print_report(r)
    if report:
        rp = base / (out_path.stem + ".report.md")
        write_report_file(rp, r)
        print(f"📄 리포트 → {rp}")


def main() -> None:
    p = argparse.ArgumentParser(description="전자책 PDF를 오프라인에서 Markdown으로 변환")
    p.add_argument("pdf", type=Path, help="입력 PDF 경로")
    p.add_argument("-o", "--output", type=Path, help="출력 .md 경로 (기본: output/<이름>.md)")
    p.add_argument("--embed-images", action="store_true", help="이미지를 base64로 .md에 임베딩(단일 파일)")
    p.add_argument("--no-images", action="store_true", help="이미지 제외(텍스트만)")
    p.add_argument("--no-toc", action="store_true", help="목차 생략")
    p.add_argument("--raw", action="store_true", help="가독성 후처리 끔(추출 원본 그대로)")
    p.add_argument("--ocr", action="store_true", help="스캔본을 Tesseract로 OCR")
    p.add_argument("--lang", default="kor+eng", help="OCR 언어 (기본: kor+eng)")
    p.add_argument("--split", action="store_true", help="챕터별 .md 파일로 분할")
    p.add_argument("--report", action="store_true", help="품질 리포트 파일(.report.md) 생성")
    args = p.parse_args()

    if not args.pdf.exists():
        sys.exit(f"입력 파일을 찾을 수 없습니다: {args.pdf}")

    out = args.output or Path("output") / (args.pdf.stem + ".md")

    convert(
        pdf_path=args.pdf,
        out_path=out,
        embed=args.embed_images,
        images=not args.no_images,
        toc=not args.no_toc,
        clean=not args.raw,
        ocr=args.ocr,
        lang=args.lang,
        split=args.split,
        report=args.report,
    )


if __name__ == "__main__":
    main()
