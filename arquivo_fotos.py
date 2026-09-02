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
