import streamlit as st
from datetime import datetime
import requests
import base64
import time

# Configurações do GitHub
GITHUB_USER = "tarcisotoledo"
GITHUB_REPO = "smfc-sistema"

st.set_page_config(page_title="SMFC Mobile", page_icon="📦")
st.title("📦 Registro de Cargas")

# --- LÓGICA DA LOJA (Fica gravada enquanto não fechar o navegador) ---
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
    # Mostra a loja fixa no topo
    st.info(f"📍 Loja: {st.session_state.numero_loja}")
    if st.button("🔄 Mudar de Loja"):
        st.session_state.loja_confirmada = False
        st.rerun()

    tipo_fluxo = st.radio("Operação:", ["Entrada", "Saída"], horizontal=True)
    
    # Câmera sempre pronta
    foto_capturada = st.camera_input("Tirar Foto")

    if foto_capturada:
        if st.button("📤 ENVIAR AGORA"):
            try:
                GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
                
                # Nome do arquivo com SEGUNDOS para não sobrescrever se tirar várias seguidas
                data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                tipo_str = "ENTRADA" if tipo_fluxo == "Entrada" else "SAIDA"
                nome_final = f"{data_hora}_{tipo_str}_LOJA{st.session_state.numero_loja}.jpg"
                
                conteudo_foto = base64.b64encode(foto_capturada.getvalue()).decode()
                url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/fotos_recebidas/{nome_final}"
                
                headers = {
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                data = {
                    "message": f"Auditoria: {nome_final}",
                    "content": conteudo_foto
                }
                
                with st.spinner("Enviando para o PC..."):
                    res = requests.put(url, headers=headers, json=data)
                
                if res.status_code in [200, 201]:
                    st.success(f"✅ Foto enviada com sucesso!")
                    st.balloons()
                    time.sleep(2) # Espera 2 segundos para o Dudu ver o sucesso
                    st.rerun()    # Limpa a câmera para a PRÓXIMA FOTO
                else:
                    st.error(f"Erro no envio. Verifique o Token.")
            except Exception as e:
                st.error("Erro técnico. Verifique as Secrets no Streamlit.")
