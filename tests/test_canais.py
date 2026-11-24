"""Confere o canais.json: um erro de digitação nele apagaria os canais do site inteiro."""
import json
import re

import main

DADOS = json.loads(main.CANAIS_ARQUIVO.read_text(encoding="utf-8"))
CHAVE_JOGO = re.compile(r"^\d{4}-\d{2}-\d{2} \S.* x \S.*$")


def _lista_de_textos(valor):
    return isinstance(valor, list) and all(isinstance(c, str) and c.strip() for c in valor)


def test_estrutura_basica():
    assert isinstance(DADOS.get("campeonatos"), dict)
    assert isinstance(DADOS.get("jogos"), dict)


def test_campeonatos_existem_no_site():
    nomes_no_site = {nome for nome, _pais, _regiao in main.LIGAS_PRINCIPAIS.values()}
    desconhecidos = set(DADOS["campeonatos"]) - nomes_no_site
    assert not desconhecidos, f"Campeonatos que o site não mostra (nome errado?): {desconhecidos}"
    for nome, canais in DADOS["campeonatos"].items():
        assert _lista_de_textos(canais), nome


def test_chaves_e_canais_dos_jogos():
    for chave, canais in DADOS["jogos"].items():
        assert CHAVE_JOGO.match(chave), f'Chave fora do formato "AAAA-MM-DD Mandante x Visitante": {chave!r}'
        assert _lista_de_textos(canais) and canais, chave
