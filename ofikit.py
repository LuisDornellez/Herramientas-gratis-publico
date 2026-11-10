import os, sys, datetime, shutil, json, io, re, zipfile, hashlib, secrets, string, csv, time, html, webbrowser
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from pypdf import PdfReader, PdfWriter
from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

APP, VER = "OfiKit", "1.3.3"
WEBS = (("saberaclick.com", "https://saberaclick.com"), ("www.luisdornellez.com", "https://www.luisdornellez.com"))
BG, SIDE, ACC = "#0f1724", "#16213a", "#3b82f6"
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def res(p):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), p)


def pick(title, types, multi=True):
    if multi:
        return list(filedialog.askopenfilenames(title=title, filetypes=types))
    return filedialog.askopenfilename(title=title, filetypes=types)


def outdir(files, name="OfiKit_salida"):
    d = os.path.join(os.path.dirname(files[0]), name)
    os.makedirs(d, exist_ok=True)
    return d


def num(s):
    s = str(s).strip().replace(" ", "")
    if not s:
        return 0.0
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    return float(s)


def open_img(f, flat=False):
    im = ImageOps.exif_transpose(Image.open(f))
    if not flat:
        return im
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.getchannel("A"))
        return bg
    return im.convert("RGB")


class Page(ctk.CTkFrame):
    title = ""
    nav = ""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=self.title, font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 12))
        self.body = ctk.CTkFrame(self, fg_color=SIDE, corner_radius=14)
        self.body.pack(fill="x")
        self.log = ctk.CTkTextbox(self, height=110, fg_color=SIDE)
        self.log.pack(fill="both", expand=True, pady=(12, 0))
        self.build()

    def say(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.update_idletasks()

    def build(self):
        pass

    def refresh(self):
        pass

    def btn(self, text, cmd):
        return ctk.CTkButton(self.body, text=text, command=lambda: self.run(cmd), fg_color=ACC, height=36)

    def run(self, cmd):
        try:
            cmd()
        except Exception as e:
            self.say(f"Error: {e}")


def data_dir():
    base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
    try:
        t = os.path.join(base, ".ofikit_test")
        with open(t, "w"):
            pass
        os.remove(t)
        return base
    except OSError:
        d = os.path.join(os.path.expanduser("~"), "OfiKit")
        os.makedirs(d, exist_ok=True)
        return d


RECIPES_FILE = os.path.join(data_dir(), "recetas.json")
IMG = (".jpg", ".jpeg", ".png", ".webp")


def load_recipes():
    try:
        with open(RECIPES_FILE, encoding="utf-8") as f:
            r = json.load(f)
        return r if isinstance(r, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        try:
            shutil.copy2(RECIPES_FILE, RECIPES_FILE + ".bak")
        except OSError:
            pass
        return {}


def save_recipes(r):
    with open(RECIPES_FILE, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)


def split_by(fs, exts):
    a = [f for f in fs if f.lower().endswith(exts)]
    return a, [f for f in fs if f not in a]


def img_conv(fs, d, ext=None, mw=1600, q=85):
    ims, rest = split_by(fs, IMG)
    outs = []
    for f in ims:
        e = ext or os.path.splitext(f)[1][1:].lower().replace("jpeg", "jpg")
        im = open_img(f, e == "jpg")
        if im.width > mw:
            im = im.resize((mw, int(im.height * mw / im.width)), Image.LANCZOS)
        out = unique(os.path.join(d, os.path.splitext(os.path.basename(f))[0] + "." + e))
        im.save(out, {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}[e], quality=q)
        outs.append(out)
    return outs + rest


def st_img2pdf(fs, d):
    ims, rest = split_by(fs, IMG)
    if not ims:
        return rest
    pil = [open_img(f, True) for f in sorted(ims)]
    out = os.path.join(d, "imagenes.pdf")
    pil[0].save(out, save_all=True, append_images=pil[1:])
    return [out] + rest


def st_merge(fs, d):
    pdfs, rest = split_by(fs, (".pdf",))
    if len(pdfs) < 2:
        return fs
    w = PdfWriter()
    for f in sorted(pdfs):
        w.append(f)
    out = os.path.join(d, "unido.pdf")
    w.write(out)
    return [out] + rest


def st_compress(fs, d):
    pdfs, rest = split_by(fs, (".pdf",))
    outs = []
    for f in pdfs:
        w = PdfWriter()
        for p in PdfReader(f).pages:
            w.add_page(p)
        for p in w.pages:
            p.compress_content_streams()
        w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
        out = os.path.join(d, os.path.basename(f))
        w.write(out)
        outs.append(out)
    return outs + rest


def st_rename(fs, d):
    today, outs = datetime.date.today().isoformat(), []
    for i, f in enumerate(sorted(fs), 1):
        out = os.path.join(d, f"{today}_{i:03d}" + os.path.splitext(f)[1])
        shutil.copy2(f, out)
        outs.append(out)
    return outs


STEPS = {
    "Reducir imágenes (1600 px)": lambda fs, d: img_conv(fs, d),
    "Convertir imágenes a JPG": lambda fs, d: img_conv(fs, d, "jpg", 100000),
    "Convertir imágenes a WEBP": lambda fs, d: img_conv(fs, d, "webp", 100000),
    "Imágenes a un solo PDF": st_img2pdf,
    "Unir PDFs": st_merge,
    "Comprimir PDFs": st_compress,
    "Renombrar con fecha y número": st_rename,
}
STEPS["Numerar páginas de PDF"] = lambda fs, d: st_numerar(fs, d)



def run_recipe(steps, files, base):
    os.makedirs(base, exist_ok=True)
    cur, tmp = list(files), []
    for i, s in enumerate(steps, 1):
        sd = os.path.join(base, f"_paso{i}")
        os.makedirs(sd, exist_ok=True)
        tmp.append(sd)
        cur = STEPS[s](cur, sd)
    outs = []
    for f in cur:
        out = os.path.join(base, os.path.basename(f))
        if os.path.abspath(f) != os.path.abspath(out):
            shutil.copy2(f, out)
        outs.append(out)
    for sd in tmp:
        shutil.rmtree(sd, ignore_errors=True)
    return outs


SEARCH_EXT = (".pdf", ".docx", ".xlsx", ".txt", ".csv", ".md", ".log")
CATS = {"Imágenes": IMG + (".gif", ".bmp", ".heic"), "PDF": (".pdf",), "Documentos": (".doc", ".docx", ".txt", ".odt", ".rtf"),
        "Hojas de cálculo": (".xls", ".xlsx", ".csv", ".ods"), "Presentaciones": (".ppt", ".pptx"),
        "Comprimidos": (".zip", ".rar", ".7z"), "Video y audio": (".mp4", ".mkv", ".avi", ".mp3", ".wav")}


def text_of(path):
    e = os.path.splitext(path)[1].lower()
    if e in (".txt", ".csv", ".md", ".log"):
        return read_text(path)
    if e == ".pdf":
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    if e in (".docx", ".xlsx"):
        with zipfile.ZipFile(path) as z:
            want = "word/document.xml" if e == ".docx" else "xl/sharedStrings.xml"
            x = z.read(want).decode("utf-8", "ignore") if want in z.namelist() else ""
        x = x.replace("</w:p>", "\n").replace("</si>", "\n").replace("</w:tc>", " ").replace("<w:tab/>", " ").replace("<w:br/>", "\n")
        return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", "", x)))
    return ""


def overlay(src, out, draw):
    r, w = PdfReader(src), PdfWriter()
    n = len(r.pages)
    for i, p in enumerate(r.pages, 1):
        if getattr(p, "rotation", 0):
            try:
                p.transfer_rotation_to_content()
            except Exception:
                pass
        W, H = float(p.mediabox.width), float(p.mediabox.height)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(W, H))
        c.translate(float(p.mediabox.left), float(p.mediabox.bottom))
        draw(c, W, H, i, n)
        c.save()
        buf.seek(0)
        p.merge_page(PdfReader(buf).pages[0])
        w.add_page(p)
    w.write(out)


def _pdf_step(draw):
    def st(fs, d):
        pdfs, rest = split_by(fs, (".pdf",))
        outs = []
        for f in pdfs:
            out = os.path.join(d, os.path.basename(f))
            overlay(f, out, draw)
            outs.append(out)
        return outs + rest
    return st


def _num(c, W, H, i, n):
    c.setFont("Helvetica", 10)
    c.drawCentredString(W / 2, 20, f"{i} / {n}")


st_numerar = _pdf_step(_num)


def make_wm(text):
    def draw(c, W, H, i, n):
        c.saveState()
        c.setFillColorRGB(.5, .5, .5)
        c.setFillAlpha(.25)
        c.translate(W / 2, H / 2)
        c.rotate(45)
        c.setFont("Helvetica-Bold", min(W, H) / 7)
        c.drawCentredString(0, 0, text)
        c.restoreState()
    return _pdf_step(draw)


def make_protect(pw, unlock=False):
    def st(fs, d):
        pdfs, rest = split_by(fs, (".pdf",))
        outs = []
        for f in pdfs:
            r, w = PdfReader(f), PdfWriter()
            if unlock and r.is_encrypted and not r.decrypt(pw):
                raise ValueError("Contraseña incorrecta: " + os.path.basename(f))
            for p in r.pages:
                w.add_page(p)
            if not unlock:
                w.encrypt(pw, algorithm="AES-256")
            out = os.path.join(d, ("abierto_" if unlock else "protegido_") + os.path.basename(f))
            w.write(out)
            outs.append(out)
        return outs + rest
    return st


def anonymize(t):
    for pat, rep in ((r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[EMAIL]"),
                     (r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)", "[TARJETA]"),
                     (r"\b\d{1,2}\.\d{3}\.\d{3}(?:-\d)?\b", "[DOCUMENTO]"),
                     (r"(?<!\d)(?:\+?\d[\s().-]?){8,14}\d(?!\d)", "[TELÉFONO]")):
        t = re.sub(pat, rep, t)
    return t


def unique(path):
    b, e = os.path.splitext(path)
    p, n = path, 1
    while os.path.exists(p):
        p, n = f"{b}_{n}{e}", n + 1
    return p


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def find_dups(d):
    by = {}
    for dp, dn, fn in os.walk(d):
        dn[:] = [x for x in dn if not x.startswith("OfiKit_")]
        for f in fn:
            p = os.path.join(dp, f)
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            if sz:
                by.setdefault(sz, []).append(p)
    out = []
    for ps in by.values():
        if len(ps) > 1:
            h = {}
            for p in ps:
                try:
                    h.setdefault(sha(p), []).append(p)
                except OSError:
                    pass
            out += [sorted(g) for g in h.values() if len(g) > 1]
    return out


class PdfPage(Page):
    title, nav = "Herramientas PDF", "PDF"

    def build(self):
        acts = [("Unir PDFs", self.merge), ("Dividir en páginas", self.split), ("Rotar 90°", self.rotate),
                ("Comprimir", self.compress), ("Imágenes a PDF", self.img2pdf),
                ("Marca de agua", self.marca), ("Numerar páginas", self.numerar),
                ("Proteger con contraseña", self.proteger), ("Quitar contraseña", self.abrir)]
        for i, (t, c) in enumerate(acts):
            self.btn(t, c).grid(row=i // 3, column=i % 3, padx=10, pady=10, sticky="ew")
        for c in range(3):
            self.body.grid_columnconfigure(c, weight=1)

    def pdfs(self, multi=True):
        return pick("Elige PDF", [("PDF", "*.pdf")], multi)

    def merge(self):
        fs = self.pdfs()
        if not fs:
            return
        w = PdfWriter()
        for f in fs:
            w.append(f)
        out = os.path.join(outdir(fs), "unido.pdf")
        w.write(out)
        self.say(f"Listo: {out}")

    def split(self):
        f = self.pdfs(False)
        if not f:
            return
        r = PdfReader(f)
        d = outdir([f])
        base = os.path.splitext(os.path.basename(f))[0]
        for i, p in enumerate(r.pages, 1):
            w = PdfWriter()
            w.add_page(p)
            w.write(os.path.join(d, f"{base}_p{i}.pdf"))
        self.say(f"{len(r.pages)} páginas guardadas en {d}")

    def rotate(self):
        f = self.pdfs(False)
        if not f:
            return
        w = PdfWriter()
        for p in PdfReader(f).pages:
            p.rotate(90)
            w.add_page(p)
        out = os.path.join(outdir([f]), "rotado_" + os.path.basename(f))
        w.write(out)
        self.say(f"Listo: {out}")

    def compress(self):
        f = self.pdfs(False)
        if not f:
            return
        w = PdfWriter()
        for p in PdfReader(f).pages:
            w.add_page(p)
        for p in w.pages:
            p.compress_content_streams()
        w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
        out = os.path.join(outdir([f]), "comprimido_" + os.path.basename(f))
        w.write(out)
        self.say(f"{os.path.getsize(f)//1024} KB -> {os.path.getsize(out)//1024} KB: {out}")

    def img2pdf(self):
        fs = pick("Elige imágenes", [("Imágenes", "*.jpg *.jpeg *.png *.webp")])
        if not fs:
            return
        ims = [open_img(f, True) for f in fs]
        out = os.path.join(outdir(fs), "imagenes.pdf")
        ims[0].save(out, save_all=True, append_images=ims[1:])
        self.say(f"Listo: {out}")


    def apply(self, fn, label):
        fs = self.pdfs()
        if not fs:
            return
        d = outdir(fs)
        self.say(f"{label}: {len(fn(fs, d))} archivo(s) en {d}")

    def numerar(self):
        self.apply(st_numerar, "Páginas numeradas")

    def marca(self):
        t = simpledialog.askstring(APP, "Texto de la marca de agua:", initialvalue="CONFIDENCIAL")
        if t:
            self.apply(make_wm(t), "Marca de agua")

    def proteger(self):
        pw = simpledialog.askstring(APP, "Contraseña para el PDF:", show="*")
        if pw:
            self.apply(make_protect(pw), "Protegidos")

    def abrir(self):
        pw = simpledialog.askstring(APP, "Contraseña actual del PDF:", show="*")
        if pw:
            self.apply(make_protect(pw, True), "Contraseña quitada")


class ImgPage(Page):
    title, nav = "Imágenes en lote", "Imágenes"

    def build(self):
        self.w = ctk.CTkEntry(self.body, width=100)
        self.w.insert(0, "1600")
        self.fmt = ctk.CTkOptionMenu(self.body, values=["JPG", "PNG", "WEBP"])
        self.q = ctk.CTkSlider(self.body, from_=40, to=100)
        self.q.set(85)
        for i, (t, wd) in enumerate([("Ancho máx. (px)", self.w), ("Formato", self.fmt), ("Calidad", self.q)]):
            ctk.CTkLabel(self.body, text=t).grid(row=i, column=0, padx=12, pady=8, sticky="w")
            wd.grid(row=i, column=1, padx=12, pady=8, sticky="w")
        self.btn("Elegir imágenes y convertir", self.go).grid(row=3, column=0, columnspan=2, padx=12, pady=12, sticky="ew")

    def go(self):
        fs = pick("Elige imágenes", [("Imágenes", "*.jpg *.jpeg *.png *.webp")])
        if not fs:
            return
        mw, ext, d = max(16, int(num(self.w.get())) or 1600), self.fmt.get().lower(), outdir(fs)
        kind = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}[ext]
        for f in fs:
            im = open_img(f, ext == "jpg")
            if im.width > mw:
                im = im.resize((mw, int(im.height * mw / im.width)), Image.LANCZOS)
            out = unique(os.path.join(d, os.path.splitext(os.path.basename(f))[0] + "." + ext))
            im.save(out, kind, quality=int(self.q.get()))
            self.say(f"OK: {out}")


class RenamePage(Page):
    title, nav = "Renombrador en lote", "Renombrar"

    def build(self):
        self.pre = ctk.CTkEntry(self.body, placeholder_text="Prefijo (ej. Factura)", width=260)
        self.num = ctk.CTkCheckBox(self.body, text="Numerar 001, 002…")
        self.num.select()
        self.date = ctk.CTkCheckBox(self.body, text="Agregar fecha de hoy")
        for w in (self.pre, self.num, self.date):
            w.pack(anchor="w", padx=14, pady=8)
        self.btn("Elegir archivos y renombrar", self.go).pack(anchor="w", padx=14, pady=12)

    def go(self):
        fs = pick("Elige archivos", [("Todos", "*.*")])
        if not fs or not messagebox.askyesno(APP, f"Se renombrarán {len(fs)} archivos. ¿Continuar?"):
            return
        pre = self.pre.get().strip() or "archivo"
        today = datetime.date.today().isoformat()
        for i, f in enumerate(sorted(fs), 1):
            parts = [pre] + ([today] if self.date.get() else []) + ([f"{i:03d}"] if self.num.get() else [])
            new = os.path.join(os.path.dirname(f), "_".join(parts) + os.path.splitext(f)[1])
            if os.path.exists(new):
                self.say(f"Omitido (ya existe): {os.path.basename(new)}")
                continue
            os.rename(f, new)
            self.say(f"{os.path.basename(f)} -> {os.path.basename(new)}")


class QuotePage(Page):
    title, nav = "Presupuestos y facturas", "Presupuestos"

    def build(self):
        self.e = {}
        for i, (k, d) in enumerate([("Empresa", ""), ("Cliente", ""), ("IVA %", "0"), ("Moneda", "$")]):
            ctk.CTkLabel(self.body, text=k).grid(row=i, column=0, padx=12, pady=6, sticky="w")
            en = ctk.CTkEntry(self.body, width=240)
            en.insert(0, d)
            en.grid(row=i, column=1, padx=12, pady=6, sticky="w")
            self.e[k] = en
        ctk.CTkLabel(self.body, text="Ítems, uno por línea: descripción;cantidad;precio").grid(row=4, column=0, columnspan=2, padx=12, sticky="w")
        self.items = ctk.CTkTextbox(self.body, height=110)
        self.items.grid(row=5, column=0, columnspan=2, padx=12, pady=6, sticky="ew")
        self.btn("Generar PDF", self.go).grid(row=6, column=0, columnspan=2, padx=12, pady=12, sticky="ew")

    def go(self):
        rows = []
        for ln in self.items.get("1.0", "end").splitlines():
            if not ln.strip():
                continue
            p = [x.strip() for x in ln.rsplit(";", 2)]
            try:
                if len(p) != 3:
                    raise ValueError
                rows.append((p[0], num(p[1]), num(p[2])))
            except ValueError:
                self.say(f"Línea ignorada (usa descripción;cantidad;precio): {ln}")
        if not rows:
            self.say("Agrega ítems con el formato: descripción;cantidad;precio")
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="presupuesto.pdf")
        if not out:
            return
        iva, m = num(self.e["IVA %"].get()), self.e["Moneda"].get()
        c = canvas.Canvas(out, pagesize=A4)
        W, H = A4
        c.setFillColorRGB(.06, .09, .14)
        c.rect(0, H - 90, W, 90, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(40, H - 55, self.e["Empresa"].get() or "Presupuesto")
        c.setFont("Helvetica", 10)
        c.drawRightString(W - 40, H - 55, datetime.date.today().isoformat())
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 12)
        c.drawString(40, H - 120, "Cliente: " + self.e["Cliente"].get())
        y = H - 160
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, "Descripción")
        c.drawRightString(380, y, "Cant.")
        c.drawRightString(460, y, "Precio")
        c.drawRightString(W - 40, y, "Total")
        c.line(40, y - 5, W - 40, y - 5)
        c.setFont("Helvetica", 11)
        sub = 0
        for d, q, p in rows:
            if y < 140:
                c.showPage()
                y = H - 60
                c.setFont("Helvetica", 11)
            y -= 22
            t = q * p
            sub += t
            c.drawString(40, y, d[:50])
            c.drawRightString(380, y, f"{q:g}")
            c.drawRightString(460, y, f"{m}{p:,.2f}")
            c.drawRightString(W - 40, y, f"{m}{t:,.2f}")
        y -= 30
        c.line(300, y + 18, W - 40, y + 18)
        for lab, val in (("Subtotal", sub), (f"IVA {iva:g}%", sub * iva / 100), ("TOTAL", sub * (1 + iva / 100))):
            c.setFont("Helvetica-Bold" if lab == "TOTAL" else "Helvetica", 12)
            c.drawString(300, y, lab)
            c.drawRightString(W - 40, y, f"{m}{val:,.2f}")
            y -= 20
        c.save()
        self.say(f"Listo: {out}")


