# -*- coding: utf-8 -*-
"""Prova das regras das fotos de carga, sem abrir navegador nem servidor.

    python teste_foto_carga.py

Mede também em cima das fotos que já estão na pasta, quando ela existe.
"""
import io
import os
import shutil
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import foto_carga as fc

PASTA_REAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fotos_recebidas')


def teste_leitura_do_nome():
    # O formato novo, com o indice do lote:
    assert fc.partes_do_nome('2026-09-01_13-05-22-01_ENTRADA_LOJA20.jpg') == \
        ('2026-09-01', '13-05-22-01', 'ENTRADA', '20')
    # O formato antigo, com segundos:
    assert fc.partes_do_nome('2026-05-17_15-03-57_ENTRADA_LOJA8.jpg') == \
        ('2026-05-17', '15-03-57', 'ENTRADA', '8')
    # E o mais antigo ainda, SEM segundos - existe na pasta:
    assert fc.partes_do_nome('2026-05-17_13-04_SAIDA_LOJA8.jpg') == \
        ('2026-05-17', '13-04', 'SAIDA', '8')
    # Lixo na pasta não vira foto de ninguém:
    for ruim in ('desktop.ini', 'foto.jpg', '2026-09-01_ENTRADA_LOJA20.jpg',
                 '2026-09-01_13-05_ENTRADA_LOJA.jpg', ''):
        assert fc.partes_do_nome(ruim) is None, ruim
    print('ok  le os tres formatos de nome que existem, e recusa lixo')


def teste_nome_do_arquivo():
    quando = datetime(2026, 9, 1, 13, 5, 22)
    assert fc.nome_do_arquivo(quando, 'Entrada', '20') == \
        '2026-09-01_13-05-22-01_ENTRADA_LOJA20.jpg'
    assert fc.nome_do_arquivo(quando, 'Saída', 8, indice=3) == \
        '2026-09-01_13-05-22-03_SAIDA_LOJA8.jpg'
    # O que ele grava, ele mesmo consegue ler de volta:
    lido = fc.partes_do_nome(fc.nome_do_arquivo(quando, 'Saída', 8, 3))
    assert lido == ('2026-09-01', '13-05-22-03', 'SAIDA', '8'), lido
    print('ok  o nome gerado e lido de volta por ele mesmo')


def teste_hora_e_do_brasil():
    from datetime import timezone
    agora = fc.agora_brasil()
    utc = datetime.now(timezone.utc)
    # A diferença tem de ser de 3 horas, não zero. Um minuto de folga para o
    # tempo que passa entre as duas leituras.
    diferenca = (utc.replace(tzinfo=None) - agora.replace(tzinfo=None)).total_seconds()
    assert 3 * 3600 - 60 < diferenca < 3 * 3600 + 60, diferenca
    print('ok  a hora vem de Sao Paulo (3h atras do UTC), e nao do servidor')


def teste_reduz_e_gira():
    from PIL import Image
    grande = Image.new('RGB', (4000, 3000), (200, 30, 30))
    bruto = io.BytesIO()
    grande.save(bruto, format='JPEG', quality=95)
    bruto = bruto.getvalue()

    dados, descricao, tamanho = fc.preparar_foto(bruto)
    with Image.open(io.BytesIO(dados)) as saiu:
        assert max(saiu.size) == fc.LADO_MAXIMO, saiu.size
        assert saiu.size == (2048, 1536), saiu.size
    assert '4000x3000' in descricao and '2048x1536' in descricao, descricao
    assert tamanho == len(dados)
    # E continua muito maior que as 344x421 de hoje:
    assert saiu.size[0] * saiu.size[1] > 20 * (344 * 421)
    print('ok  reduz 4000x3000 para 2048x1536 (20x mais pixels que hoje)')


def teste_foto_pequena_nao_e_ampliada():
    from PIL import Image
    pequena = Image.new('RGB', (344, 421), (10, 10, 200))
    bruto = io.BytesIO()
    pequena.save(bruto, format='JPEG')
    dados, descricao, _ = fc.preparar_foto(bruto.getvalue())
    with Image.open(io.BytesIO(dados)) as saiu:
        assert saiu.size == (344, 421), saiu.size
    print('ok  foto que ja e pequena nao e esticada (ampliar nao cria detalhe)')


def teste_arquivo_que_nao_e_imagem_vai_como_veio():
    bruto = b'isto nao e uma imagem'
    dados, descricao, tamanho = fc.preparar_foto(bruto)
    assert dados == bruto and tamanho == len(bruto)
    assert 'como veio' in descricao, descricao
    print('ok  formato que eu nao abro vai como veio, em vez de falhar')


