import re
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
DB = BASE / "greenbasket.db"

# Yahan apni images rakho: static/images/products/
IMG_DIR = BASE / "static" / "images" / "products"
IMG_URL = "/static/images/products/"

# Jis product ki image nahi milegi uske liye sirf yeh generic default use hoga
DEFAULT_IMAGES = {
    "Fruits": "https://images.unsplash.com/photo-1619566636858-adf3ef46400b?auto=format&fit=crop&w=700&q=85",
    "default": "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=700&q=85",
}

# (name, category, price, description, [extra filename names])
PRODUCTS = [
    ("Tomato", "Vegetables", 32, "Fresh red tomatoes", ["tamatar"]),
    ("Potato", "Vegetables", 28, "Fresh potatoes", ["aloo"]),
    ("Onion", "Vegetables", 30, "Daily-use onions", ["pyaz", "pyaaz"]),
    ("Carrot", "Vegetables", 35, "Sweet crunchy carrots", ["gajar"]),
    ("Cauliflower", "Vegetables", 36, "Fresh cauliflower", ["gobi", "phulgobi"]),
    ("Cabbage", "Vegetables", 28, "Fresh green cabbage", ["patta-gobi", "band-gobi"]),
    ("Spinach", "Leafy Greens", 25, "Fresh leafy spinach", ["palak"]),
    ("Coriander Leaves", "Leafy Greens", 15, "Fresh coriander bunch", ["coriander", "dhania"]),
    ("Fenugreek Leaves", "Leafy Greens", 18, "Fresh methi leaves", ["fenugreek", "methi"]),
    ("Lettuce", "Leafy Greens", 45, "Crisp lettuce", ["salad-patta"]),
    ("Brinjal / Eggplant", "Vegetables", 38, "Fresh purple brinjal", ["brinjal", "eggplant", "baingan"]),
    ("Okra / Bhindi", "Vegetables", 42, "Tender green okra", ["okra", "bhindi"]),
    ("Cucumber", "Vegetables", 25, "Cool crisp cucumber", ["kheera"]),
    ("Green Peas", "Vegetables", 60, "Fresh green peas", ["peas", "matar"]),
    ("Green Chilli", "Vegetables", 45, "Fresh green chillies", ["chilli", "mirch", "green-chili"]),
    ("Capsicum", "Vegetables", 55, "Fresh capsicum", ["shimla-mirch", "bell-pepper"]),
    ("Bottle Gourd / Lauki", "Vegetables", 30, "Fresh bottle gourd", ["bottle-gourd", "lauki", "ghiya"]),
    ("Bitter Gourd / Karela", "Vegetables", 38, "Fresh bitter gourd", ["bitter-gourd", "karela"]),
    ("Radish / Mooli", "Vegetables", 28, "Fresh radish", ["radish", "mooli"]),
    ("Beetroot", "Vegetables", 40, "Fresh beetroot", ["beet", "chukandar"]),
    ("Pumpkin", "Vegetables", 32, "Fresh pumpkin", ["kaddu"]),
    ("Sweet Corn", "Vegetables", 35, "Fresh sweet corn", ["corn", "makka", "bhutta"]),
    ("Garlic", "Vegetables", 100, "Fresh garlic", ["lehsun", "lahsun"]),
    ("Ginger", "Vegetables", 90, "Fresh ginger", ["adrak"]),
    ("Red Apple", "Fruits", 150, "Crisp apples", ["apple", "seb"]),
    ("Banana", "Fruits", 45, "Sweet bananas", ["kela"]),
    ("Mango", "Fruits", 90, "Seasonal mangoes", ["aam"]),
    ("Orange", "Fruits", 70, "Juicy oranges", ["santra"]),
    ("Grapes", "Fruits", 85, "Fresh grapes", ["grape", "angoor"]),
    ("Pomegranate", "Fruits", 120, "Juicy pomegranate", ["anar"]),
    ("Papaya", "Fruits", 45, "Ripe papaya", ["papita"]),
    ("Watermelon", "Fruits", 30, "Fresh watermelon", ["tarbooz"]),
    ("Muskmelon", "Fruits", 45, "Sweet muskmelon", ["kharbuja", "melon"]),
    ("Pineapple", "Fruits", 65, "Fresh pineapple", ["ananas"]),
    ("Guava", "Fruits", 60, "Fresh guava", ["amrud"]),
    ("Pear", "Fruits", 110, "Fresh pears", ["nashpati"]),
    ("Peach", "Fruits", 120, "Sweet peaches", ["aadu"]),
    ("Strawberry", "Fruits", 180, "Fresh strawberries", ["strawberries"]),
    ("Lemon", "Fruits", 60, "Fresh lemons", ["nimbu"]),
    ("Sweet Lime / Mosambi", "Fruits", 65, "Juicy mosambi", ["sweet-lime", "mosambi"]),
    ("Litchi", "Fruits", 140, "Seasonal litchi", ["lychee"]),
    ("Kiwi", "Fruits", 160, "Fresh kiwi fruit", ["kiwi-fruit"]),
    ("Coconut", "Fruits", 45, "Fresh coconut", ["nariyal"]),
    ("Dates", "Fruits", 180, "Sweet dates", ["date", "khajoor"]),
]

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".avif")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def load_local_files():
    files = {}
    if IMG_DIR.exists():
        for p in sorted(IMG_DIR.iterdir()):
            if p.suffix.lower() in IMAGE_EXTS:
                s = slug(p.stem)
                files.setdefault(s, p.name)
                files.setdefault(re.sub(r"-?\d+$", "", s), p.name)
    return files


