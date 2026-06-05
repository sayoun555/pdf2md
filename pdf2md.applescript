-- PDF → Markdown 변환기 (더블클릭 / 드래그앤드롭)
-- 더블클릭하면 파일 선택창이, 아이콘에 PDF를 끌어다 놓으면 바로 변환된다.
-- 앱 자신의 위치를 동적으로 찾아(path to me) 내부에 동봉된 CLI 바이너리를 실행한다.

on run
	set theFile to choose file with prompt "변환할 PDF를 선택하세요" of type {"com.adobe.pdf"}
	convertOne(theFile)
end run

on open theFiles
	repeat with f in theFiles
		convertOne(f)
	end repeat
end open

on convertOne(theFile)
	set inPath to POSIX path of theFile
	if not (inPath ends with ".pdf" or inPath ends with ".PDF") then
		display dialog "PDF 파일이 아닙니다." buttons {"확인"} default button 1
		return
	end if
	set outPath to (text 1 thru -5 of inPath) & ".md"
	set toolPath to (POSIX path of (path to me)) & "Contents/Resources/pdf2md"
	try
		with timeout of 3600 seconds
			do shell script quoted form of toolPath & " " & quoted form of inPath & ¬
				" -o " & quoted form of outPath & " --embed-images"
		end timeout
		display dialog "변환 완료!" & return & return & outPath buttons {"확인"} default button 1
	on error errMsg
		display dialog "오류가 발생했습니다:" & return & return & errMsg buttons {"확인"} default button 1 with icon stop
	end try
end convertOne
