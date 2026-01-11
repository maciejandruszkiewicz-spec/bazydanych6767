import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Magazyn", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

st.title("📦 Magazyn – zarządzanie produktami")

st.header("📁 Kategorie")

with st.form("add_category", clear_on_submit=True):
    cname = st.text_input("Nazwa kategorii")
    cdesc = st.text_area("Opis")
    if st.form_submit_button("➕ Dodaj kategorię") and cname:
        supabase.table("kategoria").insert({
            "nazwa": cname,
            "opis": cdesc
        }).execute()
        st.success("Dodano kategorię")

categories = supabase.table("kategoria").select("*").execute().data or []

if not categories:
    st.info("Dodaj najpierw kategorię")
    st.stop()

cat_name_to_id = {c["nazwa"]: c["id"] for c in categories}

for c in categories:
    col1, col2 = st.columns([5,1])
    col1.write(f"**{c['nazwa']}** — {c['opis']}")
    if col2.button("🗑 Usuń kategorię", key=f"del_cat_{c['id']}"):
        supabase.table("kategoria").delete().eq("id", c["id"]).execute()
        st.experimental_rerun()

st.header("🛒 Produkty")

with st.form("add_product", clear_on_submit=True):
    name = st.text_input("Nazwa produktu")
    price = st.number_input("Cena", min_value=0.0, step=0.01)
    qty = st.number_input("Stan początkowy", min_value=0, step=1)
    cat = st.selectbox("Kategoria", list(cat_name_to_id.keys()))

    if st.form_submit_button("➕ Dodaj produkt") and name:
        supabase.table("produkty1").insert({
            "nazwa": name,
            "cena": price,
            "liczba": qty,
            "kategoria_id": cat_name_to_id[cat]
        }).execute()
        st.success("Dodano produkt")

products = supabase.table("produkty1") \
    .select("id,nazwa,cena,liczba,kategoria_id") \
    .order("id") \
    .execute().data or []

st.divider()

for p in products:
    with st.expander(f"📦 {p['nazwa']} | stan: {p['liczba']}"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("✏️ Edycja")
            new_name = st.text_input("Nazwa", p["nazwa"], key=f"name_{p['id']}")
            new_price = st.number_input(
                "Cena", value=float(p["cena"]), step=0.01, key=f"price_{p['id']}"
            )
            new_qty = st.number_input(
                "Stan", value=int(p["liczba"]), step=1, key=f"qty_{p['id']}"
            )
            new_cat = st.selectbox(
                "Kategoria",
                list(cat_name_to_id.keys()),
                index=list(cat_name_to_id.values()).index(p["kategoria_id"]),
                key=f"cat_{p['id']}"
            )

            if st.button("💾 Zapisz zmiany", key=f"save_{p['id']}"):
                supabase.table("produkty1").update({
                    "nazwa": new_name,
                    "cena": new_price,
                    "liczba": new_qty,
                    "kategoria_id": cat_name_to_id[new_cat]
                }).eq("id", p["id"]).execute()
                st.success("Zapisano zmiany")
                st.experimental_rerun()

        with col2:
            st.subheader("📤 Wydanie towaru")
            wydaj = st.number_input(
                "Ilość do wydania",
                min_value=0,
                max_value=int(p["liczba"]),
                step=1,
                key=f"wydaj_{p['id']}"
            )

            if st.button("📉 Wydaj", key=f"out_{p['id']}") and wydaj > 0:
                supabase.table("produkty1").update({
                    "liczba": p["liczba"] - wydaj
                }).eq("id", p["id"]).execute()
                st.success("Towar wydany")
                st.experimental_rerun()

        with col3:
            st.subheader("🗑 Usuwanie")
            confirm = st.checkbox(
                "Potwierdzam usunięcie",
                key=f"confirm_{p['id']}"
            )

            if st.button("❌ Usuń produkt", key=f"delete_{p['id']}"):
                if confirm:
                    supabase.table("produkty1").delete().eq("id", p["id"]).execute()
                    st.warning("Produkt usunięty")
                    st.experimental_rerun()
                else:
                    st.error("Musisz zaznaczyć potwierdzenie")
