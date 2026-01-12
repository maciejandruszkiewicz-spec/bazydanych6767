import streamlit as st
from supabase import create_client
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# ---------- CONFIG ----------
st.set_page_config(
    page_title="Magazyn Pro v3.1",
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
    # Prosta funkcja do usuwania polskich znaków, aby uniknąć błędów czcionki w PDF
    def clean_text(text):
        mapowanie = {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z",
                    "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z"}
        return "".join(mapowanie.get(c, c) for c in str(text))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", 'B', 16)
    
    # Nagłówek
    pdf.cell(200, 10, clean_text("POTWIERDZENIE WYDANIA"), ln=True, align='C')
    pdf.ln(10)
    
    # Dane
    pdf.set_font("Courier", size=12)
    pdf.cell(200, 10, f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(5)
    
    # Tabela
    pdf.cell(80, 10, "Produkt", 1)
    pdf.cell(30, 10, "Ilosc", 1, 0, 'C')
    pdf.cell(40, 10, "Suma", 1, 1, 'C')
    
    total = qty * price
    pdf.cell(80, 10, clean_text(product_name), 1)
    pdf.cell(30, 10, str(qty), 1, 0, 'C')
    pdf.cell(40, 10, f"{total:.2f} zl", 1, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# ---------- POBIERANIE DANYCH ----------
def get_data():
    try:
        categories = supabase.table("kategoria").select("*").execute().data or []
        products = supabase.table("produkty1").select("*").execute().data or []
        return categories, products
    except Exception as e:
        st.error(f"Błąd: {e}")
        return [], []

categories, products = get_data()
cat_id_to_name = {c["id"]: c["nazwa"] for c in categories}
cat_name_to_id = {c["nazwa"]: c["id"] for c in categories}

# ---------- DASHBOARD ----------
st.title("📦 System Magazynowy")

if products:
    total_val = sum(p['liczba'] * p['cena'] for p in products)
    st.metric("Wartość całkowita", f"{total_val:,.2f} zł")

tab1, tab2, tab3 = st.tabs(["📊 Stan", "➕ Dodaj", "🧾 Wydaj i PDF"])

with tab1:
    if products:
        df = pd.DataFrame(products)
        df['kategoria'] = df['kategoria_id'].map(cat_id_to_name)
        st.dataframe(df[['nazwa', 'kategoria', 'liczba', 'cena']], use_container_width=True)

with tab2:
    with st.form("add"):
        c1, c2 = st.columns(2)
        nazwa = c1.text_input("Nazwa produktu")
        kat = c1.selectbox("Kategoria", list(cat_name_to_id.keys()))
        ilosc = c2.number_input("Ilość", min_value=0)
        cena = c2.number_input("Cena", min_value=0.0)
        if st.form_submit_button("Zapisz"):
            supabase.table("produkty1").insert({"nazwa": nazwa, "kategoria_id": cat_name_to_id[kat], "liczba": ilosc, "cena": cena}).execute()
            st.rerun()

with tab3:
    if products:
        p_dict = {p["nazwa"]: p for p in products}
        wybor = st.selectbox("Produkt", list(p_dict.keys()))
        ile = st.number_input("Ile wydać", min_value=1, max_value=p_dict[wybor]["liczba"])
        
        if "pdf_to_download" not in st.session_state:
            st.session_state.pdf_to_download = None

        if st.button("Wydaj i generuj PDF"):
            nowa_ilosc = p_dict[wybor]["liczba"] - ile
            supabase.table("produkty1").update({"liczba": nowa_ilosc}).eq("id", p_dict[wybor]["id"]).execute()
            
            # Generowanie
            pdf_data = generate_receipt(wybor, ile, p_dict[wybor]["cena"])
            st.session_state.pdf_to_download = {
                "content": pdf_data,
                "file": f"potwierdzenie_{wybor}.pdf"
            }
            st.success("Zaktualizowano stan bazy!")
            st.rerun()

        if st.session_state.pdf_to_download:
            st.download_button(
                "📥 Pobierz ostatni paragon",
                data=st.session_state.pdf_to_download["content"],
                file_name=st.session_state.pdf_to_download["file"],
                mime="application/pdf"
            )
