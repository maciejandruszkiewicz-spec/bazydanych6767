import streamlit as st
from supabase import create_client
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# ---------- CONFIG ----------
st.set_page_config(
    page_title="Magazyn Pro v3.0",
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

# ---------- FUNKCJA GENEROWANIA PDF ----------
def generate_receipt(product_name, qty, price):
    pdf = FPDF()
    pdf.add_page()
    
    # Nagłówek
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "POTWIERDZENIE WYDANIA (PARAGON)", ln=True, align='C')
    pdf.ln(10)
    
    # Dane transakcji
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Data wystawienia: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(5)
    
    # Tabela
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(80, 10, "Produkt", 1, 0, 'C', True)
    pdf.cell(30, 10, "Ilosc", 1, 0, 'C', True)
    pdf.cell(40, 10, "Cena jedn.", 1, 0, 'C', True)
    pdf.cell(40, 10, "Suma", 1, 1, 'C', True)
    
    total = qty * price
    pdf.cell(80, 10, str(product_name), 1)
    pdf.cell(30, 10, str(qty), 1, 0, 'C')
    pdf.cell(40, 10, f"{price:.2f} zl", 1, 0, 'R')
    pdf.cell(40, 10, f"{total:.2f} zl", 1, 1, 'R')
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"RAZEM DO ZAPLATY: {total:.2f} zl", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# ---------- STYLE CSS ----------
st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
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
        st.error(f"Błąd połączenia: {e}")
        return [], []

categories, products = get_data()
cat_name_to_id = {c["nazwa"]: c["id"] for c in categories}
cat_id_to_name = {c["id"]: c["nazwa"] for c in categories}

# ---------- HEADER & METRYKI ----------
st.title("📦 Magazyn Pro + System Paragonowy")

if products:
    total_qty = sum(p['liczba'] for p in products)
    total_value = sum(p['liczba'] * p['cena'] for p in products)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Suma towarów", f"{total_qty} szt.")
    m2.metric("Wartość", f"{total_value:,.2f} zł")
    m3.metric("Status", "Aktywny", delta="Połączono")

st.divider()

# ---------- ZAKŁADKI ----------
tab1, tab2, tab3 = st.tabs(["📊 Stan Magazynu", "➕ Dodaj Towar", "🧾 Wydaj i Paragon"])

# --- TAB 1: PRZEGLĄD ---
with tab1:
    if products:
        df = pd.DataFrame(products)
        df['kategoria'] = df['kategoria_id'].map(cat_id_to_name)
        st.dataframe(df[['nazwa', 'kategoria', 'liczba', 'cena']], use_container_width=True)
        st.bar_chart(df.set_index('nazwa')['liczba'])

# --- TAB 2: DODAWANIE ---
with tab2:
    with st.form("add_form"):
        col1, col2 = st.columns(2)
        n = col1.text_input("Nazwa")
        c = col1.selectbox("Kategoria", list(cat_name_to_id.keys()))
        q = col2.number_input("Ilość", min_value=0)
        p = col2.number_input("Cena", min_value=0.0)
        if st.form_submit_button("Dodaj"):
            supabase.table("produkty1").insert({"nazwa": n, "kategoria_id": cat_name_to_id[c], "liczba": q, "cena": p}).execute()
            st.rerun()

# --- TAB 3: WYDAWANIE I PARAGON ---
with tab3:
    st.subheader("Wydawanie towaru z potwierdzeniem PDF")
    if products:
        prod_dict = {p["nazwa"]: p for p in products}
        selected_p = st.selectbox("Wybierz produkt do wydania", list(prod_dict.keys()))
        
        col_q, col_btn = st.columns([1, 2])
        amount = col_q.number_input("Ilość do wydania", min_value=1, max_value=prod_dict[selected_p]["liczba"])
        
        # Inicjalizacja stanu dla paragonu
        if "last_receipt" not in st.session_state:
            st.session_state.last_receipt = None

        if st.button("📦 Zatwierdź wydanie i przygotuj paragon", use_container_width=True):
            new_qty = prod_dict[selected_p]["liczba"] - amount
            supabase.table("produkty1").update({"liczba": new_qty}).eq("id", prod_dict[selected_p]["id"]).execute()
            
            # Generowanie PDF
            pdf_bytes = generate_receipt(selected_p, amount, prod_dict[selected_p]["cena"])
            st.session_state.last_receipt = {
                "data": pdf_bytes,
                "name": f"paragon_{selected_p}_{datetime.now().strftime('%H%M%S')}.pdf"
            }
            st.success(f"Wydano {amount} szt. {selected_p}")
            st.rerun()

        # Jeśli paragon został wygenerowany przed chwilą, pokaż przycisk pobierania
        if st.session_state.last_receipt:
            st.info("Paragon jest gotowy do pobrania:")
            st.download_button(
                label="📥 Pobierz Paragon (PDF)",
                data=st.session_state.last_receipt["data"],
                file_name=st.session_state.last_receipt["name"],
                mime="application/pdf"
            )
    else:
        st.info("Brak produktów w magazynie.")
