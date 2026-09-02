# -*- coding: utf-8 -*-
"""Prova do arquivo no HD, sem encostar no E: nem no repositório de verdade.

    python teste_arquivo_fotos.py
"""
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import arquivo_fotos as af

PONTE = [
    '2026-09-02_10-30-00-01_ENTRADA_LOJA14.jpg',
    '2026-09-02_10-31-00-01_SAIDA_LOJA14.jpg',
    '2026-08-31_16-00-00-01_ENTRADA_LOJA20.jpg',   # mês anterior
    '2026-06-08_14-58-57_ENTRADA_LOJAL9.jpg',      # nome torto: NÃO se apaga
    'desktop.ini',                                  # lixo: NÃO se apaga
]


def montar(nomes=PONTE, conteudo=b'foto'):
    base = tempfile.mkdtemp(prefix='wf_arqfotos_')
    ponte = os.path.join(base, 'fotos_recebidas')
    arquivo = os.path.join(base, 'HD', 'Fotos_Cargas')
    os.makedirs(ponte)
    for n in nomes:
        with open(os.path.join(ponte, n), 'wb') as f:
            f.write(conteudo)
    return base, ponte, arquivo


def com_mundo(funcao):
    def rodar():
        base, ponte, arquivo = montar()
        try:
            funcao(ponte, arquivo)
        finally:
            shutil.rmtree(base, ignore_errors=True)
    return rodar


@com_mundo
def teste_importa_em_pastas_por_mes(ponte, arquivo):
    r = af.importar(ponte, arquivo)
    assert r['erros'] == [], r['erros']
    assert r['movidas'] == 3, r
    # As pastas por mês: 450 fotos/mês num diretório só engasgam o Explorer.
    assert sorted(os.listdir(arquivo)) == ['2026-08', '2026-09'], os.listdir(arquivo)
    assert len(os.listdir(os.path.join(arquivo, '2026-09'))) == 2
    assert len(os.listdir(os.path.join(arquivo, '2026-08'))) == 1
    print('ok  importa para pastas AAAA-MM, separando os meses')


@com_mundo
def teste_a_ponte_fica_vazia_das_fotos(ponte, arquivo):
    af.importar(ponte, arquivo)
    sobraram = sorted(os.listdir(ponte))
    # Só o que NÃO é foto reconhecível fica - e fica de propósito.
    assert sobraram == ['2026-06-08_14-58-57_ENTRADA_LOJAL9.jpg', 'desktop.ini'], sobraram
    print('ok  a ponte esvazia das fotos, e o que nao se entende NAO e apagado')


@com_mundo
def teste_nome_torto_e_devolvido_para_ele_ver(ponte, arquivo):
    r = af.importar(ponte, arquivo)
    assert '2026-06-08_14-58-57_ENTRADA_LOJAL9.jpg' in r['ignoradas'], r['ignoradas']
    assert 'desktop.ini' in r['ignoradas']
    print('ok  arquivo fora do padrao volta na lista, em vez de sumir calado')


@com_mundo
def teste_importar_duas_vezes_nao_duplica(ponte, arquivo):
    af.importar(ponte, arquivo)
    # Chega a mesma foto de novo (o celular reenviou):
    with open(os.path.join(ponte, PONTE[0]), 'wb') as f:
        f.write(b'foto')
    r = af.importar(ponte, arquivo)
    assert r['ja_existiam'] == 1 and r['movidas'] == 0, r
    assert len(os.listdir(os.path.join(arquivo, '2026-09'))) == 2
    assert not os.path.exists(os.path.join(ponte, PONTE[0])), 'devia sair da ponte'
    print('ok  reimportar a mesma foto nao duplica, e limpa a ponte')


@com_mundo
def teste_mesmo_nome_com_conteudo_diferente_guarda_as_duas(ponte, arquivo):
    af.importar(ponte, arquivo)
    with open(os.path.join(ponte, PONTE[0]), 'wb') as f:
        f.write(b'OUTRA foto, maior')      # mesmo nome, conteúdo diferente
    r = af.importar(ponte, arquivo)
    assert r['movidas'] == 1, r
    guardadas = sorted(os.listdir(os.path.join(arquivo, '2026-09')))
    assert len(guardadas) == 3, guardadas
    assert any('(2)' in g for g in guardadas), guardadas
    print('ok  duas fotos de mesmo nome e conteudo diferente: guarda as duas')