class RecipesPage(Page):
    title, nav = "Recetas de un clic", "Recetas"

    def build(self):
        self.steps = []
        self.name = ctk.CTkEntry(self.body, placeholder_text="Nombre de la receta", width=240)
        self.step = ctk.CTkOptionMenu(self.body, values=list(STEPS), width=300)
        self.lbl = ctk.CTkLabel(self.body, text="Pasos: (ninguno)", wraplength=560, justify="left")
        self.sel = ctk.CTkOptionMenu(self.body, values=["(sin recetas)"], width=240)
        self.name.grid(row=0, column=0, padx=12, pady=8, sticky="w")
        self.step.grid(row=0, column=1, padx=12, pady=8, sticky="w")
        self.btn("Agregar paso", self.add).grid(row=1, column=0, padx=12, pady=6, sticky="ew")
        self.btn("Guardar receta", self.save).grid(row=1, column=1, padx=12, pady=6, sticky="ew")
        self.lbl.grid(row=2, column=0, columnspan=2, padx=12, pady=6, sticky="w")
        self.sel.grid(row=3, column=0, padx=12, pady=8, sticky="w")
        self.btn("Ejecutar sobre archivos…", self.go).grid(row=3, column=1, padx=12, pady=8, sticky="ew")
        self.btn("Limpiar pasos", self.clear).grid(row=4, column=0, padx=12, pady=(0, 12), sticky="ew")
        self.btn("Borrar receta elegida", self.delete).grid(row=4, column=1, padx=12, pady=(0, 12), sticky="ew")
        self.body.grid_columnconfigure((0, 1), weight=1)
        self.refresh()

    def refresh(self):
        names = list(load_recipes()) or ["(sin recetas)"]
        self.sel.configure(values=names)
        if self.sel.get() not in names:
            self.sel.set(names[0])

    def show_steps(self):
        self.lbl.configure(text="Pasos: " + (" → ".join(self.steps) or "(ninguno)"))

    def add(self):
        self.steps.append(self.step.get())
        self.show_steps()

    def clear(self):
        self.steps = []
        self.show_steps()

    def save(self):
        n = self.name.get().strip()
        if not n or not self.steps:
            self.say("Escribe un nombre y agrega al menos un paso.")
            return
        r = load_recipes()
        r[n] = list(self.steps)
        save_recipes(r)
        self.refresh()
        self.sel.set(n)
        self.say(f"Receta guardada: {n}")

    def delete(self):
        r = load_recipes()
        if r.pop(self.sel.get(), None) is not None:
            save_recipes(r)
            self.say("Receta borrada.")
        self.refresh()

    def go(self):
        steps = load_recipes().get(self.sel.get())
        if not steps:
            self.say("Primero guarda una receta.")
            return
        fs = pick("Elige archivos", [("Todos", "*.*")])
        if not fs:
            return
        outs = run_recipe(steps, fs, os.path.join(os.path.dirname(fs[0]), "OfiKit_resultado"))
        self.say(f"Listo: {len(outs)} archivo(s) en {os.path.dirname(outs[0])}" if outs else "Sin resultados.")


