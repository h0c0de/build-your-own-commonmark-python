# Build Your Own — Parser CommonMark

Parser **CommonMark 0.31.2** lengkap dalam Python
murni (stdlib saja), ditulis sebagai latihan belajar
mengikuti spesifikasi resmi — dan dibuktikan dengan
cara paling keras yang tersedia untuk sebuah parser
Markdown: **seluruh 652 contoh konformansi resmi
lulus, 652/652.**

Sumber: *CommonMark Spec* 0.31.2 karya John MacFarlane
dkk (CC-BY-SA 4.0), `spec.txt` dari repo
`commonmark/commonmark-spec` tag `0.31.2`. Berbeda
dengan build seri lain yang mengikuti tutorial,
di sini *spesifikasinya sendiri* adalah panduan —
dan baterai ujinya tertanam di dalam dokumen yang
sama: 652 pasangan masukan Markdown → keluaran HTML
yang wajib dihasilkan persis. Ekstraktor contohnya
ditulis untuk build ini; hasilnya `contoh_spek.json`
adalah wasit seluruh pekerjaan.

## Isi

| Berkas | Isi |
| --- | --- |
| `blok.py` | Fase blok: pohon blok dari baris demi baris (kontainer, daun, list rapat/longgar, lazy continuation) |
| `inline.py` | Fase inline: delimiter stack (emphasis), bracket stack (link/gambar), code span, autolink, HTML mentah + renderer simpul |
| `tautan.py` | Pengurai label/tujuan/judul tautan + panen definisi referensi |
| `entitas.py` | Entitas HTML5 & referensi numerik (termasuk peta C1) |
| `render.py` | Renderer HTML struktur blok |
| `commonmark.py` | Titik masuk: `ke_html(teks)` |
| `contoh_spek.json` | 652 contoh resmi yang diekstrak dari spec.txt 0.31.2 |
| `uji_bersama.py` | Mesin uji: jalankan contoh per bagian / penuh |
| `uji_irisan1.py` … `uji_irisan6.py` | Uji per irisan; irisan 6 = pagar skor penuh |

## Memakai

```python
from commonmark import ke_html

print(ke_html("# Halo *dunia*\n\n- satu\n- dua\n"))
# <h1>Halo <em>dunia</em></h1>
# <ul>
# <li>satu</li>
# <li>dua</li>
# </ul>
```

## Menguji

```
python3 uji_irisan1.py   # blok dasar (58)
python3 uji_irisan2.py   # setext/pagar/HTML/quote (125)
python3 uji_irisan3.py   # list & tab (85)
python3 uji_irisan4.py   # inline dasar + definisi (140)
python3 uji_irisan5.py   # link & gambar (112)
python3 uji_irisan6.py   # emphasis (132) + SKOR PENUH 652
```

## Tiga ide yang membuatnya bekerja

1. **Dua fase, seperti spek memerintahkannya.**
   Struktur blok diputuskan dulu dari baris demi
   baris — tanpa melihat inline sama sekali — baru
   isi tiap daun diurai inline. Definisi referensi
   link dipanen di antara kedua fase, saat paragraf
   ditutup (dan, ternyata, juga tepat sebelum sebuah
   garis bawah setext menafsirkan paragraf).

2. **Kesahan kontainer adalah penjodohan awalan.**
   Tiap baris menuruni tumpukan blok terbuka:
   `>` untuk quote, indentasi relatif untuk item.
   Yang tak cocok ditutup; yang tersisa diuji sebagai
   awal blok baru — dan bila tak ada yang termakan,
   baris itu mungkin *lazy continuation* paragraf
   yang masih terbuka di cabang yang tak cocok.

3. **Emphasis & link adalah mesin tumpukan.**
   Run `*`/`_` menjadi pembatas berkemampuan
   buka/tutup menurut aturan flanking; penutup
   mencari pembuka pasangannya dengan aturan
   kelipatan-3. Kurung `[` menumpuk sampai `]`
   menawarinya tujuan inline atau label referensi —
   dan tautan yang terbentuk menonaktifkan kurung
   tautan yang lebih awal, karena tautan tak boleh
   bersarang di dalam tautan.

## Temuan paling menarik

Skor penuh pertama berhenti di 623/652, dan 29
kegagalan terakhir hampir semuanya adalah *definisi
yang dibaca kurang harfiah*: tanda baca untuk
flanking adalah kategori Unicode **P atau S** (jadi
`$` dan `>` ikut tanda baca), escape backslash hanya
untuk tanda baca **ASCII** (jadi `\«` mempertahankan
backslash-nya), judul definisi referensi wajib
dipisahkan spasi dari tujuannya *dan* definisi tanpa
judul adalah jalan mundur yang sah bila bentuk
berjudul gagal, label referensi dicocokkan **tanpa**
melepas escape, dan blok kode meng-escape tanda
kutip di isinya sementara string info pagar justru
di-decode entitasnya. Cerita lengkapnya di
`CATATAN.md`.

## Lisensi

Kode: MIT. Contoh uji di `contoh_spek.json` berasal
dari CommonMark Spec 0.31.2 © John MacFarlane dkk,
berlisensi CC-BY-SA 4.0.
