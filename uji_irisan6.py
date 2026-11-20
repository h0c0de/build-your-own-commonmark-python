"""Irisan 6 — emphasis + SKOR PENUH 652 contoh resmi.

Ini pagar akhir build 22: seluruh baterai konformansi
CommonMark 0.31.2 harus lulus 652/652.
"""
from uji_bersama import jalankan

if __name__ == "__main__":
    lulus, total, gagal = jalankan(["Emphasis and strong emphasis"])
    print("emphasis: %d/%d" % (lulus, total))
    assert lulus == total
    lulus, total, gagal = jalankan()
    print("SKOR PENUH: %d/%d" % (lulus, total))
    for n, c, h in gagal:
        print("GAGAL #%d [%s] %r" % (n, c["bagian"], c["markdown"]))
    assert lulus == total == 652, "skor penuh belum 652/652"
    print("LULUS — konformansi penuh CommonMark 0.31.2")
