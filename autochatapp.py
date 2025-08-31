# ==============================================================================
# IMPORT LIBRARY YANG DIBUTUHKAN
# ==============================================================================
import streamlit as st
import pandas as pd
from openai import OpenAI
from PIL import Image
import re
import io
import base64

# ==============================================================================
# KONFIGURASI HALAMAN UTAMA APLIKASI
# ==============================================================================
st.set_page_config(
    page_title="🚗 AutoChat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# JUDUL DAN PENGENALAN APLIKASI
# ==============================================================================
st.title("🚗 AutoChat")
st.markdown("Analisis data, visualisasikan, dan dapatkan wawasan otomotif dengan bantuan AI")

# ==============================================================================
# KONFIGURASI API KEY GPT
# ==============================================================================
def configure_gpt_api():
    """Mengonfigurasi dan mengembalikan client"""
    try:
        api_key = st.secrets["openai"]["api_key"]
        return OpenAI(api_key=api_key)
    except (KeyError, AttributeError):
        st.error("⚠️ Kunci API GPT tidak ditemukan. Harap buat file `.streamlit/secrets.toml` dan tambahkan kunci Anda.")
        return None

client = configure_gpt_api()

# ==============================================================================
# MANAJEMEN STATE APLIKASI
# ==============================================================================
def initialize_session_state():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "user_df" not in st.session_state:
        st.session_state.user_df = None
    if "pending_image" not in st.session_state:
        st.session_state.pending_image = None

initialize_session_state()

# ==============================================================================
# DATA SAMPEL
# ==============================================================================
@st.cache_data
def get_sample_data():
    data = {
        "Mobil": ["Avanza", "Xenia", "Civic", "Fortuner", "Pajero", "Jazz"],
        "Efisiensi (km/l)": [12, 11, 14, 9, 8, 15],
        "Harga (juta Rp)": [250, 240, 500, 700, 750, 300],
        "Torsi (Nm)": [141, 138, 174, 200, 210, 145],
        "Tipe Mesin": ["Bensin", "Bensin", "Bensin", "Diesel", "Diesel", "Bensin"]
    }
    return pd.DataFrame(data)

df_sample = get_sample_data()

# ==============================================================================
# FUNGSI EKSEKUSI KODE DARI RESPON GPT
# ==============================================================================
def execute_code_from_response(response_text: str):
    code_blocks = re.findall(r"```python\n(.*?)```", response_text, re.DOTALL)
    if not code_blocks:
        return

    st.info("💡 Autochat memberikan kode visualisasi. Mencoba menampilkannya...")
    for code in code_blocks:
        try:
            local_namespace = {
                "st": st, "px": px, "pd": pd,
                "df_sample": df_sample,
                "df_uploaded": st.session_state.user_df
            }
            exec(code, local_namespace)
        except Exception as e:
            st.error(f"⚠️ Gagal mengeksekusi visualisasi: {e}")
            st.code(code, language="python")

# ==============================================================================
# PAGE CHATBOT
# ==============================================================================
def page_chatbot():
    st.header("💬 Chatbot Otomotif")

    if not client:
        st.warning("Fitur chatbot tidak dapat berjalan karena API belum dikonfigurasi.")
        return

    if not st.session_state.chat_history:
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": "Halo! Saya AutoChat. Tanyakan apa saja tentang otomotif, bandingkan mobil, atau unggah data Anda!"
        })

    uploaded_file = st.file_uploader("Unggah gambar mobil (opsional)", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        st.session_state.pending_image = Image.open(uploaded_file)
        st.image(st.session_state.pending_image, caption="Gambar ini akan dikirim bersama pertanyaan Anda.", width=250)

    st.markdown("---")

    # Tampilkan riwayat chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Jalankan kode jika ada dari GPT
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "assistant":
        execute_code_from_response(st.session_state.chat_history[-1]["content"])

    # Input user
    if prompt := st.chat_input("Tulis pertanyaan Anda di sini..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("🤖 Autochat sedang memproses..."):
            try:
                # Jika ada gambar, konversi ke base64 lalu kirim bersama teks
                if st.session_state.pending_image:
                    buf = io.BytesIO()
                    st.session_state.pending_image.save(buf, format="PNG")
                    b64_image = base64.b64encode(buf.getvalue()).decode()

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Anda adalah asisten otomotif yang membantu menjawab pertanyaan."},
                            *st.session_state.chat_history[:-1],
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                                ]
                            }
                        ]
                    )
                else:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=st.session_state.chat_history
                    )

                answer = response.choices[0].message.content
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                st.rerun()  # ✅ perbaikan dari experimental_rerun
            except Exception as e:
                st.error(f"⚠️ Terjadi kesalahan API: {e}")

# ==============================================================================
# PAGE GRAFIK
# ==============================================================================
def page_grafik():
    st.header("📊 Visualisasi Data Otomotif")
    source = st.radio("Pilih Sumber Data:", ["Data Sampel", "Data yang Diunggah"], horizontal=True)

    active_df = df_sample if source == "Data Sampel" else st.session_state.user_df
    if active_df is None:
        st.warning("Unggah CSV di menu 'Unggah Data' dulu.")
        return

    st.dataframe(active_df, use_container_width=True)
    st.markdown("---")

    plot_type = st.selectbox("Pilih Jenis Grafik:", ["Scatter Plot", "Bar Chart", "Histogram"])
    cols = active_df.columns.tolist()
    numeric_cols = active_df.select_dtypes(include="number").columns.tolist()

    fig = None
    if plot_type == "Scatter Plot":
        x = st.selectbox("Sumbu X:", numeric_cols)
        y = st.selectbox("Sumbu Y:", numeric_cols)
        color = st.selectbox("Warna berdasarkan:", [None] + cols)
        fig = px.scatter(active_df, x=x, y=y, color=color, hover_name=cols[0])
    elif plot_type == "Bar Chart":
        x = st.selectbox("Kategori (X):", cols)
        y = st.selectbox("Nilai (Y):", numeric_cols)
        fig = px.bar(active_df, x=x, y=y, color=x)
    elif plot_type == "Histogram":
        x = st.selectbox("Variabel:", numeric_cols)
        fig = px.histogram(active_df, x=x)

    if fig:
        st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# PAGE UPLOAD
# ==============================================================================
def page_upload():
    st.header("📂 Unggah Data CSV")
    uploaded_file = st.file_uploader("Pilih file CSV", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state.user_df = df
            st.success(f"File {uploaded_file.name} berhasil diunggah.")
            st.dataframe(df.head())
        except Exception as e:
            st.error(f"Gagal memproses file: {e}")

# ==============================================================================
# NAVIGASI UTAMA
# ==============================================================================
def main_navigation():
    with st.sidebar:
        st.image("Autochatapp.png", use_container_width=True)
        st.title("AutoChat")
        menu = st.radio("Pilih Menu:", ["AI Chatbot", "Grafik Interaktif", "Unggah Data"])
        st.info("🚀 Created by Agung")

    if menu == "AI Chatbot":
        page_chatbot()
    elif menu == "Grafik Interaktif":
        page_grafik()
    else:
        page_upload()

# ==============================================================================
# MAIN APP
# ==============================================================================
if __name__ == "__main__":
    main_navigation()
