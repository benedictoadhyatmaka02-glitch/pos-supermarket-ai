import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL atau SUPABASE_KEY belum terisi dengan benar di file .env!")

supabase: Client = create_client(url, key)

supermarket_products = [
    {"sku": "SKU-001", "name": "Beras Rojolele 5kg", "category": "Bahan Pokok", "price": 68000, "stock": 10, "reorder_point": 5},
    {"sku": "SKU-002", "name": "Minyak Goreng 2L", "category": "Bahan Pokok", "price": 34000, "stock": 14, "reorder_point": 6},
    {"sku": "SKU-003", "name": "Gula Pasir 1kg", "category": "Bahan Pokok", "price": 17500, "stock": 8, "reorder_point": 4},
    {"sku": "SKU-004", "name": "Susu UHT Full Cream 1L", "category": "Minuman", "price": 21000, "stock": 6, "reorder_point": 4},
    {"sku": "SKU-005", "name": "Kopi Bubuk 200g", "category": "Minuman", "price": 15000, "stock": 20, "reorder_point": 8},
    {"sku": "SKU-006", "name": "Mi Instan Kari Ayam (Dus 40)", "category": "Makanan Instan", "price": 118000, "stock": 7, "reorder_point": 5},
    {"sku": "SKU-007", "name": "Telur Ayam Negeri 1kg", "category": "Bahan Pokok", "price": 28500, "stock": 12, "reorder_point": 6},
    {"sku": "SKU-008", "name": "Sabun Cuci Piring Cair 750ml", "category": "Kebutuhan Rumah", "price": 13500, "stock": 6, "reorder_point": 4},
    {"sku": "SKU-009", "name": "Deterjen Bubuk Konsentrat 1.5kg", "category": "Kebutuhan Rumah", "price": 36000, "stock": 9, "reorder_point": 5},
    {"sku": "SKU-010", "name": "Biskuit Gandum Cokelat 300g", "category": "Makanan Ringan", "price": 22500, "stock": 15, "reorder_point": 6},
    {"sku": "SKU-011", "name": "Pasta Gigi Sensitif 160g", "category": "Perawatan Diri", "price": 24000, "stock": 8, "reorder_point": 4},
    {"sku": "SKU-012", "name": "Teh Celup Melati (Isi 25)", "category": "Minuman", "price": 8000, "stock": 18, "reorder_point": 8}
]

# Masukkan 12 item produk ke tabel Supabase
response = supabase.table("products").upsert(supermarket_products, on_conflict="sku").execute()
print("Berhasil memasukkan 12 produk supermarket ke database Supabase!")