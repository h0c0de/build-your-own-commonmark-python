"""Fase inline CommonMark: string isi blok -> HTML.

Arsitektur mengikuti implementasi referensi: satu
lintasan pemindaian yang membangun simpul-simpul,
dengan *delimiter stack* untuk emphasis dan *bracket
stack* untuk link/gambar, dirujuk silang persis
seperti algoritma di Apendiks spek.
"""

import re
import string
import unicodedata

from entitas import cocok_entitas
from tautan import (lepas_escape, normalisasi_label,
                    urai_judul, urai_tujuan)

RE_AUTOLINK_URI = re.compile(
    r"<([A-Za-z][A-Za-z0-9+.-]{1,31}):([^\s<>]*)>")
RE_AUTOLINK_EMAIL = re.compile(
    r"<([A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*)>")
RE_TAG_INLINE = re.compile(
    r"^<(?:[A-Za-z][A-Za-z0-9-]*"
    r"(?:[ \t\n]+[A-Za-z_:][A-Za-z0-9_.:-]*"
    r"(?:[ \t\n]*=[ \t\n]*"
    r"(?:[^ \t\n\"'=<>`]+|'[^']*'|\"[^\"]*\"))?)*"
    r"[ \t\n]*/?>|/[A-Za-z][A-Za-z0-9-]*[ \t\n]*>)")


def _spasi(c):
    return c.isspace()


def _tanda_baca(c):
    # "Unicode punctuation character" menurut spek:
    # kategori umum P atau S
    return unicodedata.category(c)[0] in "PS"


def _tb_ascii(c):
    return c in string.punctuation


class Simpul:
    __slots__ = ("jenis", "anak", "teks", "data")

    def __init__(self, jenis, teks=None):
        self.jenis = jenis
        self.anak = []
        self.teks = teks
        self.data = {}


class Pembatas:
    """Satu run '*'/'_' pada delimiter stack."""
    __slots__ = ("karakter", "sisa", "awal", "simpul",
                 "bisa_buka", "bisa_tutup", "aktif")

    def __init__(self, karakter, jumlah, simpul,
                 bisa_buka, bisa_tutup):
        self.karakter = karakter
        self.sisa = jumlah
        self.awal = jumlah
        self.simpul = simpul
        self.bisa_buka = bisa_buka
        self.bisa_tutup = bisa_tutup
        self.aktif = True


class Kurung:
    """Satu '[' atau '![' pada bracket stack."""
    __slots__ = ("gambar", "simpul", "indeks_pembatas",
                 "aktif", "pos_awal")

    def __init__(self, gambar, simpul, indeks_pembatas, pos_awal):
        self.gambar = gambar
        self.simpul = simpul
        self.indeks_pembatas = indeks_pembatas
        self.aktif = True
        self.pos_awal = pos_awal