class WatchPage(Page):
    title, nav = "Carpeta vigilada", "Carpeta vigilada"

    def build(self):
        self.folder, self.on, self.seen, self.sizes, self.job = "", False, set(), {}, None
        self.fl = ctk.CTkLabel(self.body, text="Carpeta: (ninguna)", wraplength=560, justify="left")
        self.sel = ctk.CTkOptionMenu(self.body, values=["(sin recetas)"], width=240)
        self.fl.grid(row=0, column=0, columnspan=2, padx=12, pady=8, sticky="w")
        self.btn("Elegir carpeta", self.choose).grid(row=1, column=0, padx=12, pady=8, sticky="ew")
        self.sel.grid(row=1, column=1, padx=12, pady=8, sticky="w")
        self.tog = self.btn("Iniciar vigilancia", self.toggle)
        self.tog.grid(row=2, column=0, columnspan=2, padx=12, pady=12, sticky="ew")
        self.body.grid_columnconfigure((0, 1), weight=1)
        self.refresh()

    def refresh(self):
        names = list(load_recipes()) or ["(sin recetas)"]
        self.sel.configure(values=names)
        if self.sel.get() not in names:
            self.sel.set(names[0])

    def choose(self):
        d = filedialog.askdirectory()
        if d:
            self.folder = d
            self.fl.configure(text="Carpeta: " + d)

    def files(self):
        bad = ("~", ".")
        return [os.path.join(self.folder, f) for f in os.listdir(self.folder)
                if os.path.isfile(os.path.join(self.folder, f)) and not f.startswith(bad)
                and not f.lower().endswith((".tmp", ".crdownload", ".part"))]

    def toggle(self):
        if self.on:
            self.on = False
            if self.job:
                self.after_cancel(self.job)
                self.job = None
            self.tog.configure(text="Iniciar vigilancia")
            self.say("Vigilancia detenida.")
            return
        if not self.folder or not load_recipes().get(self.sel.get()):
            self.say("Elige una carpeta y una receta guardada.")
            return
        self.seen, self.sizes, self.on = set(self.files()), {}, True
        self.tog.configure(text="Detener vigilancia")
        self.say(f"Vigilando {self.folder} con «{self.sel.get()}». Los archivos nuevos se procesan solos.")
        self.tick()

    def tick(self):
        if not self.on:
            return
        ready = []
        if not os.path.isdir(self.folder):
            self.on = False
            self.tog.configure(text="Iniciar vigilancia")
            self.say("La carpeta ya no existe. Vigilancia detenida.")
            return
        try:
            for f in self.files():
                if f in self.seen:
                    continue
                s = os.path.getsize(f)
                if self.sizes.get(f) == s:
                    ready.append(f)
                else:
                    self.sizes[f] = s
            if ready:
                base = os.path.join(self.folder, "OfiKit_procesados", datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
                run_recipe(load_recipes()[self.sel.get()], ready, base)
                self.say(f"Procesados {len(ready)} archivo(s) -> {base}")
        except Exception as e:
            self.say(f"Error: {e}")
        self.seen.update(ready)
        self.job = self.after(3000, self.tick)


class SearchPage(Page):
    title, nav = "Buscar dentro de archivos", "Buscar"

    def build(self):
        self.q = ctk.CTkEntry(self.body, placeholder_text="Texto a buscar", width=360)
        self.q.pack(anchor="w", padx=14, pady=(14, 8))
        self.btn("Elegir carpeta y buscar", self.go).pack(anchor="w", padx=14, pady=(0, 6))
        ctk.CTkLabel(self.body, text="Busca dentro de PDF, Word, Excel, TXT y CSV (PDF escaneados no).").pack(anchor="w", padx=14, pady=(0, 12))

    def go(self):
        q, d = self.q.get().strip().lower(), filedialog.askdirectory()
        if not q or not d:
            self.say("Escribe qué buscar y elige una carpeta.")
            return
        n = hits = 0
        for dp, _, fn in os.walk(d):
            for f in fn:
                if not f.lower().endswith(SEARCH_EXT):
                    continue
                n += 1
                self.update_idletasks()
                try:
                    t = text_of(os.path.join(dp, f))
                except Exception:
                    continue
                i = t.lower().find(q)
                if i >= 0:
                    hits += 1
                    self.say(os.path.join(dp, f) + "\n   …" + " ".join(t[max(0, i - 40):i + 60].split()) + "…")
        self.say(f"Listo: {hits} archivo(s) con coincidencias, {n} revisados.")


class OrderPage(Page):
    title, nav = "Orden de carpetas", "Orden"

    def build(self):
        self.btn("Organizar por tipo de archivo", self.organize).grid(row=0, column=0, padx=12, pady=12, sticky="ew")
        self.btn("Buscar archivos duplicados", self.dups).grid(row=0, column=1, padx=12, pady=12, sticky="ew")
        self.body.grid_columnconfigure((0, 1), weight=1)

    def organize(self):
        d = filedialog.askdirectory()
        if not d:
            return
        plan = []
        for f in os.listdir(d):
            p = os.path.join(d, f)
            if os.path.isfile(p):
                for cat, ex in CATS.items():
                    if f.lower().endswith(ex):
                        plan.append((p, cat))
                        break
        if not plan or not messagebox.askyesno(APP, f"Se moverán {len(plan)} archivos a subcarpetas por tipo. ¿Continuar?"):
            return
        for p, cat in plan:
            os.makedirs(os.path.join(d, cat), exist_ok=True)
            shutil.move(p, unique(os.path.join(d, cat, os.path.basename(p))))
        self.say(f"Listo: {len(plan)} archivos organizados.")

    def dups(self):
        d = filedialog.askdirectory()
        if not d:
            return
        self.say("Buscando duplicados…")
        gs = find_dups(d)
        extra = sum(len(g) - 1 for g in gs)
        if not extra:
            self.say("No hay duplicados.")
            return
        if not messagebox.askyesno(APP, f"Hay {extra} copias repetidas. Se moverán (no se borran) a OfiKit_duplicados. ¿Continuar?"):
            return
        dd = os.path.join(d, "OfiKit_duplicados")
        os.makedirs(dd, exist_ok=True)
        for g in gs:
            for p in g[1:]:
                shutil.move(p, unique(os.path.join(dd, os.path.basename(p))))
        self.say(f"{extra} copias movidas a {dd}")


class UtilPage(Page):
    title, nav = "Utilidades", "Utilidades"

    def build(self):
        b = self.body
        ctk.CTkLabel(b, text="Contraseña segura, largo:").grid(row=0, column=0, padx=12, pady=8, sticky="w")
        self.n = ctk.CTkEntry(b, width=60)
        self.n.insert(0, "16")
        self.n.grid(row=0, column=1, padx=12, sticky="w")
        self.pw = ctk.CTkEntry(b, width=300)
        self.pw.grid(row=1, column=0, columnspan=2, padx=12, pady=4, sticky="w")
        self.btn("Generar y copiar", self.genpw).grid(row=1, column=2, padx=12, sticky="ew")
        self.qr = ctk.CTkEntry(b, width=300, placeholder_text="Texto o enlace para el QR")
        self.qr.grid(row=2, column=0, columnspan=2, padx=12, pady=8, sticky="w")
        self.btn("Crear QR (PNG)", self.mkqr).grid(row=2, column=2, padx=12, sticky="ew")
        ctk.CTkLabel(b, text="Pega un texto para ocultar emails, teléfonos, tarjetas y documentos:").grid(row=3, column=0, columnspan=3, padx=12, sticky="w")
        self.tx = ctk.CTkTextbox(b, height=110)
        self.tx.grid(row=4, column=0, columnspan=3, padx=12, pady=6, sticky="ew")
        self.btn("Ocultar datos sensibles y copiar", self.anon).grid(row=5, column=0, columnspan=3, padx=12, pady=12, sticky="ew")
        b.grid_columnconfigure(2, weight=1)

    def copy(self, t):
        self.clipboard_clear()
        self.clipboard_append(t)

    def genpw(self):
        n = max(8, min(64, int(num(self.n.get()) or 16)))
        al = string.ascii_letters + string.digits + "!@#$%&*?-_"
        p = "".join(secrets.choice(al) for _ in range(n))
        self.pw.delete(0, "end")
        self.pw.insert(0, p)
        self.copy(p)
        self.say("Contraseña generada y copiada al portapapeles.")

    def mkqr(self):
        import qrcode
        t = self.qr.get().strip()
        if not t:
            self.say("Escribe un texto o enlace para el QR.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")], initialfile="qr.png")
        if out:
            qrcode.make(t).save(out)
            self.say(f"QR guardado: {out}")

    def anon(self):
        t = anonymize(self.tx.get("1.0", "end").strip())
        self.tx.delete("1.0", "end")
        self.tx.insert("1.0", t)
        self.copy(t)
        self.say("Datos sensibles ocultados y texto copiado.")


