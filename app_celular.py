import streamlit as st
from datetime import datetime
import os

st.set_page_config(page_title="SMFC Mobile", page_icon="📦")

st.title("📦 Registro de Cargas")

if 'loja_confirmada' not in st.session_state:
    st.session_state.loja_confirmada = False

if not st.session_state.loja_confirmada:
    num_loja = st.text_input("Digite o número da loja:")
    if st.button("Confirmar Loja ➡️"):
        if num_loja:
            st.session_state.numero_loja = num_loja
            st.session_state.loja_confirmada = True
            st.rerun()
else:
    st.info(f"📍 Loja: {st.session_state.numero_loja}")
    if st.button("🔄 Mudar de Loja"):
        st.session_state.loja_confirmada = False
        st.rerun()

    tipo_fluxo = st.radio("Operação:", ["Entrada", "Saída"], horizontal=True)
    foto_capturada = st.camera_input("Tirar Foto")

    if foto_capturada:
        if st.button("📤 Enviar para o PC do Trabalho"):
            # Criar a pasta se não existir
            if not os.path.exists("fotos_recebidas"):
                os.makedirs("fotos_recebidas")
            
            data_atual = datetime.now().strftime("%Y-%m-%d")
            tipo_str = "ENTRADA" if tipo_fluxo == "Entrada" else "SAIDA"
            nome_final = f"{data_atual}_{tipo_str}_LOJA{st.session_state.numero_loja}.jpg"
            
            # Salva a foto
            with open(os.path.join("fotos_recebidas", nome_final), "wb") as f:
                f.write(foto_capturada.getbuffer())
            
            st.success(f"✅ Foto {nome_final} salva com sucesso!")
            st.balloons()
