import sqlite3

DB_PATH = "pos_simulation.db"

supermarket_products = [
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

conn = sqlite3.connect(DB_PATH, timeout=10)
cursor = conn.cursor()

# Bersihkan data produk dan log lama agar tabel kembali bersih untuk demo
cursor.execute("DELETE FROM products")
cursor.execute("DELETE FROM replenishment_logs")
cursor.execute("DELETE FROM transaction_items")
cursor.execute("DELETE FROM transactions")

# Masukkan data supermarket baru
cursor.executemany("""
    INSERT INTO products (sku, name, category, price, stock, safety_stock, reorder_point, lead_time_days)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", supermarket_products)

conn.commit()
conn.close()

print("Berhasil! Data produk supermarket siap digunakan di pos_simulation.db")