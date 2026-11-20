"""Irisan 3 — list & item, tab."""
from uji_bersama import jalankan

BAGIAN = ["List items", "Lists", "Tabs"]

if __name__ == "__main__":
    lulus, total, gagal = jalankan(BAGIAN)
    print("irisan 3: %d/%d" % (lulus, total))
    for n, c, h in gagal:
        print("GAGAL #%d [%s] %r" % (n, c["bagian"], c["markdown"]))
    assert lulus == total, "irisan 3 belum tuntas"
    print("LULUS")
