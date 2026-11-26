from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Dashboard Produksi & Stok Bahan Baku Roti",
    layout="wide",
)

st.title("Dashboard Produksi & Stok Bahan Baku Roti")


@st.cache_resource
def get_gspread_client():
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError(
            "Konfigurasi [gcp_service_account] tidak ditemukan di .streamlit/secrets.toml."
        )
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=scopes,
    )
    return gspread.authorize(creds)


def get_spreadsheet():
    if "sheet_url" not in st.secrets or not str(st.secrets["sheet_url"]).strip():
        raise RuntimeError(
            "Key 'sheet_url' tidak ditemukan di .streamlit/secrets.toml."
        )
    client = get_gspread_client()
    return client.open_by_url(str(st.secrets["sheet_url"]).strip())


def parse_number(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)


@st.cache_data(ttl=30)
def load_all_data():
    sh = get_spreadsheet()

    # Sheet 1: Stok Bahan Baku (Deteksi baris header "Nama Barang" secara otomatis)
    ws_stok = sh.worksheet("Stok Bahan Baku")
    raw_stok = ws_stok.get_all_values()

    header_idx = None
    for i, r in enumerate(raw_stok):
        cleaned_cells = [c.strip() for c in r]
        if "Nama Barang" in cleaned_cells:
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(
            "Kolom 'Nama Barang' tidak ditemukan pada sheet 'Stok Bahan Baku'."
        )

    raw_headers = [h.strip() for h in raw_stok[header_idx]]
    while raw_headers and raw_headers[-1] == "":
        raw_headers.pop()

    num_cols_data = len(raw_headers)
    rows_stok = []
    for r in raw_stok[header_idx + 1 :]:
        padded = (r + [""] * num_cols_data)[:num_cols_data]
        if padded[0].strip() != "":
            rows_stok.append(padded)

    df_stok = pd.DataFrame(rows_stok, columns=raw_headers)

    resep_cols = [
        col
        for col in df_stok.columns
        if col.strip().startswith("Kebutuhan Per 1 Resep")
    ]
    num_cols = ["Stok Awal", "Stok Min"] + resep_cols

    for col in num_cols:
        if col in df_stok.columns:
            df_stok[col] = parse_number(df_stok[col])

    # Sheet 2: Riwayat_Produksi
    ws_prod = sh.worksheet("Riwayat_Produksi")
    df_prod = pd.DataFrame(ws_prod.get_all_records())

    # Sheet 3: Riwayat_Stok_Masuk
    ws_masuk = sh.worksheet("Riwayat_Stok_Masuk")
    df_masuk = pd.DataFrame(ws_masuk.get_all_records())

    return df_stok, df_prod, df_masuk


# --- STATE UNTUK PILIHAN VARIAN ---
if "varian_terpilih" not in st.session_state:
    st.session_state.varian_terpilih = "Original"


try:
    df_stok, df_prod, df_masuk = load_all_data()
except Exception as e:
    st.error(f"Gagal terhubung ke Google Sheets: {e}")
    st.stop()


# --- RINGKASAN METRIK ATAS ---
total_item = len(df_stok)
low_stock_count = int((df_stok["Stok Awal"] <= df_stok["Stok Min"]).sum())
total_produksi = (
    int(parse_number(df_prod["Jumlah Resep"]).sum())
    if not df_prod.empty and "Jumlah Resep" in df_prod.columns
    else 0
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Jenis Bahan", f"{total_item} Bahan")
m2.metric("Stok Menipis / Kritis", f"{low_stock_count} Item")
m3.metric("Total Resep Diproduksi", f"{total_produksi} Resep")
with m4:
    st.write("")
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# --- NAVIGASI 4 TAB UTAMA ---
tab_resep, tab_stok, tab_grafik, tab_riwayat = st.tabs([
    "1. Pembuatan Resep",
    "2. Data Stok Bahan Baku",
    "3. Grafik",
    "4. Riwayat Buat Resep & Penambahan Stock",
])


# =========================================================
# TAB 1: PEMBUATAN RESEP
# =========================================================
with tab_resep:
    st.subheader("Pembuatan Resep Produksi")
    st.caption("Pilih varian roti, masukkan jumlah resep, lalu simpan untuk memotong stok otomatis.")

    v1, v2, v3 = st.columns(3)
    with v1:
        if st.button(
            "Original",
            type="primary" if st.session_state.varian_terpilih == "Original" else "secondary",
            use_container_width=True,
        ):
            st.session_state.varian_terpilih = "Original"
            st.rerun()
    with v2:
        if st.button(
            "Cokelat",
            type="primary" if st.session_state.varian_terpilih == "Cokelat" else "secondary",
            use_container_width=True,
        ):
            st.session_state.varian_terpilih = "Cokelat"
            st.rerun()
    with v3:
        if st.button(
            "Cranberry",
            type="primary" if st.session_state.varian_terpilih == "Cranberry" else "secondary",
            use_container_width=True,
        ):
            st.session_state.varian_terpilih = "Cranberry"
            st.rerun()

    varian = st.session_state.varian_terpilih
    kandidat_kolom = [
        f"Kebutuhan Per 1 Resep {varian}",
        f"Kebutuhan Per 1 Resep {'Coklat' if varian == 'Cokelat' else varian}",
    ]
    kolom_resep = next(
        (k for k in kandidat_kolom if k in df_stok.columns),
        kandidat_kolom[0],
    )

    st.info(f"**Varian Dipilih:** {varian} (Menggunakan kolom: `{kolom_resep}`)")

    c_in1, c_in2 = st.columns(2)
    with c_in1:
        jumlah_resep = st.number_input(
            "Jumlah Resep", min_value=1, value=1, step=1, key="jml_resep"
        )
    with c_in2:
        ket_prod = st.text_input(
            "Keterangan (opsional)", value="-", key="ket_prod"
        )

    # Hitung rincian pemotongan stok
    df_stok[kolom_resep] = parse_number(df_stok[kolom_resep])
    df_stok["Stok Awal"] = parse_number(df_stok["Stok Awal"])