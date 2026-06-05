# 전자책 PDF → Markdown 변환기 (로컬 / 오프라인)

## 1. 목표

전자책 PDF를 **인터넷 없이 로컬에서** 깔끔한 `.md`로 변환한다.

- ✅ 본문 텍스트 추출 + 마크다운 구조화
- ✅ **목차(TOC)** 자동 생성 (클릭 가능한 링크)
- ✅ **그림(이미지)** 추출 + 마크다운에 임베딩
- ✅ 외부 API / 클라우드 / 인터넷 **불필요**

---

## 2. 핵심 질문 답변

### Q1. 목차 되나요?
가능. 두 가지 소스를 사용:
1. **PDF 내장 북마크(outline)** — 대부분의 전자책에 들어있음. `doc.get_toc()`로 `[레벨, 제목, 페이지]` 목록을 바로 얻음.
2. **폰트 크기 기반 제목 감지** — 북마크가 없으면 폰트 통계로 큰 글씨를 제목(`#`, `##`)으로 변환.

→ 변환된 헤더로 **클릭 가능한 목차**를 `.md` 상단에 자동 삽입.
GitHub/Obsidian/VS Code 등 대부분의 뷰어에서 `- [1장 제목](#1장-제목)` 앵커 링크가 동작.

### Q2. 그림은 어떻게?
세 가지 옵션 (기본값은 **A**):

| 옵션 | 방식 | 장점 | 단점 |
|------|------|------|------|
| **A. 폴더 참조** | `images/`에 추출 후 `![](images/img-1.png)` | `.md` 가볍고 편집 쉬움 | 파일+폴더 같이 이동해야 함 |
| **B. base64 임베딩** | `.md` 안에 이미지를 직접 박음 | **파일 1개로 완결**, 인터넷·폴더 불필요 | 파일 용량 커짐 |
| **C. 텍스트만** | 그림 무시 | 가장 가벼움 | 그림 손실 |

### Q3. 인터넷 없이 기본 임베딩 형태로 되나요?
**네.** `pymupdf4llm`은 ML 모델/네트워크 없이 순수 로컬 휴리스틱으로 동작.
base64 임베딩(`옵션 B`)을 쓰면 `.md` 단 한 파일로 그림까지 전부 표시됨 → 진짜 오프라인 완결.

---

## 3. 기술 스택 (전부 오프라인)

> **스택 결정: Python (`pymupdf4llm`)**
> Rust(`mupdf`/`pdfium-render`)도 검토함 — 단일 바이너리·속도는 매력적이나,
> "폰트크기→헤더, 표 감지, 문단 병합" 같은 **마크다운 구조화 휴리스틱을 직접 구현해야** 함.
> `pymupdf4llm`은 이 부분이 이미 튜닝돼 있어 **최소 노력으로 고품질 결과** → Python 채택.
> (입력은 PDF 확정)

| 용도 | 라이브러리 | 비고 |
|------|-----------|------|
| PDF→MD 핵심 변환 | `pymupdf4llm` | 헤더/표/이미지 자동 처리, 모델 불필요 |
| PDF 저수준 처리 | `PyMuPDF (fitz)` | 북마크·이미지 추출 |
| (선택) 스캔본 OCR | `pytesseract` + Tesseract | 이미지로만 된 PDF용 |
| 언어 | Python 3.10+ | PDF 도구 생태계가 가장 성숙 |

> 스캔된(이미지만 있는) 전자책이 아니라면 OCR 없이 동작. 텍스트 PDF가 기본 가정.

---

## 4. 동작 흐름

```
입력 PDF
   │
   ├─► [1] 북마크 추출 (doc.get_toc())  ─────────► 목차 데이터
   │
   ├─► [2] pymupdf4llm.to_markdown()
   │        ├─ 폰트 크기 → 헤더(#/##/###)
   │        ├─ 본문 텍스트 → 마크다운
   │        ├─ 표 → 마크다운 테이블
   │        └─ 이미지 → 추출(write_images)
   │
   ├─► [3] 이미지 후처리
   │        ├─ A: images/ 폴더 참조 (기본)
   │        └─ B: base64 인라인 임베딩
   │
   ├─► [4] 목차(TOC) 블록 생성 → 문서 상단 삽입
   │
   └─► 출력: book.md  (+ images/ 폴더 또는 단일 파일)
```

---

## 5. 디렉토리 구조

