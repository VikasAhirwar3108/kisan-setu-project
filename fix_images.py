import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent
DB = BASE / "greenbasket.db"
OUT = BASE / "static" / "images" / "products"
URL = "/static/images/products/"
EXTS = (".jpg", ".jpeg", ".png", ".webp", ".avif")
OUT.mkdir(parents=True, exist_ok=True)

# file ka naam -> Wikipedia page. Naya product add karo to yahan bhi add kar sakti ho.
NEW_ITEMS = {
    "milk": "Milk",
    "eggs": "Egg as food",
}

HEADERS = {"User-Agent": "GreenBasketStudentProject/1.0 (learning project)"}


def get(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            return urllib.request.urlopen(req, timeout=30).read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(6)
                continue
            raise


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ---- 1) Nayi images download karo ----
for fname, page in NEW_ITEMS.items():
    if any(OUT.glob(fname + ".*")):
        print("skip (already hai):", fname)
        continue
    try:
        api = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(page.replace(" ", "_"))
        data = json.loads(get(api))
        thumb = data["thumbnail"]["source"]
        big = re.sub(r"/\d+px-", "/700px-", thumb)
        try:
            img = get(big)
        except Exception:
            img = get(thumb)
        ext = Path(urllib.parse.urlparse(thumb).path).suffix.lower()
        if ext not in EXTS:
            ext = ".jpg"
        (OUT / (fname + ext)).write_bytes(img)
        print("ok: downloaded", fname)
    except Exception as e:
        print("FAIL:", fname, "-", e)
    time.sleep(1)

# ---- 2) Database ke saare products ko image lagao ----
FILES = {}
for p in OUT.iterdir():
    if p.suffix.lower() in EXTS:
        FILES[slug(p.stem)] = p.name


def find_image(name):
    s = "-" + slug(name) + "-"
    best = None
    for stem, fn in FILES.items():
        forms = {stem, stem.rstrip("s"), stem + "s"}
        if any(("-" + f + "-") in s for f in forms if f):
            if best is None or len(stem) > len(best[0]):
                best = (stem, fn)
    return URL + best[1] if best else None


con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
rows = con.execute("SELECT id, name FROM products").fetchall()
done, missing = 0, []
for r in rows:
    img = find_image(r["name"])
    if img:
        con.execute("UPDATE products SET image=? WHERE id=?", (img, r["id"]))
        done += 1
        print("image laga di:", r["name"], "->", img)
    else:
        missing.append(r["name"])
con.commit()
con.close()

print(f"\n{done} products ki image update ho gayi.")
if missing:
    print("In products ki image file nahi mili:", missing)
    print("static\\images\\products me inke naam se file rakho (jaise 'butter.jpg') aur script dobara chalao.")