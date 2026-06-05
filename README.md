# pdf2md — PDF 전자책 → Markdown 변환기

PDF(전자책)를 **로컬/오프라인**에서 `.md`로 변환합니다.
목차 자동 생성, 이미지 추출/임베딩, **OCR 내장**(스캔본도 변환), 스캔본 구조 자동 보정.

- 🖱 **클릭 실행 앱** (Windows / Linux / macOS) — 아무것도 설치 안 함, OCR 언어데이터까지 내장
- 🧰 **개발자용 CLI** — 파이썬으로 다양한 옵션 사용

---

## 1. 그냥 쓰는 법 — 클릭 실행 앱 (설치 불필요)

### 앱 받기
GitHub에서 빌드된 앱을 받습니다: **https://github.com/sayoun555/pdf2md**
→ **Actions** 탭 → 최신 **"Build apps"** 실행 → 아래 **Artifacts** 에서 본인 OS 다운로드

| OS | 파일 |
|---|---|
| Windows | `PDF-to-Markdown-Windows.exe` |
| Linux | `PDF-to-Markdown-Linux` |
| macOS | `PDF-to-Markdown-macOS`(.app) |

> 각 파일은 **그 OS 전용**입니다 (윈도우 .exe를 맥에서 못 씀). 받는 사람에게 자기 OS 파일만 주세요.

### 사용
1. 앱을 **더블클릭**
2. 파일 선택창에서 **PDF 선택**
3. 잠시 후(스캔본은 몇 분) **PDF와 같은 폴더에 `.md` 생성** + "완료" 알림

OCR 언어데이터(eng+kor)가 앱에 내장돼 있어 **Tesseract 등 아무것도 설치할 필요가 없습니다.**

### 첫 실행 보안 경고 우회 (서명 안 된 앱이라 한 번만)
- **Windows**: "Windows의 PC 보호" → **추가 정보 → 실행**
- **macOS**: 앱 **우클릭 → 열기** (또는 터미널 `xattr -dr com.apple.quarantine "PDF-to-Markdown-macOS.app"`)
- **Linux**: `chmod +x PDF-to-Markdown-Linux` 후 실행 (GUI 데스크톱 환경 필요)

### 명령줄로도 가능 (선택)
PDF 경로를 인자로 주면 창 없이 바로 변환됩니다.
```bash
./PDF-to-Markdown-macOS "내책.pdf"      # → 내책.md
```

---

## 2. 주요 기능

- **목차(TOC)**: PDF 내장 북마크 또는 본문 헤더로 **클릭 가능한 목차** 생성
- **이미지**: 추출해서 참조, 또는 base64로 `.md` 한 파일에 임베딩
- **가독성 정리**: 반복 머리말·꼬리말/쪽번호 제거, 줄끝 하이픈 복원, 합자·특수공백 정리
- **OCR 내장**: 글자가 이미지로 된 스캔본도 변환 (언어데이터 동봉, 별도 설치 불필요)
- **스캔본 자동 보정**: 북마크가 충실하면 가짜 헤더를 걷어내고 **북마크 구조로 제목 재구성** + 중복 제목/러닝헤더 제거
- **분할/리포트**: 챕터별 파일 분할, 표/수식 품질 점검 리포트

---

## 3. 개발자용 — 소스로 실행 (CLI)

### 설치
```bash
python3 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 사용
```bash
python pdf2md.py book.pdf                  # → output/book.md + output/images/
python pdf2md.py book.pdf --embed-images   # 이미지까지 .md 한 파일로 완결
python pdf2md.py book.pdf -o 내문서/책.md  # 출력 경로 지정
python pdf2md.py book.pdf --split          # 챕터별 파일로 분할
python pdf2md.py book.pdf --report         # 품질 리포트 생성
python pdf2md.py scan.pdf --ocr            # 스캔본 OCR (아래 Tesseract 필요)
```

| 플래그 | 기능 |
|--------|------|
| `-o, --output` | 출력 `.md` 경로 (기본 `output/<이름>.md`) |
| `--embed-images` | 이미지를 base64로 임베딩 → `.md` 한 파일로 완결 |
| `--no-images` | 이미지 제외(텍스트만) |
| `--no-toc` | 목차 생략 |
| `--raw` | 가독성 후처리 끔(추출 원본 그대로) |
| `--split` | 챕터별 `.md` 파일로 분할 |
| `--report` | 표/수식/이미지 품질 리포트 생성 |
| `--ocr` | 스캔본을 Tesseract로 OCR |
| `--lang` | OCR 언어 (기본 `kor+eng`) |

> **소스로 OCR을 쓸 때만** Tesseract 설치 필요 (빌드된 앱은 내장돼 있어 불필요):
> ```bash
> brew install tesseract tesseract-lang          # macOS
> export TESSDATA_PREFIX="$(brew --prefix)/share/tessdata"
> ```

---

## 4. 직접 빌드하기

### 로컬 (빌드한 OS 전용 앱)
```bash
./build.sh        # macOS / Linux → dist/PDF-to-Markdown(.app)
build.bat         # Windows       → dist\PDF-to-Markdown.exe
```
OCR 언어데이터를 자동으로 받아 앱에 동봉합니다.

### 클라우드에서 3개 OS 한 번에 (GitHub Actions)
저장소 **Actions → "Build apps" → Run workflow** → 윈도우/리눅스/맥 앱이 빌드되어 Artifacts에 올라옵니다.

> OCR 정확도 조절: `.github/workflows/build.yml` 와 `build.sh`/`build.bat` 의
> `tessdata_best`(현재, 최고 정확도) ↔ `tessdata_fast`(가볍고 빠름) 를 바꾸면 됩니다.

---

설계 문서는 [PLAN.md](PLAN.md) 참고.
