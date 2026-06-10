import fitz
import sys
import os

# 也可以直接传文件名参数：python debug_pdf.py uploads/xxx.pdf
if len(sys.argv) > 1:
    file_path = sys.argv[1]
else:
    file_path = "uploads/<你的-uuid>.pdf"

# 如果是相对路径，加上 uploads/
# file_path = "uploads/<你的-uuid>.pdf"

print(f"Opening: {file_path}")
print(f"Absolute: {os.path.abspath(file_path)}")
print(f"File exists: {os.path.exists(file_path)}")
print()

try:
    doc = fitz.open(file_path)
    print(f"Pages: {doc.page_count}")
    print(f"Metadata: {doc.metadata}")
    print()

    total = 0
    for i, page in enumerate(doc):
        try:
            page_text = page.get_text("text", sort=True)
            total += len(page_text)
            print(f"Page {i+1}: {len(page_text)} chars extracted")
        except Exception as e:
            print(f"Page {i+1} ERROR: {type(e).__name__}: {e}")

    print(f"\nTotal text length: {total}")
    if total > 0:
        print(f"First 300 chars:\n{text[:300]}")
    else:
        print("WARNING: No text extracted!")

except Exception as e:
    print(f"FATAL: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
