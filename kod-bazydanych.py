import streamlit as st
from supabase import create_client

# ---------- CONFIG ----------
st.set_page_config(page_title="Supabase CRUD", layout="wide")

if "SUPABASE_URL" not in st.secrets or "SUPABASE_ANON_KEY" not in st.secrets:
    st.error("❌ Brakuje SUPABASE_URL lub SUPABASE_ANON_KEY w secrets")
    st.stop()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

st.title("📦 Produkty i Kategorie (Supabase + Streamlit)")

# ---------- KATEGORIE ----------
st.header("📁 Kategorie")

with st.form("add_category", clear_on_submit=True):
    cat_name = st.text_input("Nazwa kategorii")
    cat_desc = st.text_area("Opis")
    if st.form_submit_button("➕ Dodaj kategorię") and cat_name:
        supabase.table("kategoria").insert({
            "nazwa": cat_name,
            "opis": cat_desc
        }).execute()
        st.success("Dodano kategorię")

categories = supabase.table("kategoria").select("*").execute().data or []

for cat in categories:
    col1, col2 = st.columns([5,1])
    col1.write(f"**{cat['nazwa']}** — {cat['opis']}")
    if col2.button("🗑 Usuń", key=f"del_cat_{cat['id']}"):
        supabase.table("kategoria").delete().eq("id", cat["id"]).execute()
        st.experimental_rerun()

# ---------- PRODUKTY ----------
st.header("🛒 Produkty")

if not categories:
    st.info("Najpierw dodaj kategorię")
    st.stop()

category_map = {c["nazwa"]: c["id"] for c in categories}

with st.form("add_product", clear_on_submit=True):
    name = st.text_input("Nazwa produktu")
    price = st.number_input("Cena", min_value=0.0, step=0.01)
    quantity = st.number_input("Liczba", min_value=0, step=1)
    category = st.selectbox("Kategoria", list(category_map.keys()))

    if st.form_submit_button("➕ Dodaj produkt") and name:
        supabase.table("produkty1").insert({
            "nazwa": name,
            "cena": price,
            "liczba": quantity,
            "kategoria_id": category_map[category]
        }).execute()
        st.success("Dodano produkt")

products = supabase.table("produkty1") \
    .select("id,nazwa,cena,liczba,kategoria:kategoria_id(nazwa)") \
    .execute().data or []

for p in products:
    col1, col2 = st.columns([5,1])
    col1.write(
        f"**{p['nazwa']}** | {p['kategoria']['nazwa']} | "
        f"{p['cena']} zł | szt: {p['liczba']}"
    )
    if col2.button("🗑 Usuń", key=f"del_prod_{p['id']}"):
        supabase.table("produkty1").delete().eq("id", p["id"]).execute()
        st.experimental_rerun()

