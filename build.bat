@echo off
REM 클릭실행 앱 빌드 (Windows). OCR 언어데이터를 동봉(Tesseract 별도설치 불필요).
REM 이 .bat 은 '윈도우에서' 실행해야 윈도우용 exe 가 만들어집니다. 결과: dist\PDF-to-Markdown.exe
cd /d "%~dp0"

REM OCR 언어데이터(eng + kor) 내려받기
if not exist tessdata mkdir tessdata
set BASE=https://github.com/tesseract-ocr/tessdata_fast/raw/main
if not exist tessdata\eng.traineddata curl -fL -o tessdata\eng.traineddata %BASE%/eng.traineddata
if not exist tessdata\kor.traineddata curl -fL -o tessdata\kor.traineddata %BASE%/kor.traineddata

python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

pyinstaller --onefile --windowed --name "PDF-to-Markdown" ^
  --add-data "tessdata;tessdata" ^
  --collect-all pymupdf --collect-all pymupdf4llm --hidden-import fitz ^
  pdf2md_gui.py

echo.
echo [완료] dist\PDF-to-Markdown.exe  (더블클릭 -^> PDF 선택, OCR 내장)
