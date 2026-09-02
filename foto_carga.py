"""As regras das fotos de carga, sem Streamlit por perto.

Mora separado das telas por dois motivos:

1. **Dá para provar.** `teste_foto_carga.py` roda isto sem abrir navegador nem
   servidor, e mede em cima das fotos que já existem na pasta.
2. **O app do celular e o Painel liam o nome do arquivo cada um do seu jeito.**
   Duas leituras do mesmo formato divergem - foi o que aconteceu com a busca por
   loja, que casava "LOJA2" com "LOJA22".

Formato do nome, que é o contrato entre os dois programas:

    2026-09-01_13-05-22-01_ENTRADA_LOJA20.jpg
    |________| |_________|  |_____| |____|
      data     hora + nº     tipo    loja
                da foto
                do lote

O "-01" no fim da hora desempata fotos tiradas no mesmo segundo. Nomes antigos
não têm essa parte, e alguns não têm nem os segundos - os dois casos continuam
sendo lidos.
"""
import base64
import io
import os
import re
from datetime import datetime, timedelta, timezone

# Lado maior da foto guardada, e a qualidade do JPEG.
#
# Por que não os 12 MP do celular: 12 MP são ~4 MB por foto. No ritmo medido em
# 01/09/2026 (1.528 fotos em três meses e meio) o repositório passaria de 6 GB, e
# repositório do GitHub não é lugar para isso. A 2048 px com qualidade 88 a foto
# fica entre 400 KB e 1 MB - de 20 a 40 vezes mais pixels do que as 344x421 de
# hoje, e o repositório sustentável. Caixa, etiqueta e lacre ficam legíveis, que
# é para o que ela serve.
LADO_MAXIMO = 2048
QUALIDADE = 88

# As lojas, para o celular oferecer BOTÃO em vez de campo de digitar.
#
# Quem carrega este app é o motorista (e mais duas pessoas), e ele passa por
# várias lojas no mesmo dia - digitar o número a cada parada, no celular, dentro
# do caminhão, é onde nasce o erro. Cinco fotos já foram gravadas como "LOJAL9" e
# "LOJAL19", com a letra L no lugar do número, e nunca mais foram achadas na
# busca do Painel.
#
# A lista está escrita aqui porque este programa roda no Streamlit Cloud, que NÃO
# alcança o `cadastro_lojas.json` do OneDrive dele - são máquinas diferentes.
# Quando abrir ou fechar loja, é aqui que se mexe. Tirada do cadastro em
# 01/09/2026, e conferida contra ele: 21 lojas, os mesmos nomes.
LOJAS = (
    (2, 'CARREFOUR GALERIA'),
    (3, 'BANGU SHOPPING'),
    (4, 'RIO SHOPPING'),
    (6, 'GRANDE RIO SHOPPING'),
    (8, 'PARK SHOPPING'),
    (9, 'NOVA AMERICA'),
    (10, 'TERESOPOLIS'),
    (11, 'BARRA SHOPPING'),
    (12, 'PLAZA SHOPPING'),
    (14, 'MADUREIRA SHOPPING'),
    (16, 'ILHA PLAZA'),
    (17, 'LUXE'),
    (18, 'NITEROI PLAZA'),
    (19, 'TIJUCA'),
    (20, 'PARK JACAREPAGUA'),
    (21, 'LUXE DIAMOND'),
    (22, 'OUTLET SHOPPING'),
    (23, 'NS WORLD'),
    (24, 'LEBLON'),
    (25, 'LUXE RIBEIRÃO'),
    (26, 'BH OUT'),
)


# NAO existe mais lista de botoes na tela: o motorista pediu de volta o campo de
# digitar (02/09/2026), porque nao enxerga bem e o teclado ele ja sabe de cor.
# A lista LOJAS ficou por um motivo melhor - dar o NOME da loja como confirmacao
# do numero digitado. As que mais recebem carga, se um dia servir: 23, 9, 18, 22,
# 19 e 3, que somam 62% das 1.528 fotos medidas de 17/05 a 01/09/2026.


def nome_da_loja(numero):
    """"20 · PARK JACAREPAGUA", ou só o número quando não está na lista."""
    for num, nome in LOJAS:
        if str(num) == str(numero).strip():
            return "%s · %s" % (num, nome)
    return "Loja %s" % str(numero).strip()

PADRAO_NOME = re.compile(
    r'^(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}(?:-\d{2})?(?:-\d{2})?)_'
    r'(ENTRADA|SAIDA)_LOJA(\d+)\.jpe?g$', re.IGNORECASE)


def agora_brasil():
    """A hora de São Paulo, e não a do servidor.

    O Streamlit Cloud roda em UTC. Sem isto o nome do arquivo nasce 3 horas
    adiantado - medido em 01/09/2026: foto tirada 12:12 gravada como 15-12 - e a
    carga da noite cai com a data do dia seguinte, onde o Painel, que busca por
    data, não a encontra mais.
    """
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except Exception:
        # Sem a base de fusos: -03:00 fixo. O Brasil não tem horário de verão
        # desde 2019, então isto não erra.
        return datetime.now(timezone.utc) - timedelta(hours=3)


def nome_do_arquivo(quando, tipo, loja, indice=1):
    """O nome que vai para o repositório. `tipo` é "Entrada" ou "Saída"."""
    tipo_str = "SAIDA" if str(tipo).upper().startswith("SA") else "ENTRADA"
    return "%s-%02d_%s_LOJA%s.jpg" % (
        quando.strftime("%Y-%m-%d_%H-%M-%S"), int(indice), tipo_str,
        str(loja).strip())


