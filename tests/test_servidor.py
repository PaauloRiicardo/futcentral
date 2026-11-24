"""Testes do servidor (main.py). Rodam com a ESPN falsa do conftest.py, sem internet."""
import time

from fastapi.testclient import TestClient

import main
from conftest import DIA, JOGOS_ESPN

cliente = TestClient(main.app)


def _jogos(resposta):
    return {f'{j["mandante"]} x {j["visitante"]}': j for j in resposta.json()["dados"]}


# ---------- gols e cartões vermelhos ----------

def test_gols_batem_com_o_placar_em_todos_os_jogos():
    for jogos in JOGOS_ESPN.values():
        for e in jogos:
            r = main._resumir_evento(e)
            gols = [l for l in r["lances"] if l["tipo"] == "gol"]
            assert len(gols) == int(r["placarMandante"]) + int(r["placarVisitante"]), r["mandante"]


def test_gol_contra_fica_no_time_beneficiado():
    r = main._resumir_evento(JOGOS_ESPN["uefa.nations"][1])  # Georgia 0 x 2 Hungria
    dvali = next(l for l in r["lances"] if l["jogador"] == "Lasha Dvali")
    assert dvali["lado"] == "visitante" and dvali["contra"] and not dvali["penalti"]


def test_gol_de_penalti():
    r = main._resumir_evento(JOGOS_ESPN["uefa.nations"][2])  # Noruega 3 x 1 País de Gales
    haaland = next(l for l in r["lances"] if l["jogador"] == "Erling Haaland")
    assert haaland == {"tipo": "gol", "lado": "mandante", "jogador": "Erling Haaland",
                       "minuto": "88'", "penalti": True, "contra": False}


def test_vermelho_sem_nome_e_ignorado_e_amarelo_nao_entra():
    r = main._resumir_evento(JOGOS_ESPN["fifa.friendly"][0])  # Japão 3 x 2 Brasil
    vermelhos = [l for l in r["lances"] if l["tipo"] == "vermelho"]
    assert [v["jogador"] for v in vermelhos] == ["Raphinha"]
    assert all(l["tipo"] in ("gol", "vermelho") for l in r["lances"])  # Endrick (amarelo) fica de fora


def test_evento_sem_detalhes_nao_quebra():
    e = dict(JOGOS_ESPN["fifa.friendly"][1])
    e["competitions"] = [{"competitors": e["competitions"][0]["competitors"]}]  # sem "details"
    assert main._resumir_evento(e)["lances"] == []


# ---------- API /api/jogos ----------

def test_api_devolve_jogos_do_dia_em_ordem_de_horario(espn):
    r = cliente.get(f"/api/jogos?data={DIA}")
    assert r.status_code == 200 and r.json()["status"] == "sucesso"
    horarios = [j["horario"] for j in r.json()["dados"]]
    assert horarios == sorted(horarios)
    jogos = _jogos(r)
    assert jogos["Japão x Brasil"]["horario"] == "07:15"
    assert jogos["Noruega x País de Gales"]["liga"] == "Liga das Nações"


def test_jogo_a_noite_no_brasil_fica_no_dia_certo(espn):
    # 01:30 UTC do dia 15 = 22:30 de 14/11 em Brasília
    jogos = _jogos(cliente.get(f"/api/jogos?data={DIA}"))
    assert jogos["Borussia Mönchengladbach x Bayer Leverkusen"]["horario"] == "22:30"
    assert "Borussia Mönchengladbach x Bayer Leverkusen" not in _jogos(cliente.get("/api/jogos?data=2026-11-15"))


def test_amistosos_so_das_selecoes_principais(espn):
    jogos = _jogos(cliente.get(f"/api/jogos?data={DIA}"))
    assert "Andorra x Malta" not in jogos
    assert set(jogos["Japão x Brasil"]["regioes"]) == {"Seleções", "América do Sul", "Brasil"}
    assert jogos["Korea Republic x Saudi Arabia"]["regioes"] == ["Seleções"]  # nome em inglês reconhecido


