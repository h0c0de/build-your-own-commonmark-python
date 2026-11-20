"""Irisan 4 — inline dasar + definisi referensi."""
from uji_bersama import jalankan

BAGIAN = ["Backslash escapes",
          "Entity and numeric character references",
          "Link reference definitions", "Code spans",
          "Autolinks", "Raw HTML", "Hard line breaks",
          "Soft line breaks", "Textual content",
          "Inlines", "Precedence"]

if __name__ == "__main__":
    lulus, total, gagal = jalankan(BAGIAN)
    print("irisan 4: %d/%d" % (lulus, total))
    for n, c, h in gagal:
        print("GAGAL #%d [%s] %r" % (n, c["bagian"], c["markdown"]))
    assert lulus == total, "irisan 4 belum tuntas"
    print("LULUS")
