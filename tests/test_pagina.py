"""Teste da página no navegador (Playwright + Chromium), com o servidor real e a ESPN falsa.
Precisa do CSS gerado (static/site.css) — no GitHub ele é gerado antes dos testes."""
import socket
import threading
import time

import pytest
import uvicorn

import main
from conftest import DIA

playwright_api = pytest.importorskip("playwright.sync_api")

TELAS = {"celular": {"width": 360, "height": 800}, "computador": {"width": 1280, "height": 900}}


@pytest.fixture
def site(espn):
    """Sobe o FutCentral numa porta livre, em segundo plano, usando a ESPN falsa."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
    servidor = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=porta, log_level="warning"))
    threading.Thread(target=servidor.run, daemon=True).start()
    for _ in range(100):
        if servidor.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{porta}", espn
    servidor.should_exit = True


@pytest.fixture(scope="module")
def navegador():
    with playwright_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _abrir_dia(navegador, url, tela):
    pagina = navegador.new_page(viewport=TELAS[tela])
    erros = []
    pagina.on("pageerror", lambda e: erros.append(str(e)))
    pagina.goto(url)
    pagina.evaluate(f"document.getElementById('dateInput').value = '{DIA}'; carregarJogosData('{DIA}')")
    pagina.wait_for_function("document.getElementById('container-jogos').getAttribute('aria-busy') === 'false'")
    pagina.wait_for_timeout(200)
    return pagina, erros


@pytest.mark.parametrize("tela", TELAS)
def test_cards_alinhados_e_sem_erros(site, navegador, tela):
    url, _ = site
    pagina, erros = _abrir_dia(navegador, url, tela)
    medidas = pagina.evaluate("""() => [...document.querySelectorAll('#container-jogos > div')].map(card => {
        const c = card.getBoundingClientRect();
        const meio = card.children[1].children[1].getBoundingClientRect();
        return {texto: card.children[1].innerText, centro: meio.x + meio.width / 2 - c.x,
                metade: c.width / 2, largura: meio.width};
    })""")
    assert erros == []
    assert len(medidas) >= 6
    larguras = {round(m["largura"]) for m in medidas}
    assert len(larguras) == 1, f"Meio do card com larguras diferentes: {larguras}"
    for m in medidas:  # "VS"/placar no centro do card, mesmo com nomes longos e placar de 2 dígitos
        assert abs(m["centro"] - m["metade"]) <= 1, m["texto"]
    pagina.close()


def test_mostra_gols_penalti_gol_contra_e_vermelho(site, navegador):
    url, _ = site
    pagina, erros = _abrir_dia(navegador, url, "celular")
    texto = pagina.inner_text("#container-jogos")
    for esperado in ["Erling Haaland", "(pên.)", "Lasha Dvali", "(contra)", "Raphinha", "Vinícius Júnior 33', 75'"]:
        assert esperado in texto, esperado
    assert "Andorra" not in texto
    assert "Não informado" not in texto  # vermelho repetido sem nome não aparece
    assert erros == []
    pagina.close()


def test_cards_fantasma_enquanto_carrega(site, navegador):
    url, espn = site
    espn.demora = 0.4
    pagina = navegador.new_page(viewport=TELAS["celular"])
    pagina.goto(url)
    assert pagina.locator("#container-jogos .card-fantasma").count() == 3
    assert pagina.locator(".card-fantasma").first.bounding_box()["height"] > 100  # CSS gerado e aplicado
    pagina.close()


def test_espn_fora_do_ar_mostra_erro_com_botao(site, navegador):
    url, espn = site
    espn.falhar = {"todas"}
    pagina, erros = _abrir_dia(navegador, url, "celular")
    assert "Tentar novamente" in pagina.inner_text("#container-jogos")
    assert "Nenhum jogo encontrado" not in pagina.inner_text("#container-jogos")
    assert erros == []
    pagina.close()
