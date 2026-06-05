#!/usr/bin/env bash
# 단독 실행파일 빌드 (macOS / Linux). 결과: dist/pdf2md
# 빌드한 OS 전용 바이너리가 만들어진다 (맥에서 빌드 → 맥 전용).
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt pyinstaller

pyinstaller --onefile --name pdf2md \
  --collect-all pymupdf \
  --collect-all pymupdf4llm \
  --hidden-import fitz \
  pdf2md.py

echo
echo "✅ 빌드 완료 → dist/pdf2md"
echo "   사용:  ./dist/pdf2md 내전자책.pdf --embed-images"
echo "   (이 파일 하나만 복사하면 파이썬 없이 어디서나 실행)"
