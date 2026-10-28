from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PAGINA = Path(__file__).parent / "site_esportivo.html"


@app.get("/", include_in_schema=False)
def pagina_inicial():
    # O próprio backend entrega o site, assim tudo fica num endereço só
    return FileResponse(PAGINA)

# API pública da ESPN: não precisa de chave, mas não é oficial (pode mudar sem aviso)
ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/scoreboard"

# Horário de Brasília (o Brasil não tem horário de verão desde 2019)
BRT = timezone(timedelta(hours=-3))

# Só estes campeonatos aparecem no site: código da liga na ESPN -> (nome, país, região).
# Cada liga custa 2 consultas por data nova (o dia e o seguinte).
LIGAS_PRINCIPAIS = {
    "bra.1": ("Brasileirão Série A", "Brasil", "Brasil"),
    "bra.2": ("Brasileirão Série B", "Brasil", "Brasil"),
    "bra.copa_do_brazil": ("Copa do Brasil", "Brasil", "Brasil"),
    "conmebol.libertadores": ("Libertadores", "América do Sul", "América do Sul"),
    "conmebol.sudamericana": ("Sul-Americana", "América do Sul", "América do Sul"),
    "fifa.worldq.conmebol": ("Eliminatórias CONMEBOL", "América do Sul", "América do Sul"),
    "eng.1": ("Premier League", "Inglaterra", "Europa"),
    "eng.fa": ("FA Cup", "Inglaterra", "Europa"),
    "eng.league_cup": ("Copa da Liga Inglesa", "Inglaterra", "Europa"),
    "esp.1": ("LaLiga", "Espanha", "Europa"),
    "esp.copa_del_rey": ("Copa del Rey", "Espanha", "Europa"),
    "ita.1": ("Serie A (Itália)", "Itália", "Europa"),
    "ita.coppa_italia": ("Coppa Italia", "Itália", "Europa"),
    "ger.1": ("Bundesliga", "Alemanha", "Europa"),
    "ger.dfb_pokal": ("DFB-Pokal", "Alemanha", "Europa"),
    "fra.1": ("Ligue 1", "França", "Europa"),
    "por.1": ("Liga Portugal", "Portugal", "Europa"),
    "uefa.champions": ("Champions League", "Europa", "Europa"),
    "uefa.europa": ("Europa League", "Europa", "Europa"),
    "uefa.europa.conf": ("Conference League", "Europa", "Europa"),
    "uefa.nations": ("Nations League", "Europa", "Europa"),
}

# Cache em disco por (liga, dia da API), para não repetir consultas
# e sobreviver a reinícios do servidor (o --reload reinicia a cada alteração).
# Dias que já passaram não mudam mais e ficam no cache para sempre; os dias
# com jogos acontecendo agora expiram rápido para o placar ficar atualizado.
CACHE_SEGUNDOS = 3 * 3600
CACHE_SEGUNDOS_AO_VIVO = 120
CACHE_ARQUIVO = Path(__file__).parent / ".cache" / "espn.json"
_cache_lock = Lock()


# Mude a versão sempre que _resumir_evento passar a guardar campos diferentes:
# as entradas antigas são descartadas em vez de quebrar a resposta.
CACHE_VERSAO = "v2"