class PenguraiInline:
    def __init__(self, teks, referensi):
        self.teks = teks
        self.pos = 0
        self.referensi = referensi
        self.hasil = []            # simpul tingkat atas
        self.tumpukan_pembatas = []
        self.tumpukan_kurung = []
        self._buf = []             # penyangga teks berjalan

    # ---------- utilitas simpul ----------

    def _tujuan(self):
        return self.hasil

    def _buang_buf(self):
        if self._buf:
            t = "".join(self._buf)
            self._buf = []
            self.hasil.append(Simpul("teks", t))

    def _tambah(self, simpul):
        self._buang_buf()
        self.hasil.append(simpul)
        return simpul

    # ---------- lintasan utama ----------

    def urai(self):
        teks = self.teks
        n = len(teks)
        while self.pos < n:
            c = teks[self.pos]
            if c == "\\":
                self._garis_miring()
            elif c == "`":
                self._bentang_kode()
            elif c == "<":
                if not self._sudut_kiri():
                    self._buf.append("<")
                    self.pos += 1
            elif c == "&":
                cck = cocok_entitas(teks, self.pos)
                if cck:
                    self._buf.append(cck[0])
                    self.pos += cck[1]
                else:
                    self._buf.append("&")
                    self.pos += 1
            elif c == "*" or c == "_":
                self._run_pembatas()
            elif c == "!":
                if self.pos + 1 < n and teks[self.pos + 1] == "[":
                    simpul = self._tambah(Simpul("teks", "!["))
                    self.tumpukan_kurung.append(Kurung(
                        True, simpul,
                        len(self.tumpukan_pembatas), self.pos))
                    self.pos += 2
                else:
                    self._buf.append("!")
                    self.pos += 1
            elif c == "[":
                simpul = self._tambah(Simpul("teks", "["))
                self.tumpukan_kurung.append(Kurung(
                    False, simpul,
                    len(self.tumpukan_pembatas), self.pos))
                self.pos += 1
            elif c == "]":
                if not self._kurung_tutup():
                    self._buf.append("]")
                    self.pos += 1
            elif c == "\n":
                self._baris_baru()
            else:
                self._buf.append(c)
                self.pos += 1
        self._buang_buf()
        self._proses_emphasis(0)
        return self.hasil

    # ---------- potongan-potongan ----------

    def _garis_miring(self):
        teks = self.teks
        berikut = teks[self.pos + 1] if self.pos + 1 < len(teks) \
            else None
        if berikut == "\n":
            self._tambah(Simpul("break_keras"))
            self.pos += 2
            self._lewati_spasi_baris()
        elif berikut is not None and _tb_ascii(berikut):
            self._buf.append(berikut)
            self.pos += 2
        else:
            self._buf.append("\\")
            self.pos += 1

    def _lewati_spasi_baris(self):
        while self.pos < len(self.teks) \
                and self.teks[self.pos] in " \t":
            self.pos += 1

    def _baris_baru(self):
        # hitung spasi ekor pada penyangga teks
        t = "".join(self._buf)
        spasi_ekor = len(t) - len(t.rstrip(" "))
        if spasi_ekor >= 2:
            self._buf = [t.rstrip(" ")] if t.rstrip(" ") else []
            self._tambah(Simpul("break_keras"))
        else:
            if spasi_ekor:
                self._buf = [t.rstrip(" ")] if t.rstrip(" ") else []
            self._tambah(Simpul("break_lunak"))
        self.pos += 1
        self._lewati_spasi_baris()

    def _bentang_kode(self):
        teks = self.teks
        mulai = self.pos
        while self.pos < len(teks) and teks[self.pos] == "`":
            self.pos += 1
        panjang = self.pos - mulai
        pagar = "`" * panjang
        # cari run penutup dengan panjang sama persis
        cari = teks.find(pagar, self.pos)
        isi = None
        while cari != -1:
            # pastikan run di posisi itu panjangnya sama
            ujung = cari + panjang
            sebelum_ok = cari == 0 or teks[cari - 1] != "`"
            sesudah_ok = ujung >= len(teks) or teks[ujung] != "`"
            if sebelum_ok and sesudah_ok:
                isi = teks[self.pos:cari]
                self.pos = ujung
                break
            cari = teks.find(pagar, cari + 1)
        if isi is None:
            self._buf.append(pagar)
            self.pos = mulai + panjang
            return
        isi = isi.replace("\n", " ")
        if len(isi) >= 2 and isi[0] == " " and isi[-1] == " " \
                and isi.strip(" ") != "":
            isi = isi[1:-1]
        self._tambah(Simpul("kode", isi))

    def _sudut_kiri(self):
        """Autolink / HTML mentah di '<'. True bila termakan."""
        teks = self.teks
        sisa = teks[self.pos:]
        m = RE_AUTOLINK_URI.match(sisa)
        if m:
            uri = m.group(1) + ":" + m.group(2)
            simpul = self._tambah(Simpul("tautan"))
            simpul.data.update(tujuan=uri, judul=None)
            simpul.anak.append(Simpul("teks", uri))
            self.pos += m.end()
            return True
        m = RE_AUTOLINK_EMAIL.match(sisa)
        if m:
            email = m.group(1)
            simpul = self._tambah(Simpul("tautan"))
            simpul.data.update(tujuan="mailto:" + email,
                               judul=None)
            simpul.anak.append(Simpul("teks", email))
            self.pos += m.end()
            return True
        mentah = self._html_mentah(sisa)
        if mentah is not None:
            self._tambah(Simpul("html", mentah))
            self.pos += len(mentah)
            return True
        return False

    def _html_mentah(self, sisa):
        if sisa.startswith("<!--"):
            # komentar: <!--> dan <!---> bentuk khusus;
            # selain itu teks apa pun sampai --> pertama
            if sisa.startswith("<!-->"):
                return "<!-->"
            if sisa.startswith("<!--->"):
                return "<!--->"
            akhir = sisa.find("-->", 4)
            if akhir == -1:
                return None
            return sisa[:akhir + 3]
        if sisa.startswith("<?"):
            akhir = sisa.find("?>", 2)
            if akhir == -1:
                return None
            return sisa[:akhir + 2]
        if sisa.startswith("<![CDATA["):
            akhir = sisa.find("]]>", 9)
            if akhir == -1:
                return None
            return sisa[:akhir + 3]
        if re.match(r"^<![A-Z]", sisa):
            akhir = sisa.find(">", 2)
            if akhir == -1:
                return None
            return sisa[:akhir + 1]
        m = RE_TAG_INLINE.match(sisa)
        if m:
            return m.group(0)
        return None

    def _run_pembatas(self):
        teks = self.teks
        c = teks[self.pos]
        mulai = self.pos
        while self.pos < len(teks) and teks[self.pos] == c:
            self.pos += 1
        jumlah = self.pos - mulai
        # konteks flanking
        sebelum = teks[mulai - 1] if mulai > 0 else None
        sesudah = teks[self.pos] if self.pos < len(teks) else None
        sesudah_spasi = sesudah is None or _spasi(sesudah)
        sesudah_tb = sesudah is not None and _tanda_baca(sesudah)
        sebelum_spasi = sebelum is None or _spasi(sebelum)
        sebelum_tb = sebelum is not None and _tanda_baca(sebelum)
        kiri = not sesudah_spasi and (not sesudah_tb or sebelum_spasi
                                      or sebelum_tb)
        kanan = not sebelum_spasi and (not sebelum_tb or sesudah_spasi
                                       or sesudah_tb)
        if c == "*":
            bisa_buka, bisa_tutup = kiri, kanan
        else:
            bisa_buka = kiri and (not kanan or sebelum_tb)
            bisa_tutup = kanan and (not kiri or sesudah_tb)
        simpul = self._tambah(Simpul("teks", c * jumlah))
        self.tumpukan_pembatas.append(Pembatas(
            c, jumlah, simpul, bisa_buka, bisa_tutup))

    # ---------- link & gambar ----------

    def _kurung_tutup(self):
        """Coba bentuk link/gambar pada ']'. True bila
        sebuah simpul tautan/gambar terbentuk ATAU kurung
        terproses (kurung literal ditangani pemanggil)."""
        if not self.tumpukan_kurung:
            return False
        kurung = self.tumpukan_kurung[-1]
        if not kurung.aktif:
            self.tumpukan_kurung.pop()
            return False
        teks = self.teks
        pos_tutup = self.pos
        # 1) tautan inline: (tujuan "judul")
        hasil = None
        pos_sesudah = None
        if pos_tutup + 1 < len(teks) and teks[pos_tutup + 1] == "(":
            r = self._urai_tautan_inline(pos_tutup + 1)
            if r is not None:
                hasil, pos_sesudah = r
        # 2) referensi penuh / runtuh
        if hasil is None:
            label_ref = None
            if pos_tutup + 1 < len(teks) \
                    and teks[pos_tutup + 1] == "[":
                r = self._urai_label_ref(pos_tutup + 1)
                if r is not None:
                    label_ref, pos_sesudah = r
                    if label_ref == "":
                        # referensi runtuh: label = isi kurung
                        label_ref = teks[
                            kurung.pos_awal +
                            (2 if kurung.gambar else 1):
                            pos_tutup]
            if label_ref is None:
                # jalan pintas: label = isi kurung sendiri
                mentah = teks[kurung.pos_awal +
                              (2 if kurung.gambar else 1):
                              pos_tutup]
                label_ref = mentah
                pos_sesudah = pos_tutup + 1
            kunci = normalisasi_label(label_ref)
            if kunci and kunci in self.referensi:
                tujuan, judul = self.referensi[kunci]
                hasil = (tujuan, judul)
            else:
                pos_sesudah = None
        if hasil is None:
            self.tumpukan_kurung.pop()
            return False
        tujuan, judul = hasil
        # teks tepat sebelum ']' mungkin masih di penyangga
        self._buang_buf()
        # proses emphasis di dalam teks tautan dulu,
        # lalu pembatas di dalamnya keluar dari tumpukan
        self._proses_emphasis(kurung.indeks_pembatas)
        del self.tumpukan_pembatas[kurung.indeks_pembatas:]
        # kumpulkan anak: simpul sesudah simpul kurung
        i = self.hasil.index(kurung.simpul)
        anak = self.hasil[i + 1:]
        del self.hasil[i:]
        # simpul kurung ('[' / '![') dibuang; untuk gambar
        # teks '!' ikut hilang karena satu simpul
        simpul = Simpul("gambar" if kurung.gambar else "tautan")
        simpul.data.update(tujuan=tujuan, judul=judul)
        simpul.anak = anak
        self.hasil.append(simpul)
        self.tumpukan_kurung.pop()
        if not kurung.gambar:
            # tautan tak boleh berisi tautan: nonaktifkan
            # kurung tautan yang lebih awal
            for k in self.tumpukan_kurung:
                if not k.gambar:
                    k.aktif = False
        self.pos = pos_sesudah
        return True

    def _urai_tautan_inline(self, pos):
        """Urai '( tujuan "judul" )' mulai di pos '('.
        Kembalikan ((tujuan, judul), pos_baru) / None."""
        teks = self.teks
        i = pos + 1
        # lewati spasi/newline
        while i < len(teks) and teks[i] in " \t\n":
            i += 1
        if i < len(teks) and teks[i] == ")":
            return ("", None), i + 1
        t = urai_tujuan(teks, i)
        if t is None:
            return None
        tujuan_mentah, i = t
        # tujuan telanjang tak boleh mengandung '<'
        # (urai_tujuan berkurung menanganinya sendiri)
        simpan = i
        spasi = False
        while i < len(teks) and teks[i] in " \t\n":
            if teks[i] in " \t\n":
                spasi = True
            i += 1
        judul = None
        if i < len(teks) and teks[i] == ")":
            return (lepas_escape_dan_entitas(tujuan_mentah),
                    None), i + 1
        if not spasi:
            return None
        ju = urai_judul(teks, i)
        if ju is None:
            return None
        judul_mentah, i = ju
        while i < len(teks) and teks[i] in " \t\n":
            i += 1
        if i < len(teks) and teks[i] == ")":
            return (lepas_escape_dan_entitas(tujuan_mentah),
                    lepas_escape_dan_entitas(judul_mentah)), i + 1
        return None

    def _urai_label_ref(self, pos):
        """Urai '[label]' mulai di pos '['. Kembalikan
        (label_mentah, pos_baru) / None. Label kosong
        berarti referensi runtuh (None -> pemanggil
        memakai isi kurung)."""
        teks = self.teks
        i = pos + 1
        isi = []
        while i < len(teks):
            c = teks[i]
            if c == "\\" and i + 1 < len(teks):
                isi.append(teks[i:i + 2])
                i += 2
                continue
            if c == "]":
                # label kosong sah: referensi runtuh,
                # dikembalikan sebagai string kosong
                return "".join(isi), i + 1
            if c == "[":
                return None
            isi.append(c)
            i += 1
        return None

    # ---------- emphasis ----------

    def _proses_emphasis(self, batas_bawah):
        """Proses delimiter stack dari indeks batas_bawah."""
        tumpukan = self.tumpukan_pembatas
        # indeks penutup berjalan dari bawah
        i_tutup = batas_bawah
        while i_tutup < len(tumpukan):
            penutup = tumpukan[i_tutup]
            if not penutup.bisa_tutup or penutup.sisa == 0:
                i_tutup += 1
                continue
            # cari pembuka terdekat di bawahnya
            i_buka = i_tutup - 1
            ketemu = None
            while i_buka >= batas_bawah:
                pembuka = tumpukan[i_buka]
                if pembuka.karakter == penutup.karakter \
                        and pembuka.bisa_buka and pembuka.sisa > 0:
                    # aturan kelipatan 3
                    if (pembuka.bisa_tutup or penutup.bisa_buka) \
                            and (pembuka.awal + penutup.awal) % 3 == 0 \
                            and not (pembuka.awal % 3 == 0
                                     and penutup.awal % 3 == 0):
                        i_buka -= 1
                        continue
                    ketemu = i_buka
                    break
                i_buka -= 1
            if ketemu is None:
                i_tutup += 1
                continue
            pembuka = tumpukan[ketemu]
            pakai = 2 if pembuka.sisa >= 2 and penutup.sisa >= 2 \
                else 1
            pembuka.sisa -= pakai
            penutup.sisa -= pakai
            # perbarui teks simpul pembatas
            pembuka.simpul.teks = pembuka.karakter * pembuka.sisa
            penutup.simpul.teks = penutup.karakter * penutup.sisa
            # bungkus simpul di antara keduanya
            jenis = "strong" if pakai == 2 else "em"
            simpul_baru = Simpul(jenis)
            daftar = self._daftar_simpul()
            a = daftar.index(pembuka.simpul)
            b = daftar.index(penutup.simpul)
            simpul_baru.anak = daftar[a + 1:b]
            self._ganti_rentang(a + 1, b, simpul_baru)
            # pembatas di antara: keluar dari tumpukan
            for j in range(i_tutup - 1, ketemu, -1):
                tumpukan.pop(j)
            i_tutup -= (i_tutup - ketemu - 1) if False else 0
            # sesuaikan indeks penutup sesudah pemindahan
            i_tutup = tumpukan.index(penutup)
            if penutup.sisa == 0:
                tumpukan.pop(i_tutup)
            if pembuka.sisa == 0:
                tumpukan.pop(tumpukan.index(pembuka))
                i_tutup -= 1
            # penutup yang sama boleh menutup lagi
        # bersihkan pembatas habis di atas batas
        self.tumpukan_pembatas = [
            p for j, p in enumerate(tumpukan)
            if p.sisa > 0 or j < batas_bawah]

    def _daftar_simpul(self):
        return self.hasil

    def _ganti_rentang(self, a, b, simpul):
        self.hasil[a:b] = [simpul]


