"""Painel de auditoria das fotos de carga — roda no PC dele.

## O desenho, na decisão dele (02/09/2026)

    "o github não ficasse com as imagens isso seria o trabalho do meu HD ele
     funcionaria como intermediário entre o celular e o meu pc"

    celular  ->  GitHub (corredor)  ->  este Painel  ->  E:\\Arquivo_WorldFree\\Fotos_Cargas
                                                              (o arquivo de verdade)

A aba **ARQUIVO** puxa o que chegou, move para o HD por mês e **esvazia a pasta do
repositório** com um commit — a ponte fica limpa. A busca olha o HD *e* a ponte,
porque entre uma importação e outra a foto do dia está lá, e foto invisível é o
mesmo que foto perdida.

**O que este Painel NÃO resolve:** o histórico do git guarda para sempre o que já
passou por ele (191 MB medidos em 02/09/2026). Esvaziar a pasta limpa o presente,
não o passado — isso é uma limpeza destrutiva à parte, que só ele pode mandar
fazer.

As regras (ler o nome, achar por loja/dia/tipo, mover, apagar) moram em
`foto_carga.py` e `arquivo_fotos.py`, sem Streamlit, e têm teste:
`teste_foto_carga.py` e `teste_arquivo_fotos.py`.
"""
import os
import subprocess
from datetime import datetime

import streamlit as st

import arquivo_fotos as af
import foto_carga as fc          # só para o NOME da loja, na confirmação

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_PONTE = os.path.join(BASE_DIR, "fotos_recebidas")

st.set_page_config(page_title="Fotos de Carga", page_icon="🔍", layout="wide")

st.markdown("""
    <style>
    html, body, [class*="ViewContainer"] { font-size: 20px !important; }
    .stButton>button {
        height: 3.4em; width: 100%; font-size: 22px !important;
        font-weight: bold; color: white !important;
        background-color: #007bff !important; border-radius: 10px;
    }
    .stTextInput>div>div>input { font-size: 22px !important; height: 2.6em; }
    </style>
    """, unsafe_allow_html=True)

st.title("🔍 FOTOS DE CARGA")


def rodar_git(*argumentos, minutos=5):
    """Roda git na pasta do repositório. Devolve (ok, saída)."""
    try:
        r = subprocess.run(('git',) + argumentos, cwd=BASE_DIR,
                           capture_output=True, text=True, timeout=minutos * 60)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except Exception as e:
        return False, str(e)


def fotos_na_ponte():
    if not os.path.isdir(PASTA_PONTE):
        return []
    return [n for n in os.listdir(PASTA_PONTE)
            if os.path.isfile(os.path.join(PASTA_PONTE, n))]


# ------------------------------------------------------------------- a busca
def buscar_e_exibir(tipo):
    col1, col2 = st.columns(2)
    with col1:
        loja = st.text_input("Número da Loja:", key="loja_%s" % tipo)
    with col2:
        data_sel = st.date_input("Data da Carga:", datetime.now(), key="data_%s" % tipo)

    if not st.button("BUSCAR %s 🔍" % tipo.upper(), key="btn_%s" % tipo):
        return

    if not str(loja).strip().isdigit():
        return st.warning("Digite o número da loja — só números, por exemplo 20.")

    data_str = data_sel.strftime("%Y-%m-%d")
    achadas = af.fotos_de(loja, data_str, tipo, pasta_ponte=PASTA_PONTE)

    if not achadas:
        return st.warning("⚠️ Nenhuma foto de %s da Loja %s em %s."
                          % (tipo, loja, data_sel.strftime('%d/%m/%Y')))

    st.success("✅ %d foto(s)." % len(achadas))
    for caminho, nome in achadas:
        onde = "ponte (ainda não importada)" if caminho.startswith(PASTA_PONTE) \
               else os.path.basename(os.path.dirname(caminho))
        tamanho = os.path.getsize(caminho) // 1024
        st.image(caminho, use_container_width=True,
                 caption="%s  ·  %d KB  ·  %s" % (nome, tamanho, onde))
        # Exclusão pontual, que ele pediu: "um programa para consulta e exclusão".
        if st.checkbox("apagar esta foto do arquivo", key="del_%s" % caminho):
            if st.button("APAGAR AGORA — %s" % nome, key="btndel_%s" % caminho):
                n, erros = af.apagar([caminho])
                if n:
                    st.success("Apagada. Ela sai do HD e não volta.")
                if erros:
                    st.error("; ".join(erros))