def teste_busca_por_loja_nao_casa_por_pedaco():
    pasta = tempfile.mkdtemp(prefix='wf_fotos_')
    try:
        nomes = [
            '2026-09-01_10-00-00-01_ENTRADA_LOJA2.jpg',    # a que se procura
            '2026-09-01_10-00-01-01_ENTRADA_LOJA20.jpg',
            '2026-09-01_10-00-02-01_ENTRADA_LOJA22.jpg',
            '2026-09-01_10-00-03-01_ENTRADA_LOJA23.jpg',
            '2026-09-01_10-00-04-01_SAIDA_LOJA2.jpg',      # tipo diferente
            '2026-08-31_10-00-05-01_ENTRADA_LOJA2.jpg',    # dia diferente
        ]
        for n in nomes:
            open(os.path.join(pasta, n), 'wb').close()

        do_dia, herdadas = fc.fotos_de(pasta, '2', '2026-09-01', 'Entrada')
        assert do_dia == ['2026-09-01_10-00-00-01_ENTRADA_LOJA2.jpg'], do_dia
        assert herdadas == []
        # E a loja 20 acha a dela, sem trazer a 2:
        do_dia, _ = fc.fotos_de(pasta, '20', '2026-09-01', 'Entrada')
        assert do_dia == ['2026-09-01_10-00-01-01_ENTRADA_LOJA20.jpg'], do_dia
        print('ok  procurar a loja 2 nao traz mais a 20, a 22 e a 23')
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def teste_foto_da_noite_com_nome_antigo_aparece():
    """Nome em UTC: a carga das 21h de 03/08 ficou gravada como 04/08 00-15."""
    pasta = tempfile.mkdtemp(prefix='wf_fotos_')
    try:
        antiga = '2026-08-04_00-15-50_ENTRADA_LOJA8.jpg'   # existe de verdade
        nova = '2026-09-02_00-30-00-01_ENTRADA_LOJA8.jpg'  # depois do corte
        for n in (antiga, nova):
            open(os.path.join(pasta, n), 'wb').close()

        do_dia, herdadas = fc.fotos_de(pasta, '8', '2026-08-03', 'Entrada')
        assert do_dia == [] and herdadas == [antiga], (do_dia, herdadas)

        # Depois do corte a hora já é a do Brasil: 00-30 é madrugada mesmo, e
        # NÃO deve ser puxada para o dia anterior.
        do_dia, herdadas = fc.fotos_de(pasta, '8', '2026-09-01', 'Entrada')
        assert do_dia == [] and herdadas == [], (do_dia, herdadas)
        print('ok  foto da noite com nome antigo aparece; nome novo nao e remendado')
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def teste_lista_de_lojas():
    numeros = [n for n, _ in fc.LOJAS]
    assert len(numeros) == 21, len(numeros)
    assert len(set(numeros)) == len(numeros), 'loja repetida na lista'
    assert numeros == sorted(numeros), 'a lista tem de estar em ordem de numero'
    # O que o botao grava tem de ser lido de volta pelo nome do arquivo:
    quando = datetime(2026, 9, 1, 13, 0, 0)
    for numero, _ in fc.LOJAS:
        nome = fc.nome_do_arquivo(quando, 'Entrada', numero)
        assert fc.partes_do_nome(nome)[3] == str(numero), nome
    # O nome e a CONFIRMACAO do numero digitado, para o motorista que nao
    # enxerga bem conferir lendo em vez de reler o digito.
    assert 'PARK JACAREPAGUA' in fc.nome_da_loja(20)
    assert 'OUTLET SHOPPING' in fc.nome_da_loja('22')
    assert fc.nome_da_loja(99) == 'Loja 99'      # fora da lista, nao inventa nome
    assert fc.nome_da_loja(' 2 ') == '2 · CARREFOUR GALERIA'
    print('ok  as 21 lojas dos botoes viram nome de arquivo que se le de volta')


def medir_o_que_ja_existe():
    """Não é teste: é a medição das fotos reais, para ele ver o antes."""
    if not os.path.isdir(PASTA_REAL):
        return
    nomes = os.listdir(PASTA_REAL)
    lidos = [n for n in nomes if fc.partes_do_nome(n)]
    print()
    print('--- as fotos que ja estao na pasta ---')
    print('arquivos: %d   |   com nome no padrao: %d' % (len(nomes), len(lidos)))
    naos = [n for n in nomes if not fc.partes_do_nome(n)]
    if naos:
        print('fora do padrao (%d):' % len(naos), ', '.join(naos[:5]))


if __name__ == '__main__':
    teste_leitura_do_nome()
    teste_nome_do_arquivo()
    teste_hora_e_do_brasil()
    teste_reduz_e_gira()
    teste_foto_pequena_nao_e_ampliada()
    teste_arquivo_que_nao_e_imagem_vai_como_veio()
    teste_busca_por_loja_nao_casa_por_pedaco()
    teste_foto_da_noite_com_nome_antigo_aparece()
    teste_lista_de_lojas()
    medir_o_que_ja_existe()
    print('\nTODOS OS TESTES PASSARAM')
