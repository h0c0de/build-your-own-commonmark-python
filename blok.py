"""Fase blok CommonMark: teks -> pohon blok.

Mengikuti strategi resmi spek (dua fase) dengan mesin
buka/tutup blok ala implementasi referensi:

- Tiap baris: jodohkan awalan kontainer terbuka,
  coba blok awal baru (termasuk spekulatif di tingkat
  yang cocok bila ada kontainer tak cocok — dari sana
  diputuskan "lazy continuation" paragraf), lalu isi.
- Blok daun mengakumulasi string isi; paragraf yang
  ditutup dipanen definisi referensi link-nya.
- Kolom tab dihitung ke kelipatan 4 dan tab bisa
  terkonsumsi sebagian.
"""

import re

from tautan import urai_definisi_referensi


class Blok:
    __slots__ = ("jenis", "anak", "induk", "isi", "data",
                 "kosong_terakhir", "terbuka")

    def __init__(self, jenis):
        self.jenis = jenis
        self.anak = []
        self.induk = None
        self.isi = ""          # string isi untuk blok daun
        self.data = {}
        self.kosong_terakhir = False
        self.terbuka = True

    def tambah_anak(self, anak):
        anak.induk = self
        self.anak.append(anak)
        return anak


def _anak_terakhir(blok):
    return blok.anak[-1] if blok.anak else None


def diakhiri_kosong(blok):
    """Blok ini (atau anak terakhirnya, untuk kontainer
    daftar/item) diakhiri baris kosong."""
    if blok.kosong_terakhir:
        return True
    if blok.jenis in ("daftar", "item") and blok.anak:
        return diakhiri_kosong(blok.anak[-1])
    return False


def _dapat_menampung(jenis_induk, jenis_anak):
    if jenis_induk in ("dokumen", "kutipan", "item"):
        return True
    if jenis_induk == "daftar":
        return jenis_anak == "item"
    return False


# ---------- pola-pola awal blok ----------

RE_ATX = re.compile(r"^(#{1,6})(?:[ \t]+(.*))?$")
RE_ATX_TUTUP = re.compile(r"[ \t]+#+[ \t]*$|^[ \t]*#+[ \t]*$")
RE_PAGAR = re.compile(r"^(`{3,}|~{3,})[ \t]*(.*)$")
RE_HTML_TAG = re.compile(
    r"^<(?:[A-Za-z][A-Za-z0-9-]*"
    r"(?:[ \t]+[A-Za-z_:][A-Za-z0-9_.:-]*"
    r"(?:[ \t]*=[ \t]*(?:[^ \t\"'=<>`]+|'[^']*'|\"[^\"]*\"))?)*"
    r"[ \t]*/?>|/[A-Za-z][A-Za-z0-9-]*[ \t]*>)")
RE_SETEXT = re.compile(r"^(=+|-+)[ \t]*$")
RE_BREAK = [
    re.compile(r"^(?:[ \t]*%s){3,}[ \t]*$" % re.escape(c))
    for c in "*-_"
]
TAG_BLOK_HTML = {
    "address", "article", "aside", "base", "basefont",
    "blockquote", "body", "caption", "center", "col",
    "colgroup", "dd", "details", "dialog", "dir", "div",
    "dl", "dt", "fieldset", "figcaption", "figure",
    "footer", "form", "frame", "frameset", "h1", "h2",
    "h3", "h4", "h5", "h6", "head", "header", "hr",
    "html", "iframe", "legend", "li", "link", "main",
    "menu", "menuitem", "nav", "noframes", "ol",
    "optgroup", "option", "p", "param", "search", "section",
    "source", "summary", "table", "tbody", "td",
    "tfoot", "th", "thead", "title", "tr", "track", "ul",
}
TAG_AKHIR_HTML = {
    1: ("</pre", "</script", "</style", "</textarea"),
    2: ("-->",),
    3: ("?>",),
    4: (">",),
    5: ("]]>",),
}


