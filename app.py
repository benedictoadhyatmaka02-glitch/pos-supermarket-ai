import os
import datetime
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from supabase import create_client, Client

load_dotenv()

app = FastAPI()

SUPABASE_URL="https://dzuqsqeqmlanaruiugtt.supabase.co"
SUPABASE_KEY="sb_publishable_GM99Km95-NxBYfeCwJndyg_Z7D6Gh-u"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Kredensial SUPABASE_URL dan SUPABASE_KEY wajib diisi di file .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class CartItem(BaseModel):
    product_id: int
    quantity: int

class CheckoutRequest(BaseModel):
    items: List[CartItem]

@app.get("/api/products")
def get_products():
    res = supabase.table("products").select("id, sku, name, category, price, stock, reorder_point").order("id").execute()
    return res.data

@app.post("/api/checkout")
def process_checkout(req: CheckoutRequest):
    if not req.items:
        raise HTTPException(status_code=400, detail="Keranjang belanja kosong")

    total_amount = 0
    order_items_payload = []
    stock_updates = []

    # 1. Validasi stok via Supabase
    for item in req.items:
        res = supabase.table("products").select("id, name, price, stock").eq("id", item.product_id).single().execute()
        product = res.data

        if not product:
            raise HTTPException(status_code=404, detail=f"Produk ID {item.product_id} tidak ditemukan")
        if product["stock"] < item.quantity:
            raise HTTPException(status_code=400, detail=f"Stok {product['name']} tersisa {product['stock']}")

        subtotal = float(product["price"]) * item.quantity
        total_amount += subtotal

        stock_updates.append({"id": product["id"], "new_stock": product["stock"] - item.quantity})
        order_items_payload.append({
            "product_id": product["id"],
            "quantity": item.quantity,
            "price_at_sale": product["price"]
        })

    # 2. Catat Header Transaksi
    receipt_no = f"TRX-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    trx_res = supabase.table("transactions").insert({
        "receipt_number": receipt_no,
        "total_amount": total_amount
    }).execute()

    if not trx_res.data:
        raise HTTPException(status_code=500, detail="Gagal mencatat transaksi")

    trx_id = trx_res.data[0]["id"]

    # 3. Masukkan item transaksi
    for row in order_items_payload:
        row["transaction_id"] = trx_id
    supabase.table("transaction_items").insert(order_items_payload).execute()

    # 4. Potong Stok di Supabase
    for update in stock_updates:
        supabase.table("products").update({"stock": update["new_stock"]}).eq("id", update["id"]).execute()

    return {"status": "success", "receipt_number": receipt_no, "total_paid": total_amount}

app.mount("/", StaticFiles(directory="static", html=True), name="static")