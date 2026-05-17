import streamlit as st
from datetime import datetime
import os

# Configuração da página para parecer um aplicativo de celular
st.set_page_config(
    page_title="SMFC Mobile",
    page_icon="📦",
    layout="centered"
)

# Estilização para botões grandes e interface limpa
st.markdown("""
    <style>
    div.stButton > button:first-child {
        width: 100%;
        height: 60px;
        font-size: 20px;
        font-weight: bold;
        border-radius: 10px;
    }
    .status-loja {
        padding: 10px;
        background-color: #e1f5fe;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Registro de Cargas")

# 1. Gerenciamento do Estado da Loja (Para lembrar se a loja já foi confirmada)
if 'loja_confirmada' not in st.session_state:
    st.session_state.loja_confirmada = False
if 'numero_loja' not in st.session_state:
    st.session_state.numero_loja = ""

# 2. Tela Inicial: Identificação da Loja
if not st.session_state.loja_confirmada:
    st.subheader("Identificação da Filial")
    num_loja = st.text_input("Digite o número da loja:", placeholder="Ex: 3, 17, 20")
    
    if st.button("Confirmar Loja ➡️"):
        if num_loja.strip():
            st.session_state.numero_loja = num_loja.strip()
            st.session_state.loja_confirmada = True
            st.rerun()
        else:
            st.error("Por favor, insira o número da loja para continuar.")

# 3. Tela de Operação: Botões de Foto (Só aparece após confirmar a loja)
else:
    # Mostra qual loja está ativa e um botão para mudar se necessário
    st.markdown(f"<div class='status-loja'>📍 Conectado à Loja: {st.session_state.numero_loja}</div>", unsafe_allow_html=True)
    if st.button("🔄 Mudar de Loja", key="mudar_loja"):
        st.session_state.loja_confirmada = False
        st.rerun()
        
    st.divider()
    
    st.subheader("Selecione o Tipo de Fluxo")
    tipo_fluxo = st.radio("O que está registrando?", ["Entrada", "Saída"], horizontal=True)
    
    # Abre a câmera nativa do celular
    foto_capturada = st.camera_input(f"Tirar foto da {tipo_fluxo}")
    
    if foto_capturada:
        # Gerar os dados para o nome do arquivo conforme seu padrão
        data_atual = datetime.now().strftime("%Y-%m-%d")
        tipo_str = "ENTRADA" if tipo_fluxo == "Entrada" else "SAIDA"
        loja_str = f"LOJA{st.session_state.numero_loja}"
        
        nome_arquivo = f"{data_atual}_{tipo_str}_{loja_str}.jpg"
        
        st.success(f"Foto capturada pronta para envio!")
        st.info(f"Nome gerado: `{nome_arquivo}`")
        
        # Botão final para fazer o upload
        if st.button("📤 Enviar para o PC do Trabalho"):
            with st.spinner("Enviando imagem..."):
                # --- LÓGICA DE ENVIO ---
                # Aqui entrará o código que joga a foto na pasta compartilhada.
                # Por enquanto, simulamos salvando localmente para teste.
                
                os.makedirs("fotos_recebidas", exist_ok=True)
                caminho_salvar = os.path.join("fotos_recebidas", nome_arquivo)
                
                with open(caminho_salvar, "wb") as f:
                    f.write(foto_capturada.getbuffer())
                
                st.balloons()
                st.success("Feito! A foto já foi enviada e está a caminho do seu PC.")