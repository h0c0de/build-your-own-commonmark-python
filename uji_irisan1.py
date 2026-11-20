"""Irisan 1 — kerangka blok dasar.

Wasit: contoh resmi CommonMark 0.31.2 bagian Paragraphs,
Blank lines, Thematic breaks, ATX headings, Indented
code blocks. Semua harus lulus penuh.
"""
from uji_bersama import jalankan

BAGIAN = ["Paragraphs", "Blank lines", "Thematic breaks",
          "ATX headings", "Indented code blocks"]

if __name__ == "__main__":
    lulus, total, gagal = jalankan(BAGIAN)
    print("irisan 1: %d/%d" % (lulus, total))
    for n, c, h in gagal:
        print("GAGAL #%d [%s] %r" % (n, c["bagian"], c["markdown"]))
    assert lulus == total, "irisan 1 belum tuntas"
    print("LULUS")
