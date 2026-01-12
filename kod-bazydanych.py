import streamlit as st
from supabase import create_client
import pandas as pd

# ---------- CONFIG ----------
st.set_page_config(
    page_title="Magazyn Szefoski",
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

# ---------- STYLE CSS (Dla lepszego wyglądu) ----------
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
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 5px 5px 0px 0px;
        padding: 10px 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------- POBIERANIE DANYCH ----------
def get_data():
    try:
        categories = supabase.table("kategoria").select("*").execute().data or []
        products = supabase.table("produkty1").select("*").execute().data or []
        return categories, products
    except Exception as e:
        st.error(f"Błąd połączenia z bazą: {e}")
        return [], []

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
    m1.metric("Łączna ilość towaru", f"{total_qty} szt.")
    m2.metric("Wycena magazynu", f"{total_value:,.2f} zł")
    m3.metric("Niski stan (<5 szt.)", low_stock, delta="- Braki" if low_stock > 0 else "OK", delta_color="inverse")

st.divider()

# ---------- GŁÓWNY UKŁAD (TABS) ----------
tab1, tab2, tab3 = st.tabs(["📊 Przegląd i Wykresy", "➕ Dodawanie Nowych", "⚙️ Operacje Magazynowe"])

# --- TAB 1: PRZEGLĄD I WYKRESY ---
with tab1:
    if not products:
        st.info("Magazyn jest obecnie pusty. Dodaj pierwszy produkt w zakładce obok.")
    else:
        # Przygotowanie danych do analizy
        df = pd.DataFrame(products)
        df['kategoria'] = df['kategoria_id'].map(cat_id_to_name)
        
        col_chart, col_stat = st.columns([2, 1])
        
        with col_chart:
            st.markdown("#### 📈 Poziom zapasów (ilość)")
            # Wykres poziomy ilości produktów
            chart_data = df[['nazwa', 'liczba']].set_index('nazwa')
            st.bar_chart(chart_data, color="#3b82f6", horizontal=True)
            
        with col_stat:
            st.markdown("#### 📁 Struktura kategorii")
            cat_counts = df['kategoria'].value_counts()
            st.dataframe(cat_counts, use_container_width=True)
        
        st.divider()

        # Tabela z wyszukiwarką i paskami postępu
        st.markdown("#### 📋 Szczegółowa lista produktów")
        search = st.text_input("🔍 Szybkie szukanie produktu...", "")
        
        # Przygotowanie DF do tabeli
        display_df = df[['nazwa', 'kategoria', 'liczba', 'cena']].copy()
        display_df.columns = ['Nazwa Produktu', 'Kategoria', 'Ilość', 'Cena (zł)']
        
        filtered_df = display_df[display_df['Nazwa Produktu'].str.contains(search, case=False)]
        
        st.dataframe(
            filtered_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Ilość": st.column_config.ProgressColumn(
                    "Stan magazynowy",
                    help="Wizualizacja dostępności",
                    format="%d szt.",
                    min_value=0,
                    max_value=max(df['liczba']) if not df.empty else 100,
                ),
                "Cena (zł)": st.column_config.NumberColumn(format="%.2f zł")
            }
        )

# --- TAB 2: DODAWANIE ---
with tab2:
    col_p, col_c = st.columns(2)
    
    with col_p:
        st.markdown("### 📦 Nowy Produkt")
        with st.form("add_product", clear_on_submit=True):
            pname = st.text_input("Nazwa przedmiotu")
            pcat = st.selectbox("Kategoria", list(cat_name_to_id.keys()) if categories else ["Brak kategorii"])
            pqty = st.number_input("Ilość startowa", min_value=0, step=1)
            pprice = st.number_input("Cena jednostkowa (zł)", min_value=0.0, step=0.01)
            
            if st.form_submit_button("🚀 Zapisz w bazie") and pname and categories:
                supabase.table("produkty1").insert({
                    "nazwa": pname,
                    "kategoria_id": cat_name_to_id[pcat],
                    "liczba": pqty,
                    "cena": pprice
                }).execute()
                st.success(f"Produkt '{pname}' został dodany!")
                st.rerun()
            elif not categories:
                st.warning("Najpierw utwórz przynajmniej jedną kategorię!")

    with col_c:
        st.markdown("### 📁 Nowa Kategoria")
        with st.form("add_category", clear_on_submit=True):
            cname = st.text_input("Nazwa kategorii (np. Elektronika)")
            cdesc = st.text_area("Opis kategorii")
            
            if st.form_submit_button("📁 Utwórz") and cname:
                supabase.table("kategoria").insert({"nazwa": cname, "opis": cdesc}).execute()
                st.success("Nowa kategoria gotowa!")
                st.rerun()

# --- TAB 3: OPERACJE I USUWANIE ---
with tab3:
    col_ops, col_del = st.columns(2)

    with col_ops:
        st.subheader("🛠 Zarządzanie ilością")
        if products:
            prod_dict = {p["nazwa"]: p for p in products}
            selected_p = st.selectbox("Wybierz towar", list(prod_dict.keys()), key="op_select")
            current_qty = prod_dict[selected_p]["liczba"]
            
            st.info(f"Obecny stan: {current_qty} szt.")
            
            op_col1, op_col2 = st.columns(2)
            amount_to_change = op_col1.number_input("Ilość", min_value=1, step=1)
            action = op_col2.radio("Akcja", ["Wydaj (Zdejmij)", "Przyjmij (Dodaj)"])

            if st.button("Zastosuj zmianę", use_container_width=True):
                new_qty = current_qty - amount_to_change if action == "Wydaj (Zdejmij)" else current_qty + amount_to_change
                
                if new_qty < 0:
                    st.error("Błąd: Nie możesz wydać więcej niż masz!")
                else:
                    supabase.table("produkty1").update({"liczba": new_qty}).eq("id", prod_dict[selected_p]["id"]).execute()
                    st.toast(f"Zaktualizowano stan dla: {selected_p}")
                    st.rerun()
        else:
            st.write("Brak produktów.")

    with col_del:
        st.subheader("🗑 Usuwanie danych")
        
        with st.expander("Usuń produkt"):
            if products:
                to_delete = st.selectbox("Wybierz do usunięcia", [p["nazwa"] for p in products])
                if st.button("Potwierdzam usunięcie produktu", type="primary"):
                    supabase.table("produkty1").delete().eq("nazwa", to_delete).execute()
                    st.rerun()
        
        with st.expander("Usuń kategorię"):
            if categories:
                to_delete_c = st.selectbox("Wybierz kategorię", [c["nazwa"] for c in categories])
                c_id = cat_name_to_id[to_delete_c]
                if st.button("Usuń kategorię", type="primary"):
                    # Sprawdzenie czy kategoria jest pusta
                    has_items = supabase.table("produkty1").select("id").eq("kategoria_id", c_id).execute().data
                    if has_items:
                        st.error("Nie można usunąć! Kategoria zawiera produkty.")
                    else:
                        supabase.table("kategoria").delete().eq("id", c_id).execute()
                        st.rerun()
