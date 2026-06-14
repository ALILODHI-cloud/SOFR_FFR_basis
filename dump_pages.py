import fitz

jobs = [
    ("Shifting_gears", r"C:\Users\Ali Lodhi\OneDrive - Supra Fund Management\Desktop\Barclays_Global_Rates_Weekly_Shifting_gears.pdf", [0,17,18,19,20,21,22,23,24]),
    ("Hope_springs_eternal", r"C:\Users\Ali Lodhi\Downloads\Barclays_Global_Rates_Weekly_Hope_springs_eternal (1).pdf", [0,16,17,18,19,20,21,22,23]),
    ("In_the_hot_seat", r"C:\Users\Ali Lodhi\OneDrive - Supra Fund Management\Desktop\Barclays_Global_Rates_Weekly_In_the_hot_seat.pdf", [0,7,16,17,18,19,20,21,22]),
]

for name, p, pages in jobs:
    doc = fitz.open(p)
    for i in pages:
        if i >= doc.page_count:
            continue
        print("\n" + "#"*90)
        print(f"### {name} :: PAGE {i}")
        print("#"*90)
        print(doc[i].get_text())
    doc.close()