def test_data_invalida_responde_400(espn):
    r = cliente.get("/api/jogos?data=14/11/2026")
    assert r.status_code == 400 and r.json()["status"] == "erro"


def test_espn_fora_do_ar_responde_503(espn):
    espn.falhar = {"todas"}
    r = cliente.get(f"/api/jogos?data={DIA}")
    assert r.status_code == 503 and r.json()["dados"] == []


def test_uma_liga_falhando_vira_resultado_parcial(espn):
    espn.falhar = {"uefa.nations"}
    r = cliente.get(f"/api/jogos?data={DIA}")
    assert r.status_code == 200
    assert r.json()["status"] == "parcial" and r.json()["ligasComFalha"] == ["Liga das Nações"]
    assert "Japão x Brasil" in _jogos(r)


def test_espn_cai_e_o_site_usa_os_dados_guardados(espn, monkeypatch):
    cliente.get(f"/api/jogos?data={DIA}")
    agora = time.time() + 7 * 3600  # cache vencido
    monkeypatch.setattr(main.time, "time", lambda: agora)
    espn.falhar = {"todas"}
    r = cliente.get(f"/api/jogos?data={DIA}")
    assert r.status_code == 200 and r.json()["status"] == "sucesso"
    assert "Japão x Brasil" in _jogos(r)


def test_segunda_visita_usa_o_cache(espn):
    cliente.get(f"/api/jogos?data={DIA}")
    antes = len(espn.chamadas)
    cliente.get(f"/api/jogos?data={DIA}")
    assert len(espn.chamadas) == antes


def test_canais_cadastrados_aparecem_no_jogo(espn, monkeypatch):
    monkeypatch.setattr(main, "_ler_canais", lambda: ({"Liga das Nações": ["SporTV"]},
                                                      {f"{DIA} japão x brasil": ["Globo", "ge tv"]}))
    jogos = _jogos(cliente.get(f"/api/jogos?data={DIA}"))
    assert jogos["Japão x Brasil"]["transmissao"] == ["Globo", "ge tv"]
    assert jogos["Georgia x Hungria"]["transmissao"] == ["SporTV"]


# ---------- validade do cache de hoje ----------

def _ev(estado, daqui_segundos):
    return {"estado": estado, "startTimestamp": int(time.time() + daqui_segundos)}


def test_validade_do_cache_conforme_a_situacao():
    assert main._validade_hoje([_ev("in", -1800)]) == main.CACHE_SEGUNDOS_AO_VIVO
    assert main._validade_hoje([_ev("pre", 10 * 60)]) == main.CACHE_SEGUNDOS_AO_VIVO   # começa em 10 min
    assert main._validade_hoje([_ev("pre", 3 * 3600)]) == main.CACHE_SEGUNDOS_HOJE
    assert main._validade_hoje([_ev("post", -5 * 3600)]) == main.CACHE_SEGUNDOS_ENCERRADOS
    assert main._validade_hoje([]) == main.CACHE_SEGUNDOS_ENCERRADOS


# ---------- página, arquivos estáticos e compressão ----------

def test_pagina_inicial_responde_get_e_head():
    assert cliente.get("/").status_code == 200
    assert cliente.head("/").status_code == 200  # robôs de prévia do WhatsApp/Facebook


def test_so_arquivos_da_lista_sao_servidos():
    assert cliente.get("/static/og.jpg").status_code == 200
    assert cliente.get("/favicon.ico").status_code == 200
    for nome in ["main.py", "canais.json", ".env", "..%2Fmain.py"]:
        assert cliente.get(f"/static/{nome}").status_code == 404, nome


def test_respostas_grandes_sao_compactadas(espn):
    r = cliente.get(f"/api/jogos?data={DIA}", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"
    assert r.json()["dados"]  # o cliente descompacta sozinho
