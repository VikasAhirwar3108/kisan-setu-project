
import os, sqlite3, json, hmac, hashlib
from functools import wraps
from datetime import datetime
from flask import Flask, g, request, redirect, url_for, render_template, flash, session, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

try:
    import razorpay
except ImportError:
    razorpay = None

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "greenbasket.db")
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

import re

IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "images", "products")

def auto_image(name):
    def slug(s):
        return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    target = "-" + slug(name) + "-"
    best = None
    if os.path.isdir(IMG_DIR):
        for fn in os.listdir(IMG_DIR):
            stem, ext = os.path.splitext(fn)
            if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".avif"):
                continue
            s = slug(stem)
            for form in {s, s.rstrip("s"), s + "s"}:
                if form and ("-" + form + "-") in target and (best is None or len(s) > len(best[0])):
                    best = (s, fn)
    return "/static/images/products/" + best[1] if best else ""

# India state/UT list with commonly used cities. Add cities through the CITIES map as needed.
LOCATIONS = {
    "Andhra Pradesh": ["Visakhapatnam","Vijayawada","Guntur","Tirupati","Nellore","Kurnool","Rajahmundry","Kakinada"],
    "Arunachal Pradesh": ["Itanagar","Naharlagun","Tawang","Pasighat","Ziro"],
    "Assam": ["Guwahati","Silchar","Dibrugarh","Jorhat","Tezpur","Tinsukia"],
    "Bihar": ["Patna","Gaya","Muzaffarpur","Bhagalpur","Darbhanga","Purnia"],
    "Chhattisgarh": ["Raipur","Bhilai","Bilaspur","Korba","Durg","Jagdalpur"],
    "Goa": ["Panaji","Margao","Vasco da Gama","Mapusa"],
    "Gujarat": ["Ahmedabad","Surat","Vadodara","Rajkot","Bhavnagar","Jamnagar","Gandhinagar"],
    "Haryana": ["Gurugram","Faridabad","Panipat","Ambala","Hisar","Karnal"],
    "Himachal Pradesh": ["Shimla","Dharamshala","Mandi","Solan","Kullu"],
    "Jharkhand": ["Ranchi","Jamshedpur","Dhanbad","Bokaro","Deoghar","Hazaribagh"],
    "Karnataka": ["Bengaluru","Mysuru","Mangaluru","Hubballi","Belagavi","Shivamogga"],
    "Kerala": ["Thiruvananthapuram","Kochi","Kozhikode","Thrissur","Kollam","Kannur"],
    "Madhya Pradesh": ["Bhopal","Indore","Jabalpur","Gwalior","Ujjain","Sagar","Rewa","Satna","Anuppur","Kotma","Vidisha","Sehore","Dewas","Ratlam"],
    "Maharashtra": ["Mumbai","Pune","Nagpur","Nashik","Thane","Kolhapur","Aurangabad","Solapur"],
    "Manipur": ["Imphal","Thoubal","Churachandpur","Bishnupur"],
    "Meghalaya": ["Shillong","Tura","Jowai","Nongpoh"],
    "Mizoram": ["Aizawl","Lunglei","Champhai","Kolasib"],
    "Nagaland": ["Kohima","Dimapur","Mokokchung","Wokha"],
    "Odisha": ["Bhubaneswar","Cuttack","Rourkela","Sambalpur","Puri","Balasore"],
    "Punjab": ["Ludhiana","Amritsar","Jalandhar","Patiala","Bathinda","Mohali"],
    "Rajasthan": ["Jaipur","Jodhpur","Udaipur","Kota","Ajmer","Bikaner","Alwar"],
    "Sikkim": ["Gangtok","Namchi","Gyalshing","Mangan"],
    "Tamil Nadu": ["Chennai","Coimbatore","Madurai","Tiruchirappalli","Salem","Tirunelveli","Erode"],
    "Telangana": ["Hyderabad","Warangal","Nizamabad","Karimnagar","Khammam","Suryapet"],
    "Tripura": ["Agartala","Udaipur","Dharmanagar","Belonia"],
    "Uttar Pradesh": ["Lucknow","Kanpur","Varanasi","Agra","Prayagraj","Noida","Ghaziabad","Gorakhpur","Meerut","Bareilly"],
    "Uttarakhand": ["Dehradun","Haridwar","Rishikesh","Haldwani","Roorkee"],
    "West Bengal": ["Kolkata","Howrah","Siliguri","Durgapur","Asansol","Darjeeling"],
    "Andaman and Nicobar Islands": ["Port Blair","Diglipur"],
    "Chandigarh": ["Chandigarh"],
    "Dadra and Nagar Haveli and Daman and Diu": ["Daman","Silvassa","Diu"],
    "Delhi": ["New Delhi","Delhi","Dwarka","Rohini"],
    "Jammu and Kashmir": ["Srinagar","Jammu","Anantnag","Baramulla"],
    "Ladakh": ["Leh","Kargil"],
    "Lakshadweep": ["Kavaratti","Agatti"],
    "Puducherry": ["Puducherry","Karaikal","Mahe","Yanam"]
}
CROPS = [
    ("Organic Tomatoes","Vegetables",42,"Farm-fresh tomatoes"),
    ("Fresh Carrots","Vegetables",35,"Sweet, crisp carrots"),
    ("Green Spinach","Leafy Greens",28,"Fresh leafy spinach"),
    ("Red Apples","Fruits",145,"Seasonal apples"),
    ("Farm Eggs (6 pcs)","Dairy & Eggs",55,"Free-range eggs"),
    ("Organic Zucchini","Vegetables",48,"Fresh organic zucchini"),
    ("Yukon Gold Potato","Vegetables",32,"Clean, fresh potatoes"),
    ("Organic Peach","Fruits",120,"Seasonal peaches"),
    ("Bell Pepper","Vegetables",65,"Colourful bell peppers"),
    ("Soft White Wheat","Grains & Legumes",38,"Locally sourced wheat"),
    ("Onion","Vegetables",30,"Daily-use onions"),
    ("Mango","Fruits",85,"Seasonal mangoes"),
    ("Banana","Fruits",45,"Naturally sweet bananas"),
    ("Cucumber","Vegetables",25,"Cool, crisp cucumber"),
    ("Green Peas","Vegetables",60,"Fresh green peas"),
    ("Milk (1 L)","Dairy & Eggs",62,"Fresh dairy milk"),
    ("Brown Rice","Grains & Legumes",70,"Wholesome rice"),
    ("Almonds (250 g)","Nuts & Seeds",180,"Premium nuts")
]

