from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(
    page_title="Dashboard Produksi & Stok Bahan Baku Roti",
    layout="wide",
)

st.title("Dashboard Produksi & Stok Bahan Baku Roti")


def kirim_notifikasi_telegram(pesan: str) -> bool:
    if "telegram" not in st.secrets:
        return False
    token = str(st.secrets["telegram"].get("bot_token", "")).strip()
    chat_id = str(st.secrets["telegram"].get("chat_id", "")).strip()
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": pesan},
            timeout=10,
        )
        return resp.ok
    except Exception:
        return False


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

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Jenis Bahan", f"{total_item} Bahan")
m2.metric("Stok Menipis / Kritis", f"{low_stock_count} Item")
m3.metric("Total Resep Diproduksi", f"{total_produksi} Resep")
with m4:
    st.write("")
    if st.button("Refresh Data", width="stretch"):
        st.cache_data.clear()
        st.rerun()

st.divider()

tab_resep, tab_stok, tab_grafik, tab_riwayat = st.tabs([
    "1. Pembuatan Resep",
    "2. Data Stok Bahan Baku",
    "3. Grafik",
    "4. Riwayat Buat Resep & Penambahan Stock",
])

with tab_resep:
    st.subheader("Pembuatan Resep Produksi")
    st.caption(
        "Pilih varian roti, masukkan jumlah resep, lalu simpan untuk memotong stok otomatis."
    )

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

    df_stok[kolom_resep] = parse_number(df_stok[kolom_resep])
    df_stok["Stok Awal"] = parse_number(df_stok["Stok Awal"])

    cek_df = df_stok[["Nama Barang", "Stok Awal", "Stok Min", kolom_resep]].copy()
    cek_df = cek_df[cek_df[kolom_resep] > 0]
    cek_df["Kebutuhan Total"] = cek_df[kolom_resep] * jumlah_resep
    cek_df["Sisa Stok"] = cek_df["Stok Awal"] - cek_df["Kebutuhan Total"]

    st.markdown("**Simulasi Pemakaian Bahan Baku:**")
    st.dataframe(cek_df, width="stretch", hide_index=True)

    stok_kurang = cek_df[cek_df["Sisa Stok"] < 0]
    if not stok_kurang.empty:
        st.error(
            "Stok tidak mencukupi untuk bahan: "
            + ", ".join(stok_kurang["Nama Barang"].tolist())
        )
    else:
        if st.button("Simpan & Potong Stok", type="primary", width="stretch"):
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
                    f"Produksi {varian} sebanyak {jumlah_resep} resep tercatat, stok diperbarui, dan notifikasi Telegram terkirim ke owner."
                )
            else:
                st.success(
                    f"Produksi {varian} sebanyak {jumlah_resep} resep berhasil dicatat dan stok diperbarui."
                )
            st.rerun()

with tab_stok:
    st.subheader("Data Stok Bahan Baku")

    col_tabel, col_tambah = st.columns([2.2, 1])

    with col_tabel:
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

    with col_tambah:
        st.markdown("### Tambah Stok Masuk")
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

with tab_grafik:
    st.subheader("Visualisasi Stok Bahan Baku & Produksi")

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
            title="Perbandingan Stok Saat Ini vs Stok Minimum",
            color_discrete_map={"Stok Awal": "#2E86C1", "Stok Min": "#E74C3C"},
        )
        st.plotly_chart(fig_stok, width="stretch")

    if (
        not df_prod.empty
        and "Varian" in df_prod.columns
        and "Jumlah Resep" in df_prod.columns
    ):
        df_prod_chart = df_prod.copy()
        df_prod_chart["Jumlah Resep"] = parse_number(df_prod_chart["Jumlah Resep"])
        rekap_varian = df_prod_chart.groupby("Varian", as_index=False)[
            "Jumlah Resep"
        ].sum()
        fig_prod = px.bar(
            rekap_varian,
            x="Varian",
            y="Jumlah Resep",
            color="Varian",
            title="Total Resep Diproduksi per Varian",
        )
        st.plotly_chart(fig_prod, width="stretch")

with tab_riwayat:
    st.subheader("Riwayat Pembuatan Resep & Penambahan Stock")

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