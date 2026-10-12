# Panduan Implementasi Langkah demi Langkah
## Setup & Eksekusi di Terminal IDE

Panduan ini dirancang agar Anda dapat mendirikan seluruh fondasi aplikasi kasir siap-integrasi ini langsung dari terminal IDE.

---

### Langkah 1: Persiapan Lingkungan & Folder Proyek

Jalankan perintah berikut di terminal Anda untuk membuat struktur direktori dan virtual environment:

```bash
# 1. Buat folder proyek dan masuk ke dalamnya
mkdir pos-autoreplenish && cd pos-autoreplenish

# 2. Buat virtual environment python
python3 -m venv venv

# 3. Aktifkan virtual environment
# Di Linux/macOS:
source venv/bin/activate
# Di Windows Command Prompt / PowerShell:
# .\venv\Scripts\activate

# 4. Buat folder untuk asset web statis
mkdir -p static
```

---

### Langkah 2: Instalasi Dependensi

Pasang pustaka backend yang ringan dan cepat:

```bash
pip install fastapi uvicorn pydantic
```

---

### Langkah 3: Membuat Berkas Database (`database.py`)

Gunakan perintah terminal atau buat berkas `database.py` dengan isi logika berikut:

```python
# database.py
import sqlite3

DB_PATH = "pos_simulation.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(force_reset=False):
    conn = get_connection()
    c = conn.cursor()
    
    if force_reset:
        c.execute("DROP TABLE IF EXISTS replenishment_logs")
        c.execute("DROP TABLE IF EXISTS transaction_items")
        c.execute("DROP TABLE IF EXISTS transactions")
        c.execute("DROP TABLE IF EXISTS products")

    # Tabel Produk
    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER NOT NULL,
        safety_stock INTEGER NOT NULL,
        reorder_point INTEGER NOT NULL,
        lead_time_days INTEGER NOT NULL
    )
    """)

    # Tabel Transaksi
    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        total_amount REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabel Item Transaksi
    c.execute("""
    CREATE TABLE IF NOT EXISTS transaction_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        unit_price REAL,
        subtotal REAL,
        FOREIGN KEY(transaction_id) REFERENCES transactions(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    """)

    # Tabel Log AutoReplenish
    c.execute("""
    CREATE TABLE IF NOT EXISTS replenishment_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        trigger_stock INTEGER,
        predicted_demand INTEGER,
        recommended_qty INTEGER,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    """)

    # Inisialisasi Data Demo
    c.execute("SELECT COUNT(*) as count FROM products")
    if c.fetchone()["count"] == 0:
        seed_data = [
            ("SKU-001", "Beras Rojolele 5kg", "Bahan Pokok", 68000, 10, 3, 5, 2),
            ("SKU-002", "Minyak Goreng 2L", "Bahan Pokok", 34000, 14, 4, 6, 1),
            ("SKU-003", "Gula Pasir 1kg", "Bahan Pokok", 17500, 8, 2, 4, 2),
            ("SKU-004", "Susu UHT Full Cream 1L", "Minuman", 21000, 6, 2, 4, 3),
            ("SKU-005", "Kopi Bubuk 200g", "Minuman", 15000, 20, 5, 8, 1)
        ]
        c.executemany("""
        INSERT INTO products (sku, name, category, price, stock, safety_stock, reorder_point, lead_time_days)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_data)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db(force_reset=True)
    print("Database siap digunakan untuk simulasi!")
```

---

### Langkah 4: Membuat Backend API & AI Hook (`app.py`)

Buat berkas `app.py`:

