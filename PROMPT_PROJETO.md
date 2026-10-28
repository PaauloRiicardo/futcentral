# Prompt do projeto — FutCentral

> Cole o bloco abaixo no Claude Code (extensão do VS Code ou app desktop) com a pasta
> `C:\Users\PauloRicardo\Documents\Site` aberta como workspace.

---

```text
Você vai trabalhar no projeto FutCentral, um site que mostra os jogos de futebol do dia:
data, horário (fuso de Brasília), campeonato, times, status e ONDE o jogo será transmitido
(TV aberta, TV fechada e streaming).

## 1. Leia a pasta antes de qualquer alteração
Pasta: C:\Users\PauloRicardo\Documents\Site
Ignore a pasta .sitevirtual (é o ambiente virtual) e __pycache__.

Estado atual que você vai encontrar:
- main.py — backend FastAPI com a rota GET /api/jogos?data=AAAA-MM-DD, que consulta a
  SportAPI7 (RapidAPI: sportapi7.p.rapidapi.com, rota /api/v1/sport/football/events/date/{data})
  e devolve {status, dados:[{liga, mandante, visitante, horario, status, transmissao}]}.
- site_esportivo.html — frontend único com Tailwind (CDN) + Font Awesome, que chama
  http://127.0.0.1:8000/api/jogos e renderiza cards.
- .sitevirtual — venv criado com uv, Python 3.14, com fastapi, uvicorn, requests, pydantic.
- .vscode/settings.json — só define o gerenciador de ambiente Python.

Depois de ler, me mostre um resumo curto do que entendeu e a lista de problemas
encontrados ANTES de editar.

## 2. Problemas conhecidos que devem ser corrigidos (em ordem de prioridade)
1. SEGURANÇA: a chave da RapidAPI está escrita direto no main.py. Mova para um arquivo
   .env (carregado com python-dotenv), crie .env.example sem o valor real e um .gitignore
   que inclua .env, .sitevirtual e __pycache__. Me avise para eu gerar uma chave nova
   no painel da RapidAPI, porque a atual já ficou exposta.
2. FUSO HORÁRIO: o backend usa datetime.fromtimestamp sem fuso e o frontend usa
   toISOString() (UTC) para a data de hoje — depois das 21h no Brasil o site mostra o
   dia seguinte. Use zoneinfo("America/Sao_Paulo") no backend e data local no frontend.
3. TRANSMISSÃO: confirme na documentação da SportAPI7 se o evento do endpoint por data
   realmente traz canais de TV. Se não trouxer, use o endpoint de canais por evento
   (filtrando pelo país BR) e faça cache para não estourar a cota da API.
4. FILTROS: a busca por time/liga e os botões de continente existem no HTML mas não
   filtram nada. Implemente a filtragem no frontend (mapeando liga/país → continente).
5. XSS: os cards usam innerHTML com dados vindos da API externa. Escape os textos ou
   monte os elementos com textContent.
6. ROBUSTEZ: adicione timeout no requests.get, cache em memória por data
   (ex.: 10 min), e retorne erros HTTP adequados em vez de sempre 200.
7. SERVIR O FRONTEND PELO FASTAPI: monte o HTML como arquivo estático (StaticFiles)
   para abrir tudo em http://127.0.0.1:8000 sem depender de abrir o arquivo direto.

## 3. Estrutura alvo (sugestão, ajuste se fizer sentido)
Site/
  app/main.py            (FastAPI, rotas)
  app/sportapi.py        (cliente da API externa + cache)
  app/models.py          (modelos Pydantic de Jogo)
  static/index.html      (frontend)
  static/app.js          (lógica do frontend separada do HTML)
  tests/test_api.py      (pytest com respostas da API mockadas)
  pyproject.toml         (dependências via uv)
  .env / .env.example / .gitignore
  CLAUDE.md              (rode /init para gerar)

## 4. Integração com o VS Code
Crie/atualize:
- .vscode/settings.json → python.defaultInterpreterPath apontando para
  .sitevirtual\Scripts\python.exe
- .vscode/launch.json → configuração "FutCentral: API" que roda
  uvicorn app.main:app --reload --port 8000 com debug do Python
- .vscode/extensions.json → recomende: ms-python.python, ms-python.vscode-pylance,
  charliermarsh.ruff, bradlc.vscode-tailwindcss, humao.rest-client,
  anthropic.claude-code
- .claude/launch.json → mesma configuração do servidor, para o preview do Claude.

Comando para rodar (PowerShell):
  .\.sitevirtual\Scripts\Activate.ps1
  uvicorn app.main:app --reload --port 8000

## 5. Skills do Claude Code para este projeto
Use as skills que já existem:
- /init            → gerar o CLAUDE.md com a descrição do projeto e os comandos.
- /run             → subir o servidor e conferir o site no navegador depois de cada mudança.
- /security-review → rodar depois de mover a chave da API e antes de publicar.
- /code-review     → revisar cada etapa antes de eu aceitar.
- /simplify        → limpar o código quando uma etapa estiver funcionando.

Crie também estas skills do projeto em .claude/skills/<nome>/SKILL.md
(use a skill skill-creator para escrevê-las):
- rodar-futcentral: ativa a venv, sobe o uvicorn na porta 8000 e abre o site;
  explica como resolver "porta em uso" e "backend não conecta".
- sportapi7: referência dos endpoints usados (jogos por data, canais de TV por evento),
  headers necessários, formato da resposta, limites de cota e como mockar nos testes.
- mapa-ligas: como adicionar uma liga/campeonato ao mapeamento de continente e de
  canais brasileiros (ex.: Brasileirão, Libertadores, Champions, Premier League).
- testar-futcentral: roda pytest e uma checagem manual de /api/jogos para hoje,
  ontem e amanhã.

## 6. Forma de trabalhar
- Responda em português.
- Faça uma etapa da seção 2 por vez, mostre o diff, rode o servidor e confirme que
  funciona antes da próxima.
- Não invente canais de transmissão: se a API não informar, mostre "Transmissão a
  confirmar".
- Nunca coloque a chave da API em código, log ou commit.
- Inicialize git (git init) e faça um commit por etapa só quando eu pedir.
```
