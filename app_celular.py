"""Registro fotográfico de cargas, pelo celular do motorista.

Quem usa: o **motorista** e mais duas pessoas. Ele **não enxerga bem** - por isso
a tela é grande e o número da loja é digitado (ele pediu de volta em 02/09/2026,
depois de eu ter posto uma lista de 21 botões), com o NOME da loja aparecendo
como confirmação do número.

## Os quatro defeitos que a versão de 01→02/09/2026 corrigiu, todos medidos

1. **Foto miniatura:** 1.392 das 1.528 fotos tinham 344x421 px (0,14 MP), de
   celulares que fotografam a 12 MP. Culpa do `st.camera_input`, que captura no
   tamanho do widget na tela.
2. **Nome 3 horas adiantado:** o Streamlit Cloud roda em UTC, e a carga da noite
   caía com a data do dia seguinte - invisível para o Painel, que busca por data.
3. **Peso do upload:** trocar o `camera_input` pelo `file_uploader` fez o celular
   subir os 3,2 MB inteiros da câmera. Com celular ruim e sinal fraco, ZERO fotos
   chegaram. Agora a foto é reduzida **no próprio celular** pelo
   `componente_foto/index.html` (~700 KB), e o `camera_input` ficou como último
   recurso, num expander fechado.
4. **Erro que apontava para o lugar errado:** qualquer falha dizia "Verifique o
   Token", inclusive internet caindo.

As regras (hora, nome, redução, busca, envio) moram em `foto_carga.py`, sem
Streamlit, para poderem ser testadas - `teste_foto_carga.py`. Aqui fica só a tela.
"""
import base64
import importlib
import os
import time

import streamlit as st
import streamlit.components.v1 as components

import foto_carga as fc

# RELER O MÓDULO DO DISCO A CADA EXECUÇÃO.
#
# O Streamlit re-executa este arquivo a cada toque na tela, mas mantém os módulos
# importados EM MEMÓRIA. Quando um commit acrescenta uma função ao foto_carga e o
# processo do servidor não reinicia, fica valendo o app NOVO com o módulo VELHO -
# e o erro é um "AttributeError" com a mensagem escondida pelo Streamlit
# ("redacted to prevent data leaks"), que não diz nada a quem está na rua.
#
# Foi o que aconteceu em 02/09/2026, no primeiro envio depois de eu mover o
# `enviar_ao_github` para o foto_carga. A saída "reinicie o app" não serve: o
# botão Reboot só existe no computador, logado na conta dona do app - no celular
# não existe. Então o app passa a se resolver sozinho.
#
# O reload custa quase nada (o módulo é pequeno e não guarda estado) e vale para
# toda publicação futura: o que eu subir passa a valer sem depender de reinício.
importlib.reload(fc)

_FALTANDO = [_nome for _nome in ('enviar_ao_github', 'preparar_foto',
                                 'nome_do_arquivo', 'agora_brasil',
                                 'nome_da_loja', 'LADO_MAXIMO')
             if not hasattr(fc, _nome)]
if _FALTANDO:
    # Cinto e suspensório: se até o reload falhar, o recado é em português.
    st.error(
        "### ⚠️ Falta um pedaço do programa\n\n"
        "Não achei: %s.\n\n"
        "**Não é problema do celular nem da foto** — avise o Tarciso."
        % ", ".join(_FALTANDO))
    st.stop()

# O componente que reduz a foto NO CELULAR. É um componente estático: só um
# index.html, sem nada para compilar - ver o comentário dentro do arquivo.
componente_foto = components.declare_component(
    "foto_leve",
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "componente_foto"))

GITHUB_USER = "tarcisotoledo"
GITHUB_REPO = "smfc-sistema"
PASTA_NO_REPO = "fotos_recebidas"

st.set_page_config(page_title="SMFC Mobile", page_icon="📦")

