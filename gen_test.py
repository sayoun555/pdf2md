"""검증용 샘플 전자책 PDF 생성 (머리말/꼬리말/쪽번호/제목/실제이미지/한글/북마크)."""
import fitz

# 1) 진짜 래스터 이미지(fig.png) 생성 — 페이지를 렌더해서 만든다(픽셀 변화 있음)
fig = fitz.open()
fp = fig.new_page(width=300, height=180)
fp.draw_rect(fitz.Rect(0, 0, 300, 180), color=(0.1, 0.3, 0.7), fill=(0.1, 0.3, 0.7))
fp.draw_circle(fitz.Point(150, 90), 60, color=(1, 1, 1), fill=(1, 0.8, 0.2))
fp.insert_text((70, 95), "FIGURE", fontsize=24, color=(0, 0, 0))
fp.get_pixmap(dpi=120).save("fig.png")
fig.close()

# 2) 본문 PDF
doc = fitz.open()
doc.set_metadata({"title": "My Test Ebook"})

chapters = [
    ("Chapter 1: Introduction",
     "This is the first chapter. It explains the basic informa-\n"
     "tion needed to start.\nThe office workflow is efficient."),
    ("Chapter 2: Methods",
     "Here we describe the methods.\nEach step builds on the last.\n"
     "Figures appear below."),
    ("Chapter 3: Results",
     "The results show clear trends.\nReaders can follow along.\n"
     "See the figure on this page."),
    ("Chapter 4: Conclusion",
     "We conclude with a summary.\nThank you for reading."),
]

for i, (title, body) in enumerate(chapters):
    page = doc.new_page()
    page.insert_text((72, 36), "My Test Ebook", fontsize=9)        # 반복 머리말
    page.insert_text((72, 110), title, fontsize=22)                # 큰 글씨 = 제목
    page.insert_textbox(fitz.Rect(72, 150, 520, 650), body, fontsize=11)
    page.insert_text((300, 770), str(i + 1), fontsize=9)           # 쪽번호(꼬리말)
    if i == 2:  # 3장에 실제 이미지 삽입
        page.insert_image(fitz.Rect(72, 480, 372, 660), filename="fig.png")
    if i == 3:  # 한글 확인 (한국어 내장폰트)
        page.insert_textbox(fitz.Rect(72, 300, 520, 360),
                            "한글 문장도 잘 들어가는지 확인한다.",
                            fontsize=12, fontname="korea")

doc.set_toc([[1, t, i + 1] for i, (t, _) in enumerate(chapters)])
doc.save("test.pdf")
print("생성됨: test.pdf  (페이지", doc.page_count, ")")
