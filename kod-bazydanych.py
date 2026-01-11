import streamlit as st
from supabase import create_client
import os

# ---------------- CONFIG ----------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Produkty & Kategorie", layout="wide")
st.title("Zarządzanie produktami i kategoriami")

# ---------------- KATEGORIE ----------------
st.header("Kategorie")

with st.form("add_category"):
    name = st.text_input("Nazwa kategorii")
    desc = st.text_area("Opis")
    submitted = st.form_submit_button("➕ Dodaj kategorię")

    if submitted and name:
        supabase.table("kategoria").insert({
            "nazwa": name,
            "opis": desc
        }).execute()
        st.success("Dodano kategorię")

categories = supabase.table("kategoria").select("*").execute().data

for cat in categories:
    col1, col2 = st.columns([4,1])
    col1.write(f"**{cat['nazwa']}** – {cat['opis']}")
    if col2.button("🗑 Usuń", key=f"del_cat_{cat['id']}"):
        supabase.table("kategoria").delete().eq("id", cat["id"]).execute()
        st.experimental_rerun()

# ---------------- PRODUKTY ----------------
st.header("🛒 Produkty")

category_map = {c["nazwa"]: c["id"] for c in categories}

with st.form("add_product"):
    pname = st.text_input("Nazwa produktu")
    price = st.number_input("Cena", min_value=0.0, step=0.01)
    quantity = st.number_input("Liczba", min_value=0, step=1)
    category = st.selectbox("Kategoria", list(category_map.keys()))
    submitted = st.form_submit_button("➕ Dodaj produkt")

    if submitted and pname:
        supabase.table("produkty1").insert({
            "nazwa": pname,
            "cena": price,
            "liczba": quantity,
            "kategoria_id": category_map[category]
        }).execute()
        st.success("Dodano produkt")

products = supabase.table("produkty1") \
    .select("id, nazwa, cena, liczba, kategoria:kategoria_id(nazwa)") \
    .execute().data

for prod in products:
    col1, col2 = st.columns([4,1])
    col1.write(
        f"**{prod['nazwa']}** | {prod['kategoria']['nazwa']} | "
        f"{prod['cena']} zł | szt.: {prod['liczba']}"
    )
    if col2.button("🗑 Usuń", key=f"del_prod_{prod['id']}"):
        supabase.table("produkty1").delete().eq("id", prod["id"]).execute()
        st.experimental_rerun()