HORAS_FILE = os.path.join(os.path.dirname(RECIPES_FILE), "horas.json")
CALC_OPS = ["Sumar IVA", "Quitar IVA", "Descuento", "Precio con margen", "Precio con recargo", "% del monto"]


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1")


def read_csv(path):
    txt = read_text(path)
    try:
        dia = csv.Sniffer().sniff(txt[:4096], delimiters=",;\t|")
    except Exception:
        dia = csv.excel
    return list(csv.reader(io.StringIO(txt, newline=""), dia)), dia


def write_csv(path, rows, dia=csv.excel):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f, dia).writerows(rows)


def merge_csv(files):
    allr, dia, head = [], csv.excel, None
    for f in files:
        rows, d = read_csv(f)
        if not rows:
            continue
        if head is None:
            head, dia = rows[0], d
            allr += rows
        else:
            allr += rows[1:] if rows[0] == head else rows
    return allr, dia


def dedupe(rows):
    if not rows:
        return rows, 0
    seen, out = set(), [rows[0]]
    for r in rows[1:]:
        k = tuple(r)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out, len(rows) - len(out)


def conv(v):
    if re.fullmatch(r"-?([1-9]\d{0,14}|0)", v):
        return int(v)
    if re.fullmatch(r"-?(0|[1-9]\d{0,14})\.\d+", v):
        return float(v)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", v)


