"""Painel de auditoria: as fotos que as lojas mandaram, por loja e por dia.

## Os dois defeitos corrigidos em 01/09/2026

1. **A busca da loja casava por pedaço de texto.** `"LOJA2" in nome` é
   verdadeiro para `LOJA20`, `LOJA22`, `LOJA23` e `LOJA24`. Medido nas 1.528
   fotos: procurar a loja 2 (que tem **4** fotos) devolvia **432**; procurar a
   loja 1 devolvia 603 fotos das lojas 10, 12, 14, 16, 18 e 19. Agora o número é
   comparado inteiro, e não como trecho.

2. **A FAXINA não apagava nada** — o botão só escrevia "Faxina concluída". Isso é
   pior do que não existir: dava para acreditar que o disco havia sido limpo.
   Agora ela conta o que vai apagar, pede confirmação e apaga de verdade **só a
   cópia local** (o GitHub continua com tudo).

## Sobre a hora das fotos antigas

Até 01/09/2026 o app do celular nomeava os arquivos com a hora do servidor, que é
UTC — três horas à frente do Brasil. A carga da noite (21h em diante) caía com a
data do dia seguinte no nome. Por isso a busca inclui, para os arquivos anteriores
ao corte, as três primeiras horas do dia seguinte: é lá que a foto da noite
anterior foi arquivada. Ver a explicação em `app_celular.py`.
"""
import os
from datetime import datetime, timedelta

import streamlit as st

import foto_carga as fc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_FOTOS = os.path.join(BASE_DIR, "fotos_recebidas")

DIAS_DA_FAXINA = 90

st.set_page_config(page_title="Painel de Auditoria SMFC", page_icon="🔍", layout="wide")

st.markdown("""
    <style>
    html, body, [class*="ViewContainer"] { font-size: 22px !important; }
    .stButton>button {
        height: 4em;
        width: 100%;
        font-size: 24px !important;
        font-weight: bold;
        color: white !important;
        background-color: #007bff !important;
        border-radius: 10px;
    }
    .stTextInput>div>div>input { font-size: 22px !important; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

st.title("🔍 PAINEL DE AUDITORIA SMFC")


def buscar_e_exibir(tipo):
    col1, col2 = st.columns(2)
    with col1:
        loja = st.text_input("Número da Loja:", key="loja_%s" % tipo)
    with col2:
        data_sel = st.date_input("Data da Carga:", datetime.now(), key="data_%s" % tipo)

    if not st.button("CLIQUE AQUI PARA BUSCAR %s 🔍" % tipo.upper(), key="btn_%s" % tipo):
        return

    if not str(loja).strip().isdigit():
        return st.warning("Digite o número da loja — só números, por exemplo 20.")

    data_str = data_sel.strftime("%Y-%m-%d")
    achadas, do_fuso = fc.fotos_de(PASTA_FOTOS, loja, data_str, tipo)

    if not achadas and not do_fuso:
        return st.warning("⚠️ Nenhuma foto de %s da Loja %s em %s."
                          % (tipo, loja, data_sel.strftime('%d/%m/%Y')))

    st.success("✅ %d foto(s) encontrada(s)." % (len(achadas) + len(do_fuso)))
    if do_fuso:
        st.caption("%d delas foram tiradas à noite e ficaram gravadas com a data "
                   "do dia seguinte (fuso do servidor, corrigido em 01/09)."
                   % len(do_fuso))

    for nome in achadas + do_fuso:
        caminho = os.path.join(PASTA_FOTOS, nome)
        tamanho = os.path.getsize(caminho) // 1024
        st.image(caminho, caption="%s  ·  %d KB" % (nome, tamanho),
                 use_container_width=True)


aba_saida, aba_entrada, aba_faxina = st.tabs(["📤 SAÍDA", "📥 ENTRADA", "🧹 FAXINA"])

with aba_saida:
    buscar_e_exibir("Saida")

with aba_entrada:
    buscar_e_exibir("Entrada")

with aba_faxina:
    st.subheader("🧹 Limpeza da cópia local")
    st.write("Apaga da **sua máquina** as fotos com mais de %d dias. "
             "O GitHub continua com todas — isto é só o espaço do disco daqui."
             % DIAS_DA_FAXINA)

    if not os.path.isdir(PASTA_FOTOS):
        st.info("A pasta de fotos ainda não existe nesta máquina.")
    else:
        corte = datetime.now() - timedelta(days=DIAS_DA_FAXINA)
        velhas = []
        for nome in os.listdir(PASTA_FOTOS):
            partes = fc.partes_do_nome(nome)
            if not partes:
                continue
            try:
                quando = datetime.strptime(partes[0], "%Y-%m-%d")
            except ValueError:
                continue
            if quando < corte:
                velhas.append(nome)

        espaco = sum(os.path.getsize(os.path.join(PASTA_FOTOS, n)) for n in velhas)
        if not velhas:
            st.success("Nada para apagar: nenhuma foto tem mais de %d dias."
                       % DIAS_DA_FAXINA)
        else:
            st.warning("**%d foto(s)** com mais de %d dias, ocupando **%.1f MB**."
                       % (len(velhas), DIAS_DA_FAXINA, espaco / 1048576))
            # Apagar não tem volta daqui: confirma marcando, e não num clique só.
            confirmou = st.checkbox("Sim, apagar essas fotos da cópia local")
            if st.button("APAGAR AGORA"):
                if not confirmou:
                    st.warning("Marque a confirmação acima antes de apagar.")
                else:
                    apagadas, erros = 0, []
                    for nome in velhas:
                        try:
                            os.remove(os.path.join(PASTA_FOTOS, nome))
                            apagadas += 1
                        except Exception as e:
                            erros.append("%s (%s)" % (nome, e))
                    st.success("%d foto(s) apagadas da cópia local." % apagadas)
                    if erros:
                        st.error("Não consegui apagar %d: %s"
                                 % (len(erros), "; ".join(erros[:5])))
