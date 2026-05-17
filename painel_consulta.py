import streamlit as st
import os
from datetime import datetime, timedelta

# Configuração da página do painel de controle
st.set_page_config(
    page_title="SMFC - Painel de Auditoria e Limpeza",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Sistema de Monitoramento de Fluxo de Cargas")
st.subheader("Painel de Auditoria e Gestão de Arquivos")

# Caminho da pasta onde as fotos estão armazenadas no seu PC
PASTA_FOTOS = "fotos_recebidas"
DIAS_LIMITE = 90  # Regra dos 3 meses

# Função auxiliar para listar e filtrar as fotos com base nos critérios
def buscar_fotos(tipo_fluxo, numero_loja, data_inicio, data_fim=None):
    resultados = []
    if not os.path.exists(PASTA_FOTOS):
        return resultados

    arquivos = os.listdir(PASTA_FOTOS)
    for arquivo in arquivos:
        if arquivo.lower().endswith(('.jpg', '.jpeg', '.png')):
            partes = arquivo.replace(".jpg", "").split("_")
            if len(partes) >= 3:
                data_str, tipo_arq, loja_arq = partes[0], partes[1], partes[2]
                try:
                    data_compara = datetime.strptime(data_str, "%Y-%m-%d").date()
                except ValueError:
                    continue
                
                filtro_tipo = (tipo_arq == tipo_fluxo)
                filtro_loja = (loja_arq == f"LOJA{numero_loja}")
                
                if data_fim:
                    filtro_data = (data_inicio <= data_compara <= data_fim)
                else:
                    filtro_data = (data_compara == data_inicio)
                    
                if filtro_tipo and filtro_loja and filtro_data:
                    resultados.append({
                        "nome": arquivo,
                        "caminho": os.path.join(PASTA_FOTOS, arquivo),
                        "data": data_str
                    })
    return resultados

# --- CRIANÇÃO DAS ABAS (Agora com 3 abas!) ---
aba_saida, aba_entrada, aba_limpeza = st.tabs([
    "📤 Verificar Saída (Origem)", 
    "📥 Verificar Entrada (Destino)", 
    "🧹 Faxina Automática (Limpeza)"
])

# ABA 1: CONFERIR SAÍDA
with aba_saida:
    st.markdown("### Buscar Registro de Saída da Mercadoria")
    col1, col2 = st.columns(2)
    with col1:
        loja_origem = st.text_input("Número da Loja de Origem:", placeholder="Ex: 3", key="loja_orig")
    with col2:
        data_saida = st.date_input("Data exata da Saída:", datetime.now().date(), key="data_sai")
        
    if st.button("Buscar Foto de Saída 🔍"):
        if loja_origem.strip():
            fotos_encontradas = buscar_fotos("SAIDA", loja_origem.strip(), data_saida)
            if fotos_encontradas:
                st.success(f"Encontrado {len(fotos_encontradas)} registro(s) de saída!")
                for foto in fotos_encontradas:
                    st.write(f"📁 Arquivo: `{foto['nome']}`")
                    st.image(foto['caminho'], caption=f"Saída da Loja {loja_origem} em {foto['data']}", width=400)
            else:
                st.warning(f"Nenhum registro de SAÍDA encontrado para a Loja {loja_origem} na data selecionada.")
        else:
            st.error("Por favor, digite o número da loja de origem.")

# ABA 2: CONFERIR ENTRADA POR PERÍODO
with aba_entrada:
    st.markdown("### Buscar Registro de Chegada no Destino (Por Período)")
    col1, col2, col3 = st.columns(3)
    with col1:
        loja_destino = st.text_input("Número da Loja de Destino:", placeholder="Ex: 17", key="loja_dest")
    with col2:
        data_inicio = st.date_input("Data Inicial do Período:", datetime.now().date())
    with col3:
        data_fim = st.date_input("Data Final do Período:", datetime.now().date())
        
    if st.button("Buscar Fotos no Período 🔍"):
        if loja_destino.strip():
            if data_inicio <= data_fim:
                fotos_encontradas = buscar_fotos("ENTRADA", loja_destino.strip(), data_inicio, data_fim)
                if fotos_encontradas:
                    st.success(f"Encontrada(s) {len(fotos_encontradas)} foto(s) de entrada no período selecionado!")
                    col_fotos = st.columns(min(len(fotos_encontradas), 3))
                    for i, foto in enumerate(fotos_encontradas):
                        idx_col = i % 3
                        with col_fotos[idx_col]:
                            st.write(f"`{foto['nome']}`")
                            st.image(foto['caminho'], caption=f"Chegada na Loja {loja_destino} em {foto['data']}", use_container_width=True)
                else:
                    st.warning(f"Nenhum registro de ENTRADA encontrado para a Loja {loja_destino} entre {data_inicio} e {data_fim}.")
            else:
                st.error("Erro: A data inicial não pode ser maior que a data final.")
        else:
            st.error("Por favor, digite o número da loja de destino.")

# ABA 3: MODULO DE EXCLUSÃO EM LOTE (A NOVIDADE)
with aba_limpeza:
    st.markdown("### 🧹 Gerenciamento de Espaço em Disco (Regra de 3 Meses)")
    st.info(f"O sistema está configurado para manter as fotos por **{DIAS_LIMITE} dias**. Fotos mais antigas que isso podem ser removidas para liberar espaço.")
    
    data_limite = datetime.now() - timedelta(days=DIAS_LIMITE)
    st.write(f"📅 **Data de corte atual:** Arquivos criados antes de **{data_limite.strftime('%d/%m/%Y')}** serão apagados.")
    
    # Faz uma varredura prévia para avisar o usuário se existem arquivos antigos
    arquivos_antigos = []
    total_arquivos = 0
    
    if os.path.exists(PASTA_FOTOS):
        for arquivo in os.listdir(PASTA_FOTOS):
            if arquivo.lower().endswith(('.jpg', '.jpeg', '.png')):
                total_arquivos += 1
                caminho_completo = os.path.join(PASTA_FOTOS, arquivo)
                data_modificacao = datetime.fromtimestamp(os.path.getmtime(caminho_completo))
                if data_modificacao < data_limite:
                    arquivos_antigos.append(caminho_completo)
    
    # Mostra um resumo do que foi encontrado
    col_inf1, col_inf2 = st.columns(2)
    with col_inf1:
        st.metric("Total de fotos armazenadas", total_arquivos)
    with col_inf2:
        st.metric("Fotos expiradas (Mais de 3 meses)", len(arquivos_antigos), delta_color="inverse")
        
    st.divider()
    
    # Botão de ação para deletar
    if len(arquivos_antigos) > 0:
        st.warning(f"Atenção: {len(arquivos_antigos)} fotos estão fora do prazo de validade de 3 meses.")
        
        # Caixa de confirmação para o usuário não clicar por engano
        confirmar = st.checkbox("Eu confirmo que quero apagar essas fotos antigas em lote.")
        
        if st.button("🚨 Executar Limpeza em Lote", disabled=not confirmar):
            contador_removidos = 0
            for caminho in arquivos_antigos:
                try:
                    os.remove(caminho)
                    contador_removidos += 1
                except Exception as e:
                    st.error(f"Erro ao apagar arquivo {caminho}: {e}")
            
            st.success(f"Sucesso! Faxina concluída. {contador_removidos} arquivos antigos foram eliminados permanentemente.")
            st.balloons()
            st.rerun()
    else:
        st.success("✅ Tudo limpo! Nenhuma foto com mais de 3 meses foi encontrada no seu computador.")