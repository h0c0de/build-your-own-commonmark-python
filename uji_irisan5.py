"""Irisan 5 — link & gambar."""
from uji_bersama import jalankan

BAGIAN = ["Links", "Images"]

if __name__ == "__main__":
    lulus, total, gagal = jalankan(BAGIAN)
    print("irisan 5: %d/%d" % (lulus, total))
    for n, c, h in gagal:
        print("GAGAL #%d [%s] %r" % (n, c["bagian"], c["markdown"]))
    assert lulus == total, "irisan 5 belum tuntas"
    print("LULUS")
