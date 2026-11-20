"""Entitas & referensi karakter numerik CommonMark.

Mengikuti spek: entitas bernama HTML5 (wajib diakhiri
';'), referensi desimal/hex &#...; / &#x...;, dan
kode tak valid (0, surogat, > 0x10FFFF, kontrol tak
tercetak tertentu) menjadi U+FFFD. Rentang C1
(0x80-0x9F) dipetakan mengikuti tabel standar HTML.
"""

import re
from html.entities import html5

# Peta C1 standar HTML (Windows-1252)
PETA_C1 = {
    0x80: 0x20AC, 0x81: 0x0081, 0x82: 0x201A, 0x83: 0x0192,
    0x84: 0x201E, 0x85: 0x2026, 0x86: 0x2020, 0x87: 0x2021,
    0x88: 0x02C6, 0x89: 0x2030, 0x8A: 0x0160, 0x8B: 0x2039,
    0x8C: 0x0152, 0x8D: 0x008D, 0x8E: 0x017D, 0x8F: 0x008F,
    0x90: 0x0090, 0x91: 0x2018, 0x92: 0x2019, 0x93: 0x201C,
    0x94: 0x201D, 0x95: 0x2022, 0x96: 0x2013, 0x97: 0x2014,
    0x98: 0x02DC, 0x99: 0x2122, 0x9A: 0x0161, 0x9B: 0x203A,
    0x9C: 0x0153, 0x9D: 0x009D, 0x9E: 0x017E, 0x9F: 0x0178,
}

RE_ENTITAS = re.compile(
    r"&#([0-9]{1,7});|&#[xX]([0-9A-Fa-f]{1,6});"
    r"|&([A-Za-z][A-Za-z0-9]{1,31});")


def titik_kode(n):
    """Titik kode numerik -> karakter menurut spek."""
    if n == 0 or n > 0x10FFFF or 0xD800 <= n <= 0xDFFF:
        return "�"
    if n in PETA_C1:
        return chr(PETA_C1[n])
    return chr(n)


def cocok_entitas(teks, pos):
    """Bila di teks[pos] mulai entitas valid, kembalikan
    (karakter_hasil, panjang_konsumsi); else None."""
    m = RE_ENTITAS.match(teks, pos)
    if not m:
        return None
    if m.group(1) is not None:
        return titik_kode(int(m.group(1))), m.end() - pos
    if m.group(2) is not None:
        return titik_kode(int(m.group(2), 16)), m.end() - pos
    nama = m.group(3) + ";"
    if nama in html5:
        return html5[nama], m.end() - pos
    return None


def dekode_entitas(teks):
    """Ganti semua entitas valid dalam teks."""
    hasil = []
    i = 0
    while i < len(teks):
        if teks[i] == "&":
            c = cocok_entitas(teks, i)
            if c:
                hasil.append(c[0])
                i += c[1]
                continue
        hasil.append(teks[i])
        i += 1
    return "".join(hasil)
