import streamlit as st
from datetime import datetime
import requests
import base64

# Configurações do GitHub (Ajuste com seus dados)
GITHUB_USER = "tarcisotoledo"
GITHUB_REPO = "smfc-sistema"
# O Token você gera no GitHub (Settings > Developer Settings > Personal access tokens)
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"] 

st.title("📦 Registro de Cargas")

# ... (mantenha a parte de confirmar a loja igual ao código anterior) ...

if foto_capturada:
    if st.button("📤 Enviar para o PC do Trabalho"):
        data_atual = datetime.now().strftime("%Y-%m-%d")
        tipo_str = "ENTRADA" if tipo_fluxo == "Entrada" else "SAIDA"
        nome_final = f"{data_atual}_{tipo_str}_LOJA{st.session_state.numero_loja}.jpg"
        
        # Converter foto para Base64 para enviar via API
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
            st.success("✅ Foto enviada para o GitHub!")
            st.balloons()
        else:
            st.error(f"Erro no envio: {res.text}")
