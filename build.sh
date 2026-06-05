#!/usr/bin/env bash
# 클릭실행 앱 빌드 (macOS / Linux). OCR 언어데이터를 동봉한다(Tesseract 별도설치 불필요).
# 결과: dist/PDF-to-Markdown(.app)  — 빌드한 OS 전용.
set -euo pipefail
cd "$(dirname "$0")"

# OCR 언어데이터(eng + kor) 내려받기
mkdir -p tessdata
base=https://github.com/tesseract-ocr/tessdata_fast/raw/main
[ -f tessdata/eng.traineddata ] || curl -fL -o tessdata/eng.traineddata "$base/eng.traineddata"
[ -f tessdata/kor.traineddata ] || curl -fL -o tessdata/kor.traineddata "$base/kor.traineddata"

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt pyinstaller

pyinstaller --onefile --windowed --name "PDF-to-Markdown" \
  --add-data "tessdata:tessdata" \
  --collect-all pymupdf --collect-all pymupdf4llm --hidden-import fitz \
  pdf2md_gui.py

echo
echo "✅ 빌드 완료 → dist/PDF-to-Markdown(.app)"
echo "   더블클릭 → PDF 선택 → 같은 폴더에 .md 생성 (OCR 내장)"
