import streamlit as st
from supabase import create_client

# ---------- CONFIG ----------
st.set_page_config(
    page_title="System Zarządzania Magazynem",
    layout="wide",
    page_icon="📦"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------- HEADER ----------
st.title("📦 System Zarządzania Magazynem")
st.divider()

# ---------- DATA ----------
categories = supabase.table("kategoria").select("*").execute().data or []
products = supabase.table("produkty1").select("*").execute().data or []

cat_name_to_id = {c["nazwa"]: c["id"] for c in categories}
cat_id_to_name = {c["id"]: c["nazwa"] for c in categories}

# ---------- STAN MAGAZYNU ----------
st.subheader("📊 Aktualny Stan Magazynowy")

if not products:
    st.info("Magazyn jest obecnie pusty.")
else:
    for p in products:
        st.write(
            f"• **{p['nazwa']}** | {cat_id_to_name.get(p['kategoria_id'], '—')} | "
            f"{p['liczba']} szt. | {p['cena']} zł"
        )

st.divider()

# ---------- LAYOUT ----------
left, mid, right = st.columns([2, 2, 2])

# ===================== LEWA KOLUMNA =====================
with left:
    st.subheader("✨ Dodawanie do katalogu")

    # --- NOWY PRODUKT ---
    st.markdown("### ➕ Nowy Produkt")
    with st.form("add_product", clear_on_submit=True):
        pname = st.text_input("Nazwa przedmiotu")
        pcat = st.selectbox("Kategoria", list(cat_name_to_id.keys()) if categories else [])
        pqty = st.number_input("Ilość startowa", min_value=0, step=1)
        pprice = st.number_input("Cena (zł)", min_value=0.0, step=0.01)

        if st.form_submit_button("Zapisz Produkt") and pname and pcat:
            supabase.table("produkty1").insert({
                "nazwa": pname,
                "kategoria_id": cat_name_to_id[pcat],
                "liczba": pqty,
                "cena": pprice
            }).execute()
            st.success("Produkt dodany")
            st.rerun()

    # --- NOWA KATEGORIA ---
    st.markdown("### 📁 Nowa Kategoria")
    with st.form("add_category", clear_on_submit=True):
        cname = st.text_input("Nazwa kategorii")
        cdesc = st.text_area("Opis kategorii")

        if st.form_submit_button("Utwórz Kategorię") and cname:
            supabase.table("kategoria").insert({
                "nazwa": cname,
                "opis": cdesc
            }).execute()
            st.success("Kategoria dodana")
            st.rerun()

# ===================== ŚRODEK =====================
with mid:
    st.subheader("🛠 Operacje magazynowe")

    st.markdown("### 📤 Wydaj Towar")

    if not products:
        st.info("Brak produktów.")
    else:
        prod_names = {p["nazwa"]: p for p in products}
        selected = st.selectbox("Produkt", list(prod_names.keys()))
        amount = st.number_input(
            "Ilość do wydania",
            min_value=0,
            max_value=prod_names[selected]["liczba"],
            step=1
        )

        if st.button("📦 Wydaj"):
            supabase.table("produkty1").update({
                "liczba": prod_names[selected]["liczba"] - amount
            }).eq("id", prod_names[selected]["id"]).execute()
            st.success("Towar wydany")
            st.rerun()

# ===================== PRAWA =====================
with right:
    st.subheader("🗑 Usuwanie")

    # --- USUWANIE PRODUKTU ---
    st.markdown("### 🗑 Usuń produkt")
    if products:
        del_prod = st.selectbox("Usuń produkt", [p["nazwa"] for p in products])
        if st.button("Usuń Produkt"):
            supabase.table("produkty1").delete().eq(
                "nazwa", del_prod
            ).execute()
            st.warning("Produkt usunięty")
            st.rerun()
    else:
        st.info("Brak")

    st.divider()

    # --- USUWANIE KATEGORII ---
    st.markdown("### 🗑 Usuń kategorię")
    if categories:
        del_cat = st.selectbox("Usuń kategorię", [c["nazwa"] for c in categories])
        cat_id = cat_name_to_id[del_cat]

        used = supabase.table("produkty1") \
            .select("id") \
            .eq("kategoria_id", cat_id) \
            .execute().data

        if st.button("Usuń Kategorię"):
            if used:
                st.error("Nie można usunąć – są przypisane produkty")
            else:
                supabase.table("kategoria").delete().eq("id", cat_id).execute()
                st.warning("Kategoria usunięta")
                st.rerun()
    else:
        st.info("Brak")