# TUDO MAIOR: quem usa isto é o motorista, que não enxerga bem - ele mesmo
# pediu em 02/09/2026. Não é preferência de estilo, é o que decide se ele
# consegue trabalhar sem ajuda.
#
# O botão de tirar foto NÃO está aqui: ele é o `componente_foto/index.html`, que
# desenha o próprio botão e reduz a foto no celular. Antes era o botão do
# `file_uploader` renomeado por CSS.
st.markdown("""
    <style>
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
    /* A linha "200MB per file..." do Streamlit, em inglês, quando aparecer. */
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)


def enviar_ao_github(nome, conteudo):
    """So pega o token e chama a regra, que mora em foto_carga (com teste)."""
    try:
        token = st.secrets["GITHUB_TOKEN"]
    except Exception:
        token = ""
    return fc.enviar_ao_github(GITHUB_USER, GITHUB_REPO, PASTA_NO_REPO,
                               nome, conteudo, token)


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

# A FOTO É REDUZIDA NO PRÓPRIO CELULAR, antes de subir.
#
# Medido em 02/09/2026, do pior jeito: depois de eu trocar o `camera_input` pelo
# `file_uploader`, ZERO fotos chegaram ao repositório (a última foi 01/09 12:12,
# antes da minha versão). O motorista tentou e a tela ficou em "CONNECTING" com
# a foto de 3,2 MB marcada de vermelho — o celular dele é ruim e o sinal também.
#
# A causa era minha: a redução para 2048 px acontecia no SERVIDOR, depois do
# upload. O celular subia os 3,2 MB inteiros da câmera, quando antes subia 140 KB.
#
# Agora quem reduz é o `componente_foto/index.html`, rodando no celular: sobem
# ~700 KB com a mesma nitidez de 2048 px. Provado no navegador antes de publicar:
# 4000x3000 entra, 2048x1536 sai.
fotos = []

valor = componente_foto(lado_maximo=fc.LADO_MAXIMO,
                        rotulo="📸&nbsp;&nbsp;TIRAR FOTO",
                        key="camera_leve", default=None)

# O Streamlit reentrega o último valor do componente a cada recarregamento da
# tela. Sem este carimbo, a mesma foto seria enviada de novo depois do envio.
if valor and valor.get('fotos') and \
        st.session_state.get('lote_enviado') != valor.get('quando'):
    for f in valor['fotos']:
        try:
            fotos.append({'bytes': base64.b64decode(f['base64']),
                          'descricao': '%s → %s' % (f.get('de', '?'), f.get('para', '?')),
                          'nome': f.get('nome', 'foto.jpg'),
                          'lote': valor.get('quando')})
        except Exception:
            st.error("Uma das fotos chegou quebrada do celular. Tente tirar de novo.")

with st.expander("📶 Último recurso: foto pequena (só se a câmera não abrir)"):
    st.caption("Esta é a tela pequena de antes, com a foto sem nitidez. Ela sobe "
               "até com sinal muito fraco — use apenas se o botão de cima não "
               "abrir a câmera.")
    # Dentro do expander fechado de propósito: o `camera_input` pede permissão de
    # câmera e liga o vídeo assim que aparece na tela.
    rapida = st.camera_input("Foto rápida")
    if rapida:
        conteudo, descricao, _ = fc.preparar_foto(rapida.getvalue())
        fotos.append({'bytes': conteudo, 'descricao': descricao,
                      'nome': 'foto rápida', 'lote': None})

if fotos:
    st.caption("%d foto(s) prontas para enviar." % len(fotos))
    if st.button("📤 ENVIAR AGORA", use_container_width=True, type="primary"):
        quando = fc.agora_brasil()
        enviadas, falhas = 0, []
        barra = st.progress(0.0)

        for i, foto in enumerate(fotos, start=1):
            nome = fc.nome_do_arquivo(quando, tipo_fluxo, loja, indice=i)
            ok, recado = enviar_ao_github(nome, foto['bytes'])
            if ok:
                enviadas += 1
                # O tamanho aparece na tela de propósito: é assim que se vê que a
                # foto deixou de ser miniatura.
                st.success("✅ %s  ·  %s  ·  %d KB"
                           % (nome, foto['descricao'], len(foto['bytes']) // 1024))
                if foto['lote']:
                    st.session_state['lote_enviado'] = foto['lote']
            else:
                falhas.append((foto['nome'], recado))
            barra.progress(i / len(fotos))

        if falhas:
            st.error("%d foto(s) NÃO foram enviadas:" % len(falhas))
            for nome_original, recado in falhas:
                st.write("• **%s** — %s" % (nome_original, recado))
            st.info("As que falharam continuam no celular: dá para tentar de novo.")
        else:
            # Sem balões: ele pediu em 02/09/2026, e com razão - 20 cargas por
            # dia dariam 20 animações para esperar. A pausa curta existe só para
            # dar tempo de LER o ✅ antes da tela limpar para a próxima foto.
            st.success("Pronto. Pode tirar a próxima.")
            time.sleep(1.5)
            st.rerun()