def kondisi_awal_html(teks):
    """Tipe blok HTML (1-7) bila teks (sesudah <=3 spasi)
    memenuhi syarat awal spek; None bila tidak."""
    rendah = teks.lower()
    for tag in ("pre", "script", "style", "textarea"):
        if rendah.startswith("<" + tag) and (
                len(teks) == len(tag) + 1
                or teks[len(tag) + 1] in " \t>"):
            return 1
    if teks.startswith("<!--"):
        return 2
    if teks.startswith("<?"):
        return 3
    if re.match(r"^<![A-Z]", teks):
        return 4
    if teks.startswith("<![CDATA["):
        return 5
    m = re.match(r"^</?([A-Za-z][A-Za-z0-9-]*)", teks)
    if m and m.group(1).lower() in TAG_BLOK_HTML:
        # tipe 6: nama tag blok diikuti spasi/tab/EOL/>/>
        rest = teks[m.end():]
        if rest == "" or rest[0] in " \t>" \
                or rest.startswith("/>"):
            return 6
    # tipe 7: tag lengkap (bukan pre/script/style/
    # textarea) memenuhi seluruh baris
    mt = RE_HTML_TAG.match(teks)
    if mt and m and m.group(1).lower() not in (
            "pre", "script", "style", "textarea"):
        if teks[mt.end():].strip(" \t") == "":
            return 7
    return None


def kondisi_akhir_html(tipe, baris):
    """Baris ini mengakhiri blok HTML tipe tsb?"""
    rendah = baris.lower()
    if tipe == 1:
        return any(t in rendah for t in TAG_AKHIR_HTML[1])
    if tipe in TAG_AKHIR_HTML:
        return any(t in baris for t in TAG_AKHIR_HTML[tipe])
    return False  # tipe 6/7 berakhir pada baris kosong


