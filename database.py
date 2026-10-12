import sqlite3

DB_PATH = "pos_simulation.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(force_reset=False):
    conn = get_connection()
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL")
    
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
        category TEXT DEFAULT 'Bahan Pokok',
        price REAL NOT NULL,
        stock INTEGER NOT NULL,
        safety_stock INTEGER DEFAULT 3,
        reorder_point INTEGER NOT NULL,
        lead_time_days INTEGER DEFAULT 2
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
            ("SKU-005", "Kopi Bubuk 200g", "Minuman", 15000, 20, 5, 8, 1),
            ("SKU-006", "Mi Instan Kari Ayam (Dus 40)", "Makanan Instan", 118000, 7, 2, 5, 2),
            ("SKU-007", "Telur Ayam Negeri 1kg", "Bahan Pokok", 28500, 12, 3, 6, 2),
            ("SKU-008", "Sabun Cuci Piring Cair 750ml", "Kebutuhan Rumah", 13500, 6, 2, 4, 2),
            ("SKU-009", "Deterjen Bubuk Konsentrat 1.5kg", "Kebutuhan Rumah", 36000, 9, 2, 5, 2),
            ("SKU-010", "Biskuit Gandum Cokelat 300g", "Makanan Ringan", 22500, 15, 3, 6, 2),
            ("SKU-011", "Pasta Gigi Sensitif 160g", "Perawatan Diri", 24000, 8, 2, 4, 2),
            ("SKU-012", "Teh Celup Melati (Isi 25)", "Minuman", 8000, 18, 4, 8, 2)
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
