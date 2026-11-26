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


# --- STATE UNTUK MENU TOMBOL ---
if "menu_aktif" not in st.session_state:
    st.session_state.menu_aktif = None
if "varian_terpilih" not in st.session_state:
    st.session_state.varian_terpilih = None


try:
    df_stok, df_prod, df_masuk = load_all_data()
except Exception as e:
    st.error(f"Gagal terhubung ke Google Sheets: {e}")
    st.stop()


# --- RINGKASAN METRIK ---
total_item = len(df_stok)
low_stock_count = int((df_stok["Stok Awal"] <= df_stok["Stok Min"]).sum())
total_produksi = (
    int(parse_number(df_prod["Jumlah Resep"]).sum())
    if not df_prod.empty and "Jumlah Resep" in df_prod.columns
    else 0
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Jenis Bahan", total_item)
m2.metric("Stok Menipis / Kritis", f"{low_stock_count} Item")
m3.metric("Total Resep Diproduksi", total_produksi)
with m4:
    st.write("")
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# --- TOMBOL AKSI UTAMA ---
act1, act2 = st.columns(2)
with act1:
    if st.button("Buat Resep", type="primary", use_container_width=True):
        st.session_state.menu_aktif = "buat_resep"
with act2:
    if st.button("Tambah Bahan", use_container_width=True):
        st.session_state.menu_aktif = "tambah_bahan"


# --- ALUR BUAT RESEP ---
if st.session_state.menu_aktif == "buat_resep":
    st.subheader("Buat Resep Produksi")
    v1, v2, v3 = st.columns(3)
    with v1:
        if st.button("Original", use_container_width=True):
            st.session_state.varian_terpilih = "Original"
    with v2:
        if st.button("Cokelat", use_container_width=True):
            st.session_state.varian_terpilih = "Cokelat"
    with v3:
        if st.button("Cranberry", use_container_width=True):
            st.session_state.varian_terpilih = "Cranberry"

    if st.session_state.varian_terpilih:
        varian = st.session_state.varian_terpilih
        kandidat_kolom = [
            f"Kebutuhan Per 1 Resep {varian}",
            f"Kebutuhan Per 1 Resep {'Coklat' if varian == 'Cokelat' else varian}",
        ]
        kolom_resep = next(
            (k for k in kandidat_kolom if k in df_stok.columns),
            kandidat_kolom[0],
        )

        st.markdown(f"**Varian Dipilih:** {varian} (`{kolom_resep}`)")

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

        cek_df = df_stok[["Nama Barang", "Stok Awal", "Stok Min", kolom_resep]].copy()
        cek_df = cek_df[cek_df[kolom_resep] > 0]
        cek_df["Kebutuhan Total"] = cek_df[kolom_resep] * jumlah_resep
        cek_df["Sisa Stok"] = cek_df["Stok Awal"] - cek_df["Kebutuhan Total"]

        st.dataframe(cek_df, use_container_width=True, hide_index=True)

        stok_kurang = cek_df[cek_df["Sisa Stok"] < 0]
        if not stok_kurang.empty:
            st.error(
                "Stok tidak mencukupi untuk bahan: "
                + ", ".join(stok_kurang["Nama Barang"].tolist())
            )
        else:
            if st.button("Simpan & Potong Stok", type="primary"):
                sh = get_spreadsheet()
                ws_stok = sh.worksheet("Stok Bahan Baku")
                ws_prod = sh.worksheet("Riwayat_Produksi")

                raw_stok = ws_stok.get_all_values()
                header_idx = next(
                    i
                    for i, r in enumerate(raw_stok)
                    if "Nama Barang" in [c.strip() for c in r]
                )
                headers = [h.strip() for h in raw_stok[header_idx]]
                idx_nama = headers.index("Nama Barang")
                idx_stok_awal = headers.index("Stok Awal")

                sisa_map = dict(zip(cek_df["Nama Barang"], cek_df["Sisa Stok"]))

                for row_offset, r in enumerate(
                    raw_stok[header_idx + 1 :], start=header_idx + 2
                ):
                    nama_barang = r[idx_nama].strip() if idx_nama < len(r) else ""
                    if nama_barang in sisa_map:
                        nilai_baru = float(sisa_map[nama_barang])
                        ws_stok.update_cell(row_offset, idx_stok_awal + 1, nilai_baru)

                waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ws_prod.append_row(
                    [waktu_sekarang, varian, int(jumlah_resep), ket_prod]
                )

                st.cache_data.clear()
                st.success(
                    f"Produksi {varian} sebanyak {jumlah_resep} resep berhasil dicatat dan stok diperbarui."
                )
                st.rerun()


# --- ALUR TAMBAH BAHAN ---
elif st.session_state.menu_aktif == "tambah_bahan":
    st.subheader("Tambah Stok Bahan Baku")
    daftar_bahan = df_stok["Nama Barang"].tolist()
    with st.form("form_tambah_bahan"):
        bahan_dipilih = st.selectbox("Pilih Bahan Baku", options=daftar_bahan)
        jumlah_masuk = st.number_input(
            "Jumlah Stok Masuk", min_value=0.1, value=1.0, step=0.5
        )
        ket_masuk = st.text_input("Keterangan (opsional)", value="Restock")
        submit_masuk = st.form_submit_button("Simpan Stok Masuk", type="primary")

    if submit_masuk:
        sh = get_spreadsheet()
        ws_stok = sh.worksheet("Stok Bahan Baku")
        ws_masuk = sh.worksheet("Riwayat_Stok_Masuk")

        raw_stok = ws_stok.get_all_values()
        header_idx = next(
            i
            for i, r in enumerate(raw_stok)
            if "Nama Barang" in [c.strip() for c in r]
        )
        headers = [h.strip() for h in raw_stok[header_idx]]
        idx_nama = headers.index("Nama Barang")
        idx_stok_awal = headers.index("Stok Awal")

        stok_lama = float(
            df_stok.loc[df_stok["Nama Barang"] == bahan_dipilih, "Stok Awal"].iloc[0]
        )
        stok_baru = stok_lama + float(jumlah_masuk)

        for row_offset, r in enumerate(
            raw_stok[header_idx + 1 :], start=header_idx + 2
        ):
            nama_barang = r[idx_nama].strip() if idx_nama < len(r) else ""
            if nama_barang == bahan_dipilih:
                ws_stok.update_cell(row_offset, idx_stok_awal + 1, stok_baru)
                break

        waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws_masuk.append_row(
            [waktu_sekarang, bahan_dipilih, float(jumlah_masuk), stok_baru, ket_masuk]
        )

        st.cache_data.clear()
        st.success(
            f"Stok {bahan_dipilih} bertambah +{jumlah_masuk} menjadi {stok_baru}."
        )
        st.rerun()


# --- VISUALISASI & TABEL DATA ---
st.divider()
st.subheader("Data Stok Bahan Baku")
st.dataframe(df_stok, use_container_width=True, hide_index=True)

if (
    not df_stok.empty
    and "Nama Barang" in df_stok.columns
    and "Stok Awal" in df_stok.columns
):
    fig = px.bar(
        df_stok,
        x="Nama Barang",
        y="Stok Awal",
        title="Grafik Stok Awal Bahan Baku",
    )
    st.plotly_chart(fig, use_container_width=True)

tab1, tab2 = st.tabs(["Riwayat Produksi", "Riwayat Stok Masuk"])
with tab1:
    st.dataframe(df_prod, use_container_width=True, hide_index=True)
with tab2:
    st.dataframe(df_masuk, use_container_width=True, hide_index=True)