def _ler_cache():
    try:
        dados = json.loads(CACHE_ARQUIVO.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return {chave: valor for chave, valor in dados.items() if chave.startswith(f"{CACHE_VERSAO}:")}


_cache = _ler_cache()


def _salvar_cache():
    CACHE_ARQUIVO.parent.mkdir(exist_ok=True)
    with _cache_lock:
        CACHE_ARQUIVO.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")


# Canais de TV preenchidos à mão (a ESPN só informa canais dos EUA).
# O arquivo é lido a cada consulta, então editar não exige reiniciar o servidor.
CANAIS_ARQUIVO = Path(__file__).parent / "canais.json"


def _ler_canais():
    try:
        dados = json.loads(CANAIS_ARQUIVO.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, {}
    except json.JSONDecodeError as e:
        print(f"Erro no canais.json (linha {e.lineno}): {e.msg}. Os canais não serão exibidos até corrigir.")
        return {}, {}
    # Chaves de jogo sem diferença de maiúsculas/espaços extras, para facilitar o preenchimento
    jogos = {" ".join(chave.lower().split()): canais for chave, canais in dados.get("jogos", {}).items()}
    return dados.get("campeonatos", {}), jogos


def _resumir_evento(event):
    # Guarda só o que o site usa, para o arquivo de cache não ficar enorme
    competidores = event.get("competitions", [{}])[0].get("competitors", [])
    times = {c.get("homeAway"): c.get("team", {}).get("displayName") for c in competidores}
    placar = {c.get("homeAway"): c.get("score") for c in competidores}
    status = event.get("status", {}).get("type", {})
    return {
        "id": event.get("id"),
        "startTimestamp": int(datetime.fromisoformat(event["date"].replace("Z", "+00:00")).timestamp()),
        "mandante": times.get("home") or "Time Casa",
        "visitante": times.get("away") or "Time Fora",
        "placarMandante": placar.get("home"),
        "placarVisitante": placar.get("away"),
        # "pre" = não começou, "in" = em andamento, "post" = encerrado
        "estado": status.get("state", "pre"),
        "status": status.get("description", "Agendado"),
    }


def buscar_eventos_liga(liga, data_api):
    chave = f"{CACHE_VERSAO}:{liga}:{data_api}"
    em_cache = _cache.get(chave)
    if em_cache:
        dia = date.fromisoformat(data_api)
        hoje = datetime.now(timezone.utc).date()
        idade = time.time() - em_cache["salvo_em"]
        if dia < hoje - timedelta(days=1):
            return em_cache["eventos"]
        validade = CACHE_SEGUNDOS_AO_VIVO if dia <= hoje else CACHE_SEGUNDOS
        if idade < validade:
            return em_cache["eventos"]

    url = ESPN_URL.format(liga=liga)
    try:
        # lang=pt traz o status em português ("Agendado", "Final da Partida")
        response = requests.get(url, params={"dates": data_api.replace("-", ""), "lang": "pt", "region": "br"}, timeout=20)
    except requests.RequestException as e:
        print(f"Erro na API da ESPN (liga {liga}): {e}")
        return None
    if response.status_code != 200:
        print(f"Erro na API da ESPN (liga {liga}, status {response.status_code}): {response.text[:200]}")
        return None

    eventos = [_resumir_evento(e) for e in response.json().get("events", []) if e.get("date")]
    with _cache_lock:
        _cache[chave] = {"salvo_em": time.time(), "eventos": eventos}
    return eventos


@app.get("/api/jogos")
def obter_jogos(data: str):
    try:
        dia = date.fromisoformat(data)
    except ValueError:
        return {"status": "erro", "dados": [], "mensagem": "Data inválida, use AAAA-MM-DD"}

    # A ESPN agrupa os jogos pelo dia de outro fuso; jogos à noite no Brasil podem
    # cair no dia seguinte, então buscamos os dois dias e filtramos pelo horário local.
    datas_api = [dia.isoformat(), (dia + timedelta(days=1)).isoformat()]

    try:
        consultas = [(liga, data_api) for liga in LIGAS_PRINCIPAIS for data_api in datas_api]
        # Consultas em paralelo (máx. 5 simultâneas para não sobrecarregar a ESPN)
        with ThreadPoolExecutor(max_workers=5) as executor:
            respostas = list(executor.map(lambda c: (c[0], buscar_eventos_liga(*c)), consultas))
        _salvar_cache()

        eventos = {}
        falhas = 0
        for liga, lista in respostas:
            if lista is None:
                falhas += 1
                continue
            for event in lista:
                if datetime.fromtimestamp(event["startTimestamp"], BRT).date() != dia:
                    continue
                eventos[event["id"]] = (liga, event)

        canais_campeonato, canais_jogo = _ler_canais()

        jogos_formatados = []
        for liga, event in sorted(eventos.values(), key=lambda item: item[1]["startTimestamp"]):
            nome_liga, pais, regiao = LIGAS_PRINCIPAIS[liga]
            chave_jogo = " ".join(f"{data} {event['mandante']} x {event['visitante']}".lower().split())
            transmissao = canais_jogo.get(chave_jogo) or canais_campeonato.get(nome_liga) or []
            jogo = {
                "liga": nome_liga,
                "pais": pais,
                "regiao": regiao,
                "mandante": event["mandante"],
                "visitante": event["visitante"],
                "placarMandante": event["placarMandante"],
                "placarVisitante": event["placarVisitante"],
                "estado": event["estado"],
                "horario": datetime.fromtimestamp(event["startTimestamp"], BRT).strftime('%H:%M'),
                "status": event["status"],
                "transmissao": transmissao
            }
            jogos_formatados.append(jogo)

        if falhas == len(consultas):
            return {"status": "erro", "dados": []}
        if falhas:
            # Resultado incompleto: as ligas que falharam não entram no cache
            return {"status": "parcial", "dados": jogos_formatados}
        return {"status": "sucesso", "dados": jogos_formatados}

    except Exception as e:
        print(f"Erro interno no servidor: {str(e)}")
        return {"status": "erro", "dados": []}