def lepas_escape_dan_entitas(teks):
    from entitas import dekode_entitas
    return dekode_entitas(lepas_escape(teks))


# ---------- rendering ----------

def escape_html(teks, kutip=False):
    teks = teks.replace("&", "&amp;").replace("<", "&lt;") \
        .replace(">", "&gt;")
    if kutip:
        teks = teks.replace('"', "&quot;")
    return teks


_HREF_AMAN = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "0123456789-._~:/?#@!$&'()*+,;=")


def encode_url(url):
    """Pengkodean persen ala referensi (houdini):
    karakter aman dipertahankan, %XX valid dipertahankan,
    sisanya di-encode persen per byte UTF-8."""
    hasil = []
    i = 0
    while i < len(url):
        c = url[i]
        if c in _HREF_AMAN:
            hasil.append(c)
            i += 1
        elif c == "%" and i + 2 < len(url) + 0 and \
                i + 2 <= len(url) - 1 and \
                all(ch in "0123456789ABCDEFabcdef"
                    for ch in url[i + 1:i + 3]):
            hasil.append("%")
            i += 1
        else:
            for b in c.encode("utf-8"):
                hasil.append("%%%02X" % b)
            i += 1
    return "".join(hasil)


def render_simpul(simpul):
    jenis = simpul.jenis
    if jenis == "teks":
        return escape_html(simpul.teks, kutip=True)
    if jenis == "kode":
        return "<code>%s</code>" % escape_html(simpul.teks,
                                               kutip=True)
    if jenis == "html":
        return simpul.teks
    if jenis == "em":
        return "<em>%s</em>" % render_anak(simpul)
    if jenis == "strong":
        return "<strong>%s</strong>" % render_anak(simpul)
    if jenis == "break_keras":
        return "<br />\n"
    if jenis == "break_lunak":
        return "\n"
    if jenis == "tautan":
        href = escape_html(encode_url(simpul.data["tujuan"]),
                           kutip=True)
        if simpul.data.get("judul") is not None:
            return '<a href="%s" title="%s">%s</a>' % (
                href,
                escape_html(simpul.data["judul"], kutip=True),
                render_anak(simpul))
        return '<a href="%s">%s</a>' % (href, render_anak(simpul))
    if jenis == "gambar":
        src = escape_html(encode_url(simpul.data["tujuan"]),
                          kutip=True)
        alt = teks_poloss(simpul)
        if simpul.data.get("judul") is not None:
            return '<img src="%s" alt="%s" title="%s" />' % (
                src, escape_html(alt, kutip=True),
                escape_html(simpul.data["judul"], kutip=True))
        return '<img src="%s" alt="%s" />' % (
            src, escape_html(alt, kutip=True))
    return render_anak(simpul)


def render_anak(simpul):
    return "".join(render_simpul(a) for a in simpul.anak)


def teks_poloss(simpul):
    """Teks polos isi simpul (untuk alt gambar)."""
    if simpul.jenis == "teks" or simpul.jenis == "kode":
        return simpul.teks
    if simpul.jenis == "html":
        return simpul.teks
    if simpul.jenis in ("break_keras", "break_lunak"):
        return "\n"
    return "".join(teks_poloss(a) for a in simpul.anak)


def render_inline(isi, referensi):
    teks = isi.strip("\n")
    # buang spasi ekor baris terakhir & newline penutup
    teks = teks.rstrip(" \t")
    pengurai = PenguraiInline(teks, referensi)
    simpul = pengurai.urai()
    return "".join(render_simpul(s) for s in simpul)