@com_mundo
def teste_busca_no_arquivo_e_na_ponte(ponte, arquivo):
    # Antes de importar: a foto está só na ponte, e tem de aparecer.
    achadas = af.fotos_de('14', '2026-09-02', 'Entrada', arquivo, ponte)
    assert len(achadas) == 1, achadas
    assert achadas[0][0].startswith(ponte), achadas

    af.importar(ponte, arquivo)

    # Depois de importar: aparece, agora vindo do HD.
    achadas = af.fotos_de('14', '2026-09-02', 'Entrada', arquivo, ponte)
    assert len(achadas) == 1 and '2026-09' in achadas[0][0], achadas
    # A loja 14 não pode trazer a 1 nem a 4, e o tipo tem de bater:
    assert af.fotos_de('1', '2026-09-02', 'Entrada', arquivo, ponte) == []
    assert len(af.fotos_de('14', '2026-09-02', 'Saida', arquivo, ponte)) == 1
    assert af.fotos_de('14', '2026-09-01', 'Entrada', arquivo, ponte) == []
    print('ok  busca acha no HD e na ponte, sem confundir loja, dia nem tipo')


@com_mundo
def teste_resumo_por_mes(ponte, arquivo):
    af.importar(ponte, arquivo)
    r = af.resumo(arquivo)
    assert r['fotos'] == 3, r
    assert sorted(r['por_mes']) == ['2026-08', '2026-09'], r['por_mes']
    assert r['por_mes']['2026-09']['fotos'] == 2
    assert r['bytes'] > 0
    print('ok  resumo diz quantas fotos e quanto espaco, por mes')


@com_mundo
def teste_apagar_do_arquivo(ponte, arquivo):
    af.importar(ponte, arquivo)
    achadas = af.fotos_de('14', '2026-09-02', 'Entrada', arquivo, ponte)
    n, erros = af.apagar([c for c, _ in achadas])
    assert n == 1 and erros == [], (n, erros)
    assert af.fotos_de('14', '2026-09-02', 'Entrada', arquivo, ponte) == []
    # Apagar o que não existe devolve erro, não explode:
    n, erros = af.apagar(['C:/nao/existe/foto.jpg'])
    assert n == 0 and len(erros) == 1
    print('ok  apaga do arquivo e relata o que nao conseguiu')


def teste_hd_ausente_nao_mente():
    base, ponte, _ = montar()
    try:
        ok, motivo = af.destino_disponivel('Z:\\nao_existe\\Fotos')
        assert not ok and 'Z:' in motivo, motivo
        r = af.importar(ponte, 'Z:\\nao_existe\\Fotos')
        assert r['movidas'] == 0 and r['erros'], r
        # E NADA saiu da ponte: sem destino, não se mexe na origem.
        assert len(os.listdir(ponte)) == len(PONTE)
        print('ok  sem o HD, nada e movido e ele avisa')
    finally:
        shutil.rmtree(base, ignore_errors=True)




