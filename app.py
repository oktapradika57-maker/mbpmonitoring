import streamlit as str
import pandas as pd
import numpy as np

# Konfigurasi Halaman
str.set_page_config(
    page_title="Genset Backup Monitor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ID Spreadsheet Anda
SPREADSHEET_ID = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"

str.title("⚡ Genset Backup Monitor")
str.caption("Komparasi Durasi Nyata (Waktu Start/Stop) vs Running Hours (RH) Genset")

# Tombol Refresh Data
if str.button("🔄 Refresh Data", type="primary"):
    str.rerun()

# Memuat Data dari Google Sheets
@str.cache_data(ttl=60) # Cache data selama 60 detik agar tidak membebani kuota download
def load_data(url):
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        str.error(f"Gagal mengambil data dari Google Sheets. Pastikan link sudah 'Anyone with link can view'. Error: {e}")
        return None

df_raw = load_data(csv_url)

if df_raw is not None and not df_raw.empty:
    # --- PROSES STANDARISASI KOLOM ---
    # Mencari kolom berdasarkan kata kunci (tidak sensitif huruf besar/kecil)
    cols = df_raw.columns
    
    start_backup_col = next((c for c in cols if 'start' in c.lower() and ('backup' in c.lower() or 'waktu' in c.lower())), None)
    stop_backup_col = next((c for c in cols if 'stop' in c.lower() and ('backup' in c.lower() or 'waktu' in c.lower())), None)
    rh_start_col = next((c for c in cols if 'rh' in c.lower() and 'start' in c.lower() or ('start' in c.lower() and 'rh' in c.lower())), None)
    rh_stop_col = next((c for c in cols if 'rh' in c.lower() and 'stop' in c.lower() or ('stop' in c.lower() and 'rh' in c.lower())), None)

    if not all([start_backup_col, stop_backup_col, rh_start_col, rh_stop_col]):
        str.warning("⚠️ Beberapa kolom krusial tidak ditemukan. Pastikan nama kolom di Google Sheets mengandung kata kunci 'Start Backup', 'Stop Backup', 'RH Start', dan 'RH Stop'.")
        str.write("Kolom yang terdeteksi di sheet Anda:", list(cols))
    else:
        # Buat dataframe baru untuk kalkulasi bersih
        df = df_raw.copy()
        
        # Konversi kolom waktu ke tipe Datetime
        df[start_backup_col] = pd.to_datetime(df[start_backup_col], errors='coerce')
        df[stop_backup_col] = pd.to_datetime(df[stop_backup_col], errors='coerce')
        
        # Konversi kolom RH ke angka murni
        df[rh_start_col] = pd.to_numeric(df[rh_start_col], errors='coerce').fillna(0)
        df[rh_stop_col] = pd.to_numeric(df[rh_stop_col], errors='coerce').fillna(0)
        
        # Drop baris yang waktu start-nya kosong agar tidak merusak perhitungan
        df = df.dropna(subset=[start_backup_col])

        # --- LOGIKAL PERHITUNGAN ---
        # 1. Durasi Waktu Nyata (dalam Jam pecahan)
        df['Durasi Waktu Nyata (Jam)'] = (df[stop_backup_col] - df[start_backup_col]).dt.total_seconds() / 3600
        df['Durasi Waktu Nyata (Jam)'] = df['Durasi Waktu Nyata (Jam)'].fillna(0).round(2)
        
        # 2. Durasi Running Hours (RH)
        df['Durasi RH (Jam)'] = np.where(df[rh_stop_col] >= df[rh_start_col], df[rh_stop_col] - df[rh_start_col], 0)
        df['Durasi RH (Jam)'] = df['Durasi RH (Jam)'].round(2)
        
        # 3. Selisih / Discrepancy
        df['Selisih (Jam)'] = (df['Durasi Waktu Nyata (Jam)'] - df['Durasi RH (Jam)']).abs().round(2)

        # --- TAMPILAN KPI METRICS ---
        total_backup = len(df)
        total_waktu_nyata = df['Durasi Waktu Nyata (Jam)'].sum()
        total_rh = df['Durasi RH (Jam)'].sum()

        col1, col2, col3 = str.columns(3)
        with col1:
            str.metric(label="Total Kejadian Backup", value=f"{total_backup} Kali")
        with col2:
            str.metric(label="Total Akumulasi Waktu Nyata", value=f"{total_waktu_nyata:.2f} Jam")
        with col3:
            str.metric(label="Total Akumulasi RH Genset", value=f"{total_rh:.2f} Jam")

        str.markdown("---")

        # --- TAMPILAN TABEL LOG DATA ---
        str.subheader("📋 Log Perhitungan & Komparasi Data")
        
        # Mempercantik format tampilan tabel sebelum di-display
        df_display = pd.DataFrame({
            "No": range(1, len(df) + 1),
            "Waktu Start": df[start_backup_col].dt.strftime('%Y-%m-%d %H:%M'),
            "Waktu Stop": df[stop_backup_col].dt.strftime('%Y-%m-%d %H:%M'),
            "Durasi Nyata": df['Durasi Waktu Nyata (Jam)'].map("{:.2f} Jam".format),
            "RH Start": df[rh_start_col],
            "RH Stop": df[rh_stop_col],
            "Durasi RH": df['Durasi RH (Jam)'].map("{:.2f} Jam".format),
            "Selisih Komparasi": df['Selisih (Jam)'].map("{:.2f} Jam".format)
        })

        # Menampilkan data ke dalam tabel interaktif Streamlit
        str.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    str.info("Belum ada data atau spreadsheet kosong.")
