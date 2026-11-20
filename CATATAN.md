# CATATAN — Build 22: Parser CommonMark

Satu halaman per irisan: konsep inti + temuan.
Wasit tunggal seluruh build: 652 contoh resmi
CommonMark 0.31.2 yang diekstrak dari `spec.txt`
(SHA f1fab281; distribusi bagian cocok dengan spek:
Emphasis 132, Links 90, List items 48, …).

## Irisan 1 — Kerangka blok dasar (58/58)

**Konsep.** Parser blok adalah mesin keadaan atas
*baris*: jodohkan awalan kontainer terbuka, coba
awal blok baru, isi daun. Paragraf adalah daun yang
"berlanjut" — baris berikutnya tidak menutupnya,
hanya mengisinya; awal blok yang menginterupsi
(ATX, pagar, quote, …) menutupnya secara implisit
dengan menjadi *saudara*, bukan anak.

**Temuan.** Hampir semua kegagalan awal berasal dari
satu akar: baris yang sudah termakan blok awal
diproses *dua kali* (judul tampil + baris yang sama
jadi paragraf). Pelajarannya generik: mesin dua
langkah butuh sinyal eksplisit "baris habis" —
di sini nilai kembali `True` dari pembuka blok.

## Irisan 2 — Setext, pagar, HTML, quote (125/125)

**Konsep.** Blok HTML punya 7 kondisi awal dan
kondisi akhir yang berbeda-beda; tipe 6/7 berakhir
pada baris kosong, tipe 1–5 pada penanda penutup.
Setext adalah *transformasi* paragraf yang sudah
terbuka, bukan blok baru — karena itu urutan ceknya
kritis: setext sebelum break tematik (`---` di bawah
paragraf adalah garis bawah judul, bukan `<hr />`),
dan break sebelum list (`* * *` adalah `<hr />`,
bukan item).

**Temuan.** Kondisi 6 tidak menuntut tag yang
*lengkap* — cukup nama tag blok diikuti spasi/EOL/
`>`/`/>` (`<div id="foo"` yang menggantung tetap
membuka blok HTML). Yang menuntut tag lengkap +
seluruh baris adalah kondisi 7. Membaca rumusan
speknya kata per kata menghemat dua putaran tebak.

## Irisan 3 — List & item (85/85)

**Konsep.** Item daftar dijodohkan oleh *indentasi
konten relatif*: penanda + spasi sesudahnya (1–4
dihitung penuh, 0 atau ≥5 menjadi penanda+1)
menentukan kolom tempat konten item harus mulai,
diukur relatif terhadap dasar kontainer induknya —
bukan kolom absolut, karena awalan quote yang
dijodohkan ulang bisa bergeser satu spasi antar
baris. Rapat/longgar ditentukan di finalisasi daftar
dari jejak "diakhiri baris kosong" pada item dan
sub-bloknya.

**Temuan.** Tiga aturan kecil yang menentukan:
(1) item hanya boleh *diawali* paling banyak satu
baris kosong — item yang sudah berisi tidak pernah
ditutup oleh baris kosong; (2) baris yang tak cocok
dengan item mana pun tetapi merupakan kelanjutan
paragraf yang terbuka adalah *lazy continuation*
dan tinggal di dalam item, kecuali awal blok di
tingkat yang cocok benar-benar memakannya (dan kode
indentasi tidak pernah menginterupsi paragraf, jadi
ia bukan pemakan yang sah dalam mode lazy);
(3) break tematik di bawah item menutup daftar —
blok baru naik ke induk pertama yang *bisa
menampungnya*.

## Irisan 4 — Inline dasar + definisi (140/140)

**Konsep.** Fase inline adalah satu lintasan atas
string isi daun: escape backslash (hanya tanda baca
ASCII), entitas bernama HTML5 (wajib `;`) dan
numerik (0/surogat/di luar jangkauan → U+FFFD,
0x80–0x9F lewat peta C1), code span berpagar run
backtick sama panjang (newline → spasi; satu spasi
di kedua ujung dikupas bila isi bukan spasi semua),
autolink URI/email, HTML mentah (tag, komentar,
PI, deklarasi, CDATA), dan hard break (backslash
atau ≥2 spasi sebelum newline) vs soft break.

**Temuan.** Definisi referensi adalah tarian dua
bentuk: coba bentuk *berjudul* dulu (judul wajib
terpisah whitespace dari tujuan dan sendirian di
akhir barisnya), dan bila itu gagal, bentuk *tanpa
judul* yang berakhir tepat di akhir baris tujuan
tetap sah — contoh `"title" ok` di baris berikut
membatalkan judul, bukan definisinya. Dan definisi
dipanen bukan hanya saat paragraf ditutup: garis
bawah setext menafsirkan *sisa* paragraf sesudah
definisi dipanen, jadi pemanenan juga terjadi tepat
sebelum konversi setext.

## Irisan 5 — Link & gambar (112/112)

**Konsep.** Kurung `[`/`![` menumpuk; `]` menawari
tiga bentuk berurutan: inline `(tujuan "judul")`,
referensi penuh `[label]`, runtuh `[]`, jalan
pintas. Label dinormalisasi (runtuhkan whitespace,
lipat kasus) dan dicocokkan **mentah** — tanpa
melepas backslash escape: `[foo\!]` tidak cocok
dengan definisi `[foo!]`. Tautan yang terbentuk
memproses emphasis di dalam teksnya lebih dulu,
lalu menonaktifkan semua kurung tautan yang lebih
awal (tautan tak boleh mengandung tautan; gambar
boleh). Alt gambar adalah teks polos anak-anaknya.

**Temuan.** URL di-escape persen ala referensi:
kurung siku `[` `]` *tidak* termasuk karakter aman
(`%5B`/`%5D`), backslash di dalam autolink ikut
ter-encode (`%5C`), dan `%` yang sudah menjadi
awal `%XX` yang valid dipertahankan apa adanya.

## Irisan 6 — Emphasis + skor penuh (132/132; 652/652)

**Konsep.** Run `*`/`_` dicatat sebagai pembatas
dengan kemampuan buka/tutup dari aturan flanking:
kiri = tak diikuti whitespace dan (tak diikuti
tanda baca atau didahului whitespace/tanda baca);
kanan simetris; `_` dibatasi tambahan agar tak
membentuk emphasis di tengah kata. Penutup mencari
pembuka sejenis terdekat; pasangan yang jumlah
run aslinya berkelipatan 3 dilarang bila salah
satunya bisa berperan ganda — kecuali keduanya
berkelipatan 3. Yang terpakai 2 menjadi `<strong>`,
1 menjadi `<em>`; pembatas di antara pasangan yang
terbentuk gugur dari tumpukan.

**Temuan.** Definisi "tanda baca Unicode" di spek
adalah kategori umum **P atau S** — huruf mata uang
`$` (Sc) dan simbol `>` (Sm) adalah tanda baca untuk
flanking, sehingga `*$*` tidak membentuk emphasis:
penutupnya didahului tanda baca dan diikuti bukan
tanda baca, jadi bukan right-flanking. Satu huruf
definisi (S) bernilai satu contoh terakhir dari 132.
