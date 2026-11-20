"""Titik masuk: Markdown CommonMark -> HTML."""

from blok import PenguraiBlok
from render import render_html


def ke_html(teks):
    pengurai = PenguraiBlok()
    dokumen = pengurai.urai(teks)
    return render_html(dokumen, pengurai.referensi)
