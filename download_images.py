import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).parent / "static" / "images" / "products"
OUT.mkdir(parents=True, exist_ok=True)

# file ka naam -> Wikipedia page ka naam
ITEMS = {
    "tomato": "Tomato", "potato": "Potato", "onion": "Onion",
    "carrot": "Carrot", "cauliflower": "Cauliflower", "cabbage": "Cabbage",
    "spinach": "Spinach", "coriander": "Coriander", "fenugreek": "Fenugreek",
    "lettuce": "Lettuce", "brinjal": "Eggplant", "okra": "Okra",
    "cucumber": "Cucumber", "peas": "Pea", "chilli": "Chili pepper",
    "capsicum": "Bell pepper", "lauki": "Calabash", "karela": "Momordica charantia",
    "radish": "Radish", "beetroot": "Beetroot", "pumpkin": "Pumpkin",
    "sweet-corn": "Sweet corn", "garlic": "Garlic", "ginger": "Ginger",
    "apple": "Apple", "banana": "Banana", "mango": "Mango",
    "orange": "Orange (fruit)", "grapes": "Grape", "pomegranate": "Pomegranate",
    "papaya": "Papaya", "watermelon": "Watermelon", "muskmelon": "Cantaloupe",
    "pineapple": "Pineapple", "guava": "Guava", "pear": "Pear",
    "peach": "Peach", "strawberry": "Strawberry", "lemon": "Lemon",
    "mosambi": "Citrus limetta", "litchi": "Lychee", "kiwi": "Kiwifruit",
    "coconut": "Coconut", "dates": "Date palm",
}

HEADERS = {"User-Agent": "GreenBasketStudentProject/1.0 (learning project)"}


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=30).read()


failed = []
for fname, page in ITEMS.items():
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
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        (OUT / (fname + ext)).write_bytes(img)
        print("ok:", fname)
    except Exception as e:
        print("FAIL:", fname, "-", e)
        failed.append(fname)
    time.sleep(0.5)

print("\nDone. Nahi hui:", failed if failed else "koi nahi")