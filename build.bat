@echo off
REM 단독 실행파일 빌드 (Windows). 결과: dist\pdf2md.exe
REM 이 .bat 은 반드시 '윈도우에서' 실행해야 윈도우용 exe 가 만들어집니다.
cd /d "%~dp0"

python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

pyinstaller --onefile --name pdf2md ^
  --collect-all pymupdf ^
  --collect-all pymupdf4llm ^
  --hidden-import fitz ^
  pdf2md.py

echo.
echo [완료] dist\pdf2md.exe
echo   사용:  dist\pdf2md.exe "내전자책.pdf" --embed-images
