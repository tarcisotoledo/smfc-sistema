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

# O BOTÃO DE TIRAR FOTO.
#
# O `st.camera_input` antigo mostrava um botão "Tirar Foto" na própria página -
# e era isso que dava a foto de 344x421, porque ele captura no tamanho do widget.
# O `st.file_uploader`, que usa a câmera do aparelho e dá a resolução de verdade,
# vem com um botão que diz "Upload": ninguém olha isso e pensa em fotografar.
#
# Então o rótulo do botão é trocado aqui, por CSS. É CSS no documento da própria
# página (o `st.markdown` injeta no DOM do app, sem iframe), e não um truque de
# JavaScript mexendo no DOM de fora - se um dia o Streamlit mudar as classes, o
# botão volta a dizer "Upload" e CONTINUA FUNCIONANDO. A falha é cosmética, não
# quebra o envio.
st.markdown("""
    <style>
    /* O botão do uploader vira o botão de tirar foto: grande, colorido, e com
       texto em português. */
    [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
        width: 100% !important;
        min-height: 4.2em !important;
        background-color: #d92d20 !important;
        border: none !important;
        border-radius: 12px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    /* Esconde o "Upload" original SEM removê-lo - leitor de tela continua lendo,
       e o texto novo fica centralizado porque o antigo deixa de ocupar espaço.
       (É o padrão "visually hidden"; font-size: 0 sozinho descentralizava.) */
    [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] > * {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        overflow: hidden !important;
        clip-path: inset(50%) !important;
    }
    [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"]::after {
        content: "📸  TIRAR FOTO";
        color: #ffffff;
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: .5px;
    }
    /* A linha "200MB per file • JPG, PNG..." é do Streamlit e vem em inglês. */
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }

    /* TUDO MAIOR: quem usa isto é o motorista, que não enxerga bem — ele
       mesmo pediu em 02/09/2026. Não é preferência de estilo, é o que decide
       se ele consegue trabalhar sem ajuda. */
    [data-testid="stRadio"] label p { font-size: 1.4rem !important; }
    /* O campo do número da loja: fonte grande e centralizada, para ele
       conferir o que digitou sem aproximar o celular do olho. */
    [data-testid="stTextInput"] input {
        font-size: 2.2rem !important;
        height: 3.2em !important;
        text-align: center !important;
        font-weight: 800 !important;
        letter-spacing: 2px !important;
    }
    [data-testid="stTextInput"] label p { font-size: 1.3rem !important; }
    /* O aviso da loja escolhida, que é a confirmação que evita foto na loja
       errada. */
    [data-testid="stAlert"] p { font-size: 1.5rem !important; font-weight: 700 !important; }
    </style>
    """, unsafe_allow_html=True)


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
    # DIGITAR o número, como era antes - o motorista pediu de volta em
    # 02/09/2026: ele não enxerga bem, e a lista de 21 botões era pior para ele
    # do que o teclado, que ele já sabia de cor.
    #
    # O que ficou da tentativa dos botões: o NOME da loja aparece grande, como
    # confirmação. Digitar sozinho foi o que gerou cinco arquivos "LOJAL9" e
    # "LOJAL19", perdidos para sempre na busca do Painel; agora só entra número,
    # e ele confere lendo o nome em vez de reler o dígito.
    st.write("## Qual é o número da loja?")
    digitado = st.text_input("Digite e confira o nome que aparecer:",
                             key="loja_digitada", max_chars=3)

    numero = digitado.strip()
    if numero and not numero.isdigit():
        st.error("### Só números, por favor — por exemplo **20**.")
    elif numero:
        # A confirmação pelo NOME: se ele digitou 22 querendo 2, ele lê
        # "OUTLET SHOPPING" e percebe ANTES de fotografar.
        nome = fc.nome_da_loja(numero)
        if nome.startswith("Loja "):
            st.warning("### %s\nEste número não está na minha lista." % nome)
        else:
            st.success("### %s" % nome)

    if st.button("CONFIRMAR ➡️", use_container_width=True, type="primary"):
        if numero.isdigit():
            st.session_state.numero_loja = numero
            st.rerun()
        else:
            st.error("Digite o número da loja antes de continuar.")
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
# DOIS CAMINHOS, porque eles custam coisas diferentes - e um deles tem de
# funcionar SEMPRE.
#
# Medido em 02/09/2026, o pior jeito de descobrir: depois de eu trocar o
# `camera_input` pelo `file_uploader`, ZERO fotos chegaram ao repositório (a
# última foi 01/09 12:12, antes da minha versão). O motorista tentou e a tela
# ficou em "CONNECTING" com a foto marcada de vermelho.
#
# A causa é minha: a redução para 2048 px acontece no SERVIDOR, depois do
# upload. O celular passou a subir os 3,2 MB inteiros da câmera, quando antes
# subia 140 KB. Em dado móvel, dentro de um caminhão, isso não sobe.
#
# Então: a foto nítida continua sendo o caminho principal, e a rápida existe
# para quando o sinal não deixa. Quem escolhe é quem está lá, sabendo o preço.
fotos = []

nitidas = st.file_uploader(
    "Toque no botão e escolha **Câmera** (ou a galeria, se a foto já está lá):",
    type=["jpg", "jpeg", "png", "heic", "heif"],
    accept_multiple_files=True)
if nitidas:
    fotos.extend(nitidas)

with st.expander("📶 A foto não sobe? Toque aqui para a FOTO RÁPIDA"):
    st.caption("A foto rápida é bem menor e sobe com sinal fraco. A nitidez é "
               "pior — use quando a de cima não conseguir subir.")
    # Dentro do expander de propósito: o `camera_input` pede permissão de
    # câmera e liga o vídeo assim que aparece na tela. Fechado, ele não incomoda
    # quem não precisa dele.
    rapida = st.camera_input("Foto rápida")
    if rapida:
        fotos.append(rapida)

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
