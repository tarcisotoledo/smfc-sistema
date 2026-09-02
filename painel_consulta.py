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
    ["📤 SAÍDA", "📥 ENTRADA", "🗄️ ARQUIVO (importar do GitHub)"])

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
