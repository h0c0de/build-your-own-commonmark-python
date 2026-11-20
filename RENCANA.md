# RENCANA — Build 22: Parser CommonMark

Seri build-your-own-x, build ke-22. Sumber BARU di
luar fork: **Spesifikasi CommonMark 0.31.2** karya
John MacFarlane dkk (CC-BY-SA 4.0) — spesifikasi yang
sekaligus MEMUAT baterai ujinya: 652 contoh tertanam
di `spec.txt` resmi, tiap contoh = masukan Markdown +
keluaran HTML yang diwajibkan.

Bukti emas SEBELUM kode ditulis (20 Nov 2026):
spec.txt 0.31.2 (205.025 byte, SHA f1fab281) diunduh
dari repo commonmark/commonmark-spec tag 0.31.2;
ekstraktor contoh menghasilkan TEPAT 652 contoh
dengan distribusi bagian yang cocok dengan spek
(Emphasis 132, Links 90, List items 48, HTML blocks
44, Fenced code 29, Setext 27, dst.) — tersimpan
sebagai `contoh_spek.json`, wasit seluruh build.

## Ruang lingkup (dinyatakan di muka)

MASUK — parser CommonMark penuh dua fase mengikuti
strategi resmi spek (Apendiks "A parsing strategy"):
- Fase blok: pohon blok (dokumen, block quote, list,
  item, heading ATX/setext, blok kode indentasi &
  pagar, blok HTML 7 tipe, paragraf, break tematik)
  dengan mesin buka/tutup blok ala implementasi
  referensi (penjodohan awalan kontainer, tab parsial,
  list rapat/longgar).
- Definisi referensi link dipanen saat paragraf
  ditutup; peta referensi dipakai fase inline.
- Fase inline: delimiter stack untuk emphasis/strong
  (aturan flanking + kelipatan-3), link & gambar
  (inline, referensi penuh/runtuh/jalan-pintas),
  code span, autolink, entitas HTML5 + referensi
  numerik (peta C1), escape backslash, HTML mentah,
  hard/soft break.
- Renderer HTML dengan konvensi keluaran referensi
  (escaping, pengkodean URL, list rapat tanpa <p>).

DILUAR: ekstensi di luar spek (tabel, footnote,
strikethrough ala GFM) — bukan CommonMark. Opsi
"smart punctuation" tidak dipakai (bukan bawaan).

## Irisan

- [x] Irisan 1 — Kerangka blok dasar: dokumen,
  paragraf, ATX, break tematik, kode indentasi.
  Wasit: contoh bagian terkait dari 652.
- [x] Irisan 2 — Setext, kode pagar, blok HTML, block
  quote. Wasit: bagian Setext/Fenced/HTML/Quotes.
- [x] Irisan 3 — List & item (marker, offset konten,
  rapat/longgar, aturan dua baris kosong, interupsi
  paragraf). Wasit: List items + Lists (74 contoh).
- [x] Irisan 4 — Inline dasar + definisi referensi:
  code span, escape, entitas, autolink, HTML mentah,
  hard/soft break, teks. Wasit: bagian-bagian itu +
  Link reference definitions.
- [x] Irisan 5 — Link & gambar. Wasit: Links (90) +
  Images (22).
- [x] Irisan 6 — Emphasis (delimiter stack penuh).
  Wasit: Emphasis (132) + skor PENUH 652 dilaporkan
  apa adanya.

## Pagar selesai

- [x] `uji_irisan1.py` … `uji_irisan6.py` hijau pada
  target bagiannya; skor total 652 tercetak jujur.
- [x] `CATATAN.md` satu halaman per irisan.
- [x] Repo GitHub publik
  `build-your-own-commonmark-python` terbit dan
  terverifikasi (SHA blob lokal == remote, halaman
  publik terbaca).
