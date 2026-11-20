"""Renderer HTML untuk pohon blok CommonMark.

Inline dirender oleh inline.py; di sini hanya struktur
blok dan konvensi keluaran referensi: list rapat
tanpa <p>, <hr />, info string kode pagar menjadi
class="language-...", dan seterusnya.
"""

import re

from inline import render_inline


def escape_html(teks, kutip=False):
    teks = teks.replace("&", "&amp;").replace("<", "&lt;") \
        .replace(">", "&gt;")
    if kutip:
        teks = teks.replace('"', "&quot;")
    return teks


def render_html(dokumen, referensi):
    keluar = []
    for anak in dokumen.anak:
        _render(anak, keluar, referensi, rapat=False)
    return "".join(keluar)


def _render(blok, keluar, referensi, rapat):
    jenis = blok.jenis
    if jenis == "paragraf":
        if rapat:
            keluar.append(render_inline(blok.isi, referensi))
        else:
            keluar.append("<p>")
            keluar.append(render_inline(blok.isi, referensi))
            keluar.append("</p>\n")
    elif jenis == "judul":
        level = blok.data["level"]
        keluar.append("<h%d>" % level)
        keluar.append(render_inline(blok.isi, referensi))
        keluar.append("</h%d>\n" % level)
    elif jenis == "kode":
        info = blok.data.get("info", "")
        if blok.data.get("pagar") and info:
            from tautan import lepas_escape
            from entitas import dekode_entitas
            kata = dekode_entitas(lepas_escape(info)).split()
            kata = kata[0] if kata else ""
            keluar.append('<pre><code class="language-%s">'
                          % escape_html(kata, kutip=True))
        else:
            keluar.append("<pre><code>")
        keluar.append(escape_html(blok.isi, kutip=True))
        keluar.append("</code></pre>\n")
    elif jenis == "html":
        keluar.append(blok.isi)
    elif jenis == "break":
        keluar.append("<hr />\n")
    elif jenis == "kutipan":
        keluar.append("<blockquote>\n")
        for anak in blok.anak:
            _render(anak, keluar, referensi, rapat=False)
        keluar.append("</blockquote>\n")
    elif jenis == "daftar":
        if blok.data["tipe"] == "bullet":
            keluar.append("<ul>\n")
            tutup = "</ul>\n"
        else:
            mulai = blok.data.get("mulai", 1)
            if mulai != 1:
                keluar.append('<ol start="%d">\n' % mulai)
            else:
                keluar.append("<ol>\n")
            tutup = "</ol>\n"
        for anak in blok.anak:
            _render(anak, keluar, referensi,
                    rapat=blok.data.get("rapat", True))
        keluar.append(tutup)
    elif jenis == "item":
        rapat = rapat
        if not blok.anak:
            keluar.append("<li></li>\n")
            return
        anak_pertama_par = blok.anak[0].jenis == "paragraf"
        if rapat:
            # <li> langsung menyatu hanya bila rapat dan
            # anak pertama paragraf; selain itu baris baru
            keluar.append("<li>" if anak_pertama_par
                          else "<li>\n")
            anak_terakhir = len(blok.anak) - 1
            for i, anak in enumerate(blok.anak):
                if anak.jenis == "paragraf":
                    keluar.append(
                        render_inline(anak.isi, referensi))
                    if i != anak_terakhir:
                        keluar.append("\n")
                else:
                    _render(anak, keluar, referensi, rapat=False)
            keluar.append("</li>\n")
        else:
            keluar.append("<li>\n")
            for anak in blok.anak:
                _render(anak, keluar, referensi, rapat=False)
            keluar.append("</li>\n")
    else:
        for anak in blok.anak:
            _render(anak, keluar, referensi, rapat)
