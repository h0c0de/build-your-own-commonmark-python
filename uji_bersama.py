"""Mesin uji bersama: jalankan contoh_spek.json.

Dipakai semua uji_irisan*.py. Memuat 652 contoh
resmi CommonMark 0.31.2 dan melaporkan skor per
bagian serta daftar kegagalan.
"""

import json
import os

from commonmark import ke_html

DASAR = os.path.dirname(os.path.abspath(__file__))
CONTOH = json.load(open(os.path.join(DASAR, "contoh_spek.json")))


def jalankan(bagian=None):
    """Kembalikan (lulus, total, daftar_gagal)."""
    lulus = 0
    total = 0
    gagal = []
    for i, c in enumerate(CONTOH, 1):
        if bagian is not None and c["bagian"] not in bagian:
            continue
        total += 1
        try:
            hasil = ke_html(c["markdown"])
        except Exception as e:  # parser tak boleh jatuh
            hasil = "<GALAT: %r>" % e
        if hasil == c["html"]:
            lulus += 1
        else:
            gagal.append((i, c, hasil))
    return lulus, total, gagal


def laporkan(bagian=None, maks_tampil=5):
    lulus, total, gagal = jalankan(bagian)
    print("skor: %d/%d" % (lulus, total))
    for nomor, c, hasil in gagal[:maks_tampil]:
        print("--- GAGAL contoh %d [%s]" % (nomor, c["bagian"]))
        print("md   : %r" % c["markdown"])
        print("emas : %r" % c["html"])
        print("dapat: %r" % hasil)
    return lulus, total, gagal