def csv_to_xlsx(src, out):
    import openpyxl
    rows, dia = read_csv(src)
    dec = getattr(dia, "delimiter", ",") != ","
    wb = openpyxl.Workbook()
    ws = wb.active
    for i, r in enumerate(rows, 1):
        for j, x in enumerate(r, 1):
            if dec and re.fullmatch(r"-?(0|[1-9]\d{0,14}),\d+", x):
                x = x.replace(",", ".")
            c = ws.cell(row=i, column=j, value=conv(x))
            if isinstance(c.value, str) and c.value.startswith("="):
                c.data_type = "s"
    wb.save(out)


def xlsx_to_csv(src, out):
    import openpyxl
    wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
    rows = [["" if c is None else c for c in r] for r in wb.active.iter_rows(values_only=True)]
    wb.close()
    write_csv(out, rows)


def calc(op, a, p):
    if op == "Sumar IVA":
        i = a * p / 100
        return f"IVA: {i:,.2f}  |  Total: {a + i:,.2f}"
    if op == "Quitar IVA":
        b = a / (1 + p / 100)
        return f"Base: {b:,.2f}  |  IVA: {a - b:,.2f}"
    if op == "Descuento":
        return f"Descuento: {a * p / 100:,.2f}  |  Final: {a * (1 - p / 100):,.2f}"
    if op == "Precio con margen":
        if p >= 100:
            raise ValueError("El margen debe ser menor a 100")
        v = a / (1 - p / 100)
        return f"Precio de venta: {v:,.2f}  |  Ganancia: {v - a:,.2f}"
    if op == "Precio con recargo":
        v = a * (1 + p / 100)
        return f"Precio de venta: {v:,.2f}  |  Ganancia: {v - a:,.2f}"
    if op == "% del monto":
        return f"{p:g}% de {a:,.2f} = {a * p / 100:,.2f}"
    raise ValueError(op)