```
sion/
├── PLAN.md                 # 이 문서
├── pdf2md.py               # 변환 스크립트 (CLI)
├── requirements.txt        # 의존성
├── README.md               # 사용법
└── output/
    ├── book.md             # 변환 결과
    └── images/             # 옵션 A일 때 추출 이미지
        ├── img-1.png
        └── img-2.png
```

---

## 6. CLI 인터페이스 (설계)

```bash
# 기본: 이미지 폴더 참조 방식
python pdf2md.py book.pdf -o output/book.md

# base64 임베딩 (파일 1개로 완결)
python pdf2md.py book.pdf -o output/book.md --embed-images

# 목차 생략
python pdf2md.py book.pdf -o output/book.md --no-toc

# 그림 무시 (텍스트만)
python pdf2md.py book.pdf -o output/book.md --no-images

# 스캔본 OCR (한국어+영어)
python pdf2md.py scan.pdf -o out.md --ocr --lang kor+eng
```

| 플래그 | 기능 | 기본값 |
|--------|------|--------|
| `-o, --output` | 출력 경로 | `output/<원본이름>.md` |
| `--embed-images` | base64 인라인 임베딩 | off (폴더 참조) |
| `--no-images` | 이미지 제외 | off |
| `--no-toc` | 목차 생략 | off |
| `--raw` | 가독성 후처리 끔 | off |
| `--split` | 챕터별 파일 분할 | off |
| `--report` | 품질 리포트 파일 생성 | off |
| `--ocr` | 스캔본 OCR 사용 | off |
| `--lang` | OCR 언어 | `kor+eng` |

---

## 7. 구현 단계 (Phase)

### Phase 1 — 기본 변환 (MVP)
- [ ] `requirements.txt` + 가상환경
- [ ] `pymupdf4llm.to_markdown()`으로 텍스트→md
- [ ] 결과 파일 저장
- **검증**: 텍스트 PDF가 읽을 만한 md로 나오는지 확인

### Phase 2 — 이미지 처리
- [ ] `write_images=True`로 `images/` 추출 + 상대경로 참조 (옵션 A)
- [ ] `--embed-images`: 추출 이미지를 base64로 인라인 치환 (옵션 B)
- [ ] `--no-images` 처리
- **검증**: 뷰어에서 그림이 보이는지, 임베딩 시 단일 파일로 열리는지

### Phase 3 — 목차(TOC)
- [ ] `doc.get_toc()`로 북마크 추출
- [ ] 북마크 없으면 md 헤더 파싱으로 대체
- [ ] 앵커 슬러그 생성 → 클릭 가능한 목차 블록 상단 삽입
- **검증**: 목차 링크 클릭 시 해당 섹션으로 이동

### Phase 4 — 가독성 다듬기 ✅ (구현됨, `--raw`로 끔)
가독성을 떨어뜨리는 PDF 추출 노이즈를 후처리로 정리:
- [x] **반복 머리말·꼬리말 제거** — 페이지 30%+ 상/하단에 반복되는 줄(책 제목·장 제목 러닝헤더). 진짜 `#` 헤더는 보호
- [x] **떠다니는 쪽번호 제거** — `12`, `- 12 -` 같은 단독 숫자 줄
- [x] **줄 끝 하이픈 복원** — `informa-\ntion` → `information`
- [x] **합자/특수공백 정리** — `ﬁ`→`fi`, nbsp·zero-width·soft-hyphen 제거
- [x] **빈 줄/줄끝 공백 정리** — 3줄+ 빈 줄 → 1줄
- [x] **문서 제목(H1)** — PDF 메타데이터 제목을 맨 위에
- **검증**: 머리말/쪽번호 사라짐 + 문단 자연스러움 + 목차 링크 이동. 과교정 의심 시 `--raw` 비교

### Phase 5 — 확장 ✅ (구현됨)
- [x] **`--ocr` 스캔본 지원** — Tesseract OCR(`page.get_textpage_ocr`)로 페이지 텍스트화. `--lang kor+eng`. (Tesseract 별도 설치 필요)
- [x] **챕터별 파일 분할(`--split`)** — 최상위 헤더 기준으로 `<이름>/NN-제목.md` + 링크 목차 `index.md`
- [x] **표/수식 품질 점검** — 표 열 수 불일치·수식 의심 줄 탐지 → 요약 출력, `--report`로 `.report.md` 저장

### Phase 6 — 배포: 단독 실행파일 ✅ (`build.sh`)
- [x] **PyInstaller `--onefile`** — `./build.sh` → `dist/pdf2md` 바이너리 하나
- [x] 파이썬·설치 불필요(파일 1개 복사로 실행), 빌드한 OS 전용
- [x] `--collect-all pymupdf / pymupdf4llm`로 네이티브 라이브러리 동봉
- **주의**: OCR은 바이너리로 묶어도 시스템 Tesseract 설치 필요

