"""Irisan 2 — setext, kode pagar, blok HTML, block quote."""
from uji_bersama import jalankan

BAGIAN = ["Setext headings", "Fenced code blocks",
          "HTML blocks", "Block quotes"]

if __name__ == "__main__":
    lulus, total, gagal = jalankan(BAGIAN)
    print("irisan 2: %d/%d" % (lulus, total))
    for n, c, h in gagal:
        print("GAGAL #%d [%s] %r" % (n, c["bagian"], c["markdown"]))
    assert lulus == total, "irisan 2 belum tuntas"
    print("LULUS")
