from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(
    page_title="Bakery Production & Raw Material Inventory System",
    page_icon="🍞",
    layout="wide",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus+Jakarta+Sans', sans-serif;
            color: #F9F3EC;
        }

        .stApp {
            background: radial-gradient(circle at top center, #261810 0%, #140E0B 58%, #0E0A08 100%);
            color: #F9F3EC;
        }

        h1, h2, h3, h4, h5, h6, p, span, div, label {
            color: #F9F3EC;
        }

        .sketch-hero {
            background: linear-gradient(180deg, #FBBF24 0%, #F59E0B 100%);
            color: #1A110B !important;
            padding: 1.15rem 1.6rem;
            border-radius: 14px;
            box-shadow: 0 12px 28px rgba(0, 0, 0, 0.38);
            margin-bottom: 1.1rem;
            text-align: center;
        }

        .sketch-hero-title {
            font-size: 1.72rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin: 0;
            color: #1A110B !important;
        }

        .sketch-hero-sub {
            font-size: 0.86rem;
            font-weight: 700;
            color: #2C180B !important;
            margin-top: 0.25rem;
        }

        .metric-box {
            background: #1B130F;
            border: 1px solid #4A3528;
            border-radius: 12px;
            padding: 1rem 1.2rem;
            box-shadow: 0 8px 18px rgba(0, 0, 0, 0.28);
            min-height: 96px;
        }

        .metric-box.alert-highlight {
            background: linear-gradient(135deg, #451A03 0%, #78350F 100%);
            border: 1px solid #FBBF24;
        }

        .metric-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.4rem;
        }

        .metric-title {
            font-size: 0.9rem;
            font-weight: 700;
            color: #FDE68A !important;
        }

        .metric-icon {
            font-size: 1.25rem;
            color: #FFFBEB !important;
        }

        .metric-num {
            font-size: 1.9rem;
            font-weight: 800;
            color: #FFFFFF !important;
            line-height: 1.15;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 1.5rem;
            background-color: #1A120E;
            border: 1px solid #35251C;
            border-radius: 10px;
            padding: 0.4rem 0.6rem;
            margin-bottom: 0.75rem;
        }

        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            border-radius: 8px;
            padding: 0.5rem 1.25rem;
            font-weight: 700;
            color: #E7D5C3 !important;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(180deg, #FBBF24 0%, #F59E0B 100%) !important;
            color: #1A110B !important;
        }

        .stTabs [aria-selected="true"] p,
        .stTabs [aria-selected="true"] span,
        .stTabs [aria-selected="true"] div {
            color: #1A110B !important;
            font-weight: 700 !important;
        }

        div[data-testid="stDataFrame"] {
            background: #150E0B;
            border: 1px solid #3B2A1F;
            border-radius: 12px;
            padding: 0.2rem;
        }

        div[data-testid="stAlert"] {
            background-color: #241913 !important;
            border: 1px solid #6B4423 !important;
            color: #FFFBEB !important;
        }

        div[data-testid="stAlert"] p,
        div[data-testid="stAlert"] span,
        div[data-testid="stAlert"] div {
            color: #FFFBEB !important;
        }

        div[data-testid="stExpander"] {
            background-color: #1B130F;
            border: 1px solid #4A3528;
            border-radius: 12px;
        }

        div[data-testid="stExpander"] summary,
        div[data-testid="stExpander"] summary p,
        div[data-testid="stExpander"] summary span {
            color: #FDE68A !important;
            font-weight: 700 !important;
        }

        input, textarea {
            color: #FFFBEB !important;
            background-color: #231812 !important;
        }

        div[data-baseweb="select"] > div {
            background-color: #231812 !important;
            color: #FFFBEB !important;
            border-color: #4A3528 !important;
        }

        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div {
            color: #FFFBEB !important;
        }

        button[kind="secondary"] {
            background-color: #241913 !important;
            color: #F9F3EC !important;
            border: 1px solid #573E2D !important;
            font-weight: 700 !important;
        }

        button[kind="secondary"]:hover {
            border-color: #FBBF24 !important;
            color: #FBBF24 !important;
        }

        button[kind="primary"] {
            background: linear-gradient(180deg, #FBBF24 0%, #F59E0B 100%) !important;
            color: #1A110B !important;
            border: none !important;
            font-weight: 800 !important;
        }

        button[kind="primary"] p,
        button[kind="primary"] span,
        button[kind="primary"] div {
            color: #1A110B !important;
            font-weight: 800 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="sketch-hero">
        <div class="sketch-hero-title">🍞 Bakery Production &amp; Raw Material Inventory System</div>
        <div class="sketch-hero-sub">Pemantauan stok bahan baku, pencatatan resep (Original, Cokelat, Cranberry), dan notifikasi Telegram multi-penerima</div>
    </div>
    """,
    unsafe_allow_html=True,
)


def kirim_notifikasi_telegram(pesan: str) -> bool:
    if "telegram" not in st.secrets:
        return False

    tg_cfg = st.secrets["telegram"]
    token = str(tg_cfg.get("bot_token", "")).strip()
    if not token:
        return False

    raw_ids = tg_cfg.get("chat_ids", [])
    if isinstance(raw_ids, (list, tuple)):
        target_ids = [str(cid).strip() for cid in raw_ids if str(cid).strip()]
    elif str(raw_ids).strip():
        target_ids = [
            x.strip() for x in str(raw_ids).split(",") if x.strip()
        ]
    else:
        target_ids = []

    single_id = str(tg_cfg.get("chat_id", "")).strip()
    if single_id and single_id not in target_ids:
        target_ids.insert(0, single_id)

    if not target_ids:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    berhasil_minimal_satu = False

    for cid in target_ids:
        try:
            resp = requests.post(
                url,
                json={"chat_id": cid, "text": pesan},
                timeout=10,
            )
            if resp.ok:
                berhasil_minimal_satu = True
        except Exception:
            continue

    return berhasil_minimal_satu


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


def highlight_status_rows(df: pd.DataFrame, status_col: str):
    def style_row(row: pd.Series):
        val = str(row.get(status_col, "")).strip().lower()
        if "menipis" in val or "kritis" in val or "kurang" in val:
            css = (
                "background-color: #FDE047; color: #1A120B; font-weight: 800;"
            )
        elif "aman" in val:
            css = (
                "background-color: #14532D; color: #F0FDF4; font-weight: 700;"
            )
        else:
            css = "background-color: #1B130F; color: #F9F3EC; font-weight: 500;"
        return [css] * len(row)

    return df.style.apply(style_row, axis=1)


@st.cache_data(ttl=30)
def load_all_data():
    sh = get_spreadsheet()

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

    ws_prod = sh.worksheet("Riwayat_Produksi")
    df_prod = pd.DataFrame(ws_prod.get_all_records())

    ws_masuk = sh.worksheet("Riwayat_Stok_Masuk")
    df_masuk = pd.DataFrame(ws_masuk.get_all_records())

    return df_stok, df_prod, df_masuk


def find_recipe_column(df: pd.DataFrame, varian: str) -> str:
    kandidat = [
        f"Kebutuhan Per 1 Resep {varian}",
        f"Kebutuhan Per 1 Resep {'Coklat' if varian == 'Cokelat' else varian}",
    ]
    for k in kandidat:
        if k in df.columns:
            return k
    for col in df.columns:
        if col.strip().startswith("Kebutuhan Per 1 Resep") and varian.lower() in col.lower():
            return col
    return kandidat[0]


if "varian_terpilih" not in st.session_state:
    st.session_state.varian_terpilih = "Original"


try:
    df_stok, df_prod, df_masuk = load_all_data()
except Exception as e:
    st.error(f"Gagal terhubung ke Google Sheets: {e}")
    st.stop()


total_item = len(df_stok)
low_stock_count = int((df_stok["Stok Awal"] <= df_stok["Stok Min"]).sum())
total_produksi = (
    int(parse_number(df_prod["Jumlah Resep"]).sum())
    if not df_prod.empty and "Jumlah Resep" in df_prod.columns
    else 0
)

m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-top">
                <span class="metric-title">Total Jenis Bahan</span>
                <span class="metric-icon">🌾</span>
            </div>
            <div class="metric-num">{total_item}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with m2:
    alert_cls = "metric-box alert-highlight" if low_stock_count > 0 else "metric-box"
    st.markdown(
        f"""
        <div class="{alert_cls}">
            <div class="metric-top">
                <span class="metric-title">Stok Menipis / Kritis</span>
                <span class="metric-icon">⚠️</span>
            </div>
            <div class="metric-num">{low_stock_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-top">
                <span class="metric-title">Total Resep Diproduksi</span>
                <span class="metric-icon">📋</span>
            </div>
            <div class="metric-num">{total_produksi}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 0.45rem;'></div>", unsafe_allow_html=True)

tab_resep, tab_stok, tab_grafik, tab_riwayat = st.tabs([
    "Pembuatan resep",
    "Data stok bahan baku",
    "Grafik",
    "Riwayat buat resep & penambahan stock",
])

with tab_resep:
    col_kiri, col_kanan = st.columns([1.0, 1.5])

    with col_kiri:
        st.subheader("Buat Resep")

        v1, v2, v3 = st.columns(3)
        with v1:
            if st.button(
                "Original",
                type="primary"
                if st.session_state.varian_terpilih == "Original"
                else "secondary",
                width="stretch",
            ):
                st.session_state.varian_terpilih = "Original"
                st.rerun()
        with v2:
            if st.button(
                "Cokelat",
                type="primary"
                if st.session_state.varian_terpilih == "Cokelat"
                else "secondary",
                width="stretch",
            ):
                st.session_state.varian_terpilih = "Cokelat"
                st.rerun()
        with v3:
            if st.button(
                "Cranberry",
                type="primary"
                if st.session_state.varian_terpilih == "Cranberry"
                else "secondary",
                width="stretch",
            ):
                st.session_state.varian_terpilih = "Cranberry"
                st.rerun()

        varian = st.session_state.varian_terpilih
        kolom_resep = find_recipe_column(df_stok, varian)

        st.info(f"**Varian Dipilih:** {varian}  •  `{kolom_resep}`")

        c_in1, c_in2 = st.columns(2)
        with c_in1:
            jumlah_resep = st.number_input(
                "Jumlah Resep", min_value=1, value=1, step=1, key="jml_resep"
            )
        with c_in2:
            ket_prod = st.text_input(
                "Keterangan (opsional)", value="-", key="ket_prod"
            )

        df_stok[kolom_resep] = parse_number(df_stok[kolom_resep])
        df_stok["Stok Awal"] = parse_number(df_stok["Stok Awal"])
        df_stok["Stok Min"] = parse_number(df_stok["Stok Min"])

        cek_df = df_stok[
            ["Nama Barang", "Stok Awal", "Stok Min", kolom_resep]
        ].copy()
        cek_df = cek_df[cek_df[kolom_resep] > 0]
        cek_df["Kebutuhan Total"] = cek_df[kolom_resep] * jumlah_resep
        cek_df["Sisa Stok"] = cek_df["Stok Awal"] - cek_df["Kebutuhan Total"]
        cek_df["Status"] = cek_df.apply(
            lambda r: "Kurang Stok"
            if r["Sisa Stok"] < 0
            else ("Menipis" if r["Sisa Stok"] <= r["Stok Min"] else "Aman"),
            axis=1,
        )

        stok_kurang = cek_df[cek_df["Sisa Stok"] < 0]
        if not stok_kurang.empty:
            st.error(
                "Stok tidak mencukupi untuk bahan: "
                + ", ".join(stok_kurang["Nama Barang"].tolist())
            )
        else:
            if st.button(
                "Simpan & Potong Stok", type="primary", width="stretch"
            ):
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
                    nama_barang = (
                        r[idx_nama].strip() if idx_nama < len(r) else ""
                    )
                    if nama_barang in sisa_map:
                        nilai_baru = float(sisa_map[nama_barang])
                        ws_stok.update_cell(
                            row_offset, idx_stok_awal + 1, nilai_baru
                        )

                waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ws_prod.append_row(
                    [waktu_sekarang, varian, int(jumlah_resep), ket_prod]
                )

                df_update = df_stok.copy()
                df_update["Stok Awal"] = df_update.apply(
                    lambda r: float(sisa_map[r["Nama Barang"]])
                    if r["Nama Barang"] in sisa_map
                    else float(r["Stok Awal"]),
                    axis=1,
                )
                kritis = df_update[
                    df_update["Stok Awal"] <= df_update["Stok Min"]
                ]["Nama Barang"].tolist()

                daftar_pakai = "\n".join(
                    f"- {row['Nama Barang']}: -{int(round(row['Kebutuhan Total']))} g (sisa {int(round(row['Sisa Stok']))} g)"
                    for _, row in cek_df.iterrows()
                )
                teks_kritis = (
                    "\n⚠️ Stok Menipis/Kritis: " + ", ".join(kritis)
                    if kritis
                    else "\n✅ Tidak ada stok kritis."
                )
                pesan_tg = (
                    f"🍞 Update Produksi Roti ({waktu_sekarang})\n"
                    f"Varian: {varian} | Jumlah: {int(jumlah_resep)} resep\n"
                    f"Keterangan: {ket_prod}\n"
                    f"Pemakaian (gram):\n{daftar_pakai}"
                    f"{teks_kritis}"
                )
                terkirim = kirim_notifikasi_telegram(pesan_tg)

                st.cache_data.clear()
                if terkirim:
                    st.success(
                        f"Produksi {varian} sebanyak {jumlah_resep} resep tercatat, stok diperbarui, dan notifikasi Telegram terkirim."
                    )
                else:
                    st.success(
                        f"Produksi {varian} sebanyak {jumlah_resep} resep berhasil dicatat dan stok diperbarui."
                    )
                st.rerun()

    with col_kanan:
        st.subheader("Daftar Kebutuhan & Sisa Stok")
        cek_ringkas = pd.DataFrame({
            "Nama Barang": cek_df["Nama Barang"],
            "Stok (g)": cek_df["Stok Awal"].round(0).astype(int),
            "Min (g)": cek_df["Stok Min"].round(0).astype(int),
            "Pakai (g)": cek_df[kolom_resep].round(0).astype(int),
            "Total (g)": cek_df["Kebutuhan Total"].round(0).astype(int),
            "Sisa (g)": cek_df["Sisa Stok"].round(0).astype(int),
            "Status": cek_df["Status"],
        })
        st.dataframe(
            highlight_status_rows(cek_ringkas, "Status"),
            width="stretch",
            hide_index=True,
        )

with tab_stok:
    col_tabel, col_tambah = st.columns([2.35, 1.0])

    with col_tabel:
        df_tampil = df_stok.copy()
        df_tampil["Status"] = df_tampil.apply(
            lambda r: "Menipis" if r["Stok Awal"] <= r["Stok Min"] else "Aman",
            axis=1,
        )

        filter_status = st.selectbox(
            "Filter Status Stok",
            options=["Semua Bahan", "Menipis", "Aman"],
            key="filter_status_stok",
        )
        if filter_status != "Semua Bahan":
            df_tampil = df_tampil[df_tampil["Status"] == filter_status]

        col_orig = find_recipe_column(df_tampil, "Original")
        col_coklat = find_recipe_column(df_tampil, "Cokelat")
        col_cranb = find_recipe_column(df_tampil, "Cranberry")

        def get_int_col(df_src: pd.DataFrame, col_name: str) -> pd.Series:
            if col_name in df_src.columns:
                return parse_number(df_src[col_name]).round(0).astype(int)
            return pd.Series([0] * len(df_src), index=df_src.index, dtype=int)

        df_ringkas_tampil = pd.DataFrame({
            "Nama Barang": df_tampil["Nama Barang"],
            "Stok (g)": get_int_col(df_tampil, "Stok Awal"),
            "Min (g)": get_int_col(df_tampil, "Stok Min"),
            "Orig (g)": get_int_col(df_tampil, col_orig),
            "Coklat (g)": get_int_col(df_tampil, col_coklat),
            "Cranb (g)": get_int_col(df_tampil, col_cranb),
            "Status": df_tampil["Status"],
        })

        st.dataframe(
            highlight_status_rows(df_ringkas_tampil, "Status"),
            width="stretch",
            hide_index=True,
        )

    with col_tambah:
        st.subheader("Tambah Stok Masuk")
        daftar_bahan = df_stok["Nama Barang"].tolist()
        with st.form("form_tambah_bahan"):
            bahan_dipilih = st.selectbox("Pilih Bahan Baku", options=daftar_bahan)
            jumlah_masuk = st.number_input(
                "Jumlah Stok Masuk (g)",
                min_value=0,
                value=1000,
                step=1000,
                format="%d",
            )
            ket_masuk = st.text_input("Keterangan (opsional)", value="Restock")
            submit_masuk = st.form_submit_button(
                "Simpan Stok Masuk", type="primary", width="stretch"
            )

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
                df_stok.loc[
                    df_stok["Nama Barang"] == bahan_dipilih, "Stok Awal"
                ].iloc[0]
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
            ws_masuk.append_row([
                waktu_sekarang,
                bahan_dipilih,
                int(jumlah_masuk),
                int(round(stok_baru)),
                ket_masuk,
            ])

            pesan_tg = (
                f"📦 Penambahan Stok Masuk ({waktu_sekarang})\n"
                f"Bahan: {bahan_dipilih}\n"
                f"Masuk: +{int(jumlah_masuk)} g | Stok Sekarang: {int(round(stok_baru))} g\n"
                f"Keterangan: {ket_masuk}"
            )
            terkirim = kirim_notifikasi_telegram(pesan_tg)

            st.cache_data.clear()
            if terkirim:
                st.success(
                    f"Stok {bahan_dipilih} bertambah +{int(jumlah_masuk)} g menjadi {int(round(stok_baru))} g dan notifikasi Telegram terkirim."
                )
            else:
                st.success(
                    f"Stok {bahan_dipilih} bertambah +{int(jumlah_masuk)} g menjadi {int(round(stok_baru))} g."
                )
            st.rerun()

        st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
        with st.expander("➕ Tambah Bahan Baku Baru", expanded=False):
            with st.form("form_bahan_baru", clear_on_submit=True):
                nama_bahan_baru = st.text_input(
                    "Nama Barang", placeholder="Contoh: Air"
                )
                b1, b2 = st.columns(2)
                with b1:
                    stok_awal_baru = st.number_input(
                        "Stok (g)", min_value=0, value=0, step=1000, format="%d"
                    )
                with b2:
                    stok_min_baru = st.number_input(
                        "Min (g)",
                        min_value=0,
                        value=1000,
                        step=1000,
                        format="%d",
                    )
                r1, r2, r3 = st.columns(3)
                with r1:
                    orig_baru = st.number_input(
                        "Orig (g)", min_value=0, value=0, step=1, format="%d"
                    )
                with r2:
                    coklat_baru = st.number_input(
                        "Coklat (g)", min_value=0, value=0, step=1, format="%d"
                    )
                with r3:
                    cranb_baru = st.number_input(
                        "Cranb (g)", min_value=0, value=0, step=1, format="%d"
                    )
                submit_bahan_baru = st.form_submit_button(
                    "Simpan Bahan Baku", type="primary", width="stretch"
                )

            if submit_bahan_baru:
                nama_bersih = nama_bahan_baru.strip()
                if not nama_bersih:
                    st.error("Nama Barang tidak boleh kosong.")
                elif nama_bersih.lower() in [
                    str(x).strip().lower()
                    for x in df_stok["Nama Barang"].tolist()
                ]:
                    st.error(f"Bahan '{nama_bersih}' sudah ada di tabel.")
                else:
                    sh = get_spreadsheet()
                    ws_stok = sh.worksheet("Stok Bahan Baku")
                    raw_stok = ws_stok.get_all_values()
                    header_idx = next(
                        i
                        for i, r in enumerate(raw_stok)
                        if "Nama Barang" in [c.strip() for c in r]
                    )
                    headers = [h.strip() for h in raw_stok[header_idx]]
                    while headers and headers[-1] == "":
                        headers.pop()

                    row_to_append = [""] * len(headers)
                    for idx_h, h_name in enumerate(headers):
                        h_low = h_name.lower()
                        if h_name == "Nama Barang":
                            row_to_append[idx_h] = nama_bersih
                        elif h_name == "Stok Awal":
                            row_to_append[idx_h] = int(stok_awal_baru)
                        elif h_name == "Stok Min":
                            row_to_append[idx_h] = int(stok_min_baru)
                        elif (
                            h_low.startswith("kebutuhan per 1 resep")
                            and "orig" in h_low
                        ):
                            row_to_append[idx_h] = int(orig_baru)
                        elif h_low.startswith("kebutuhan per 1 resep") and (
                            "coklat" in h_low or "cokelat" in h_low
                        ):
                            row_to_append[idx_h] = int(coklat_baru)
                        elif (
                            h_low.startswith("kebutuhan per 1 resep")
                            and "cranb" in h_low
                        ):
                            row_to_append[idx_h] = int(cranb_baru)

                    ws_stok.append_row(row_to_append)

                    status_baru = (
                        "Menipis"
                        if int(stok_awal_baru) <= int(stok_min_baru)
                        else "Aman"
                    )
                    pesan_tg = (
                        f"🆕 Bahan Baku Baru Ditambahkan\n"
                        f"Bahan: {nama_bersih}\n"
                        f"Stok: {int(stok_awal_baru)} g | Min: {int(stok_min_baru)} g ({status_baru})\n"
                        f"Resep (g) -> Orig: {int(orig_baru)} | Coklat: {int(coklat_baru)} | Cranb: {int(cranb_baru)}"
                    )
                    kirim_notifikasi_telegram(pesan_tg)

                    st.cache_data.clear()
                    st.success(
                        f"Bahan baku '{nama_bersih}' berhasil ditambahkan dengan status {status_baru}."
                    )
                    st.rerun()

with tab_grafik:
    st.subheader("Visualisasi Tren Stok & Produksi")

    g1, g2 = st.columns(2)

    with g1:
        if (
            not df_stok.empty
            and "Nama Barang" in df_stok.columns
            and "Stok Awal" in df_stok.columns
        ):
            df_chart = df_stok[["Nama Barang", "Stok Awal", "Stok Min"]].melt(
                id_vars="Nama Barang",
                value_vars=["Stok Awal", "Stok Min"],
                var_name="Kategori",
                value_name="Jumlah (g)",
            )
            fig_stok = px.bar(
                df_chart,
                x="Nama Barang",
                y="Jumlah (g)",
                color="Kategori",
                barmode="group",
                title="Stok Saat Ini vs Batas Minimum (gram)",
                color_discrete_map={
                    "Stok Awal": "#FBBF24",
                    "Stok Min": "#FB7185",
                },
            )
            fig_stok.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#140D0A",
                font=dict(color="#FFFBEB"),
                legend=dict(
                    bgcolor="rgba(26,18,14,0.92)",
                    bordercolor="#4A3528",
                    borderwidth=1,
                    font=dict(color="#FFFBEB"),
                ),
                xaxis=dict(
                    gridcolor="#2A1C15",
                    linecolor="#4A3528",
                    tickfont=dict(color="#FFFBEB"),
                ),
                yaxis=dict(
                    gridcolor="#2A1C15",
                    linecolor="#4A3528",
                    tickfont=dict(color="#FFFBEB"),
                ),
            )
            st.plotly_chart(fig_stok, width="stretch")

    with g2:
        if (
            not df_prod.empty
            and "Varian" in df_prod.columns
            and "Jumlah Resep" in df_prod.columns
        ):
            df_prod_chart = df_prod.copy()
            df_prod_chart["Jumlah Resep"] = parse_number(
                df_prod_chart["Jumlah Resep"]
            )
            rekap_varian = df_prod_chart.groupby("Varian", as_index=False)[
                "Jumlah Resep"
            ].sum()
            fig_prod = px.bar(
                rekap_varian,
                x="Varian",
                y="Jumlah Resep",
                color="Varian",
                title="Produksi per Varian",
                color_discrete_map={
                    "Original": "#FBBF24",
                    "Cokelat": "#F59E0B",
                    "Cranberry": "#38BDF8",
                },
            )
            fig_prod.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#140D0A",
                font=dict(color="#FFFBEB"),
                legend=dict(
                    bgcolor="rgba(26,18,14,0.92)",
                    bordercolor="#4A3528",
                    borderwidth=1,
                    font=dict(color="#FFFBEB"),
                ),
                xaxis=dict(
                    gridcolor="#2A1C15",
                    linecolor="#4A3528",
                    tickfont=dict(color="#FFFBEB"),
                ),
                yaxis=dict(
                    gridcolor="#2A1C15",
                    linecolor="#4A3528",
                    tickfont=dict(color="#FFFBEB"),
                ),
            )
            st.plotly_chart(fig_prod, width="stretch")

with tab_riwayat:
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown("### Riwayat Pembuatan Resep")
        if df_prod.empty:
            st.info("Belum ada riwayat pembuatan resep.")
        else:
            st.dataframe(df_prod, width="stretch", hide_index=True)

    with col_r2:
        st.markdown("### Riwayat Penambahan Stock")
        if df_masuk.empty:
            st.info("Belum ada riwayat penambahan stok.")
        else:
            st.dataframe(df_masuk, width="stretch", hide_index=True)