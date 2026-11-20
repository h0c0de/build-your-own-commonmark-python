"""Pengurai potongan tautan: label, tujuan, judul.

Dipakai dua kali: definisi referensi (fase blok) dan
tautan inline (fase inline). Tujuan & judul yang
berhasil diurai dikembalikan sudah bebas-escape
(backslash) dan terdekode entitasnya.
"""

import re
import string

from entitas import dekode_entitas

PUNCT = set(string.punctuation)


def lepas_escape(teks):
    """Hapus backslash di depan tanda baca ASCII."""
    hasil = []
    i = 0
    while i < len(teks):
        if teks[i] == "\\" and i + 1 < len(teks) \
                and teks[i + 1] in PUNCT:
            hasil.append(teks[i + 1])
            i += 2
        else:
            hasil.append(teks[i])
            i += 1
    return "".join(hasil)


def normalisasi_label(label):
    """Lipatan kasus + runtuhkan whitespace (aturan spek)."""
    return re.sub(r"\s+", " ", label.strip()).casefold()


def _lewati_spasi(teks, pos, maks_newline=1):
    """Lewati spasi/tab/newline; kembalikan pos baru
    atau None bila newline melebihi batas / blank line."""
    nl = 0
    while pos < len(teks) and teks[pos] in " \t\n":
        if teks[pos] == "\n":
            nl += 1
            if nl > maks_newline:
                return None
        pos += 1
    return pos


def urai_tujuan(teks, pos):
    """Urai tujuan tautan di pos. Kembalikan
    (tujuan_mentah, pos_baru) atau None."""
    if pos >= len(teks):
        return None
    if teks[pos] == "<":
        # tujuan berkurung: tanpa newline / < / > liar
        i = pos + 1
        while i < len(teks):
            c = teks[i]
            if c == "\\" and i + 1 < len(teks):
                i += 2
                continue
            if c == ">":
                return teks[pos + 1:i], i + 1
            if c in "<\n":
                return None
            i += 1
        return None
    # tujuan telanjang: kurung harus seimbang
    i = pos
    seimbang = 0
    while i < len(teks):
        c = teks[i]
        if c == "\\" and i + 1 < len(teks) and teks[i + 1] in PUNCT:
            i += 2
            continue
        if c in " \t\n" or ord(c) < 0x20 or ord(c) == 0x7F:
            break
        if c == "(":
            seimbang += 1
        elif c == ")":
            if seimbang == 0:
                break
            seimbang -= 1
        i += 1
    if i == pos or seimbang != 0:
        return None
    return teks[pos:i], i


def urai_judul(teks, pos):
    """Urai judul tautan di pos ("..." / '...' / (...)).
    Kembalikan (judul_mentah, pos_baru) atau None."""
    if pos >= len(teks):
        return None
    pembuka = teks[pos]
    if pembuka == '"':
        penutup = '"'
    elif pembuka == "'":
        penutup = "'"
    elif pembuka == "(":
        penutup = ")"
    else:
        return None
    i = pos + 1
    while i < len(teks):
        c = teks[i]
        if c == "\\" and i + 1 < len(teks):
            i += 2
            continue
        if c == penutup:
            return teks[pos + 1:i], i + 1
        if pembuka == "(" and c == "(":
            return None
        if teks.startswith("\n\n", i):
            return None
        i += 1
    return None


def _bersihkan(nilai_mentah):
    return dekode_entitas(lepas_escape(nilai_mentah))


def urai_definisi_referensi(teks, referensi):
    """Panen definisi referensi dari awal isi paragraf.

    Mengisi dict referensi {label_ternormalisasi:
    (tujuan, judul)}. Mengembalikan sisa isi paragraf,
    atau None bila seluruh isi adalah definisi.
    Mengembalikan teks asli bila tak ada definisi."""
    pos = 0
    ada = False
    while True:
        hasil = _urai_satu_definisi(teks, pos)
        if hasil is None:
            break
        label, tujuan, judul, pos = hasil
        if label not in referensi:
            referensi[label] = (tujuan, judul)
        ada = True
    if not ada:
        return teks
    sisa = teks[pos:]
    if sisa.strip() == "":
        return None
    return sisa


def _urai_satu_definisi(teks, pos):
    n = len(teks)
    # indentasi awal <= 3 spasi
    spasi = 0
    while pos < n and teks[pos] == " " and spasi < 4:
        pos += 1
        spasi += 1
    if spasi > 3 or pos >= n or teks[pos] != "[":
        return None
    # label: sampai ']' tak ter-escape, tanpa '[' liar
    i = pos + 1
    label_mentah = []
    while i < n:
        c = teks[i]
        if c == "\\" and i + 1 < n:
            label_mentah.append(teks[i:i + 2])
            i += 2
            continue
        if c == "]":
            break
        if c == "[":
            return None
        label_mentah.append(c)
        i += 1
    if i >= n or i - pos > 1000:
        return None
    label = normalisasi_label("".join(label_mentah))
    if not label:
        return None
    i += 1  # lewati ']'
    if i >= n or teks[i] != ":":
        return None
    i += 1
    i = _lewati_spasi(teks, i)
    if i is None:
        return None
    t = urai_tujuan(teks, i)
    if t is None:
        return None
    tujuan_mentah, i = t
    # Bentuk dengan judul: wajib ada whitespace pemisah
    # dari tujuan; judul lalu harus diikuti akhir baris.
    j = i
    ada_spasi = False
    nl = 0
    while j < n and teks[j] in " \t\n":
        if teks[j] == "\n":
            nl += 1
        ada_spasi = True
        j += 1
    if ada_spasi and nl <= 1:
        ju = urai_judul(teks, j)
        if ju is not None:
            judul_mentah, k = ju
            while k < n and teks[k] in " \t":
                k += 1
            if k >= n or teks[k] == "\n":
                if k < n:
                    k += 1
                return label, _bersihkan(tujuan_mentah), \
                    _bersihkan(judul_mentah), k
    # Bentuk tanpa judul: tujuan diikuti akhir baris
    k = i
    while k < n and teks[k] in " \t":
        k += 1
    if k >= n or teks[k] == "\n":
        if k < n:
            k += 1
        return label, _bersihkan(tujuan_mentah), None, k
    return None