def diff_text(a, b):
    import difflib
    la = [x.strip() for x in a.splitlines() if x.strip()]
    lb = [x.strip() for x in b.splitlines() if x.strip()]
    lines = list(difflib.unified_diff(la, lb, "A", "B", lineterm="", n=0))
    return [l for l in lines[2:] if not l.startswith("@@")]


def hms(s):
    s = int(s)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def load_hours():
    try:
        with open(HORAS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_hours(rows):
    with open(HORAS_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)


def hours_summary(rows, rate=0.0):
    tot = {}
    for r in rows:
        tot[r["cliente"]] = tot.get(r["cliente"], 0) + r["segundos"]
    return [(c, s, s / 3600 * rate) for c, s in sorted(tot.items())]


class DataPage(Page):
    title, nav = "Datos: CSV y Excel", "Datos"

    def build(self):
        acts = [("Unir varios CSV", self.merge), ("Quitar filas duplicadas (CSV)", self.dedupe),
                ("CSV a Excel", self.c2x), ("Excel a CSV", self.x2c)]
        for i, (t, c) in enumerate(acts):
            self.btn(t, c).grid(row=i // 2, column=i % 2, padx=10, pady=10, sticky="ew")
        self.body.grid_columnconfigure((0, 1), weight=1)

    def merge(self):
        fs = pick("Elige los CSV", [("CSV", "*.csv")])
        if not fs:
            return
        rows, dia = merge_csv(fs)
        out = os.path.join(outdir(fs), "unido.csv")
        write_csv(out, rows, dia)
        self.say(f"Listo: {len(rows)} filas en {out}")

    def dedupe(self):
        f = pick("Elige un CSV", [("CSV", "*.csv")], False)
        if not f:
            return
        rows, dia = read_csv(f)
        rows, n = dedupe(rows)
        out = os.path.join(outdir([f]), "sin_duplicados_" + os.path.basename(f))
        write_csv(out, rows, dia)
        self.say(f"Se quitaron {n} filas repetidas: {out}")

    def c2x(self):
        fs = pick("Elige CSV", [("CSV", "*.csv")])
        if not fs:
            return
        d = outdir(fs)
        for f in fs:
            out = os.path.join(d, os.path.splitext(os.path.basename(f))[0] + ".xlsx")
            csv_to_xlsx(f, out)
            self.say(f"Listo: {out}")

    def x2c(self):
        fs = pick("Elige Excel", [("Excel", "*.xlsx")])
        if not fs:
            return
        d = outdir(fs)
        for f in fs:
            out = os.path.join(d, os.path.splitext(os.path.basename(f))[0] + ".csv")
            xlsx_to_csv(f, out)
            self.say(f"Listo (primera hoja): {out}")


class CalcPage(Page):
    title, nav = "Calculadoras", "Calculadoras"

    def build(self):
        self.a = ctk.CTkEntry(self.body, width=180, placeholder_text="Monto")
        self.p = ctk.CTkEntry(self.body, width=180, placeholder_text="Porcentaje %")
        self.a.grid(row=0, column=0, padx=12, pady=12, sticky="w")
        self.p.grid(row=0, column=1, padx=12, pady=12, sticky="w")
        for i, op in enumerate(CALC_OPS):
            self.btn(op, lambda o=op: self.go(o)).grid(row=1 + i // 3, column=i % 3, padx=10, pady=8, sticky="ew")
        self.body.grid_columnconfigure((0, 1, 2), weight=1)

    def go(self, op):
        self.say(f"[{op}] " + calc(op, num(self.a.get()), num(self.p.get())))


class ClipPage(Page):
    title, nav = "Historial del portapapeles", "Portapapeles"

    def build(self):
        self.hist, self.last = [], ""
        ctk.CTkLabel(self.body, text="Guarda lo que copias (solo en memoria, no se escribe en disco). Pulsa un elemento para copiarlo otra vez.",
                     wraplength=560, justify="left").pack(anchor="w", padx=14, pady=(12, 4))
        self.box = ctk.CTkScrollableFrame(self.body, height=210, fg_color=BG)
        self.box.pack(fill="x", padx=14, pady=6)
        self.btn("Limpiar historial", self.clear).pack(anchor="w", padx=14, pady=(0, 12))
        self.poll()

    def poll(self):
        try:
            t = self.clipboard_get()
        except Exception:
            t = ""
        if isinstance(t, str) and t.strip() and t != self.last:
            self.last = t
            if t in self.hist:
                self.hist.remove(t)
            self.hist.insert(0, t)
            del self.hist[50:]
            self.render()
        self.after(1000, self.poll)

    def render(self):
        for w in self.box.winfo_children():
            w.destroy()
        for t in self.hist:
            ctk.CTkButton(self.box, text=" ".join(t.split())[:80], anchor="w", fg_color=SIDE, hover_color=ACC,
                          command=lambda x=t: self.recopy(x)).pack(fill="x", pady=2)

    def recopy(self, t):
        self.last = t
        self.clipboard_clear()
        self.clipboard_append(t)

    def clear(self):
        self.hist = []
        self.render()


class ComparePage(Page):
    title, nav = "Comparar documentos", "Comparar"

    def build(self):
        self.fa = self.fb = ""
        self.la = ctk.CTkLabel(self.body, text="A: (sin elegir)")
        self.lb = ctk.CTkLabel(self.body, text="B: (sin elegir)")
        self.btn("Elegir documento A", lambda: self.choose("a")).grid(row=0, column=0, padx=12, pady=8, sticky="ew")
        self.la.grid(row=0, column=1, padx=12, sticky="w")
        self.btn("Elegir documento B", lambda: self.choose("b")).grid(row=1, column=0, padx=12, pady=8, sticky="ew")
        self.lb.grid(row=1, column=1, padx=12, sticky="w")
        self.btn("Comparar", self.go).grid(row=2, column=0, columnspan=2, padx=12, pady=12, sticky="ew")

    def choose(self, w):
        f = pick("Elige documento", [("Documentos", "*.pdf *.docx *.xlsx *.txt *.csv *.md")], False)
        if f:
            setattr(self, "f" + w, f)
            getattr(self, "l" + w).configure(text=f"{w.upper()}: {os.path.basename(f)}")

    def go(self):
        if not (self.fa and self.fb):
            self.say("Elige los dos documentos.")
            return
        res = diff_text(text_of(self.fa), text_of(self.fb))
        if not res:
            self.say("Los dos documentos tienen el mismo texto.")
            return
        rep = ["Solo en A: " + l[1:] if l[0] == "-" else "Solo en B: " + l[1:] for l in res]
        out = os.path.join(outdir([self.fa]), "comparacion.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(rep))
        for l in rep[:200]:
            self.say(l)
        self.say(f"--- {len(rep)} diferencias. Informe completo: {out}")


class HoursPage(Page):
    title, nav = "Control de horas", "Horas"

    def build(self):
        self.t0, self.job, self.cur = None, None, ("", "")
        self.cl = ctk.CTkEntry(self.body, width=240, placeholder_text="Cliente / proyecto")
        self.note = ctk.CTkEntry(self.body, width=240, placeholder_text="Nota (opcional)")
        self.rate = ctk.CTkEntry(self.body, width=140, placeholder_text="Tarifa por hora")
        self.clock = ctk.CTkLabel(self.body, text="00:00:00", font=("Segoe UI", 30, "bold"))
        self.tog = self.btn("Iniciar", self.toggle)
        self.cl.grid(row=0, column=0, padx=12, pady=8, sticky="w")
        self.note.grid(row=0, column=1, padx=12, pady=8, sticky="w")
        self.rate.grid(row=1, column=0, padx=12, pady=4, sticky="w")
        self.clock.grid(row=1, column=1, padx=12, pady=4)
        self.tog.grid(row=2, column=0, padx=12, pady=10, sticky="ew")
        self.btn("Resumen por cliente", self.summary).grid(row=2, column=1, padx=12, pady=10, sticky="ew")
        self.btn("Exportar a CSV", self.export).grid(row=3, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")

    def toggle(self):
        if self.t0 is None:
            if not self.cl.get().strip():
                self.say("Escribe el cliente o proyecto.")
                return
            self.t0 = time.time()
            self.cur = (self.cl.get().strip(), self.note.get().strip())
            self.tog.configure(text="Detener")
            self.tick()
            return
        s = int(time.time() - self.t0)
        self.t0 = None
        if self.job:
            self.after_cancel(self.job)
        self.tog.configure(text="Iniciar")
        self.clock.configure(text="00:00:00")
        rows = load_hours()
        rows.append({"cliente": self.cur[0], "nota": self.cur[1],
                     "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "segundos": s})
        save_hours(rows)
        self.say(f"Guardado: {self.cur[0]} — {hms(s)}")

    def tick(self):
        if self.t0 is not None:
            self.clock.configure(text=hms(time.time() - self.t0))
            self.job = self.after(1000, self.tick)

    def summary(self):
        rate = num(self.rate.get())
        rows = hours_summary(load_hours(), rate)
        if not rows:
            self.say("Todavía no hay horas registradas.")
        for c, s, m in rows:
            self.say(f"{c}: {hms(s)} ({s / 3600:.2f} h)" + (f"  ->  {m:,.2f}" if rate else ""))

    def export(self):
        rows = load_hours()
        if not rows:
            self.say("Todavía no hay horas registradas.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="horas.csv")
        if out:
            write_csv(out, [["Fecha", "Cliente", "Nota", "Horas"]] +
                      [[r["fecha"], r["cliente"], r.get("nota", ""), f"{r['segundos'] / 3600:.2f}"] for r in rows])
            self.say(f"Exportado: {out}")


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        self.title(f"{APP} {VER}")
        self.geometry("1040x700")
        self.minsize(900, 620)
        self.after(300, self.set_icon)
        left = ctk.CTkFrame(self, fg_color=SIDE, corner_radius=0)
        left.pack(side="left", fill="y")
        foot = ctk.CTkFrame(left, fg_color=SIDE, corner_radius=0)
        foot.pack(side="bottom", fill="x", pady=(0, 12))
        ctk.CTkLabel(foot, text="Creado por:", text_color="#8aa0c0").pack(pady=(6, 0))
        for txt, url in WEBS:
            link = ctk.CTkLabel(foot, text=txt, text_color=ACC,
                                font=ctk.CTkFont(family="Segoe UI", size=13, underline=True))
            link.pack(pady=1)
            link.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
            try:
                link.configure(cursor="hand2")
            except Exception:
                pass
        side = ctk.CTkScrollableFrame(left, width=180, fg_color=SIDE, corner_radius=0)
        side.pack(side="top", fill="both", expand=True)
        ctk.CTkLabel(side, text=APP, font=("Segoe UI", 26, "bold"), text_color=ACC).pack(pady=(24, 2))
        ctk.CTkLabel(side, text="Tu oficina portátil", text_color="#8aa0c0").pack(pady=(0, 20))
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.pack(side="left", fill="both", expand=True, padx=24, pady=20)
        self.pages = {}
        for cls in (PdfPage, ImgPage, RenamePage, QuotePage, RecipesPage, WatchPage, SearchPage, OrderPage, UtilPage, DataPage, CalcPage, ClipPage, ComparePage, HoursPage):
            self.pages[cls] = cls(self.main)
            ctk.CTkButton(side, text=cls.nav, anchor="w", fg_color="transparent", hover_color=BG, height=34,
                          command=lambda c=cls: self.show(c)).pack(fill="x", padx=10, pady=2)
        self.show(PdfPage)

    def set_icon(self):
        try:
            self.iconbitmap(res("icon.ico"))
        except Exception:
            pass

    def show(self, cls):
        for p in self.pages.values():
            p.pack_forget()
        self.pages[cls].refresh()
        self.pages[cls].pack(fill="both", expand=True)


if __name__ == "__main__":
    App().mainloop()
