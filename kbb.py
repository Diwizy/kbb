import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from datetime import datetime
import os

DB = "kebab.db"
SESSION = {"user_id": None, "nama": None, "last_receipt": None}

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT,
        harga INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS pelanggan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT,
        username TEXT UNIQUE,
        password TEXT,
        tanggal_daftar TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS penjualan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pelanggan_id INTEGER,
        nama_user TEXT,
        nama_pesanan TEXT,
        qty INTEGER,
        ukuran TEXT,
        level_pedas TEXT,
        total_bayar INTEGER,
        metode TEXT,
        tanggal TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS keranjang (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pelanggan_id INTEGER,
        nama TEXT,
        harga INTEGER,
        qty INTEGER,
        ukuran TEXT,
        level_pedas TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

def page(content):
    return f"""
    <html>
    <head>
    <style>
        body{{font-family:'Segoe UI', Tahoma; background:#f4f7f6; margin:0; color:#333}}
        .nav{{background:#075e54; color:white; padding:15px 5%; display:flex; justify-content:space-between; align-items:center}}
        .nav a{{color:white; margin-left:15px; text-decoration:none; font-weight:bold}}
        .container{{width:90%; max-width:1000px; margin:30px auto; background:white; padding:25px; border-radius:12px; box-shadow:0 4px 10px rgba(0,0,0,0.1)}}
        .login-box{{width:320px; margin:100px auto; background:white; padding:30px; border-radius:15px; box-shadow:0 10px 25px rgba(0,0,0,0.1); text-align:center}}
        input, select{{width:100%; padding:10px; margin:8px 0; border:1px solid #ddd; border-radius:6px; box-sizing:border-box}}
        button{{padding:12px; width:100%; background:#075e54; color:white; border:none; border-radius:6px; font-weight:bold; cursor:pointer}}
        button:hover{{background:#054d44}}
        table{{width:100%; border-collapse:collapse; margin-top:20px}}
        th, td{{border:1px solid #eee; padding:12px; text-align:center}}
        th{{background:#f8f9fa}}
        .card{{border:1px solid #eee; padding:15px; border-radius:10px; width:230px; display:inline-block; margin:10px; vertical-align:top; background:#fff}}
        .struk{{width:300px; margin:20px auto; border:1px dashed #000; padding:20px; font-family:'Courier New', monospace; background:#fff; text-align:left}}
        @media print {{
            .nav, button, a {{ display: none !important; }}
            .container {{ box-shadow: none !important; border: none !important; }}
            .struk {{ border: none !important; width: 100% !important; }}
        }}
    </style>
    </head>
    <body>{content}</body>
    </html>
    """

def nav(role):
    if role == "admin":
        link = '<a href="/admin/menu">Menu</a> <a href="/admin/pelanggan">Pelanggan</a> <a href="/admin/laporan">Laporan</a>'
    else:
        link = f'<a href="/user">Pesan Kebab</a> <a href="/keranjang">Keranjang</a>'
    return f'<div class="nav"><b> KEBAB-LASAN</b><div>{link}<a href="/logout" style="color:#ffcdd2">Logout</a></div></div>'

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row

        if path == "/":
            self.html(page('<div class="login-box"><h2>Login</h2><form method="POST" action="/login">'
            '<input name="u" placeholder="Username" required>'
            '<input type="password" name="p" placeholder="Password" required>'
            '<button>MASUK</button></form><p>Belum punya akun? <a href="/daftar">Daftar</a></p></div>'))

        elif path == "/daftar":
            self.html(page('<div class="login-box"><h2>Daftar</h2><form method="POST" action="/reg">'
            '<input name="nama" placeholder="Nama Lengkap" required>'
            '<input name="u" placeholder="Username" required>'
            '<input type="password" name="p" placeholder="Password" required>'
            '<button>DAFTAR</button></form><br><a href="/">Kembali ke Login</a></div>'))

        elif path == "/user":
            menu = conn.execute("SELECT * FROM menu").fetchall()
            h = nav("user") + "<div class='container'><h2>Menu Kebab</h2>"
            if not menu:
                h += "<p>Menu belum tersedia. Silakan tambah di Admin.</p>"
            for m in menu:
                h += f"""<div class='card'><b>{m['nama']}</b><br>Rp {m['harga']}<form method='POST' action='/add_cart'>
                    <input type='hidden' name='id' value='{m['id']}'>
                    <small>Ukuran:</small><select name='sz'><option>Kecil</option><option>Sedang</option><option>Besar</option></select>
                    <small>Level:</small><select name='pd'><option>Tidak</option><option>Sedang</option><option>Pedas</option></select>
                    <small>Jumlah:</small><input type='number' name='q' value='1' min='1'>
                    <button style='background:#2ecc71'>+ Tambah</button></form></div>"""
            self.html(page(h + "</div>"))

        elif path == "/keranjang":
            h = nav("user") + "<div class='container'><h2>Keranjang Belanja</h2>"
            if not SESSION["user_id"]:
                self.redirect("/")
                return
            items = conn.execute("SELECT * FROM keranjang WHERE pelanggan_id=?", (SESSION["user_id"],)).fetchall()
            if not items:
                h += "<p>Keranjang kosong (0). <a href='/user'>Ayo pesan dulu!</a></p>"
                total = 0
            else:
                h += "<table><tr><th>Item</th><th>Detail</th><th>Qty</th><th>Subtotal</th><th>Aksi</th></tr>"
                total = 0
                for i in items:
                    subtotal = i['qty'] * i['harga']
                    total += subtotal
                    h += f"<tr><td>{i['nama']}</td><td>{i['ukuran']} | {i['level_pedas']}</td><td>{i['qty']}</td><td>Rp {subtotal}</td>"
                    h += f"<td><form method='POST' action='/remove_item' style='display:inline'><input type='hidden' name='id' value='{i['id']}'><button style='background:#e74c3c; color:white'>Hapus</button></form></td></tr>"
                h += "</table>"
            h += f"<h3 align='right'>Total Pesanan: Rp {total}</h3>"
            h += '<form method="POST" action="/checkout">Metode: <select name="met" style="width:150px">'
            h += '<option>Cash</option><option>QRIS</option></select>'
            h += '<button style="width:200px">BAYAR SEKARANG</button></form>'
            self.html(page(h + "</div>"))

        elif path == "/struk":
            s = SESSION.get("last_receipt")
            if not s:
                self.redirect("/user")
                return
            items_html = ""
            for i in s["items"]:
                subtotal = i['qty'] * i['price']
                items_html += f"""
                <div style='display:flex; justify-content:space-between; font-size:14px'>
                    <span>{i['name']} ({i['sz']}) x {i['qty']}</span>
                    <span>Rp {subtotal}</span>
                </div>"""
            total_bayar = s.get("total", 0)
            h = nav("user") + f"""
            <div class='container' style='text-align:center;'>
                <div id="printArea" class='struk' style='margin: 0 auto; box-shadow: 0 0 10px rgba(0,0,0,0.1); border: 1px dashed #999;'>
                    <h3 style='margin:0'> KEBAB-LASAN</h3>
                    <small> Cabang Tanjung Duren</small>
                    <hr style='border-top: 1px dashed #999'>
                    <div style='text-align:left; font-size:12px'>
                        Tgl: {s['tanggal']}<br>
                        customer: {s['nama']}<br>
                        Metode: {s['metode']}
                    </div>
                    <hr style='border-top: 1px dashed #999'>
                    {items_html}
                    <hr style='border-top: 1px dashed #999'>
                    <div style='display:flex; justify-content:space-between; font-weight:bold'>
                        <span>TOTAL</span>
                        <span>Rp {total_bayar}</span>
                    </div>
                    <hr style='border-top: 1px dashed #999'>
                    <p style='font-size:11px'>Terima kasih sudah memesan!<br>Nikmati Kebab Lezat Kami.</p>
                    <p style='font-size:11px'>Metode Pembayaran: {s['metode']}</p>
                </div>
                <br>
                <button onclick='window.print()' style='width:150px; background:#3498db'> Cetak Struk</button>
                <a href='/user'><button style='width:150px; background:#95a5a6; margin-left:10px'>Pesan Lagi</button></a>
            </div>
            """
            self.html(page(h))

        elif path == "/admin/menu":
            data = conn.execute("SELECT * FROM menu").fetchall()
            h = nav("admin") + "<div class='container'><h2>Manajemen Menu</h2>"
            h += "<form method='POST' action='/add_menu'>"
            h += "<input name='n' placeholder='Nama Menu' required>"
            h += "<input name='h' type='number' placeholder='Harga' required>"
            h += "<button>Tambah Menu</button></form>"
            h += "<table><tr><th>Nama</th><th>Harga</th><th>Aksi</th></tr>"
            for d in data:
                h += f"""
                <tr>
                    <td>{d['nama']}</td>
                    <td>Rp {d['harga']}</td>
                    <td>
                        <form style='display:inline' method='POST' action='/update_menu'>
                            <input type='hidden' name='id' value='{d['id']}'>
                            <input name='n' value='{d['nama']}' required>
                            <input name='h' type='number' value='{d['harga']}' required>
                            <button type='submit'>Update</button>
                        </form>
                        <form style='display:inline' method='POST' action='/delete_menu' onsubmit="return confirm('Hapus menu ini?')">
                            <input type='hidden' name='id' value='{d['id']}'>
                            <button type='submit' style='background:#e74c3c; color:white'>Hapus</button>
                        </form>
                    </td>
                </tr>"""
            self.html(page(h + "</table></div>"))

        elif path == "/admin/pelanggan":
            data = conn.execute("SELECT * FROM pelanggan").fetchall()
            h = nav("admin") + "<div class='container'><h2>Data Pelanggan</h2>"
            h += "<table><tr><th>ID</th><th>Nama</th><th>Username</th><th>Tanggal Daftar</th><th>Aksi</th></tr>"
            for p in data:
                h += f"<tr><td>{p['id']}</td><td>{p['nama']}</td><td>{p['username']}</td><td>{p['tanggal_daftar']}</td>"
                h += f"<td><form method='POST' action='/admin/delete_pelanggan' onsubmit='return confirm(\"Hapus pelanggan ini?\")'>"
                h += f"<input type='hidden' name='id' value='{p['id']}'>"
                h += "<button type='submit' style='background:#e74c3c; color:white'>Hapus</button></form></td></tr>"
            self.html(page(h))

        elif path == "/admin/laporan":
            data = conn.execute("SELECT * FROM penjualan ORDER BY id DESC").fetchall()
            total_all = sum(d['total_bayar'] for d in data)
            query = urlparse(self.path).query
            params = parse_qs(query)
            start_date = params.get("start", [None])[0]
            end_date = params.get("end", [None])[0]
            if start_date and end_date:
                filtered_data = [d for d in data if start_date <= d['tanggal'] <= end_date]
            else:
                filtered_data = data

            h = nav("admin") + "<div class='container'><h2>Laporan Penjualan</h2>"
            # Filter tanggal
            h += "<div class='filter-box'><form method='GET' action='/admin/laporan'>"
            h += f"Tanggal mulai: <input type='date' name='start' value='{start_date if start_date else ''}'> "
            h += f"Tanggal akhir: <input type='date' name='end' value='{end_date if end_date else ''}'> "
            h += "<button type='submit'>Filter</button></form></div>"

            h += "<table><tr><th>User</th><th>Item</th><th>Size</th><th>Level</th><th>Total</th><th>Tanggal</th></tr>"
            total_filtered = 0
            for d in filtered_data:
                h += f"<tr><td>{d['nama_user']}</td><td>{d['nama_pesanan']}</td><td>{d['ukuran']}</td><td>{d['level_pedas']}</td><td>Rp {d['total_bayar']}</td><td>{d['tanggal']}</td></tr>"
                total_filtered += d['total_bayar']
            h += f"<tr style='font-weight:bold'><td colspan='4'>TOTAL (FILTER)</td><td>Rp {total_filtered}</td></tr>"
            h += f"<tr style='font-weight:bold'><td colspan='4'>TOTAL KESELURUHAN</td><td>Rp {total_all}</td></tr>"
            h += "</table></div>"
            self.html(page(h))
        elif path == "/logout":
            SESSION["user_id"] = None
            SESSION["nama"] = None
            SESSION["last_receipt"] = None
            self.redirect("/")
        else:
            self.html(page("<h2>404 Not Found</h2>"))

        conn.close()

    def do_POST(self):
        length = int(self.headers['Content-Length'])
        post_data = parse_qs(self.rfile.read(length).decode())

        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row

        if self.path == "/login":
            u = post_data.get("u", [""])[0]
            p = post_data.get("p", [""])[0]
            if u == "admin" and p == "admin":
                SESSION["user_id"] = 0
                SESSION["nama"] = "Admin"
                self.redirect("/admin/menu")
            else:
                user = conn.execute("SELECT * FROM pelanggan WHERE username=? AND password=?", (u, p)).fetchone()
                if user:
                    SESSION["user_id"] = user["id"]
                    SESSION["nama"] = user["nama"]
                    self.redirect("/user")
                else:
                    self.html(page('<div class="login-box"><h2>Login Gagal</h2><p>Periksa username/password.</p><a href="/">Kembali</a></div>'))

        elif self.path == "/reg":
            username_baru = post_data["u"][0]
            existing_user = conn.execute("SELECT * FROM pelanggan WHERE username=?", (username_baru,)).fetchone()
            if existing_user:
                self.html(page('<div class="login-box"><h2>Daftar</h2><p style="color:red;">Username sudah digunakan.</p><form method="POST" action="/reg"><input name="nama" placeholder="Nama Lengkap" required><input name="u" placeholder="Username" required><input type="password" name="p" placeholder="Password" required><button>DAFTAR</button></form><br><a href="/">Kembali ke Login</a></div>'))
            else:
                conn.execute("INSERT INTO pelanggan (nama, username, password, tanggal_daftar) VALUES (?,?,?,?)",
                    (post_data["nama"][0], username_baru, post_data["p"][0], datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                self.redirect("/")

        elif self.path == "/add_menu":
            conn.execute("INSERT INTO menu (nama, harga) VALUES (?,?)", (post_data["n"][0], int(post_data["h"][0])))
            conn.commit()
            self.redirect("/admin/menu")

        elif self.path == "/update_menu":
            menu_id = post_data.get("id", [None])[0]
            nama_baru = post_data.get("n", [""])[0]
            harga_baru = int(post_data.get("h", [0])[0])
            if menu_id:
                conn.execute("UPDATE menu SET nama=?, harga=? WHERE id=?", (nama_baru, harga_baru, menu_id))
                conn.commit()
            self.redirect("/admin/menu")

        elif self.path == "/delete_menu":
            menu_id = post_data.get("id", [None])[0]
            if menu_id:
                conn.execute("DELETE FROM menu WHERE id=?", (menu_id,))
                conn.commit()
            self.redirect("/admin/menu")

        elif self.path == "/add_cart":
            menu_id = post_data.get("id", [None])[0]
            if menu_id:
                m = conn.execute("SELECT * FROM menu WHERE id=?", (menu_id,)).fetchone()
                if m:
                    size = post_data.get("sz", ["Sedang"])[0]
                    base_price = m["harga"]
                    if size == "Kecil":
                        harga_akhir = base_price
                    elif size == "Besar":
                        harga_akhir = base_price + 4000
                    elif size == "Sedang":
                        harga_akhir = base_price + 2000
                    else:
                        harga_akhir = base_price
                    if SESSION["user_id"]:
                        conn.execute("INSERT INTO keranjang (pelanggan_id, nama, harga, qty, ukuran, level_pedas) VALUES (?,?,?,?,?,?)",
                            (SESSION["user_id"], m["nama"], harga_akhir, int(post_data.get("q", [1])[0]), size, post_data.get("pd", ["Tidak"])[0]))
                        conn.commit()
            self.redirect("/user")

        elif self.path == "/checkout":
            if not SESSION["user_id"]:
                self.redirect("/")
                return
            user = conn.execute("SELECT nama FROM pelanggan WHERE id=?", (SESSION["user_id"],)).fetchone()
            nama_u = user["nama"] if user else "Pengguna"
            tgl = datetime.now().strftime("%Y-%m-%d %H:%M")
            items = conn.execute("SELECT * FROM keranjang WHERE pelanggan_id=?", (SESSION["user_id"],)).fetchall()
            total = sum(i['qty'] * i['harga'] for i in items)
            metode_pembayaran = post_data["met"][0]
            # Simpan ke laporan dan data struk
            for i in items:
                conn.execute("INSERT INTO penjualan (pelanggan_id, nama_user, nama_pesanan, qty, ukuran, level_pedas, total_bayar, metode, tanggal) VALUES (?,?,?,?,?,?,?,?,?)",
                    (SESSION["user_id"], nama_u, i["nama"], i["qty"], i["ukuran"], i["level_pedas"], i["qty"]*i["harga"], metode_pembayaran, tgl))
            conn.commit()

            # Simpan data struk di session
            SESSION["last_receipt"] = {
                "nama": nama_u,
                "tanggal": tgl,
                "metode": metode_pembayaran,
                "items": [
                    {
                        "name": i["nama"],
                        "sz": i["ukuran"],
                        "qty": i["qty"],
                        "price": i["harga"]
                    } for i in items
                ],
                "total": total
            }

            # Hapus keranjang
            conn.execute("DELETE FROM keranjang WHERE pelanggan_id=?", (SESSION["user_id"],))
            conn.commit()
            self.redirect("/struk")

        elif self.path == "/remove_item":
            item_id = post_data.get("id", [None])[0]
            if item_id and SESSION["user_id"]:
                conn.execute("DELETE FROM keranjang WHERE id=? AND pelanggan_id=?", (item_id, SESSION["user_id"]))
                conn.commit()
            self.redirect("/keranjang")

        elif self.path == "/admin/delete_pelanggan":
            id_pelanggan = post_data.get("id", [None])[0]
            if id_pelanggan:
                conn.execute("DELETE FROM pelanggan WHERE id=?", (id_pelanggan,))
                conn.commit()
            self.redirect("/admin/pelanggan")

        else:
            self.html(page("<h2>404 Not Found</h2>"))

        conn.close()

    def html(self, c):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(c.encode())

    def redirect(self, p):
        self.send_response(302)
        self.send_header("Location", p)
        self.end_headers()

print("SERVER JALAN DI: http://0.0.0.0:8000")
port = int(os.environ.get("PORT", 8000))
HTTPServer(("0.0.0.0", port), Handler).serve_forever()