```python
# app.py
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
import uuid
import sqlite3
from database import get_connection, init_db

app = FastAPI(title="POS AutoReplenish Simulator")

# Inisialisasi DB saat start
init_db()

# --- Schema Pydantic ---
class CartItem(BaseModel):
    product_id: int
    quantity: int

class CheckoutRequest(BaseModel):
    items: List[CartItem]

# --- MODUL HOOK AUTOREPLENISH.AI ---
def run_autoreplenish_ai_engine(product_id: int, current_stock: int, reorder_point: int, lead_time: int, safety_stock: int):
    """
    Titik integrasi modul AutoReplenish.AI.
    Nantinya di fungsi ini Anda dapat memanggil model machine learning / pipeline AI Anda.
    """
    if current_stock <= reorder_point:
        # Simulasi formula prediksi permintaan AI:
        # (d * L) + SS - Stock
        estimated_daily_demand = 8  # Nilai estimasi dari model
        predicted_demand = estimated_daily_demand * lead_time
        suggested_order = (predicted_demand + safety_stock) - current_stock
        
        if suggested_order <= 0:
            suggested_order = 15

        conn = get_connection()
        c = conn.cursor()
        
        # Cegah duplikasi order berstatus PENDING untuk produk yang sama
        c.execute("""
            SELECT id FROM replenishment_logs 
            WHERE product_id = ? AND status = 'PENDING_APPROVAL'
        """, (product_id,))
        existing = c.fetchone()
        
        if not existing:
            c.execute("""
                INSERT INTO replenishment_logs 
                (product_id, trigger_stock, predicted_demand, recommended_qty, status)
                VALUES (?, ?, ?, ?, ?)
            """, (product_id, current_stock, predicted_demand, suggested_order, 'PENDING_APPROVAL'))
            conn.commit()
            
        conn.close()

# --- Endpoints ---
@app.get("/api/products")
def list_products():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM products ORDER BY id ASC")
    products = [dict(row) for row in c.fetchall()]
    conn.close()
    return products

@app.post("/api/checkout")
def process_checkout(req: CheckoutRequest):
    if not req.items:
        raise HTTPException(status_code=400, detail="Keranjang belanja kosong")
    
    conn = get_connection()
    c = conn.cursor()
    
    try:
        # 1. Validasi ketersediaan stok
        products_to_update = []
        total_bill = 0.0
        
        for item in req.items:
            c.execute("SELECT * FROM products WHERE id = ?", (item.product_id,))
            prod = c.fetchone()
            if not prod:
                raise HTTPException(status_code=404, detail=f"Produk ID {item.product_id} tidak ditemukan")
            
            if prod["stock"] < item.quantity:
                raise HTTPException(status_code=400, detail=f"Stok {prod['name']} tidak mencukupi (Tersisa: {prod['stock']})")
            
            subtotal = prod["price"] * item.quantity
            total_bill += subtotal
            products_to_update.append((prod, item.quantity, subtotal))
        
        # 2. Catat transaksi utama
        inv = f"INV-{uuid.uuid4().hex[:8].upper()}"
        c.execute("INSERT INTO transactions (invoice_number, total_amount) VALUES (?, ?)", (inv, total_bill))
        tx_id = c.lastrowid
        
        # 3. Potong stok dan catat rincian
        for prod, qty, subtotal in products_to_update:
            new_stock = prod["stock"] - qty
            c.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, prod["id"]))
            c.execute("""
                INSERT INTO transaction_items (transaction_id, product_id, quantity, unit_price, subtotal)
                VALUES (?, ?, ?, ?, ?)
            """, (tx_id, prod["id"], qty, prod["price"], subtotal))
            
            # 4. Trigger AutoReplenish.AI Hook
            run_autoreplenish_ai_engine(
                product_id=prod["id"],
                current_stock=new_stock,
                reorder_point=prod["reorder_point"],
                lead_time=prod["lead_time_days"],
                safety_stock=prod["safety_stock"]
            )
            
        conn.commit()
        return {"status": "SUCCESS", "invoice": inv, "total": total_bill}
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

@app.get("/api/replenish/logs")
def get_replenish_logs():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT r.id, r.product_id, p.name as product_name, r.trigger_stock, 
               r.predicted_demand, r.recommended_qty, r.status, r.created_at
        FROM replenishment_logs r
        JOIN products p ON r.product_id = p.id
        ORDER BY r.id DESC
    """)
    logs = [dict(row) for row in c.fetchall()]
    conn.close()
    return logs

@app.post("/api/replenish/approve/{log_id}")
def approve_replenishment(log_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM replenishment_logs WHERE id = ?", (log_id,))
    log = c.fetchone()
    
    if not log:
        conn.close()
        raise HTTPException(status_code=404, detail="Log tidak ditemukan")
        
    if log["status"] == "COMPLETED":
        conn.close()
        raise HTTPException(status_code=400, detail="Rekomendasi sudah pernah dieksekusi")
        
    # Tambahkan stok sesuai usulan AI
    c.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (log["recommended_qty"], log["product_id"]))
    c.execute("UPDATE replenishment_logs SET status = 'COMPLETED' WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return {"message": "Stok berhasil diperbarui"}

@app.post("/api/demo/reset")
def reset_demo():
    init_db(force_reset=True)
    return {"status": "RESET_SUCCESS"}

# Sajikan file static UI
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

---

### Langkah 5: Membuat Frontend Terpadu (`static/index.html`)

Simpan kode antarmuka berikut di dalam `static/index.html`:

```html
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Smart POS - AutoReplenish.AI Demo</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen">
  <!-- Header Bar -->
  <header class="border-b border-slate-800 bg-slate-950/80 backdrop-blur px-6 py-4 flex items-center justify-between">
    <div class="flex items-center space-x-3">
      <div class="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></div>
      <h1 class="text-xl font-bold tracking-wide">POS Sandbox <span class="text-blue-400 font-normal">× AutoReplenish.AI</span></h1>
    </div>
    <div class="flex items-center space-x-4">
      <button onclick="resetDemo()" class="px-3 py-1.5 text-xs font-semibold rounded bg-rose-600 hover:bg-rose-500 text-white transition">
        ↺ Reset Demo Data
      </button>
    </div>
  </header>

  <!-- Layout Utama Grid 2 Kolom -->
  <main class="p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
    
    <!-- Kolom Kiri: Kasir & Katalog (7 Kolom) -->
    <section class="lg:col-span-7 space-y-4">
      <div class="bg-slate-800/80 rounded-xl border border-slate-700/60 p-5 shadow-lg">
        <h2 class="text-base font-semibold text-slate-200 mb-3 flex items-center justify-between">
          <span>Katalog Produk Aktif</span>
          <span class="text-xs font-normal text-slate-400">Klik 'Jual' untuk simulasi transaksi kasir</span>
        </h2>
        
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="text-xs text-slate-400 border-b border-slate-700">
              <tr>
                <th class="py-2.5">Produk</th>
                <th class="py-2.5">Harga</th>
                <th class="py-2.5">Stok / ROP</th>
                <th class="py-2.5 text-center">Status</th>
                <th class="py-2.5 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody id="product-rows" class="divide-y divide-slate-700/50"></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Kolom Kanan: Monitoring AutoReplenish.AI (5 Kolom) -->
    <section class="lg:col-span-5 space-y-4">
      <div class="bg-slate-800/80 rounded-xl border border-slate-700/60 p-5 shadow-lg">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-base font-semibold text-slate-200 flex items-center gap-2">
            <span>Decision Log AI</span>
            <span class="bg-blue-500/20 text-blue-300 text-xs px-2 py-0.5 rounded-full border border-blue-500/30">Live Hook</span>
          </h2>
        </div>
        <p class="text-xs text-slate-400 mb-4">
          Tampilan tangkapan sinyal saat stok melewati $ROP$. Rekomendasi kuantitas restock dihitung oleh model.
        </p>

        <div id="logs-container" class="space-y-3 max-h-[550px] overflow-y-auto pr-1"></div>
      </div>
    </section>
  </main>

  <script>
    async function fetchProducts() {
      const res = await fetch('/api/products');
      const data = await res.json();
      const tbody = document.getElementById('product-rows');
      tbody.innerHTML = data.map(p => {
        const isCritical = p.stock <= p.reorder_point;
        return `
          <tr class="hover:bg-slate-700/30 transition">
            <td class="py-3">
              <div class="font-medium text-slate-200">${p.name}</div>
              <div class="text-xs text-slate-400">${p.sku} • ${p.category}</div>
            </td>
            <td class="py-3">Rp ${p.price.toLocaleString('id-ID')}</td>
            <td class="py-3">
              <span class="font-bold ${isCritical ? 'text-rose-400' : 'text-slate-200'}">${p.stock}</span>
              <span class="text-xs text-slate-500">/ ${p.reorder_point} ROP</span>
            </td>
            <td class="py-3 text-center">
              <span class="inline-block px-2 py-0.5 rounded text-xs font-medium ${
                isCritical ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
              }">
                ${isCritical ? 'Restock Triggered' : 'Aman'}
              </span>
            </td>
            <td class="py-3 text-right space-x-1">
              <button onclick="checkoutOne(${p.id}, 1)" class="px-2.5 py-1 text-xs font-medium rounded bg-indigo-600 hover:bg-indigo-500 text-white">
                Jual 1
              </button>
              <button onclick="checkoutOne(${p.id}, 3)" class="px-2.5 py-1 text-xs font-medium rounded bg-indigo-900/60 hover:bg-indigo-800 text-indigo-200 border border-indigo-700">
                -3
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }

    async function fetchLogs() {
      const res = await fetch('/api/replenish/logs');
      const logs = await res.json();
      const container = document.getElementById('logs-container');
      
      if (logs.length === 0) {
        container.innerHTML = `
          <div class="text-center py-10 text-slate-500 text-xs">
            Belum ada trigger restock. Kurangi stok produk hingga di bawah batas ROP untuk melihat aksi AI.
          </div>
        `;
        return;
      }

      container.innerHTML = logs.map(l => `
        <div class="p-3.5 rounded-lg border ${l.status === 'COMPLETED' ? 'border-slate-700 bg-slate-900/40 opacity-75' : 'border-amber-500/40 bg-amber-950/20'} flex flex-col gap-2">
          <div class="flex items-center justify-between text-xs">
            <span class="font-bold text-slate-200">${l.product_name}</span>
            <span class="text-slate-400 text-[11px]">${l.created_at.split(' ')[1] || ''}</span>
          </div>
          <div class="text-xs grid grid-cols-2 gap-2 text-slate-300">
            <div>Stok Terakhir: <span class="font-semibold text-rose-400">${l.trigger_stock} unit</span></div>
            <div>Prediksi Kebutuhan: <span class="font-semibold text-blue-400">${l.predicted_demand} unit</span></div>
          </div>
          <div class="pt-2 border-t border-slate-700/50 flex items-center justify-between text-xs">
            <span class="text-amber-300 font-medium">Usulan Order: <strong>+${l.recommended_qty} pcs</strong></span>
            ${l.status === 'PENDING_APPROVAL' ? `
              <button onclick="approveRestock(${l.id})" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded text-[11px]">
                Setujui Restock
              </button>
            ` : `
              <span class="text-emerald-400 font-semibold text-[11px]">✓ Selesai Diisi</span>
            `}
          </div>
        </div>
      `).join('');
    }

    async function checkoutOne(productId, qty) {
      await fetch('/api/checkout', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ items: [{ product_id: productId, quantity: qty }] })
      });
      syncData();
    }

    async function approveRestock(id) {
      await fetch(`/api/replenish/approve/${id}`, { method: 'POST' });
      syncData();
    }

    async function resetDemo() {
      await fetch('/api/demo/reset', { method: 'POST' });
      syncData();
    }

    function syncData() {
      fetchProducts();
      fetchLogs();
    }

    syncData();
    setInterval(fetchLogs, 4000); // Polling otomatis
  </script>
</body>
</html>
```

---

### Langkah 6: Menjalankan Server & Validasi

Jalankan perintah ini di terminal:

```bash
uvicorn app:app --reload --port 8000
```

Buka peramban di `http://127.0.0.1:8000`. Coba klik tombol `-3` pada salah satu produk beberapa kali. Anda akan melihat stok turun di bawah batas reorder, lalu panel kanan secara otomatis mengeluarkan tiket usulan pengisian stok dari AutoReplenish.AI.