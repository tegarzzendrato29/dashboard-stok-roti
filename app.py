from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(
    page_title="Dashboard Produksi & Stok Bahan Baku Roti",
    page_icon="🍞",
    layout="wide",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        .stApp {
            background: radial-gradient(circle at top right, #2A1B12 0%, #16100D 52%, #100C0A 100%);
            color: #FBF5EE;
        }

        .hero-card {
            background: linear-gradient(125deg, #2D1A10 0%, #4A2814 55%, #78350F 100%);
            border: 1px solid #6B3B1E;
            padding: 1.45rem 1.8rem;
            border-radius: 18px;
            color: #FFFBEB;
            box-shadow: 0 14px 30px rgba(0, 0, 0, 0.35);
            margin-bottom: 1.15rem;
        }

        .hero-title {
            font-size: 1.75rem;
            font-weight: 700;
            margin: 0 0 0.35rem 0;
            letter-spacing: -0.02em;
        }

        .hero-sub {
            font-size: 0.92rem;
            color: #FDE68A;
            margin: 0 0 0.9rem 0;
        }

        .badge-chip {
            display: inline-block;
            background: rgba(245, 158, 11, 0.16);
            border: 1px solid rgba(251, 191, 36, 0.38);
            color: #FEF3C7;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            margin-right: 0.45rem;
            margin-bottom: 0.25rem;
        }

        .stat-card {
            background: #211712;
            border: 1px solid #3A281E;
            border-top: 4px solid #F59E0B;
            border-radius: 15px;
            padding: 1.05rem 1.2rem;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.28);
            transition: transform 0.15s ease, border-color 0.15s ease;
            min-height: 118px;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            border-color: #9A5B2C;
        }

        .stat-card.danger {
            border-top-color: #EF4444;
        }

        .stat-card.success {
            border-top-color: #10B981;
        }

        .stat-label {
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #D6B89C;
            margin-bottom: 0.35rem;
        }

        .stat-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: #FFFBEB;
            line-height: 1.2;
        }

        .stat-meta {
            font-size: 0.78rem;
            color: #A88B73;
            margin-top: 0.3rem;
        }

        .panel-card {
            background: #1D1410;
            border: 1px solid #35251C;
            border-radius: 15px;
            padding: 1.15rem 1.25rem;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.24);
            margin-bottom: 0.85rem;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.45rem;
            background-color: #1E1511;
            border: 1px solid #35251C;
            padding: 0.4rem;
            border-radius: 13px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 9px;
            padding: 0.52rem 0.95rem;
            font-weight: 600;
            color: #D6B89C;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #D97706 0%, #B45309 100%) !important;
            color: #FFFBEB !important;
            box-shadow: 0 4px 12px rgba(217, 119, 6, 0.28);
        }

        div[data-testid="stDataFrame"] {
            background: #1B120E;
            border: 1px solid #35251C;
            border-radius: 13px;
            padding: 0.2rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-title">🍞 Dashboard Produksi &amp; Stok Bahan Baku Roti</div>
        <div class="hero-sub">Kontrol stok real-time, pencatatan resep (Original, Cokelat, Cranberry), dan notifikasi Telegram multi-penerima</div>
        <span class="badge-chip">Dark Mode Active</span>
        <span class="badge-chip">Google Sheets Sync</span>
        <span class="badge-chip">Telegram Multi-ID</span>
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
        <div class="stat-card success">
            <div class="stat-label">Total Jenis Bahan</div>
            <div class="stat-value">{total_item} Bahan</div>
            <div class="stat-meta">Terdaftar di Stok Bahan Baku</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with m2:
    card_cls = "danger" if low_stock_count > 0 else "success"
    meta_txt = (
        "Perlu perhatian / restock"
        if low_stock_count > 0
        else "Semua stok di atas batas minimum"
    )
    st.markdown(
        f"""
        <div class="stat-card {card_cls}">
            <div class="stat-label">Stok Menipis / Kritis</div>
            <div class="stat-value">{low_stock_count} Item</div>
            <div class="stat-meta">{meta_txt}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">Total Resep Diproduksi</div>
            <div class="stat-value">{total_produksi} Resep</div>
            <div class="stat-meta">Akumulasi seluruh varian</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 0.7rem;'></div>", unsafe_allow_html=True)

tab_resep, tab_stok, tab_grafik, tab_riwayat = st.tabs([
    "🥖 1. Pembuatan Resep",
    "📦 2. Data Stok Bahan Baku",
    "📊 3. Grafik",
    "🧾 4. Riwayat Buat Resep & Penambahan Stock",
])

with tab_resep:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.subheader("Pembuatan Resep Produksi")
    st.caption(
        "Pilih varian roti, masukkan jumlah resep, lalu simpan untuk memotong stok otomatis."
    )

    v1, v2, v3 = st.columns(3)
    with v1:
        if st.button(
            "🥖 Original",
            type="primary"
            if st.session_state.varian_terpilih == "Original"
            else "secondary",
            width="stretch",
        ):
            st.session_state.varian_terpilih = "Original"
            st.rerun()
    with v2:
        if st.button(
            "🍫 Cokelat",
            type="primary"
            if st.session_state.varian_terpilih == "Cokelat"
            else "secondary",
            width="stretch",
        ):
            st.session_state.varian_terpilih = "Cokelat"
            st.rerun()
    with v3:
        if st.button(
            "🍒 Cranberry",
            type="primary"
            if st.session_state.varian_terpilih == "Cranberry"
            else "secondary",
            width="stretch",
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

    st.info(f"**Varian Aktif:** {varian}  •  **Kolom Acuan:** `{kolom_resep}`")

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

    cek_df = df_stok[["Nama Barang", "Stok Awal", "Stok Min", kolom_resep]].copy()
    cek_df = cek_df[cek_df[kolom_resep] > 0]
    cek_df["Kebutuhan Total"] = cek_df[kolom_resep] * jumlah_resep
    cek_df["Sisa Stok"] = cek_df["Stok Awal"] - cek_df["Kebutuhan Total"]
    cek_df["Status Simulasi"] = cek_df.apply(
        lambda r: "Kurang Stok"
        if r["Sisa Stok"] < 0
        else ("Menipis" if r["Sisa Stok"] <= r["Stok Min"] else "Aman"),
        axis=1,
    )

    st.markdown("**Simulasi Pemakaian Bahan Baku:**")
    st.dataframe(cek_df, width="stretch", hide_index=True)

    stok_kurang = cek_df[cek_df["Sisa Stok"] < 0]
    if not stok_kurang.empty:
        st.error(
            "Stok tidak mencukupi untuk bahan: "
            + ", ".join(stok_kurang["Nama Barang"].tolist())
        )
    else:
        if st.button("✅ Simpan & Potong Stok", type="primary", width="stretch"):
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

            df_update = df_stok.copy()
            df_update["Stok Awal"] = df_update.apply(
                lambda r: float(sisa_map[r["Nama Barang"]])
                if r["Nama Barang"] in sisa_map
                else float(r["Stok Awal"]),
                axis=1,
            )
            kritis = df_update[df_update["Stok Awal"] <= df_update["Stok Min"]][
                "Nama Barang"
            ].tolist()

            daftar_pakai = "\n".join(
                f"- {row['Nama Barang']}: -{row['Kebutuhan Total']} (sisa {row['Sisa Stok']})"
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
                f"Pemakaian:\n{daftar_pakai}"
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
    st.markdown("</div>", unsafe_allow_html=True)

with tab_stok:
    st.subheader("Data Stok Bahan Baku")

    col_tabel, col_tambah = st.columns([2.15, 1.05])

    with col_tabel:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        df_tampil = df_stok.copy()
        df_tampil["Status Stok"] = df_tampil.apply(
            lambda r: "Menipis / Perlu Restock"
            if r["Stok Awal"] <= r["Stok Min"]
            else "Aman",
            axis=1,
        )

        filter_status = st.selectbox(
            "Filter Status Stok",
            options=["Semua Bahan", "Menipis / Perlu Restock", "Aman"],
            key="filter_status_stok",
        )
        if filter_status != "Semua Bahan":
            df_tampil = df_tampil[df_tampil["Status Stok"] == filter_status]

        st.dataframe(df_tampil, width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_tambah:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown("### ➕ Tambah Stok Masuk")
        daftar_bahan = df_stok["Nama Barang"].tolist()
        with st.form("form_tambah_bahan"):
            bahan_dipilih = st.selectbox("Pilih Bahan Baku", options=daftar_bahan)
            jumlah_masuk = st.number_input(
                "Jumlah Stok Masuk", min_value=0.1, value=1.0, step=0.5
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
                float(jumlah_masuk),
                stok_baru,
                ket_masuk,
            ])

            pesan_tg = (
                f"📦 Penambahan Stok Masuk ({waktu_sekarang})\n"
                f"Bahan: {bahan_dipilih}\n"
                f"Masuk: +{float(jumlah_masuk)} | Stok Sekarang: {stok_baru}\n"
                f"Keterangan: {ket_masuk}"
            )
            terkirim = kirim_notifikasi_telegram(pesan_tg)

            st.cache_data.clear()
            if terkirim:
                st.success(
                    f"Stok {bahan_dipilih} bertambah +{jumlah_masuk} menjadi {stok_baru} dan notifikasi Telegram terkirim."
                )
            else:
                st.success(
                    f"Stok {bahan_dipilih} bertambah +{jumlah_masuk} menjadi {stok_baru}."
                )
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

with tab_grafik:
    st.subheader("Visualisasi Stok Bahan Baku & Produksi")

    g1, g2 = st.columns(2)

    with g1:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        if (
            not df_stok.empty
            and "Nama Barang" in df_stok.columns
            and "Stok Awal" in df_stok.columns
        ):
            df_chart = df_stok[["Nama Barang", "Stok Awal", "Stok Min"]].melt(
                id_vars="Nama Barang",
                value_vars=["Stok Awal", "Stok Min"],
                var_name="Kategori",
                value_name="Jumlah",
            )
            fig_stok = px.bar(
                df_chart,
                x="Nama Barang",
                y="Jumlah",
                color="Kategori",
                barmode="group",
                title="Stok Saat Ini vs Batas Minimum",
                color_discrete_map={
                    "Stok Awal": "#38BDF8",
                    "Stok Min": "#FB7185",
                },
            )
            fig_stok.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#160F0C",
                font=dict(color="#FBF5EE"),
                legend=dict(
                    bgcolor="rgba(27,18,14,0.85)",
                    bordercolor="#3A281E",
                    borderwidth=1,
                ),
                xaxis=dict(gridcolor="#2B1E17", linecolor="#4A3528"),
                yaxis=dict(gridcolor="#2B1E17", linecolor="#4A3528"),
            )
            st.plotly_chart(fig_stok, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

    with g2:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
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
                title="Total Resep Diproduksi per Varian",
                color_discrete_map={
                    "Original": "#34D399",
                    "Cokelat": "#FBBF24",
                    "Cranberry": "#F472B6",
                },
            )
            fig_prod.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#160F0C",
                font=dict(color="#FBF5EE"),
                legend=dict(
                    bgcolor="rgba(27,18,14,0.85)",
                    bordercolor="#3A281E",
                    borderwidth=1,
                ),
                xaxis=dict(gridcolor="#2B1E17", linecolor="#4A3528"),
                yaxis=dict(gridcolor="#2B1E17", linecolor="#4A3528"),
            )
            st.plotly_chart(fig_prod, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

with tab_riwayat:
    st.subheader("Riwayat Pembuatan Resep & Penambahan Stock")

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown("### Riwayat Pembuatan Resep")
        if df_prod.empty:
            st.info("Belum ada riwayat pembuatan resep.")
        else:
            st.dataframe(df_prod, width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r2:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown("### Riwayat Penambahan Stock")
        if df_masuk.empty:
            st.info("Belum ada riwayat penambahan stok.")
        else:
            st.dataframe(df_masuk, width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)