import fitz
import sys

paths = {
    "Shifting_gears": r"C:\Users\Ali Lodhi\OneDrive - Supra Fund Management\Desktop\Barclays_Global_Rates_Weekly_Shifting_gears.pdf",
    "Hope_springs_eternal": r"C:\Users\Ali Lodhi\Downloads\Barclays_Global_Rates_Weekly_Hope_springs_eternal (1).pdf",
    "In_the_hot_seat": r"C:\Users\Ali Lodhi\OneDrive - Supra Fund Management\Desktop\Barclays_Global_Rates_Weekly_In_the_hot_seat.pdf",
}

keywords = ["money market", "money markets", "sofr", "repo", "funding", "reserves", "rrp", "reverse repo", "effr", "fed funds", "bills", "tga", "qt"]

for name, p in paths.items():
    doc = fitz.open(p)
    print("="*100)
    print(f"DOC: {name}  pages={doc.page_count}")
    print("="*100)
    for i in range(doc.page_count):
        text = doc[i].get_text()
        low = text.lower()
        hits = [k for k in keywords if k in low]
        if hits:
            # crude relevance score
            score = sum(low.count(k) for k in hits)
            print(f"--- page {i} | hits={set(hits)} | score={score} ---")
    doc.close()
