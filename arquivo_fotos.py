"""O arquivo das fotos de carga: o HD secundário guarda, o GitHub só atravessa.

## O pedido dele (02/09/2026)

    "eu que queria de verdade seria o github não ficasse com as imagens isso
     seria o trabalho do meu HD ele funcionaria como intermediário entre o
     celular e o meu pc onde ele guardaria as fotos, e do meu pc para ele quando
     eu fosse consultar as fotos caso tenhamos algum problema com a saida ou
     entrada de mercadoria, caso não poça ter intermédio entre pc e github
     poderia fazer um programa para consulta e exclusão se for o caso"

Ele apagou 225 fotos do disco achando que aliviava o GitHub - e não aliviava: o
repositório tinha (e tem) as 1.528, e o histórico do git guarda tudo para sempre.

Medido em 02/09/2026, para dar tamanho ao problema:

    .git (o que o GitHub guarda) ....... 191 MB
    fotos por mês ...................... ~450  (jun 398, jul 453, ago 477)
    peso novo por foto ................. ~700 KB  -> ~315 MB/mês

## O caminho, agora

    celular  ->  GitHub (corredor)  ->  ESTE MÓDULO  ->  E:\\Arquivo_WorldFree\\Fotos_Cargas\\AAAA-MM
                                                              (o arquivo de verdade)

A pasta do repositório fica VAZIA depois de cada importação. O que o histórico do
git já carrega não sai daqui - isso depende de uma limpeza à parte, que ele tem
de mandar fazer, porque é destrutiva.

Por que uma pasta por mês: 450 fotos/mês num diretório só viram 20 mil arquivos
em quatro anos, e o Explorer do Windows engasga. Por mês, cada pasta fica com o
tamanho de uma gaveta.
"""
import os
import shutil

# O mesmo HD secundário onde vive o arquivo morto das notas.
PASTA_ARQUIVO = r"E:\Arquivo_WorldFree\Fotos_Cargas"

# Lido de foto_carga para não ter duas leituras do nome do arquivo - já
# divergiram uma vez (a busca por loja casava "LOJA2" com "LOJA22").
from foto_carga import partes_do_nome


def destino_disponivel(pasta=None):
    """O HD está aí e dá para escrever? (True, '') ou (False, motivo).

    Sem plano B em pasta local, de propósito: arquivo no mesmo disco do sistema
    é o que ele já tinha, e não é arquivo.
    """
    pasta = pasta or PASTA_ARQUIVO
    raiz = os.path.splitdrive(pasta)[0] or pasta
    if not os.path.exists(raiz + os.sep):
        return False, "o HD %s não está disponível nesta máquina" % raiz
    try:
        os.makedirs(pasta, exist_ok=True)
        teste = os.path.join(pasta, '.escrita_ok')
        with open(teste, 'wb') as f:
            f.write(b'1')
        os.remove(teste)
        return True, ''
    except Exception as e:
        return False, "não consegui escrever em %s (%s)" % (pasta, e)


def mes_do_nome(nome):
    """"2026-09" a partir do nome do arquivo, ou None quando não dá para ler."""
    partes = partes_do_nome(nome)
    if not partes:
        return None
    return partes[0][:7]


def importar(pasta_ponte, pasta_arquivo=None, mover=True):
    """Leva as fotos da ponte para o arquivo do HD, em pastas por mês.

    Devolve {'movidas': n, 'ja_existiam': n, 'erros': [...], 'ignoradas': [...],
             'nomes': [...]}.

    - Arquivo com nome fora do padrão é IGNORADO e devolvido na lista, nunca
      apagado: os cinco "LOJAL9" são disso, e apagar o que não se entende é a
      forma mais rápida de perder prova.
    - Foto que já existe no arquivo (mesmo nome e mesmo tamanho) conta como
      `ja_existiam` e sai da ponte - não é erro, é reimportação.
    - `mover=False` copia em vez de mover, para o teste conferir sem destruir.
    """
    resultado = {'movidas': 0, 'ja_existiam': 0, 'erros': [], 'ignoradas': [],
                 'nomes': []}
    pasta_arquivo = pasta_arquivo or PASTA_ARQUIVO

    if not os.path.isdir(pasta_ponte):
        resultado['erros'].append('a pasta da ponte não existe: %s' % pasta_ponte)
        return resultado

    ok, motivo = destino_disponivel(pasta_arquivo)
    if not ok:
        resultado['erros'].append(motivo)
        return resultado

    for nome in sorted(os.listdir(pasta_ponte)):
        origem = os.path.join(pasta_ponte, nome)
        if not os.path.isfile(origem):
            continue
        mes = mes_do_nome(nome)
        if not mes:
            resultado['ignoradas'].append(nome)
            continue

        destino_pasta = os.path.join(pasta_arquivo, mes)
        destino = os.path.join(destino_pasta, nome)
        try:
            os.makedirs(destino_pasta, exist_ok=True)
            if os.path.exists(destino):
                if os.path.getsize(destino) == os.path.getsize(origem):
                    if mover:
                        os.remove(origem)
                    resultado['ja_existiam'] += 1
                    continue
                # Mesmo nome e tamanho diferente: guarda as duas, sem escolher.
                raiz, ext = os.path.splitext(nome)
                n = 2
                while os.path.exists(destino):
                    destino = os.path.join(destino_pasta, '%s (%d)%s' % (raiz, n, ext))
                    n += 1
            if mover:
                shutil.move(origem, destino)
            else:
                shutil.copy2(origem, destino)
            resultado['movidas'] += 1
            resultado['nomes'].append(os.path.basename(destino))
        except Exception as e:
            resultado['erros'].append('%s: %s' % (nome, e))

    return resultado