LOCAL_FILES = load_local_files()


def local_image(name, aliases):
    candidates = [slug(name)]
    candidates += [slug(part) for part in name.split("/")]
    candidates += [slug(a) for a in aliases]
    for c in candidates:
        if c in LOCAL_FILES:
            return IMG_URL + LOCAL_FILES[c]
    return None


def default_image(category):
    return DEFAULT_IMAGES["Fruits"] if category == "Fruits" else DEFAULT_IMAGES["default"]


def main():
    if not DB.exists():
        print("greenbasket.db not found. Run python app.py once first, then run this script.")
        return
    if not IMG_DIR.exists():
        print(f"Folder not found: {IMG_DIR}\nIsme apni product images rakho, phir script dobara chalao.")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    seller = con.execute("SELECT id FROM users WHERE username='farmer1'").fetchone()
    if not seller:
        print("Demo farmer 'farmer1' not found. Register a farmer account, then edit seller_id in this script if needed.")
        con.close()
        return
    seller_id = seller["id"]

    inserted = updated = 0
    missing = []

    for name, category, price, desc, aliases in PRODUCTS:
        img = local_image(name, aliases)
        if not img:
            missing.append(name)

        existing = con.execute(
            "SELECT id, image FROM products WHERE lower(name)=lower(?)", (name,)
        ).fetchone()

        if existing:
            if img:
                con.execute("UPDATE products SET image=? WHERE id=?", (img, existing["id"]))
                updated += 1
            elif not existing["image"]:
                con.execute("UPDATE products SET image=? WHERE id=?", (default_image(category), existing["id"]))
        else:
            con.execute(
                """INSERT INTO products(seller_id,name,category,description,price,stock,unit,state,city,image,active)
                   VALUES(?,?,?,?,?,?,?,?,?,?,1)""",
                (seller_id, name, category, desc, price, 80, "kg",
                 "Madhya Pradesh", "Bhopal", img or default_image(category)),
            )
            inserted += 1

    con.commit()
    con.close()

    print(f"Catalog ready. Added {inserted} products, updated {updated} product images.")
    if missing:
        print(f"\nIn {len(missing)} products ki image '{IMG_DIR}' me nahi mili:")
        for m in missing:
            print("  -", m)
        print("\nInke naam se image file rakho (jaise garlic.jpg) aur script dobara chalao.")
    else:
        print("Sabhi products ko apni alag image mil gayi.")


if __name__ == "__main__":
    main()