def teste_importar_do_whatsapp():
    """Fotos soltas, com nome do WhatsApp, viram nome do sistema e vao ao HD."""
    import tempfile as _tmp
    from datetime import datetime
    from PIL import Image

    base = _tmp.mkdtemp(prefix='wf_zap_')
    downloads = os.path.join(base, 'Downloads')
    arquivo = os.path.join(base, 'HD')
    os.makedirs(downloads)
    # Como o WhatsApp baixa: nome proprio, e uma foto grande de verdade.
    nomes_zap = ['IMG-20260902-WA0007.jpg', 'IMG-20260902-WA0008.jpg']
    for i, n in enumerate(nomes_zap):
        # Cores diferentes de propósito: duas fotos IGUAIS agora contam como
        # uma só, e isso tem prova em teste_whatsapp_nao_reimporta_a_mesma_pasta.
        Image.new('RGB', (3000, 4000), (20, 90 + i * 40, 40)).save(
            os.path.join(downloads, n), format='JPEG', quality=92)
    # E um arquivo que JA esta no padrao: nao e do WhatsApp, nao entra.
    open(os.path.join(downloads, '2026-09-02_10-00-00-01_ENTRADA_LOJA14.jpg'), 'wb').close()

    try:
        soltas = af.fotos_soltas(downloads)
        assert sorted(os.path.basename(c) for c in soltas) == nomes_zap, soltas

        quando = datetime(2026, 9, 2, 12, 0, 0)
        r = af.importar_do_whatsapp(soltas, '14', 'Saida', quando=quando,
                                    pasta_arquivo=arquivo)
        assert r['erros'] == [], r['erros']
        assert len(r['arquivadas']) == 2, r

        guardadas = sorted(os.listdir(os.path.join(arquivo, '2026-09')))
        assert all('_SAIDA_LOJA14.jpg' in g for g in guardadas), guardadas
        # O nome gerado tem de ser legivel pela mesma regra da busca:
        for g in guardadas:
            partes = af.partes_do_nome(g)
            assert partes and partes[3] == '14' and partes[2] == 'SAIDA', g
        # E a foto foi reduzida, como as do app:
        with Image.open(os.path.join(arquivo, '2026-09', guardadas[0])) as im:
            assert max(im.size) == 2048, im.size
        # A origem NAO foi apagada (mover=False e o padrao):
        assert len(af.fotos_soltas(downloads)) == 2

        # A busca acha:
        achadas = af.fotos_de('14', '2026-09-02', 'Saida', pasta_arquivo=arquivo)
        assert len(achadas) == 2, achadas
        # E a 1 nao vem de brinde:
        assert af.fotos_de('1', '2026-09-02', 'Saida', pasta_arquivo=arquivo) == []

        # O manifesto guarda de onde cada arquivo veio:
        with io.open(os.path.join(arquivo, af.MANIFESTO), encoding='utf-8-sig') as f:
            conteudo = f.read()
        assert 'IMG-20260902-WA0007.jpg' in conteudo, conteudo
        print('ok  foto do WhatsApp vira nome do sistema, reduzida, com manifesto')
    finally:
        shutil.rmtree(base, ignore_errors=True)


@com_mundo
def teste_mesma_foto_com_outro_nome_nao_duplica(ponte, arquivo):
    """O defeito medido: 181 copias no arquivo dele, uma foto repetida 7x.

    Cada reenvio ganha a hora do momento, logo um NOME novo - so o conteudo
    denuncia. Foi o caso das 3 fotos identicas da loja 19 em 02/09/2026,
    gravadas as 11:48:41, :43 e :45.
    """
    af.importar(ponte, arquivo)
    mesmo_conteudo = open(os.path.join(arquivo, '2026-09',
                                       PONTE[0]), 'rb').read()
    for hora in ('10-30-05', '10-30-07'):
        novo = '2026-09-02_%s-01_ENTRADA_LOJA14.jpg' % hora
        with open(os.path.join(ponte, novo), 'wb') as f:
            f.write(mesmo_conteudo)

    r = af.importar(ponte, arquivo)
    assert r['movidas'] == 0, r
    assert r['ja_existiam'] == 2, r
    assert len(r['repetidas']) == 2, r['repetidas']
    # A que ficou e a primeira, e o arquivo NAO cresceu:
    assert len(os.listdir(os.path.join(arquivo, '2026-09'))) == 2
    # E as repetidas sairam da ponte, senao voltam a cada importacao:
    assert not [n for n in os.listdir(ponte) if '10-30-0' in n]
    print('ok  mesma foto com nome diferente nao entra duas vezes no arquivo')