def partes_do_nome(nome):
    """(data, hora, tipo, loja), ou None quando o nome não segue o padrão.

    None em vez de exceção: arquivo estranho na pasta não pode derrubar a busca
    nem ser contado como foto de alguma loja.
    """
    casou = PADRAO_NOME.match(str(nome))
    if not casou:
        return None
    return (casou.group(1), casou.group(2),
            casou.group(3).upper(), casou.group(4))


def preparar_foto(bruto):
    """Gira pelo EXIF e reduz. Devolve (bytes, descricao, tamanho_final).

    Foto de celular chega virada quando a pessoa fotografa deitado - o celular
    grava a orientação no EXIF em vez de girar os pixels, e quem não lê o EXIF
    mostra de lado.

    Falhando qualquer coisa (formato que o Pillow não abre, como HEIC de iPhone
    sem a biblioteca extra), devolve o arquivo COMO VEIO: reduzir é melhoria, não
    requisito, e foto grande é melhor do que foto nenhuma.
    """
    try:
        from PIL import Image, ImageOps
        with Image.open(io.BytesIO(bruto)) as imagem:
            imagem = ImageOps.exif_transpose(imagem)
            largura, altura = imagem.size
            if imagem.mode not in ("RGB", "L"):
                imagem = imagem.convert("RGB")
            imagem.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)
            saida = io.BytesIO()
            imagem.save(saida, format="JPEG", quality=QUALIDADE, optimize=True)
            dados = saida.getvalue()
            return (dados,
                    "%dx%d → %dx%d" % (largura, altura, imagem.size[0], imagem.size[1]),
                    len(dados))
    except Exception:
        return bruto, "enviada como veio (não consegui abrir para reduzir)", len(bruto)


def fotos_de(pasta, loja, data_str, tipo, corte_do_fuso="2026-09-01"):
    """As fotos daquela loja, naquele dia, daquele tipo: (do_dia, herdadas).

    A loja é comparada INTEIRA. Medido em 01/09/2026 nas 1.528 fotos: com a
    comparação por trecho que havia antes, procurar a loja 2 (4 fotos) devolvia
    432, e a loja 1 (nenhuma) devolvia 603 - das lojas 10, 12, 14, 16, 18 e 19.

    `herdadas` são as fotos da NOITE deste dia que ficaram gravadas com a data do
    dia seguinte, por causa do fuso do servidor, nos nomes anteriores ao corte.
    """
    if not os.path.isdir(pasta):
        return [], []

    alvo_tipo = "SAIDA" if str(tipo).upper().startswith("SA") else "ENTRADA"
    alvo_loja = str(loja).strip()
    do_dia, herdadas = [], []

    try:
        dia_seguinte = (datetime.strptime(data_str, "%Y-%m-%d")
                        + timedelta(days=1)).strftime("%Y-%m-%d")
    except ValueError:
        dia_seguinte = None

    for nome in sorted(os.listdir(pasta)):
        partes = partes_do_nome(nome)
        if not partes:
            continue
        data, hora, tipo_arq, loja_arq = partes
        if loja_arq != alvo_loja or tipo_arq != alvo_tipo:
            continue
        if data == data_str:
            do_dia.append(nome)
        elif (dia_seguinte and data == dia_seguinte and data < corte_do_fuso
              and hora[:2] in ("00", "01", "02")):
            herdadas.append(nome)

    return do_dia, herdadas

# ------------------------------------------------- o envio para o repositorio
CAMINHO_API = "https://api.github.com/repos/%s/%s/contents/%s/%s"


def enviar_ao_github(usuario, repo, pasta, nome, conteudo, token, pedir=None):
    """Manda a foto para o repositorio. Devolve (ok, recado).

    Mora aqui, e nao na tela, para PODER SER TESTADO: `pedir` e o requests.put,
    e o teste passa um falso para conferir o endereco, o cabecalho e o corpo.
    Este era o unico trecho do caminho da foto que nunca tinha sido provado - e
    em 02/09/2026 eu publiquei duas coisas quebradas justamente por confiar em
    trecho nao provado.

    O recado traz o que o GitHub respondeu, e nao um palpite: antes, qualquer
    falha dizia "Verifique o Token", inclusive internet caindo e foto repetida.
    """
    if not token:
        return False, ("Falta o GITHUB_TOKEN nas Secrets do Streamlit - "
                       "sem ele nenhuma foto sai.")
    if pedir is None:
        import requests
        pedir = requests.put

    url = CAMINHO_API % (usuario, repo, pasta, nome)
    try:
        resposta = pedir(
            url,
            headers={"Authorization": "token %s" % token,
                     "Accept": "application/vnd.github.v3+json"},
            json={"message": "Auditoria: %s" % nome,
                  "content": base64.b64encode(conteudo).decode()},
            timeout=60)
    except Exception as e:
        return False, "A internet caiu no meio do envio (%s)." % e

    if getattr(resposta, 'status_code', None) in (200, 201):
        return True, ""

    detalhe = ""
    try:
        detalhe = resposta.json().get("message", "")
    except Exception:
        detalhe = str(getattr(resposta, 'text', ''))[:200]
    return False, "O GitHub respondeu %s: %s" % (resposta.status_code, detalhe)
