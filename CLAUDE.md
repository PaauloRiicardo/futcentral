# FutCentral — regras para agentes (Claude, Claude Code, /code-review)

Site com os jogos de futebol do dia, horário de Brasília, placar ao vivo, gols/cartões vermelhos e onde assistir no Brasil.
Detalhes de uso e arquitetura: `README.md`. Fale com o dono (Paulo) em português do Brasil.

## Mapa rápido
- `main.py` — FastAPI. `GET /` (página), `GET /api/jogos?data=AAAA-MM-DD`, `/static/{nome}` (lista fechada), `/favicon.ico`.
- `site_esportivo.html` — página inteira (HTML + JS puro). Classes do Tailwind 3 escritas por extenso.
- `estilos/entrada.css` → `static/site.css` (gerado no GitHub; ver abaixo).
- `canais.json` — onde assistir (padrão por campeonato + exceções por jogo).
- `tests/` — testes (pytest + Playwright). `.github/workflows/` — CI, deploy, medição, tarefas.

## Regras (o `/code-review` deve cobrar)
1. **Nunca edite `static/site.css` à mão.** Ele é gerado pelo Tailwind 3.4.17 a partir de `estilos/entrada.css` e das classes do `site_esportivo.html`, a cada publicação (`publicar-render.yml`). Estilo novo = classe do Tailwind no HTML ou regra em `estilos/entrada.css`.
2. **Classes do Tailwind sempre por extenso** no HTML/JS (ex.: `'bg-green-500'`), nunca montadas com concatenação (`'bg-' + cor`): o gerador só enxerga texto completo.
3. **Mudou o formato do que `_resumir_evento` guarda?** Suba `CACHE_VERSAO` em `main.py` (ex.: `"v3"` → `"v4"`), senão o cache antigo quebra a resposta.
4. **`canais.json`:** a seção `"campeonatos"` só muda a pedido do Paulo. A seção `"jogos"` é mantida pela tarefa agendada diária ("FutCentral – canais do dia"), que só cadastra canal confirmado por fonte do dia. Chave de jogo: `"AAAA-MM-DD Mandante x Visitante"` com os nomes exatamente como o site mostra.
5. **Texto vindo da API vai para o HTML sempre por `esc()`** (proteção contra XSS). Nada de `innerHTML` com dado cru.
6. **Arquivos estáticos:** só os nomes de `ARQUIVOS_ESTATICOS` são servidos. Arquivo novo em `static/` precisa entrar nessa lista (e nunca liberar caminhos com `/` ou `..`).
7. **Linha dos times no card:** 3 colunas (`COLUNAS_JOGO`: time | meio fixo 4,5rem | time). Não volte para `flex-1`: nomes longos desalinhavam o "VS"/placar.
8. **Segredos:** nunca no código nem no front-end. O deploy usa o segredo `RENDER_DEPLOY_HOOK` do GitHub — não leia, não imprima, não peça.
9. **URLs absolutas** (canonical, `og:*`, `twitter:*` no `<head>`) usam `https://futcentral.onrender.com` até o domínio próprio entrar; ao trocar, troque todas e aumente o `?v=` da imagem `og.jpg`.
10. **ESPN não é oficial:** trate campos ausentes (use `.get(...)`), nunca deixe uma liga com erro derrubar a resposta inteira.

## Antes de dizer que terminou
- Rode os testes: `pip install -r requirements.txt -r requirements-dev.txt && python -m playwright install chromium && pytest`.
- Mexeu em comportamento? **Escreva ou ajuste um teste** em `tests/`. Bug corrigido = teste que falharia antes.
- Mexeu na página? Rode também o teste no navegador (está no `pytest`) e, se puder, `Actions → Medir site` depois do deploy (meta: 100 no Lighthouse).
- Mudanças pequenas e fáceis de desfazer, com mensagem de commit clara em português.

## Fluxo de publicação
- Um push na `main` roda **Testes → (só se passar) gera o CSS → publica no Render**. Teste falhou = site não muda.
- Mudança de código: de preferência em branch + Pull Request (os testes rodam no PR). A tarefa diária de canais faz push direto na `main` (só `canais.json`).
- Repositório público: nunca commitar `.env`, chaves ou dados pessoais.