def teste_whatsapp_nao_reimporta_a_mesma_pasta(caminho_ignorado=None):
    """Importar duas vezes a mesma pasta de download nao dobra o arquivo."""
    import tempfile as _tmp
    from datetime import datetime
    from PIL import Image

    base = _tmp.mkdtemp(prefix='wf_zap4_')
    try:
        buf = io.BytesIO()
        Image.new('RGB', (3000, 4000), (12, 34, 56)).save(buf, format='JPEG',
                                                          quality=90)
        lote = [('IMG-20260902-WA0041.jpg', buf.getvalue())]
        quando = datetime(2026, 9, 2, 11, 50)

        r1 = af.importar_do_whatsapp(lote, '16', 'Saida', quando=quando,
                                     pasta_arquivo=base)
        assert len(r1['arquivadas']) == 1 and r1['repetidas'] == [], r1

        # De novo, o mesmo lote - e ainda por cima com outro nome de origem:
        lote2 = [('IMG-20260902-WA0099.jpg', buf.getvalue())]
        r2 = af.importar_do_whatsapp(lote2, '16', 'Saida', quando=quando,
                                     pasta_arquivo=base)
        assert r2['arquivadas'] == [] and len(r2['repetidas']) == 1, r2
        assert len(os.listdir(os.path.join(base, '2026-09'))) == 1
        print('ok  reimportar a mesma foto do WhatsApp nao dobra o arquivo')
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_whatsapp_com_nome_e_bytes():
    """O caminho do Painel: fotos escolhidas na janela, sem passar pelo disco."""
    import tempfile as _tmp
    from datetime import datetime
    from PIL import Image

    base = _tmp.mkdtemp(prefix='wf_zap3_')
    try:
        def foto(cor):
            buf = io.BytesIO()
            Image.new('RGB', (3000, 4000), cor).save(buf, format='JPEG', quality=90)
            return buf.getvalue()

        lote = [('IMG-20260902-WA0021.jpg', foto((10, 80, 30))),
                ('IMG-20260902-WA0022.jpg', foto((80, 10, 30)))]
        # A hora que ELE informou tem de virar a hora do nome: 11:50 na loja 19.
        quando = datetime(2026, 9, 2, 11, 50)
        r = af.importar_do_whatsapp(lote, '19', 'Entrada', quando=quando,
                                    pasta_arquivo=base)
        assert r['erros'] == [] and len(r['arquivadas']) == 2, r

        guardadas = sorted(os.listdir(os.path.join(base, '2026-09')))
        assert all(g.startswith('2026-09-02_11-50-') for g in guardadas), guardadas
        assert all('_ENTRADA_LOJA19.jpg' in g for g in guardadas), guardadas
        # Dois arquivos, dois nomes: o segundo NAO pode sobrescrever o primeiro.
        assert len(guardadas) == 2, guardadas
        # E a busca do Painel acha pelo dia:
        assert len(af.fotos_de('19', '2026-09-02', 'Entrada',
                               pasta_arquivo=base)) == 2
        with Image.open(os.path.join(base, '2026-09', guardadas[0])) as im:
            assert max(im.size) == 2048, im.size
        print('ok  foto escolhida na janela (nome+bytes) arquiva na hora informada')
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_whatsapp_recusa_loja_invalida():
    import tempfile as _tmp
    base = _tmp.mkdtemp(prefix='wf_zap2_')
    try:
        r = af.importar_do_whatsapp([], 'L9', 'Entrada', pasta_arquivo=base)
        assert r['arquivadas'] == [] and r['erros'], r
        print('ok  loja com letra e recusada - e o "LOJAL9" nao se repete')
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == '__main__':
    teste_importa_em_pastas_por_mes()
    teste_a_ponte_fica_vazia_das_fotos()
    teste_nome_torto_e_devolvido_para_ele_ver()
    teste_importar_duas_vezes_nao_duplica()
    teste_mesmo_nome_com_conteudo_diferente_guarda_as_duas()
    teste_busca_no_arquivo_e_na_ponte()
    teste_resumo_por_mes()
    teste_apagar_do_arquivo()
    teste_mesma_foto_com_outro_nome_nao_duplica()
    teste_importar_do_whatsapp()
    teste_whatsapp_nao_reimporta_a_mesma_pasta()
    teste_whatsapp_com_nome_e_bytes()
    teste_whatsapp_recusa_loja_invalida()
    teste_hd_ausente_nao_mente()
    print('\nTODOS OS TESTES PASSARAM')