def connect_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def query(sql, args=(), one=False):
    cur = connect_db().execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows

def execute(sql, args=()):
    db = connect_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'buyer', phone TEXT DEFAULT '',
      state TEXT DEFAULT '', city TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER, name TEXT NOT NULL, category TEXT NOT NULL,
      description TEXT DEFAULT '', price REAL NOT NULL, stock REAL NOT NULL DEFAULT 0, unit TEXT DEFAULT 'kg',
      state TEXT DEFAULT '', city TEXT DEFAULT '', image TEXT DEFAULT '', active INTEGER DEFAULT 1,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(seller_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS orders(
      id INTEGER PRIMARY KEY AUTOINCREMENT, buyer_id INTEGER, address TEXT NOT NULL, state TEXT NOT NULL,
      city TEXT NOT NULL, pincode TEXT NOT NULL, subtotal REAL NOT NULL, delivery_fee REAL NOT NULL DEFAULT 0,
      total REAL NOT NULL, payment_method TEXT NOT NULL, payment_status TEXT NOT NULL DEFAULT 'pending',
      payment_reference TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'Placed', driver_name TEXT DEFAULT '',
      driver_phone TEXT DEFAULT '', vehicle_number TEXT DEFAULT '', driver_lat REAL, driver_lon REAL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(buyer_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS order_items(
      id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, product_id INTEGER, seller_id INTEGER,
      product_name TEXT, qty REAL, price REAL, FOREIGN KEY(order_id) REFERENCES orders(id));
    CREATE TABLE IF NOT EXISTS payment_history(
      id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, user_id INTEGER, amount REAL,
      method TEXT, status TEXT, reference TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS cart(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, qty REAL DEFAULT 1,
      UNIQUE(user_id, product_id));
    """)
    # Safe schema migration for databases created by earlier versions.
    order_columns = {row[1] for row in db.execute("PRAGMA table_info(orders)").fetchall()}
    if "driver_id" not in order_columns:
        db.execute("ALTER TABLE orders ADD COLUMN driver_id INTEGER")

    product_columns = {row[1] for row in db.execute("PRAGMA table_info(products)").fetchall()}
    if "image" not in product_columns:
        db.execute("ALTER TABLE products ADD COLUMN image TEXT DEFAULT ''")
    if "active" not in product_columns:
        db.execute("ALTER TABLE products ADD COLUMN active INTEGER DEFAULT 1")

    count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        demo = [
            ("Portal Admin","admin","Admin@123","admin","9999999999","Delhi","New Delhi"),
            ("Green Farmer","farmer1","Farmer@123","farmer","9876543210","Madhya Pradesh","Bhopal"),
            ("Fresh Mart Buyer","buyer1","Buyer@123","buyer","9123456780","Madhya Pradesh","Indore"),
            ("Delivery Driver","driver1","Driver@123","driver","9000000001","Delhi","Delhi")
        ]
        for name, username, password, role, phone, state, city in demo:
            db.execute("INSERT INTO users(name,username,password_hash,role,phone,state,city) VALUES(?,?,?,?,?,?,?)",
                       (name, username, generate_password_hash(password), role, phone, state, city))
        farmer_row = db.execute(
            "SELECT id FROM users WHERE username = ?",
            ("farmer1",)
        ).fetchone()

        if farmer_row:
            farmer_id = farmer_row[0]

            for name, category, price, desc in CROPS:
                db.execute(
                    """INSERT INTO products
                    (seller_id, name, category, description, price, stock, unit, state, city)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        farmer_id,
                        name,
                        category,
                        desc,
                        price,
                        random_stock(name),
                        "kg" if "Eggs" not in name and "Milk" not in name else "pack",
                        "Madhya Pradesh",
                        "Bhopal",
                    ),
                )

        db.commit()

    # Keep the documented demo accounts available in this local prototype,
    # even when the SQLite file already contains older user records.
    demo_accounts = [
        ("Portal Admin", "admin", "Admin@123", "admin", "9999999999", "Delhi", "New Delhi"),
        ("Green Farmer", "farmer1", "Farmer@123", "farmer", "9876543210", "Madhya Pradesh", "Bhopal"),
        ("Fresh Mart Buyer", "buyer1", "Buyer@123", "buyer", "9123456780", "Madhya Pradesh", "Indore"),
        ("Delivery Driver", "driver1", "Driver@123", "driver", "9000000001", "Delhi", "Delhi"),
    ]
    for name, username, password, role, phone, state, city in demo_accounts:
        existing = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            db.execute("UPDATE users SET password_hash=?, role=? WHERE username=?",
                       (generate_password_hash(password), role, username))
        else:
            db.execute("""INSERT INTO users(name,username,password_hash,role,phone,state,city)
                          VALUES(?,?,?,?,?,?,?)""",
                       (name, username, generate_password_hash(password), role, phone, state, city))
    db.commit()
    db.close()
def random_stock(name):
    return 80 if "Milk" not in name else 40

def login_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login", next=request.path))
            if roles and session.get("role") not in roles:
                flash("Aapko is action ki permission nahi hai.", "error")
                return redirect(url_for("home"))
            return fn(*args, **kwargs)
        return wrapped
    return decorator

@app.context_processor
def global_context():
    return {"states": sorted(LOCATIONS.keys()), "locations": LOCATIONS, "categories": sorted(set(x[1] for x in CROPS))}

@app.route("/")
def home():
    products = query("SELECT p.*,u.name AS seller_name FROM products p LEFT JOIN users u ON u.id=p.seller_id WHERE p.active=1 ORDER BY p.id DESC LIMIT 10")
    return render_template("home.html", products=products)

@app.route("/products")
def products():
    category = request.args.get("category","")
    search = request.args.get("q","").strip()
    sql = "SELECT p.*,u.name AS seller_name FROM products p LEFT JOIN users u ON u.id=p.seller_id WHERE p.active=1"
    args=[]
    if category:
        sql += " AND p.category=?"; args.append(category)
    if search:
        sql += " AND (p.name LIKE ? OR p.description LIKE ?)"; args.extend([f"%{search}%",f"%{search}%"])
    sql += " ORDER BY p.id DESC"
    return render_template("products.html", products=query(sql,args), selected=category, search=search)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form.get("name","").strip()
        username=request.form.get("username","").strip().lower()
        password=request.form.get("password","")
        role=request.form.get("role","buyer")
        phone=request.form.get("phone","").strip()
        state=request.form.get("state","")
        city=request.form.get("city","")
        if not name or len(username)<4 or len(password)<6 or role not in ("buyer","farmer","driver"):
            flash("Naam, username (4+), password (6+) aur valid role bharna zaroori hai.","error")
        elif state not in LOCATIONS or city not in LOCATIONS.get(state,[]):
            flash("Valid state aur city select karein.","error")
        else:
            try:
                execute("INSERT INTO users(name,username,password_hash,role,phone,state,city) VALUES(?,?,?,?,?,?,?)",
                        (name,username,generate_password_hash(password),role,phone,state,city))
                flash("Registration successful. Ab login karein.","success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Ye username pehle se maujood hai.","error")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username=request.form.get("username","").strip().lower()
        password=request.form.get("password","")
        user=query("SELECT * FROM users WHERE username=?",(username,),one=True)
        if user and check_password_hash(user["password_hash"],password):
            session.clear()
            session.update(user_id=user["id"],name=user["name"],role=user["role"])
            nxt=request.args.get("next","")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
        flash("Username ya password galat hai.","error")
    return render_template("login.html")

@app.route("/dashboard")
@login_required()
def dashboard():
    role = session.get("role")
    uid = session["user_id"]
    data = {}
    if role == "admin":
        data = {
            "users_count": query("SELECT COUNT(*) n FROM users", one=True)["n"],
            "products_count": query("SELECT COUNT(*) n FROM products", one=True)["n"],
            "orders_count": query("SELECT COUNT(*) n FROM orders", one=True)["n"],
            "paid_total": query("SELECT COALESCE(SUM(amount),0) n FROM payment_history WHERE status='paid'", one=True)["n"],
            "recent_orders": query("SELECT o.*,u.name buyer_name FROM orders o LEFT JOIN users u ON u.id=o.buyer_id ORDER BY o.id DESC LIMIT 8"),
            "recent_users": query("SELECT name,username,role,city,state FROM users ORDER BY id DESC LIMIT 8"),
        }
    elif role == "farmer":
        data = {
            "products_count": query("SELECT COUNT(*) n FROM products WHERE seller_id=?", (uid,), one=True)["n"],
            "stock_count": query("SELECT COALESCE(SUM(stock),0) n FROM products WHERE seller_id=? AND active=1", (uid,), one=True)["n"],
            "sales_count": query("SELECT COUNT(DISTINCT oi.order_id) n FROM order_items oi WHERE oi.seller_id=?", (uid,), one=True)["n"],
            "sales_total": query("SELECT COALESCE(SUM(oi.qty*oi.price),0) n FROM order_items oi WHERE oi.seller_id=?", (uid,), one=True)["n"],
            "sales": query("""SELECT o.id,o.created_at,o.status,o.payment_status,o.payment_method,o.city,o.state,
                              SUM(oi.qty*oi.price) seller_total
                              FROM order_items oi JOIN orders o ON o.id=oi.order_id
                              WHERE oi.seller_id=? GROUP BY o.id ORDER BY o.id DESC LIMIT 10""", (uid,)),
            "products": query("SELECT * FROM products WHERE seller_id=? ORDER BY id DESC LIMIT 8", (uid,)),
        }
    elif role == "buyer":
        data = {
            "orders_count": query("SELECT COUNT(*) n FROM orders WHERE buyer_id=?", (uid,), one=True)["n"],
            "cart_count": query("SELECT COUNT(*) n FROM cart WHERE user_id=?", (uid,), one=True)["n"],
            "paid_total": query("SELECT COALESCE(SUM(amount),0) n FROM payment_history WHERE user_id=? AND status='paid'", (uid,), one=True)["n"],
            "orders": query("SELECT * FROM orders WHERE buyer_id=? ORDER BY id DESC LIMIT 10", (uid,)),
            "payments": query("SELECT * FROM payment_history WHERE user_id=? ORDER BY id DESC LIMIT 8", (uid,)),
        }
    elif role == "driver":
        data = {
            "assigned_count": query("SELECT COUNT(*) n FROM orders WHERE driver_id=? AND status NOT IN ('Delivered','Cancelled')", (uid,), one=True)["n"],
            "completed_count": query("SELECT COUNT(*) n FROM orders WHERE driver_id=? AND status='Delivered'", (uid,), one=True)["n"],
            "deliveries": query("""SELECT * FROM orders WHERE (driver_id=? OR driver_id IS NULL)
                                  AND status NOT IN ('Delivered','Cancelled') ORDER BY CASE WHEN driver_id=? THEN 0 ELSE 1 END,id DESC LIMIT 12""", (uid,uid)),
        }
    return render_template("dashboard.html", role=role, data=data)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/sell", methods=["GET","POST"])
@login_required("farmer","admin","buyer")
def sell():
    if request.method=="POST":
        f=request.form
        name=f.get("name","").strip()
        category=f.get("category","")
        try:
            price=float(f.get("price","0")); stock=float(f.get("stock","0"))
        except ValueError:
            price=stock=0
        state=f.get("state",""); city=f.get("city","")
        if not name or category not in [c[1] for c in CROPS] or price<=0 or stock<=0 or state not in LOCATIONS or city not in LOCATIONS.get(state,[]):
            flash("Product, category, price, stock aur valid location check karein.","error")
        else:
            execute("INSERT INTO products(seller_id,name,category,description,price,stock,unit,state,city,image) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (session["user_id"],name,category,f.get("description","")[:400],price,stock,f.get("unit","kg"),state,city,auto_image(name)))
            flash("Aapki listing publish ho gayi.","success")
            return redirect(url_for("products"))
    return render_template("sell.html")
@app.post("/cart/add/<int:pid>")
@login_required()
def cart_add(pid):
    product = query("SELECT id, stock, active FROM products WHERE id=?", (pid,), one=True)
    if not product or not product["active"]:
        flash("Yeh product ab available nahi hai.", "error")
        return redirect(request.referrer or url_for("products"))
    if product["stock"] <= 0:
        flash("Is product ka stock khatam hai.", "error")
        return redirect(request.referrer or url_for("products"))
    try:
        qty = max(1.0, float(request.form.get("qty", "1")))
    except (TypeError, ValueError):
        qty = 1.0
    existing = query("SELECT id, qty FROM cart WHERE user_id=? AND product_id=?",
                     (session["user_id"], pid), one=True)
    if existing:
        new_qty = min(float(existing["qty"]) + qty, float(product["stock"]))
        execute("UPDATE cart SET qty=? WHERE id=?", (new_qty, existing["id"]))
    else:
        execute("INSERT INTO cart(user_id, product_id, qty) VALUES(?,?,?)",
                (session["user_id"], pid, min(qty, float(product["stock"]))))
    flash("Product cart mein add ho gaya.", "success")
    return redirect(url_for("cart"))

@app.route("/cart")
@login_required("buyer")
def cart():
    rows=query("""SELECT c.qty,p.id product_id,p.name,p.price,p.stock,p.unit FROM cart c
                  JOIN products p ON p.id=c.product_id WHERE c.user_id=?""",(session["user_id"],))
    return render_template("cart.html",items=rows,total=sum(r["qty"]*r["price"] for r in rows))

@app.route("/checkout", methods=["GET","POST"])
@login_required("buyer")
def checkout():
    items=query("""SELECT c.qty,p.* FROM cart c JOIN products p ON p.id=c.product_id
                   WHERE c.user_id=? AND p.active=1""",(session["user_id"],))
    if not items:
        flash("Cart khaali hai.","error")
        return redirect(url_for("products"))
    subtotal=round(sum(i["qty"]*i["price"] for i in items),2)
    delivery_fee=0 if subtotal>=999 else 49
    total=round(subtotal+delivery_fee,2)
    if request.method=="POST":
        f=request.form
        address=f.get("address","").strip(); state=f.get("state",""); city=f.get("city","")
        pincode=f.get("pincode","").strip(); method=f.get("payment_method","")
        if not address or len(pincode)!=6 or not pincode.isdigit() or state not in LOCATIONS or city not in LOCATIONS.get(state,[]) or method not in ("cod","upi","card","netbanking","razorpay"):
            flash("Delivery address, PIN code, location ya payment method check karein.","error")
            return redirect(url_for("checkout"))
        db=connect_db()
        cur=db.execute("""INSERT INTO orders(buyer_id,address,state,city,pincode,subtotal,delivery_fee,total,payment_method,payment_status)
                          VALUES(?,?,?,?,?,?,?,?,?,?)""",
                       (session["user_id"],address,state,city,pincode,subtotal,delivery_fee,total,method,"pending" if method!="cod" else "pending"))
        oid=cur.lastrowid
        for item in items:
            if item["stock"] < item["qty"]:
                db.rollback()
                flash(f"{item['name']} ka stock ab available nahi hai.","error")
                return redirect(url_for("cart"))
            db.execute("INSERT INTO order_items(order_id,product_id,seller_id,product_name,qty,price) VALUES(?,?,?,?,?,?)",
                       (oid,item["id"],item["seller_id"],item["name"],item["qty"],item["price"]))
            db.execute("UPDATE products SET stock=stock-? WHERE id=?",(item["qty"],item["id"]))
        db.execute("DELETE FROM cart WHERE user_id=?",(session["user_id"],))
        db.commit()
        if method=="razorpay":
            return redirect(url_for("pay",oid=oid))
        if method=="cod":
            execute("INSERT INTO payment_history(order_id,user_id,amount,method,status,reference) VALUES(?,?,?,?,?,?)",
                    (oid,session["user_id"],total,"Cash on Delivery","pending","COD-"+str(oid)))
            flash("Order place ho gaya. Cash on Delivery select kiya hai.","success")
        else:
            # Demo placeholder for non-gateway methods: do not mark paid automatically.
            execute("INSERT INTO payment_history(order_id,user_id,amount,method,status,reference) VALUES(?,?,?,?,?,?)",
                    (oid,session["user_id"],total,method.upper(),"pending","Awaiting payment gateway"))
            flash("Order place ho gaya. Payment abhi pending hai. Secure payment gateway configure karein.","success")
        return redirect(url_for("orders"))
    return render_template("checkout.html",items=items,subtotal=subtotal,delivery_fee=delivery_fee,total=total)

def rp_client():
    if not (razorpay and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET):
        return None
    return razorpay.Client(auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET))

@app.route("/pay/<int:oid>",methods=["GET","POST"])
@login_required("buyer")
def pay(oid):
    order=query("SELECT * FROM orders WHERE id=? AND buyer_id=?",(oid,session["user_id"]),one=True)
    if not order:
        abort(404)
    if order["payment_status"]=="paid":
        return redirect(url_for("orders"))
    client=rp_client()
    if request.method=="POST":
        if not client:
            flash("Razorpay keys configure nahi hain. Test keys set karke restart karein.","error")
            return redirect(url_for("pay",oid=oid))
        try:
            rp_order=client.order.create({"amount":int(round(order["total"]*100)),"currency":"INR","receipt":f"greenbasket_{oid}"})
            execute("UPDATE orders SET payment_reference=? WHERE id=?",(rp_order["id"],oid))
            return render_template("pay.html",order=order,key_id=RAZORPAY_KEY_ID,rp_order=rp_order)
        except Exception:
            flash("Payment order create nahi hua. Razorpay keys check karein.","error")
    return render_template("pay.html",order=order,key_id=RAZORPAY_KEY_ID,rp_order=None)

@app.post("/payment/verify")
@login_required("buyer")
def payment_verify():
    f=request.form
    oid=int(f.get("order_id","0"))
    order=query("SELECT * FROM orders WHERE id=? AND buyer_id=?",(oid,session["user_id"]),one=True)
    if not order:
        abort(404)
    payment_id=f.get("razorpay_payment_id",""); rp_order_id=f.get("razorpay_order_id",""); signature=f.get("razorpay_signature","")
    expected=hmac.new(RAZORPAY_KEY_SECRET.encode(),(rp_order_id+"|"+payment_id).encode(),hashlib.sha256).hexdigest()
    if not RAZORPAY_KEY_SECRET or not all([payment_id,rp_order_id,signature]) or not hmac.compare_digest(expected,signature) or order["payment_reference"]!=rp_order_id:
        flash("Payment verify nahi hua. Order unpaid hi rahega.","error")
        return redirect(url_for("orders"))
    execute("UPDATE orders SET payment_status='paid',payment_reference=? WHERE id=?",(payment_id,oid))
    execute("INSERT INTO payment_history(order_id,user_id,amount,method,status,reference) VALUES(?,?,?,?,?,?)",
            (oid,session["user_id"],order["total"],"Razorpay","paid",payment_id))
    flash("Payment successful.","success")
    return redirect(url_for("orders"))

@app.route("/orders")
@login_required("buyer")
def orders():
    rows=query("SELECT * FROM orders WHERE buyer_id=? ORDER BY id DESC",(session["user_id"],))
    return render_template("orders.html",orders=rows)

@app.route("/payments")
@login_required()
def payments():
    role = session.get("role")
    uid = session["user_id"]
    if role == "admin":
        rows = query("""SELECT ph.*,u.name AS account_name FROM payment_history ph
                        LEFT JOIN users u ON u.id=ph.user_id ORDER BY ph.id DESC""")
        title = "All Payment Records"
    elif role == "buyer":
        rows = query("SELECT * FROM payment_history WHERE user_id=? ORDER BY id DESC", (uid,))
        title = "My Payment History"
    elif role == "farmer":
        rows = query("""SELECT o.id AS order_id, o.total AS amount, o.payment_method AS method,
                        o.payment_status AS status, o.payment_reference AS reference, o.created_at
                        FROM orders o JOIN order_items oi ON oi.order_id=o.id
                        WHERE oi.seller_id=? GROUP BY o.id ORDER BY o.id DESC""", (uid,))
        title = "Sales Payment Status"
    else:
        flash("Driver account ko payment history dekhne ki permission nahi hai.", "error")
        return redirect(url_for("dashboard"))
    return render_template("payments.html", payments=rows, title=title, role=role)

@app.route("/track/<int:oid>")
@login_required()
def track(oid):
    if session.get("role") == "admin":
        order = query("SELECT * FROM orders WHERE id=?", (oid,), one=True)
    elif session.get("role") == "buyer":
        order = query("SELECT * FROM orders WHERE id=? AND buyer_id=?", (oid,session["user_id"]), one=True)
    elif session.get("role") == "driver":
        order = query("SELECT * FROM orders WHERE id=? AND (driver_id=? OR driver_id IS NULL)", (oid,session["user_id"]), one=True)
    else:
        order = None
    if not order:
        abort(404)
    return render_template("track.html",order=order)

@app.route("/api/track/<int:oid>")
@login_required()
def track_api(oid):
    if session.get("role") == "admin":
        order = query("SELECT * FROM orders WHERE id=?", (oid,), one=True)
    elif session.get("role") == "buyer":
        order = query("SELECT * FROM orders WHERE id=? AND buyer_id=?", (oid,session["user_id"]), one=True)
    elif session.get("role") == "driver":
        order = query("SELECT * FROM orders WHERE id=? AND (driver_id=? OR driver_id IS NULL)", (oid,session["user_id"]), one=True)
    else:
        order = None
    if not order:
        abort(404)
    return jsonify({"status":order["status"],"driver_name":order["driver_name"],"driver_phone":order["driver_phone"],
                    "vehicle_number":order["vehicle_number"],"lat":order["driver_lat"],"lon":order["driver_lon"]})

@app.route("/driver/orders")
@login_required("driver","admin")
def driver_orders():
    if session.get("role") == "admin":
        rows = query("SELECT * FROM orders WHERE status NOT IN ('Delivered','Cancelled') ORDER BY id DESC")
    else:
        rows = query("""SELECT * FROM orders WHERE (driver_id=? OR driver_id IS NULL)
                        AND status NOT IN ('Delivered','Cancelled')
                        ORDER BY CASE WHEN driver_id=? THEN 0 ELSE 1 END,id DESC""",
                     (session["user_id"],session["user_id"]))
    return render_template("driver_orders.html",orders=rows)

@app.post("/driver/update/<int:oid>")
@login_required("driver","admin")
def driver_update(oid):
    order=query("SELECT * FROM orders WHERE id=?",(oid,),one=True)
    if not order:
        abort(404)
    f=request.form
    status=f.get("status","")
    if status not in ("Placed","Confirmed","Packed","Out for delivery","Delivered","Cancelled"):
        abort(400)
    if session.get("role") == "driver" and order["driver_id"] not in (None, session["user_id"]):
        abort(403)
    assigned_driver = session["user_id"] if session.get("role") == "driver" else order["driver_id"]
    execute("""UPDATE orders SET status=?,driver_name=?,driver_phone=?,vehicle_number=?,driver_lat=?,driver_lon=?,driver_id=? WHERE id=?""",
            (status,f.get("driver_name","")[:80],f.get("driver_phone","")[:20],f.get("vehicle_number","")[:30],
             float(f["lat"]) if f.get("lat") else None,float(f["lon"]) if f.get("lon") else None,assigned_driver,oid))
    flash("Delivery update save ho gaya.","success")
    return redirect(url_for("driver_orders"))

@app.route("/sell/manage")
@login_required("farmer","admin","buyer")
def manage_listings():
    rows=query("SELECT * FROM products WHERE seller_id=? ORDER BY id DESC",(session["user_id"],))
    return render_template("manage_listings.html",products=rows)

@app.route("/sell/toggle/<int:pid>",methods=["POST"])
@login_required("farmer","admin","buyer")
def toggle_listing(pid):
    execute("UPDATE products SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=? AND seller_id=?",(pid,session["user_id"]))
    return redirect(url_for("manage_listings"))

@app.route("/admin")
@login_required("admin")
def admin():
    return render_template("admin.html",users=query("SELECT id,name,username,role,phone,state,city FROM users ORDER BY id"),
                           orders=query("SELECT * FROM orders ORDER BY id DESC"),products=query("SELECT * FROM products ORDER BY id DESC"))

@app.route("/api/cities/<state>")
def api_cities(state):
    return jsonify(LOCATIONS.get(state,[]))

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html",code=404,message="Page nahi mila."),404

@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html",code=403,message="Aapko is page ki permission nahi hai."),403

if __name__=="__main__":
    init_db()
    app.run(debug=True)
