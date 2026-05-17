import streamlit as st
from datetime import datetime
import requests
import base64

# Configurações do GitHub
GITHUB_USER = "tarcisotoledo"
GITHUB_REPO = "smfc-sistema"

st.set_page_config(page_title="SMFC Mobile", page_icon="📦")
st.title("📦 Registro de Cargas")

# --- LÓGICA DA LOJA ---
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
    
    # AQUI ESTAVA O ERRO - AGORA ESTÁ CORRIGIDO:
    foto_capturada = st.camera_input("Tirar Foto")

    if foto_capturada:
        if st.button("📤 Enviar para o PC do Trabalho"):
            try:
                # Puxa o Token das Secrets do Streamlit
                GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
                
                data_atual = datetime.now().strftime("%Y-%m-%d_%H-%M")
                tipo_str = "ENTRADA" if tipo_fluxo == "Entrada" else "SAIDA"
                nome_final = f"{data_atual}_{tipo_str}_LOJA{st.session_state.numero_loja}.jpg"
                
                conteudo_foto = base64.b64encode(foto_capturada.getvalue()).decode()
                url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/fotos_recebidas/{nome_final}"
                
                headers = {
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                data = {
                    "message": f"Nova foto: {nome_final}",
                    "content": conteudo_foto
                }
                
                res = requests.put(url, headers=headers, json=data)
                
                if res.status_code in [200, 201]:
                    st.success(f"✅ Foto {nome_final} enviada!")
                    st.balloons()
                else:
                    st.error(f"Erro no GitHub: {res.status_code}")
            except Exception as e:
                st.error("Erro: Verifique se o GITHUB_TOKEN foi configurado nas Secrets.")
