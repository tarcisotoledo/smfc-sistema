"""Registro fotográfico de cargas, pelo celular da loja.

## O que estava errado (medido em 01/09/2026, nas 1.528 fotos já recebidas)

1. **A foto saía como miniatura.** 1.392 das 1.528 tinham **344x421 pixels** —
   0,14 megapixel, de um celular que fotografa a 12 MP. A culpa era do
   `st.camera_input`: ele captura o vídeo no tamanho do widget na tela, não no da
   câmera. Agora quem fotografa é a **câmera do próprio celular** (o
   `st.file_uploader`, no telefone, oferece a câmera), e o arquivo chega na
   resolução real.

2. **O nome do arquivo estava 3 horas adiantado.** O servidor do Streamlit roda
   em UTC: foto tirada 12:12 era gravada como `15-12`. Além de confundir, jogava
   a carga da noite para o dia seguinte — e o Painel busca por data, então a foto
   ficava invisível.

3. **Abrir dava trabalho.** Agora a loja entra pelo link já com o número dela
   (`...?loja=20`), guarda na tela inicial do celular e cai direto na câmera.

As regras (hora, nome, redução) moram em `foto_carga.py`, sem Streamlit, para
poderem ser testadas — `teste_foto_carga.py`. Aqui fica só a tela.
"""
import base64
import time

import requests
import streamlit as st

import foto_carga as fc

GITHUB_USER = "tarcisotoledo"
GITHUB_REPO = "smfc-sistema"
PASTA_NO_REPO = "fotos_recebidas"

st.set_page_config(page_title="SMFC Mobile", page_icon="📦")


def enviar_ao_github(nome, conteudo):
    """(ok, recado). O recado traz o que o GitHub respondeu, e não um palpite.

    Antes, qualquer falha dizia "Verifique o Token" - inclusive falta de
    internet e foto repetida. Erro que aponta para o lugar errado custa mais
    tempo do que erro nenhum.
    """
    try:
        token = st.secrets["GITHUB_TOKEN"]
    except Exception:
        return False, ("Falta o GITHUB_TOKEN nas Secrets do Streamlit — "
                       "sem ele nenhuma foto sai.")

    url = "https://api.github.com/repos/%s/%s/contents/%s/%s" % (
        GITHUB_USER, GITHUB_REPO, PASTA_NO_REPO, nome)
    try:
        resposta = requests.put(
            url,
            headers={"Authorization": "token %s" % token,
                     "Accept": "application/vnd.github.v3+json"},
            json={"message": "Auditoria: %s" % nome,
                  "content": base64.b64encode(conteudo).decode()},
            timeout=60)
    except requests.RequestException as e:
        return False, "A internet caiu no meio do envio (%s)." % e

    if resposta.status_code in (200, 201):
        return True, ""

    try:
        detalhe = resposta.json().get("message", "")
    except Exception:
        detalhe = resposta.text[:200]
    return False, "O GitHub respondeu %s: %s" % (resposta.status_code, detalhe)


# ------------------------------------------------------------------ a tela
st.title("📦 Registro de Cargas")

# A loja pode vir no endereço: .../?loja=20 - e aí a gerente guarda o link na
# tela inicial do celular e abre já na câmera, sem digitar nada.
if 'numero_loja' not in st.session_state:
    try:
        da_url = st.query_params.get("loja", "")
    except Exception:
        da_url = ""
    if str(da_url).strip().isdigit():
        st.session_state.numero_loja = str(da_url).strip()

if 'numero_loja' not in st.session_state:
    # BOTÃO, e não campo de digitar: quem usa isto é o motorista, que passa em
    # várias lojas no mesmo dia. Um toque por parada, sem teclado - e sem o
    # "LOJAL9" que já aconteceu cinco vezes e sumiu da busca do Painel.
    st.write("### Em qual loja você está?")

    # Uma coluna só, e não duas: no celular o Streamlit empilha as colunas, e a
    # ordem sai quebrada (2, 4, 8, 10... e depois 3, 6, 9...). Testado em tela de
    # 375 px antes de publicar.
    #
    # As mais usadas primeiro, porque 21 botões em fila são quatro telas de
    # rolagem para quem está com a mercadoria na mão. Medido: seis lojas são 62%
    # das cargas.
    def botao_da_loja(numero, nome, prefixo=""):
        if st.button("%s%d · %s" % (prefixo, numero, nome),
                     key="loja_%s%d" % (prefixo and "top", numero),
                     use_container_width=True):
            st.session_state.numero_loja = str(numero)
            st.rerun()

    por_numero = dict(fc.LOJAS)
    for numero in fc.MAIS_USADAS:
        if numero in por_numero:
            botao_da_loja(numero, por_numero[numero], prefixo="⭐ ")

    with st.expander("Todas as lojas"):
        for numero, nome in fc.LOJAS:
            botao_da_loja(numero, nome)

    with st.expander("Outro lugar (digitar o número)"):
        digitado = st.text_input("Número", key="loja_digitada")
        if st.button("Confirmar ➡️"):
            if digitado.strip().isdigit():
                st.session_state.numero_loja = digitado.strip()
                st.rerun()
            else:
                st.warning("Digite só o número, por exemplo 20.")
    st.stop()

loja = st.session_state.numero_loja
st.info("📍 %s" % fc.nome_da_loja(loja))
if st.button("🔄 Trocar de loja", use_container_width=True):
    del st.session_state.numero_loja
    st.rerun()

tipo_fluxo = st.radio("Operação:", ["Entrada", "Saída"], horizontal=True)

# file_uploader, e NÃO camera_input: no celular ele abre a câmera do aparelho,
# que fotografa na resolução de verdade. E aceita várias de uma vez - carga
# raramente é uma foto só.
fotos = st.file_uploader(
    "Tirar foto (ou escolher da galeria)",
    type=["jpg", "jpeg", "png", "heic", "heif"],
    accept_multiple_files=True)

if fotos:
    st.caption("%d foto(s) prontas para enviar." % len(fotos))
    if st.button("📤 ENVIAR AGORA", use_container_width=True, type="primary"):
        quando = fc.agora_brasil()
        enviadas, falhas = 0, []
        barra = st.progress(0.0)

        for i, foto in enumerate(fotos, start=1):
            conteudo, mudanca, tamanho = fc.preparar_foto(foto.getvalue())
            nome = fc.nome_do_arquivo(quando, tipo_fluxo, loja, indice=i)
            ok, recado = enviar_ao_github(nome, conteudo)
            if ok:
                enviadas += 1
                # O tamanho aparece na tela de propósito: é assim que se vê que a
                # foto deixou de ser miniatura.
                st.success("✅ %s  ·  %s  ·  %d KB" % (nome, mudanca, tamanho // 1024))
            else:
                falhas.append((foto.name, recado))
            barra.progress(i / len(fotos))

        if falhas:
            st.error("%d foto(s) NÃO foram enviadas:" % len(falhas))
            for nome_original, recado in falhas:
                st.write("• **%s** — %s" % (nome_original, recado))
            st.info("As que falharam continuam no celular: dá para tentar de novo.")
        else:
            st.balloons()
            time.sleep(2)
            st.rerun()
