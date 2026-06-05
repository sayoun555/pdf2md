#!/usr/bin/env python3
"""PDF → Markdown 변환기 GUI (더블클릭 실행). Windows / Linux / macOS 공용.

PyInstaller --windowed 로 빌드하면 각 OS에서 더블클릭 가능한 앱이 된다.
"""
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pdf2md  # 변환 로직 재사용


def _convert(pdf_path: str, on_done):
    try:
        out = Path(pdf_path).with_suffix(".md")
        pdf2md.convert(pdf_path=Path(pdf_path), out_path=out,
                       embed=True, images=True, toc=True, clean=True)
        on_done(True, str(out))
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        on_done(False, str(e))


def main():
    root = tk.Tk()
    root.title("PDF → Markdown")
    root.geometry("470x230")

    status = tk.StringVar(value="PDF 파일을 선택하면 같은 폴더에 .md 가 만들어집니다.")
    tk.Label(root, text="PDF → Markdown 변환기", font=("", 16, "bold")).pack(pady=14)
    tk.Label(root, textvariable=status, wraplength=430).pack(pady=6)
    bar = ttk.Progressbar(root, mode="indeterminate", length=300)

    def pick():
        path = filedialog.askopenfilename(
            title="변환할 PDF 선택", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        btn.config(state="disabled")
        status.set("변환 중입니다... (스캔본은 몇 분 걸릴 수 있어요)")
        bar.pack(pady=6)
        bar.start(12)

        def done(ok, msg):
            def ui():
                bar.stop()
                bar.pack_forget()
                btn.config(state="normal")
                if ok:
                    status.set("완료!  " + msg)
                    messagebox.showinfo("완료", "변환 완료:\n" + msg)
                else:
                    status.set("오류 발생")
                    messagebox.showerror("오류", msg)
            root.after(0, ui)

        threading.Thread(target=_convert, args=(path, done), daemon=True).start()

    btn = tk.Button(root, text="📄 PDF 선택해서 변환", command=pick,
                    font=("", 13), height=2)
    btn.pack(pady=12)
    root.mainloop()


if __name__ == "__main__":
    main()