def fotos_de(loja, data_str, tipo, pasta_arquivo=None, pasta_ponte=None,
             corte_do_fuso="2026-09-01"):
    """As fotos daquela loja, naquele dia: [(caminho, nome)], mais antigas primeiro.

    Procura no ARQUIVO (todas as pastas de mês) e TAMBÉM na ponte, porque entre
    uma importação e outra a foto do dia está lá - e foto invisível é o mesmo que
    foto perdida.

    A loja é comparada INTEIRA e a carga da noite com nome antigo (UTC) entra:
    as duas regras moram em foto_carga.fotos_de, e aqui só se aplica a cada pasta.
    """
    from foto_carga import fotos_de as fotos_da_pasta

    pasta_arquivo = pasta_arquivo or PASTA_ARQUIVO
    achadas = []

    pastas = []
    if os.path.isdir(pasta_arquivo):
        for mes in sorted(os.listdir(pasta_arquivo)):
            caminho = os.path.join(pasta_arquivo, mes)
            if os.path.isdir(caminho):
                pastas.append(caminho)
    if pasta_ponte and os.path.isdir(pasta_ponte):
        pastas.append(pasta_ponte)

    for pasta in pastas:
        do_dia, herdadas = fotos_da_pasta(pasta, loja, data_str, tipo,
                                          corte_do_fuso=corte_do_fuso)
        for nome in do_dia + herdadas:
            achadas.append((os.path.join(pasta, nome), nome))

    achadas.sort(key=lambda x: x[1])
    return achadas


def apagar(caminhos):
    """Apaga do arquivo. Devolve (quantas, [erros]). Sem volta - quem chama avisa."""
    apagadas, erros = 0, []
    for caminho in caminhos:
        try:
            os.remove(caminho)
            apagadas += 1
        except Exception as e:
            erros.append('%s: %s' % (os.path.basename(caminho), e))
    return apagadas, erros


def resumo(pasta_arquivo=None):
    """Quantas fotos e quanto espaço o arquivo tem, por mês."""
    pasta_arquivo = pasta_arquivo or PASTA_ARQUIVO
    por_mes = {}
    total_bytes = 0
    if not os.path.isdir(pasta_arquivo):
        return {'fotos': 0, 'bytes': 0, 'por_mes': {}}

    for mes in sorted(os.listdir(pasta_arquivo)):
        caminho = os.path.join(pasta_arquivo, mes)
        if not os.path.isdir(caminho):
            continue
        quantas, bytes_mes = 0, 0
        for nome in os.listdir(caminho):
            arquivo = os.path.join(caminho, nome)
            if os.path.isfile(arquivo):
                quantas += 1
                bytes_mes += os.path.getsize(arquivo)
        if quantas:
            por_mes[mes] = {'fotos': quantas, 'bytes': bytes_mes}
            total_bytes += bytes_mes

    return {'fotos': sum(m['fotos'] for m in por_mes.values()),
            'bytes': total_bytes, 'por_mes': por_mes}


# ------------------------------------------- fotos que vieram pelo WhatsApp
MANIFESTO = 'importadas_do_whatsapp.csv'


