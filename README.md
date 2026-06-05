# pdf2md — 전자책 PDF → Markdown (로컬/오프라인)

전자책 PDF를 인터넷 없이 로컬에서 `.md`로 변환합니다.
목차(TOC) 자동 생성, 이미지 추출/임베딩 지원. (자세한 설계는 [PLAN.md](PLAN.md))

## 설치 (최초 1회만 네트워크 필요)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 사용법

```bash
# 기본: output/book.md + output/images/ (상대경로 참조)
python pdf2md.py book.pdf

# 단일 파일로 완결 (이미지를 base64로 .md 안에 임베딩)
python pdf2md.py book.pdf --embed-images

# 출력 경로 지정
python pdf2md.py book.pdf -o 내문서/책.md

# 챕터별 파일로 분할 / 품질 리포트
python pdf2md.py book.pdf --split
python pdf2md.py book.pdf --report

# 스캔본(이미지 PDF) OCR — Tesseract 필요
python pdf2md.py scan.pdf --ocr --lang kor+eng

# 텍스트만 / 목차 생략 / 가독성 후처리 끔
python pdf2md.py book.pdf --no-images
python pdf2md.py book.pdf --no-toc
python pdf2md.py book.pdf --raw
```

| 플래그 | 기능 |
|--------|------|
| `-o, --output` | 출력 `.md` 경로 (기본 `output/<이름>.md`) |
| `--embed-images` | 이미지를 base64로 임베딩 → `.md` 한 파일로 완결 |
| `--no-images` | 이미지 제외(텍스트만) |
| `--no-toc` | 목차 생략 |
| `--raw` | 가독성 후처리 끔(추출 원본 그대로) |
| `--split` | 챕터별 `.md` 파일로 분할(`<이름>/index.md` + 챕터들) |
| `--report` | 표/수식/이미지 품질 리포트(`.report.md`) 생성 |
| `--ocr` | 스캔본을 Tesseract로 OCR |
| `--lang` | OCR 언어 (기본 `kor+eng`) |

## 동작
- **본문**: 폰트 크기로 제목을 감지해 `#`/`##` 헤더로 구조화 (`pymupdf4llm`)
- **가독성 후처리** (기본 ON): 반복 머리말·꼬리말 제거, 떠다니는 쪽번호 제거,
  줄 끝 하이픈 복원(`informa-tion`→`information`), 합자(`ﬁ`→`fi`)·특수공백 정리, 빈 줄 정리
- **목차**: md 헤더로 클릭 가능한 목차 생성 (없으면 PDF 북마크 사용)
- **이미지**: `images/` 폴더 추출(기본) 또는 base64 임베딩(`--embed-images`)
- **분할**: 최상위 헤더 기준으로 챕터별 파일 + 링크 목차(`index.md`)
- **점검**: 변환 후 표 열 수 불일치·수식 의심 줄을 요약 출력(`--report`로 파일 저장)
- **스캔본 자동 보정**: 내장 북마크가 충실한데(≥5개) 자동 헤더가 과다하면(스캔본 신호),
  가짜 헤더를 걷어내고 **북마크 구조로 제목을 재구성** + 중복 제목·러닝헤더 제거

## 스캔본(이미지 PDF) OCR
글자가 이미지로 된 스캔 PDF는 `--ocr`로 처리. **Tesseract 별도 설치 필요**:

```bash
brew install tesseract tesseract-lang
export TESSDATA_PREFIX="$(brew --prefix)/share/tessdata"
python pdf2md.py scan.pdf --ocr --lang kor+eng
```

## 단독 실행파일 빌드 (파이썬 없이 실행)

```bash
./build.sh          # → dist/pdf2md (이 파일 하나만 있으면 됨)
./dist/pdf2md 내전자책.pdf --embed-images
```

> 빌드한 OS 전용 바이너리입니다(맥에서 빌드 → 맥 전용). OCR은 바이너리로 묶어도
> 시스템에 Tesseract가 설치돼 있어야 동작합니다.