aba_saida, aba_entrada, aba_arquivo = st.tabs(
    ["📤 SAÍDA", "📥 ENTRADA", "🗄️ ARQUIVO (do app e do WhatsApp)"])

with aba_saida:
    buscar_e_exibir("Saida")

with aba_entrada:
    buscar_e_exibir("Entrada")

# ----------------------------------------------------------------- o arquivo
with aba_arquivo:
    st.subheader("🗄️ O arquivo mora no HD; o GitHub é só o corredor")

    ok_hd, motivo_hd = af.destino_disponivel()
    if ok_hd:
        st.caption("Arquivo em **%s**" % af.PASTA_ARQUIVO)
    else:
        st.error("⚠️ %s — sem ele nada pode ser importado." % motivo_hd)

    r = af.resumo()
    na_ponte = fotos_na_ponte()
    col1, col2 = st.columns(2)
    col1.metric("No HD (arquivo)", "%d fotos" % r['fotos'],
                "%.0f MB" % (r['bytes'] / 1048576) if r['fotos'] else None)
    col2.metric("Na ponte (GitHub)", "%d arquivo(s)" % len(na_ponte))

    st.write("")
    if st.button("📥 IMPORTAR: trazer do GitHub e guardar no HD", disabled=not ok_hd):
        registro = st.container()

        # 1) As fotos que uma faxina antiga apagou do disco voltam ANTES de tudo:
        #    elas nunca foram para o HD, e commitar a exclusão as tiraria da
        #    única cópia que existe. Foi o caso das 225 de 02/09/2026.
        with st.spinner("Recuperando o que faltava no disco..."):
            ok, saida = rodar_git('checkout', '--', 'fotos_recebidas')
            if not ok:
                registro.warning("git checkout: %s" % saida[:300])

        with st.spinner("Buscando fotos novas no GitHub..."):
            ok, saida = rodar_git('pull', 'origin', 'main')
            registro.write("**git pull:** %s" % (saida[:300] or "sem novidades"))
            if not ok:
                registro.error("Não consegui puxar do GitHub. Nada foi movido.")
                st.stop()

        with st.spinner("Movendo para o HD..."):
            res = af.importar(PASTA_PONTE)

        registro.success("**%d foto(s) movidas para o HD.**" % res['movidas'])
        if res['ja_existiam']:
            registro.info("%d já estavam no arquivo (reenvio do celular)."
                          % res['ja_existiam'])
        if res['ignoradas']:
            registro.warning(
                "%d arquivo(s) com nome fora do padrão ficaram na ponte, de "
                "propósito — apagar o que não se entende é a forma mais rápida "
                "de perder prova:\n\n%s"
                % (len(res['ignoradas']), ", ".join(res['ignoradas'][:8])))
        if res['erros']:
            registro.error("Erros:\n\n" + "\n".join(res['erros'][:8]))

        # 2) Esvazia a ponte no GitHub - só o que de fato foi para o HD.
        if res['movidas'] or res['ja_existiam']:
            with st.spinner("Esvaziando a ponte no GitHub..."):
                ok, saida = rodar_git('add', '-A', 'fotos_recebidas')
                if ok:
                    ok, saida = rodar_git(
                        'commit', '-m',
                        'Ponte esvaziada: %d foto(s) arquivadas no HD' % res['movidas'])
                if ok or 'nothing to commit' in saida:
                    ok, saida = rodar_git('push', 'origin', 'master:main')
                if ok:
                    registro.success("Ponte esvaziada no GitHub.")
                else:
                    registro.error(
                        "As fotos ESTÃO salvas no HD, mas não consegui esvaziar a "
                        "ponte:\n\n%s\n\nNada foi perdido: na próxima importação "
                        "ele tenta de novo." % saida[:400])
        st.rerun()

    # ------------------------------------------- fotos que vieram pelo WhatsApp
    st.write("")
    st.markdown("---")
    st.subheader("📲 Importar fotos que vieram pelo WhatsApp")
    st.caption(
        "Quando ele manda pelo WhatsApp em vez do app — que é o que ele faz: "
        "salve as fotos e traga aqui. Os dois caminhos terminam no mesmo "
        "arquivo, então não depende de ele mudar de hábito.")

    # SEM DIGITAR CAMINHO: ele escolhe na janela do Windows ou arrasta as fotos
    # do WhatsApp Web para cá. A primeira versão pedia o caminho da pasta de
    # download - dois cliques valem mais do que um caminho colado, e ainda
    # funciona com foto que está em qualquer lugar.
    escolhidas = st.file_uploader(
        "Arraste as fotos aqui, ou clique para escolher:",
        type=['jpg', 'jpeg', 'png', 'webp'], accept_multiple_files=True,
        key="zap_arquivos")

    if not escolhidas:
        st.info("Nada escolhido ainda. No WhatsApp Web: baixe as fotos da "
                "conversa e arraste para o quadro acima.")
    else:
        st.success("**%d foto(s)** prontas para arquivar." % len(escolhidas))

        c1, c2, c3 = st.columns([2, 3, 2])
        with c1:
            loja_zap = st.text_input("Número da loja:", key="loja_zap")
            nome_zap = ""
            if str(loja_zap).strip().isdigit():
                nome_zap = fc.nome_da_loja(loja_zap.strip())
                if nome_zap.startswith("Loja "):
                    st.warning(nome_zap)
                else:
                    st.success(nome_zap)
        with c2:
            # "saiu / chegou" em vez de Entrada/Saída: entrada de quê, do
            # caminhão ou da loja? A palavra tem de dizer sozinha.
            #
            # O padrão é CHEGOU porque é o que ele descreveu em 02/09/2026:
            # "estava chegando na loja 19 e tirou as fotos".
            direcao = st.radio("Estas fotos são de:",
                               ["a carga CHEGOU nesta loja",
                                "a carga SAIU desta loja"], key="dir_zap")
        with c3:
            dia_zap = st.date_input("Dia:", datetime.now(), key="dia_zap")
            hora_zap = st.text_input("Hora (hh:mm):",
                                     value=datetime.now().strftime("%H:%M"),
                                     key="hora_zap")

        tipo_zap = "Saida" if "SAIU" in direcao else "Entrada"
        st.caption(
            "A hora importa: é ela que põe as fotos na ordem da viagem. Duas "
            "lojas seguidas no mesmo dia contam a transferência sozinhas — "
            "o que ele fotografou às 11:50 na 19 e depois na 16 é a mesma carga.")

        if st.button("📲 ARQUIVAR ESTAS FOTOS NO HD", disabled=not ok_hd):
            hh, mm = 12, 0
            partes_hora = str(hora_zap).replace('h', ':').split(':')
            try:
                hh = int(partes_hora[0])
                mm = int(partes_hora[1]) if len(partes_hora) > 1 else 0
            except (ValueError, IndexError):
                pass
            if not str(loja_zap).strip().isdigit():
                st.error("Digite o número da loja — só números.")
            elif not (0 <= hh <= 23 and 0 <= mm <= 59):
                st.error("Hora fora do relógio: escreva como 11:50.")
            else:
                quando = datetime.combine(dia_zap, datetime.min.time()).replace(
                    hour=hh, minute=mm)
                # (nome, bytes): o arquivo escolhido nunca sai do lugar de origem.
                lote = [(f.name, f.getvalue()) for f in escolhidas]
                res = af.importar_do_whatsapp(lote, loja_zap.strip(), tipo_zap,
                                              quando=quando)
                if res['arquivadas']:
                    st.success("**%d foto(s) arquivadas** — %s, %s, %s."
                               % (len(res['arquivadas']),
                                  fc.nome_da_loja(loja_zap.strip()),
                                  direcao.replace('a carga ', ''),
                                  quando.strftime('%d/%m às %H:%M')))
                    for origem, destino in res['arquivadas'][:12]:
                        st.write("· %s → **%s**" % (origem, destino))
                    st.caption(
                        "A hora do nome é a que você informou — a origem de cada "
                        "arquivo fica registrada em `%s`, no HD, para depois "
                        "ninguém confundir foto do app com foto do WhatsApp."
                        % af.MANIFESTO)
                if res['erros']:
                    st.error("Erros:\n\n" + "\n".join(res['erros'][:8]))

    if r['por_mes']:
        st.write("")
        st.write("**O que há no HD, por mês:**")
        st.table([{'Mês': mes, 'Fotos': d['fotos'],
                   'Espaço': "%.0f MB" % (d['bytes'] / 1048576)}
                  for mes, d in sorted(r['por_mes'].items(), reverse=True)])

    st.write("")
    st.info(
        "**O histórico do git.** Esvaziar a pasta limpa o presente, não o "
        "passado: o que já passou pela ponte continua guardado no histórico do "
        "GitHub (191 MB medidos em 02/09/2026, e cada foto nova soma). Para o "
        "repositório encolher de verdade é preciso uma limpeza destrutiva do "
        "histórico, ou uma ponte separada do código — decisão sua, não faço "
        "sozinho.")