def importar_do_whatsapp(caminhos, loja, tipo, quando=None, pasta_arquivo=None,
                         mover=False):
    """Renomeia e arquiva fotos soltas, baixadas do WhatsApp.

    Existe por um problema que nao e de software (02/09/2026), nas palavras dele:

        "meu maior problema e que ele trabalha do jeito que ele quer se eu pedir
         ele vai fazer durante um tempo e depois ele volta a fazer tudo errado
         novamente, infelizmente nao tenho controle sobre ele"

    Avisado da mudanca no app, o motorista mandou as fotos pelo WhatsApp. Nao ha
    como consertar isso pedindo disciplina - entao os DOIS caminhos passam a
    terminar no mesmo arquivo: se ele usa o app, ja esta arquivado; se manda pelo
    WhatsApp, ele importa aqui em dois cliques.

    E resolve o impasse do entrada/saida: quem sabe a direcao e QUEM COMBINOU A
    TRANSFERENCIA, nao o motorista no meio da rua. A direcao entra aqui, uma vez
    por lote.

    `caminhos`: as fotos, de duas formas que valem igual -
        - caminho de arquivo no disco (uma pasta de downloads), ou
        - `(nome_original, bytes)`, que e o que o seletor de arquivos do Painel
          entrega. Assim ele nao precisa digitar caminho nenhum: escolhe as
          fotos na janela do Windows, ou arrasta para a tela.
    `tipo`: "Entrada" ou "Saida" - um lote por ponta da viagem.
    `quando`: o dia da carga (padrao: hoje). A HORA do nome vem da hora do
              arquivo quando ela cai no dia escolhido; senao, do meio-dia mais o
              indice. A hora de foto vinda do WhatsApp e aproximada, e por isso
              a origem de cada arquivo fica registrada no MANIFESTO.

    Devolve {'arquivadas': [(origem, destino)], 'erros': [...]}.
    """
    from datetime import datetime
    import csv as _csv

    from foto_carga import nome_do_arquivo, preparar_foto

    resultado = {'arquivadas': [], 'erros': []}
    pasta_arquivo = pasta_arquivo or PASTA_ARQUIVO
    quando = quando or datetime.now()

    if not str(loja).strip().isdigit():
        resultado['erros'].append('o numero da loja tem de ser so numero')
        return resultado

    ok, motivo = destino_disponivel(pasta_arquivo)
    if not ok:
        resultado['erros'].append(motivo)
        return resultado

    mes = quando.strftime('%Y-%m')
    destino_pasta = os.path.join(pasta_arquivo, mes)
    os.makedirs(destino_pasta, exist_ok=True)

    def _chave(item):
        return item[0] if isinstance(item, (tuple, list)) else item

    for i, item in enumerate(sorted(caminhos, key=_chave), start=1):
        origem = _chave(item)
        try:
            if isinstance(item, (tuple, list)):
                # Veio do seletor do Painel: nome + conteudo, sem disco.
                bruto = item[1]
                do_arquivo = None
            else:
                with open(origem, 'rb') as f:
                    bruto = f.read()
                # A hora: a do arquivo, se for do mesmo dia; senao meio-dia +
                # indice.
                try:
                    do_arquivo = datetime.fromtimestamp(os.path.getmtime(origem))
                except OSError:
                    do_arquivo = None
            if do_arquivo and do_arquivo.date() == quando.date():
                momento = do_arquivo
            else:
                # Sem hora confiavel no arquivo, vale a hora que ELE informou
                # (ex.: "chegou na 19 as 11:50"). O segundo separa os nomes.
                momento = quando.replace(second=min(59, i), microsecond=0)

            nome = nome_do_arquivo(momento, tipo, loja, indice=i)
            destino = os.path.join(destino_pasta, nome)
            raiz, ext = os.path.splitext(nome)
            n = 2
            while os.path.exists(destino):
                destino = os.path.join(destino_pasta, '%s (%d)%s' % (raiz, n, ext))
                n += 1

            # Passa pelo mesmo redutor do app: arquivo com tamanhos parecidos, e
            # foto de 3 MB baixada do celular nao entra crua no arquivo.
            conteudo, _descricao, _tam = preparar_foto(bruto)
            with open(destino, 'wb') as f:
                f.write(conteudo)

            # De onde veio cada arquivo, para a hora aproximada nao virar
            # afirmacao: o manifesto guarda o nome original e a data da importacao.
            try:
                caminho_manifesto = os.path.join(pasta_arquivo, MANIFESTO)
                novo = not os.path.exists(caminho_manifesto)
                with open(caminho_manifesto, 'a', encoding='utf-8-sig',
                          newline='') as f:
                    escritor = _csv.writer(f, delimiter=';')
                    if novo:
                        escritor.writerow(['Importado_em', 'Arquivo_no_arquivo',
                                           'Nome_original', 'Loja', 'Tipo',
                                           'Hora_aproximada'])
                    escritor.writerow([
                        datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                        os.path.basename(destino), os.path.basename(origem),
                        str(loja).strip(), tipo,
                        'sim' if not (do_arquivo and do_arquivo.date() == quando.date()) else 'nao'])
            except Exception:
                pass          # o manifesto e registro extra, nao pode barrar

            if mover:
                try:
                    os.remove(origem)
                except Exception:
                    pass
            resultado['arquivadas'].append((os.path.basename(origem),
                                            os.path.basename(destino)))
        except Exception as e:
            resultado['erros'].append('%s: %s' % (os.path.basename(origem), e))

    return resultado


def fotos_soltas(pasta, so_imagens=True):
    """Os arquivos de imagem de uma pasta que NAO seguem o padrao do sistema.

    Serve para o Painel oferecer o que baixou do WhatsApp sem misturar com o que
    ja esta arquivado.
    """
    if not os.path.isdir(pasta):
        return []
    achados = []
    for nome in sorted(os.listdir(pasta)):
        caminho = os.path.join(pasta, nome)
        if not os.path.isfile(caminho):
            continue
        if so_imagens and not nome.lower().endswith(('.jpg', '.jpeg', '.png',
                                                     '.heic', '.heif', '.webp')):
            continue
        if partes_do_nome(nome):
            continue          # ja esta no padrao: veio do app, nao do WhatsApp
        achados.append(caminho)
    return achados
