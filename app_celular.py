import streamlit as st
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
import io
import json

# Configuração da página
st.set_page_config(page_title="SMFC Mobile", page_icon="📦")

# --- FUNÇÃO PARA CONECTAR AO GOOGLE DRIVE ---
def carregar_para_drive(foto_bytes, nome_arquivo):
    try:
        # Carrega as credenciais das Secrets do Streamlit
        info_servico = json.loads(st.secrets["gcp_service_account"])
        credenciais = service_account.Credentials.from_service_account_info(info_servico)
        service = build('drive', 'v3', credentials=credenciais)

        # ID da pasta SMFC_FOTOS (Você vai pegar esse ID no próximo passo)
        ID_PASTA_DESTINO = st.secrets["id_pasta_drive"]

        file_metadata = {
            'name': nome_arquivo,
            'parents': [ID_PASTA_DESTINO]
        }
        
        # Converte os bytes da foto para o formato que o Drive aceita
        fh = io.BytesIO(foto_bytes)
        media = MediaIoBaseUpload(fh, mimetype='image/jpeg')
        
        arquivo_criado = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        return arquivo_criado.get('id')
    except Exception as e:
        st.error(f"Erro ao enviar: {e}")
        return None

# --- INTERFACE ---
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
            with st.spinner("Enviando..."):
                data_atual = datetime.now().strftime("%Y-%m-%d")
                tipo_str = "ENTRADA" if tipo_fluxo == "Entrada" else "SAIDA"
                nome_final = f"{data_atual}_{tipo_str}_LOJA{st.session_state.numero_loja}.jpg"
                
                # Chama a função de upload
                id_foto = carregar_para_drive(foto_capturada.getvalue(), nome_final)
                
                if id_foto:
                    st.success("✅ Enviada com sucesso!")
                    st.balloons()