class PenguraiBlok:
    def __init__(self):
        self.dokumen = Blok("dokumen")
        self.ujung = self.dokumen
        self.referensi = {}
        # keadaan baris berjalan
        self.baris = ""
        self.pos = 0
        self.kolom = 0
        self.tab_parsial = False

    # ---------- mesin posisi/kolom ----------

    def _intip(self):
        if self.pos < len(self.baris):
            return self.baris[self.pos]
        return None

    def _indentasi(self):
        """Kolom spasi dari posisi kini ke non-spasi berikut."""
        kolom = 0
        i = self.pos
        if self.tab_parsial:
            kolom += 4 - (self.kolom % 4)
            i += 1
        while i < len(self.baris):
            c = self.baris[i]
            if c == " ":
                kolom += 1
            elif c == "\t":
                kolom += 4 - ((self.kolom + kolom) % 4)
            else:
                break
            i += 1
        return kolom

    def _maju(self, n_kolom):
        """Maju n kolom (tab boleh terkonsumsi sebagian)."""
        while n_kolom > 0:
            c = self._intip()
            if c is None:
                break
            if c == "\t":
                lebar = 4 - (self.kolom % 4)
                if n_kolom < lebar:
                    self.tab_parsial = True
                    self.kolom += n_kolom
                    return
                self.pos += 1
                self.kolom += lebar
                n_kolom -= lebar
                self.tab_parsial = False
            else:
                self.pos += 1
                self.kolom += 1
                n_kolom -= 1
                self.tab_parsial = False

    def _maju_karakter(self, n=1):
        for _ in range(n):
            if self.pos < len(self.baris):
                if self.baris[self.pos] == "\t":
                    self.kolom += 4 - (self.kolom % 4)
                else:
                    self.kolom += 1
                self.pos += 1
        self.tab_parsial = False

    def _simpan(self):
        return (self.pos, self.kolom, self.tab_parsial)

    def _pulihkan(self, keadaan):
        self.pos, self.kolom, self.tab_parsial = keadaan

    def _sisa(self):
        if self.tab_parsial:
            sisa_tab = 4 - (self.kolom % 4)
            return " " * sisa_tab + self.baris[self.pos + 1:]
        return self.baris[self.pos:]

    def _kosong(self):
        return self._sisa().strip() == ""

    # ---------- utilitas pohon ----------

    def _tutup_sampai(self, target):
        """Finalisasi semua blok terbuka sampai (tidak
        termasuk) target; ujung berpindah ke target."""
        while self.ujung is not target:
            self._finalisasi(self.ujung)
            self.ujung = self.ujung.induk

    def _tambah(self, jenis):
        blok = self.ujung.tambah_anak(Blok(jenis))
        self.ujung = blok
        return blok

    def _tambah_blok(self, jenis):
        """Tambah blok baru, naik menutup blok yang tak
        bisa menampungnya (paragraf, daftar, dst.)."""
        while not _dapat_menampung(self.ujung.jenis, jenis):
            induk = self.ujung.induk
            self._finalisasi(self.ujung)
            self.ujung = induk
        return self._tambah(jenis)

    # ---------- finalisasi per jenis ----------

    def _finalisasi(self, blok):
        blok.terbuka = False
        if blok.jenis == "paragraf":
            sisa = urai_definisi_referensi(blok.isi, self.referensi)
            if sisa is None:
                blok.induk.anak.remove(blok)
            else:
                blok.isi = sisa
        elif blok.jenis == "kode":
            if not blok.data.get("pagar"):
                blok.isi = blok.isi.rstrip("\n")
                if blok.isi:
                    blok.isi += "\n"
            else:
                if blok.isi and not blok.isi.endswith("\n"):
                    blok.isi += "\n"
        elif blok.jenis == "daftar":
            self._finalisasi_daftar(blok)

    def _finalisasi_daftar(self, daftar):
        rapat = True
        item = daftar.anak[0] if daftar.anak else None
        while item is not None:
            if diakhiri_kosong(item) and \
                    self._saudara(item) is not None:
                rapat = False
                break
            for sub in item.anak:
                if diakhiri_kosong(sub) and (
                        self._saudara(sub) is not None
                        or self._saudara(item) is not None):
                    rapat = False
                    break
            if not rapat:
                break
            item = self._saudara(item)
        daftar.data["rapat"] = rapat

    @staticmethod
    def _saudara(blok):
        saudara = blok.induk.anak
        i = saudara.index(blok)
        return saudara[i + 1] if i + 1 < len(saudara) else None

    # ---------- proses baris ----------

    def urai(self, teks):
        if not teks.endswith("\n"):
            teks += "\n"
        for baris in teks.split("\n")[:-1]:
            self._proses_baris(baris)
        self._tutup_sampai(self.dokumen)
        return self.dokumen

    def _proses_baris(self, baris):
        self.baris = baris
        self.pos = 0
        self.kolom = 0
        self.tab_parsial = False
        # kosong_terakhir = "baris terakhir yang masuk ke
        # blok ini kosong": nolkan pada rantai terbuka
        node = self.dokumen
        while True:
            node.kosong_terakhir = False
            anak = _anak_terakhir(node)
            if anak is None or not anak.terbuka:
                break
            node = anak

        tip_awal = self.ujung
        cocok = self._jodohkan_kontainer()
        semua_cocok = cocok is tip_awal

        # --- daun konsumen yang cocok penuh ---
        if semua_cocok and cocok.jenis == "kode" \
                and cocok.data.get("pagar"):
            self._baris_kode_pagar(cocok)
            return
        if semua_cocok and cocok.jenis == "kode":
            if self._kosong():
                self._tangani_kosong()
            else:
                cocok.isi += self._sisa() + "\n"
            return
        if semua_cocok and cocok.jenis == "html":
            tipe = cocok.data["tipe"]
            if tipe in (6, 7) and self._kosong():
                self._tutup_sampai(cocok.induk)
                self._tangani_kosong()
                return
            self._tambah_isi_html(cocok)
            return

        if semua_cocok:
            if self._kosong():
                self._tangani_kosong()
                return
            if self._buka_blok_baru():
                return
            if self._kosong():
                # sisa baris sesudah penanda item kosong:
                # baris ini kosong bagi item tsb
                self._tangani_kosong()
                return
            self._isi_baris()
            return

        # --- ada kontainer yang tak cocok ---
        if self._kosong():
            self._tutup_sampai(cocok)
            self._tangani_kosong()
            return
        # coba blok awal di tingkat yang cocok
        self.ujung = cocok
        anak_sebelum = len(cocok.anak)
        # paragraf terbuka di cabang tak cocok = kandidat
        # lazy: kode indentasi tak boleh menginterupsinya
        self._dari_lazy = tip_awal.jenis == "paragraf"
        habis = self._buka_blok_baru()
        self._dari_lazy = False
        if habis or self.ujung is not cocok \
                or len(cocok.anak) != anak_sebelum:
            tip_baru = self.ujung
            self.ujung = tip_awal
            self._tutup_sampai(cocok)
            self.ujung = tip_baru
            if not habis:
                if self._kosong():
                    self._tangani_kosong()
                else:
                    self._isi_baris()
            return
        # tak termakan: lanjutkan paragraf secara lazy
        self.ujung = tip_awal
        if tip_awal.jenis == "paragraf":
            tip_awal.isi += self._sisa() + "\n"
            return
        self._tutup_sampai(cocok)
        if self._buka_blok_baru():
            return
        self._isi_baris()

    def _isi_baris(self):
        """Baris ini menjadi isi daun berjalan / paragraf baru."""
        if self.ujung.jenis == "paragraf":
            self.ujung.isi += self._sisa() + "\n"
        elif self.ujung.jenis == "kode":
            self.ujung.isi += self._sisa() + "\n"
        else:
            if self._indentasi() <= 3:
                self._maju(self._indentasi())
            par = self._tambah_blok("paragraf")
            par.isi = self._sisa() + "\n"

    def _tangani_kosong(self):
        # tandai ujung dan rantai anak-terakhir di
        # bawahnya sebagai diakhiri-kosong (semantik
        # endsWithBlankLine referensi)
        node = self.ujung
        while node is not None:
            if not (node is self.ujung and node.jenis == "kode"):
                node.kosong_terakhir = True
            if node.jenis in ("dokumen", "kutipan",
                              "daftar", "item") and node.anak:
                node = node.anak[-1]
            else:
                break
        if self.ujung.jenis == "paragraf":
            self._tutup_sampai(self.ujung.induk)
        elif self.ujung.jenis == "kode" and \
                not self.ujung.data.get("pagar"):
            # baris kosong masuk kode indentasi sebagai
            # isi spekulatif (dipotong bila jadi ekor)
            self._maju(min(self._indentasi(), 4))
            self.ujung.isi += self._sisa() + "\n"
        elif self.ujung.jenis == "html":
            self._tutup_sampai(self.ujung.induk)
        elif self.ujung.jenis == "item":
            self.ujung.kosong_terakhir = True
            if not self.ujung.anak:
                self.ujung.data["pernah_kosong"] = True

    def _jodohkan_kontainer(self):
        """Jalan menuruni blok terbuka; kembalikan blok
        terdalam yang awalannya cocok dengan baris ini."""
        kontainer = self.dokumen
        while True:
            anak = _anak_terakhir(kontainer)
            if anak is None or not anak.terbuka:
                return kontainer
            if anak.jenis == "kutipan":
                keadaan = self._simpan()
                if self._indentasi() <= 3:
                    self._maju(self._indentasi())
                    if self._intip() == ">":
                        self._maju_karakter(1)
                        if self._intip() == " ":
                            self._maju_karakter(1)
                        elif self._intip() == "\t":
                            self._maju(1)
                        kontainer = anak
                        continue
                self._pulihkan(keadaan)
                return kontainer
            elif anak.jenis == "daftar":
                kontainer = anak
            elif anak.jenis == "item":
                if self._kosong():
                    # baris kosong cocok — kecuali item
                    # masih kosong (belum berisi) dan sudah
                    # diawali satu baris kosong: item hanya
                    # boleh diawali MAKS satu baris kosong
                    if not anak.anak and \
                            anak.data.get("pernah_kosong"):
                        return kontainer
                    kontainer = anak
                elif self._indentasi() >= anak.data["rel_konten"]:
                    self._maju(anak.data["rel_konten"])
                    kontainer = anak
                else:
                    return kontainer
            elif anak.jenis == "kode" and anak.data.get("pagar"):
                return anak
            elif anak.jenis == "kode":
                if self._kosong() or self._indentasi() >= 4:
                    if not self._kosong():
                        self._maju(4)
                    return anak
                return kontainer
            elif anak.jenis == "html":
                if anak.data.get("berakhir"):
                    return kontainer
                return anak
            else:
                # paragraf: daun yang berlanjut
                return anak

    # ---------- kode pagar & html ----------

    def _baris_kode_pagar(self, blok):
        data = blok.data
        simpan = self._simpan()
        if self._indentasi() <= 3:
            self._maju(self._indentasi())
            sisa = self._sisa()
            m = re.match(r"^(`{3,}|~{3,})[ \t]*$", sisa)
            if m and m.group(1)[0] == data["karakter"] \
                    and len(m.group(1)) >= data["panjang"]:
                self._tutup_sampai(blok.induk)
                return
        self._pulihkan(simpan)
        strip = min(self._indentasi(), data["indent"])
        self._maju(strip)
        blok.isi += self._sisa() + "\n"
        self.ujung = blok

    def _tambah_isi_html(self, blok):
        blok.isi += self._sisa() + "\n"
        self.ujung = blok
        if kondisi_akhir_html(blok.data["tipe"], self._sisa()):
            blok.data["berakhir"] = True

    # ---------- membuka blok baru ----------

    def _buka_blok_baru(self):
        """Coba mulai blok baru. True bila baris habis
        termakan; False bila baris adalah isi daun."""
        while True:
            jenis_ujung = self.ujung.jenis
            if jenis_ujung in ("kode", "html"):
                return True
            simpan = self._simpan()
            indent = self._indentasi()

            # --- kutipan blok ---
            if indent <= 3:
                self._maju(indent)
                if self._intip() == ">":
                    self._maju_karakter(1)
                    if self._intip() == " ":
                        self._maju_karakter(1)
                    elif self._intip() == "\t":
                        self._maju(1)
                    self._tambah_blok("kutipan")
                    continue
                self._pulihkan(simpan)

            sisa = self._sisa_setelah_indent(indent)

            # --- judul ATX ---
            if indent <= 3:
                m = RE_ATX.match(sisa)
                if m:
                    blok = self._tambah_blok("judul")
                    blok.data["level"] = len(m.group(1))
                    isi = (m.group(2) or "").rstrip(" \t")
                    isi = RE_ATX_TUTUP.sub("", isi).rstrip(" \t")
                    blok.isi = isi
                    self._tutup_sampai(blok.induk)
                    return True

            # --- kode pagar ---
            if indent <= 3:
                m = RE_PAGAR.match(sisa)
                if m and not (m.group(1)[0] == "`"
                              and "`" in m.group(2)):
                    blok = self._tambah_blok("kode")
                    blok.data.update(
                        pagar=True, karakter=m.group(1)[0],
                        panjang=len(m.group(1)), indent=indent,
                        info=m.group(2).strip())
                    return True

            # --- blok HTML ---
            if indent <= 3:
                tipe = kondisi_awal_html(sisa)
                if tipe is not None and not (
                        tipe == 7 and jenis_ujung == "paragraf"):
                    blok = self._tambah_blok("html")
                    blok.data.update(tipe=tipe, berakhir=False)
                    self._tambah_isi_html(blok)
                    return True

            # --- judul setext (hanya di atas paragraf) ---
            if jenis_ujung == "paragraf" and indent <= 3:
                m = RE_SETEXT.match(sisa)
                if m:
                    par = self.ujung
                    # definisi referensi di awal paragraf
                    # dipanen DULU: paragraf yang isinya
                    # habis oleh definisi bukan judul
                    sisa_isi = urai_definisi_referensi(
                        par.isi, self.referensi)
                    if sisa_isi is None:
                        self._tutup_sampai(par.induk)
                        # baris garis bawah kini berdiri
                        # sendiri: nilai ulang sbg awal lain
                        continue
                    par.isi = sisa_isi
                    par.jenis = "judul"
                    par.data["level"] = 1 if m.group(1)[0] == "=" else 2
                    par.isi = par.isi.rstrip("\n")
                    self._tutup_sampai(par.induk)
                    return True

            # --- break tematik (bisa menginterupsi
            # paragraf; setext sudah didahulukan) ---
            if indent <= 3 \
                    and any(r.match(sisa) for r in RE_BREAK):
                blok = self._tambah_blok("break")
                self._tutup_sampai(blok.induk)
                return True

            # --- daftar / item ---
            if self._coba_daftar(indent, jenis_ujung):
                continue

            # --- kode indentasi ---
            if indent >= 4 and jenis_ujung != "paragraf" \
                    and not getattr(self, "_dari_lazy", False):
                self._maju(4)
                blok = self._tambah_blok("kode")
                blok.data.update(pagar=False)
                blok.isi = self._sisa() + "\n"
                return True

            return False

    def _sisa_setelah_indent(self, indent):
        simpan = self._simpan()
        self._maju(indent)
        sisa = self._sisa()
        self._pulihkan(simpan)
        return sisa

    # ---------- daftar ----------

    def _urai_penanda(self, indent):
        """Kenali penanda item pada posisi sesudah indent.
        Kembalikan (data, lebar, spasi, kosong) / None."""
        if indent > 3:
            return None
        simpan = self._simpan()
        self._maju(indent)
        teks = self._sisa()
        m = re.match(r"^([*+-])([ \t]|$)", teks)
        if m:
            data = {"tipe": "bullet", "penanda": m.group(1)}
            lebar = 1
        else:
            m = re.match(r"^(\d{1,9})([.)])([ \t]|$)", teks)
            if not m:
                self._pulihkan(simpan)
                return None
            data = {"tipe": "urut", "penanda": m.group(2),
                    "mulai": int(m.group(1))}
            lebar = len(m.group(1)) + 1
        self._maju_karakter(lebar)
        spasi = 0
        i = self.pos
        kolom = self.kolom
        kosong = True
        while i < len(self.baris):
            c = self.baris[i]
            if c == " ":
                spasi += 1
                i += 1
            elif c == "\t":
                spasi += 4 - (kolom + spasi) % 4
                i += 1
            else:
                kosong = False
                break
        self._pulihkan(simpan)
        return data, lebar, spasi, kosong

    def _coba_daftar(self, indent, jenis_ujung):
        hasil = self._urai_penanda(indent)
        if hasil is None:
            return False
        data, lebar, spasi, kosong = hasil
        # aturan interupsi paragraf
        if jenis_ujung == "paragraf":
            if kosong:
                return False
            if data["tipe"] == "urut" and data["mulai"] != 1:
                return False
        # indent konten: spasi 1-4 penuh; 0 / >=5 ->
        # selebar penanda + 1
        if kosong or spasi == 0 or spasi > 4:
            indent_konten = lebar + 1
        else:
            indent_konten = lebar + spasi
        # daftar terbuka dengan data sama dipakai lagi
        induk = self.ujung
        daftar_lama = None
        if induk.jenis == "daftar":
            d = induk.data
            sama = d["tipe"] == data["tipe"] and \
                d.get("penanda") == data.get("penanda")
            if sama:
                daftar_lama = induk
        if daftar_lama is None:
            daftar = self._tambah_blok("daftar")
            daftar.data.update(data)
            daftar.data["rapat"] = True
        # maju melewati indent + indent konten; simpan
        # indent konten RELATIF terhadap dasar induk
        # (posisi sesudah awalan leluhur dicerna)
        self._maju(indent)
        self._maju(indent_konten)
        item = self._tambah("item")
        item.data["rel_konten"] = indent + indent_konten
        return True
