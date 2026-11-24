"""Preparação dos testes: uma ESPN falsa, com jogos reais de 14/11/2026 (Liga das Nações e
amistosos) copiados da API da ESPN, e o cache zerado a cada teste. Nenhum teste acessa a internet."""
import sys
import threading
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import main  # noqa: E402

DIA = "2026-11-14"


def _evento(id_, data, mandante, visitante, placar, estado="post", lances=()):
    """Evento no formato da ESPN. lances: (minuto, lado 'm'/'v', jogador, tipo, extras)."""
    ids = {"m": f"{id_}1", "v": f"{id_}2"}
    detalhes = []
    for minuto, lado, jogador, tipo, *extra in lances:
        extra = extra[0] if extra else {}
        detalhes.append({
            "clock": {"displayValue": minuto},
            "team": {"id": ids[lado]},
            "scoringPlay": tipo == "gol",
            "redCard": tipo == "vermelho",
            "yellowCard": tipo == "amarelo",
            "penaltyKick": extra.get("penalti", False),
            "ownGoal": extra.get("contra", False),
            "athletesInvolved": [] if jogador is None else [{"displayName": jogador}],
        })
    descricao = {"pre": "Agendado", "in": "2º Tempo", "post": "Final da Partida"}[estado]
    return {
        "id": id_, "date": data,
        "status": {"type": {"state": estado, "description": descricao}},
        "competitions": [{
            "competitors": [
                {"homeAway": "home", "score": str(placar[0]), "team": {"id": ids["m"], "displayName": mandante}},
                {"homeAway": "away", "score": str(placar[1]), "team": {"id": ids["v"], "displayName": visitante}},
            ],
            "details": detalhes,
        }],
    }


# Jogos reais de 14/11/2026 (dados da ESPN conferidos em 17/11/2026)
JOGOS_ESPN = {
    "uefa.nations": [
        _evento("101", "2026-11-14T14:00Z", "Kosovo", "Israel", (0, 0), lances=[
            ("20'", "m", "Veldin Hodza", "amarelo"),
            ("66'", "m", "Veldin Hodza", "vermelho"),
        ]),
        _evento("102", "2026-11-14T17:00Z", "Georgia", "Hungria", (0, 2), lances=[
            ("73'", "v", "Lasha Dvali", "gol", {"contra": True}),  # gol contra: a ESPN põe no time beneficiado
            ("85'", "v", "Barnabás Varga", "gol"),
        ]),
        _evento("103", "2026-11-14T17:00Z", "Noruega", "País de Gales", (3, 1), lances=[
            ("59'", "m", "Antonio Nusa", "gol"),
            ("68'", "m", "Andreas Schjelderup", "gol"),
            ("79'", "v", "David Brooks", "gol"),
            ("88'", "m", "Erling Haaland", "gol", {"penalti": True}),
        ]),
    ],
    "fifa.friendly": [
        _evento("201", "2026-11-14T10:15Z", "Japão", "Brasil", (3, 2), lances=[
            ("15'", "m", "Takefusa Kubo", "gol"),
            ("19'", "m", "Keito Nakamura", "gol"),
            ("33'", "v", "Vinícius Júnior", "gol"),
            ("75'", "v", "Vinícius Júnior", "gol"),
            ("87'", "v", "Endrick", "amarelo"),
            ("90'+1'", "m", "Tatsuhiro Sakamoto", "gol"),
            ("90'+2'", "v", None, "vermelho"),  # a ESPN repetiu o vermelho sem nome
            ("90'+2'", "v", "Raphinha", "vermelho"),
        ]),
        _evento("202", "2026-11-14T15:00Z", "Andorra", "Malta", (1, 1)),  # seleções fora da lista: não aparece
        _evento("203", "2026-11-14T12:00Z", "Korea Republic", "Saudi Arabia", (0, 0)),  # nomes em inglês
    ],
    "ger.1": [
        # Nomes longos (teste de alinhamento) e jogo às 22h30 de Brasília, que na ESPN cai no dia seguinte
        _evento("301", "2026-11-15T01:30Z", "Borussia Mönchengladbach", "Bayer Leverkusen", (0, 0), estado="pre"),
    ],
    "bra.1": [
        _evento("401", "2026-11-14T23:30Z", "Chapecoense", "Vasco da Gama", (0, 2), lances=[
            ("36'", "v", "Bruno Duarte", "gol"),
            ("81'", "v", "Bruno Duarte", "gol"),
        ]),
    ],
}


class EspnFalsa:
    """Substitui requests.get do main.py. Registra as chamadas e pode simular falhas e demora."""

    def __init__(self):
        self.chamadas = []
        self.falhar = set()      # ligas que falham; "todas" derruba tudo
        self.demora = 0.0
        self._lock = threading.Lock()

    def get(self, url, params=None, timeout=None):
        liga = url.split("/soccer/")[1].split("/")[0]
        datas = params["dates"]
        with self._lock:
            self.chamadas.append((liga, datas))
        if self.demora:
            time.sleep(self.demora)
        if "todas" in self.falhar or liga in self.falhar:
            raise main.requests.RequestException("ESPN fora do ar (simulado)")
        eventos = [e for e in JOGOS_ESPN.get(liga, []) if e["date"][:10].replace("-", "") == datas]
        return _Resposta({"events": eventos})


class _Resposta:
    status_code = 200
    text = ""

    def __init__(self, dados):
        self._dados = dados

    def json(self):
        return self._dados


@pytest.fixture
def espn(monkeypatch, tmp_path):
    falsa = EspnFalsa()
    monkeypatch.setattr(main.requests, "get", falsa.get)
    monkeypatch.setattr(main, "CACHE_ARQUIVO", tmp_path / "espn.json")
    main._cache.clear()
    yield falsa
    main._cache.clear()