---

## 8. 핵심 코드 스케치

```python
import fitz                  # PyMuPDF
import pymupdf4llm
import base64, re, pathlib

def convert(pdf_path, out_path, embed=False, images=True, toc=True):
    out = pathlib.Path(out_path)
    img_dir = out.parent / "images"

    # [2] 본문 변환 (+ 이미지 추출)
    md = pymupdf4llm.to_markdown(
        pdf_path,
        write_images=images and not embed,   # 폴더 추출
        image_path=str(img_dir),
        embed_images=embed,                  # base64 인라인
    )

    # [1][4] 목차 생성
    if toc:
        doc = fitz.open(pdf_path)
        bookmarks = doc.get_toc()            # [[level, title, page], ...]
        md = build_toc(bookmarks, md) + "\n\n---\n\n" + md

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")

def slugify(title):
    s = title.strip().lower()
    s = re.sub(r"[^\w\s가-힣-]", "", s)
    return re.sub(r"\s+", "-", s)

def build_toc(bookmarks, md):
    lines = ["# 목차\n"]
    if bookmarks:                            # 내장 북마크 우선
        for level, title, _page in bookmarks:
            lines.append("  " * (level-1) + f"- [{title}](#{slugify(title)})")
    else:                                    # 폴백: md 헤더 파싱
        for line in md.splitlines():
            m = re.match(r"^(#{1,3})\s+(.*)", line)
            if m:
                depth = len(m.group(1)) - 1
                t = m.group(2)
                lines.append("  " * depth + f"- [{t}](#{slugify(t)})")
    return "\n".join(lines)
```

> 참고: `pymupdf4llm`의 `embed_images` 옵션 지원 여부는 설치 버전에서 확인하고,
> 미지원 시 `write_images`로 추출 후 `![](path)` → `![](data:image/png;base64,...)`로
> 직접 치환하는 폴백을 둔다.

---

## 9. 설치 / 사용법

```bash
# 1. 가상환경
python3 -m venv .venv && source .venv/bin/activate

# 2. 의존성 (최초 1회만 인터넷 필요, 이후 완전 오프라인)
pip install -r requirements.txt
#   pymupdf4llm
#   PyMuPDF
#   (선택) pytesseract  + brew install tesseract tesseract-lang

# 3. 변환
python pdf2md.py 내전자책.pdf -o output/book.md --embed-images
```

> ⚠️ "오프라인"은 **실행 시점** 기준. 라이브러리 설치(`pip install`)는 최초 한 번 네트워크가 필요.
> 완전 에어갭 환경이면 `pip download`로 휠을 미리 받아 USB로 옮겨 설치.

---

## 10. 엣지 케이스 / 주의점

| 상황 | 대응 |
|------|------|
| 스캔본(이미지만 PDF) | `--ocr` (Tesseract). 텍스트 추출 0이면 자동 권고 |
| DRM 걸린 전자책 | 열기 불가 — 변환 대상 아님 (합법 보유본만) |
| 2단 편집(컬럼) | `pymupdf4llm`이 대체로 처리하나 순서 검수 필요 |
| 수식(LaTeX) | 이미지로 빠질 수 있음 → 옵션 A/B로 보존 |
| 머리말/꼬리말 반복 | Phase 4에서 정규식으로 제거 |
| 표 깨짐 | 복잡한 표는 수동 보정 또는 이미지 보존 |

---

## 11. 확장 아이디어 (나중에)

- 여러 PDF 일괄 변환 (폴더 단위)
- 챕터별 파일 분할 (`book/01-chapter.md` ...)
- EPUB 입력 지원
- 간단한 GUI (drag & drop)
- 변환 품질 비교용 `marker-pdf`(고품질, 모델 필요) 선택 백엔드

---

## 다음 액션

1. **Phase 1~3 구현** (`pdf2md.py` + `requirements.txt`) — 기본 변환 + 이미지 + 목차
2. 보유한 샘플 PDF 1개로 테스트 → 결과 검수
3. 필요 시 Phase 4 다듬기

> 진행하려면: "구현 시작해" 또는 "Phase 1만 먼저" 등으로 알려주세요.
> 이미지 기본 방식(폴더 참조 vs base64 임베딩)도 선호 알려주시면 그대로 기본값 설정합니다.
