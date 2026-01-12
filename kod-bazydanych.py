import streamlit as st
from supabase import create_client
import pandas as pd

# ---------- CONFIG ----------
st.set_page_config(
    page_title="Magazyn Pro v2",
    layout="wide",
    page_icon="📦"
)

# Inicjalizacja połączenia z Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

supabase = init_connection()

# ---------- STYLE CSS ----------
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# ---------- POBIERANIE DANYCH ----------
def get_data():
    categories = supabase.table("kategoria").select("*").execute().data or []
    products = supabase.table("produkty1").select("*").execute().data or []
    return categories, products

categories, products = get_data()

cat_name_to_id = {c["nazwa"]: c["id"] for c in categories}
cat_id_to_name = {c["id"]: c["nazwa"] for c in categories}

# ---------- HEADER & METRYKI ----------
st.title("📦 System Zarządzania Magazynem")

if products:
    total_qty = sum(p['liczba'] for p in products)
    total_value = sum(p['liczba'] * p['cena'] for p in products)
    low_stock = len([p for p in products if p['liczba'] < 5])

    m1, m2, m3 = st.columns(3)
    m1.metric("Suma produktów", f"{total_qty} szt.")
    m2.metric("Wartość magazynu", f"{total_value:,.2f} zł")
    m3.metric("Niski stan (<5)", low_stock, delta="- Braki" if low_stock > 0 else "OK", delta_color="inverse")

st.divider()

# ---------- GŁÓWNY UKŁAD (TABS) ----------
tab1, tab2, tab3 = st.tabs(["📊 Przegląd Magazynu", "➕ Dodawanie", "⚙️ Operacje i Usuwanie"])

# --- TAB 1: PRZEGLĄD ---
with tab1:
    st.subheader("Aktualne stany magazynowe")
    if not products:
        st.info("Magazyn jest pusty.")
    else:
        # Przygotowanie DataFrame do wyświetlenia
        df = pd.DataFrame(products)
        df['kategoria'] = df['kategoria_id'].map(cat_id_to_name)
        df = df[['nazwa', 'kategoria', 'liczba', 'cena']]
        df.columns = ['Nazwa Produktu', 'Kategoria', 'Ilość', 'Cena (zł)']
        
        # Wyszukiwarka i tabela
        search = st.text_input("🔍 Szukaj produktu...", "")
        filtered_df = df[df['Nazwa Produktu'].str.contains(search, case=False)]
        
        st.dataframe(
            filtered_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Ilość": st.column_config.NumberColumn(format="%d szt."),
                "Cena (zł)": st.column_config.NumberColumn(format="%.2f zł")
            }
        )

# --- TAB 2: DODAWANIE ---
with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("➕ Dodaj nowy produkt", expanded=True):
            with st.form("add_product", clear_on_submit=True):
                pname = st.text_input("Nazwa przedmiotu")
                pcat = st.selectbox("Kategoria", list(cat_name_to_id.keys()))
                pqty = st.number_input("Ilość startowa", min_value=0, step=1)
                pprice = st.number_input("Cena (zł)", min_value=0.0, step=0.01)
                
                if st.form_submit_button("Zapisz Produkt") and pname:
                    supabase.table("produkty1").insert({
                        "nazwa": pname,
                        "kategoria_id": cat_name_to_id[pcat],
                        "liczba": pqty,
                        "cena": pprice
                    }).execute()
                    st.success(f"Dodano: {pname}")
                    st.rerun()

    with col2:
        with st.expander("📁 Utwórz nową kategorię"):
            with st.form("add_category", clear_on_submit=True):
                cname = st.text_input("Nazwa kategorii")
                cdesc = st.text_area("Opis (opcjonalnie)")
                
                if st.form_submit_button("Utwórz Kategorię") and cname:
                    supabase.table("kategoria").insert({"nazwa": cname, "opis": cdesc}).execute()
                    st.success("Kategoria utworzona")
                    st.rerun()

# --- TAB 3: OPERACJE I USUWANIE ---
with tab3:
    col_op, col_del = st.columns(2)

    with col_op:
        st.markdown("### 🛠 Operacje na stanie")
        if products:
            prod_names = {p["nazwa"]: p for p in products}
            selected = st.selectbox("Wybierz produkt do wydania", list(prod_names.keys()))
            max_val = prod_names[selected]["liczba"]
            
            amount = st.number_input("Ilość do wydania", min_value=0, max_value=max_val, step=1)
            
            if st.button("📦 Potwierdź wydanie towaru", use_container_width=True):
                supabase.table("produkty1").update({
                    "liczba": max_val - amount
                }).eq("id", prod_names[selected]["id"]).execute()
                st.toast(f"Wydano {amount} szt. {selected}")
                st.rerun()
        else:
            st.info("Brak produktów do edycji.")

    with col_del:
        st.markdown("### 🗑 Usuwanie")
        
        # Usuwanie produktu
        with st.expander("Usuń produkt"):
            if products:
                del_p = st.selectbox("Produkt do usunięcia", [p["nazwa"] for p in products], key="del_p")
                if st.button("Usuń bezpowrotnie", type="primary"):
                    supabase.table("produkty1").delete().eq("nazwa", del_p).execute()
                    st.rerun()
            else: st.write("Brak danych")

        # Usuwanie kategorii
        with st.expander("Usuń kategorię"):
            if categories:
                del_c = st.selectbox("Kategoria do usunięcia", [c["nazwa"] for c in categories], key="del_c")
                c_id = cat_name_to_id[del_c]
                
                if st.button("Usuń kategorię"):
                    # Sprawdź czy pusta
                    used = supabase.table("produkty1").select("id").eq("kategoria_id", c_id).execute().data
                    if used:
                        st.error("Kategoria zawiera produkty!")
                    else:
                        supabase.table("kategoria").delete().eq("id", c_id).execute()
                        st.rerun()
