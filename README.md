# ⚽ FutCentral

Jogos de futebol do dia dos principais campeonatos do Brasil, da América do Sul e da Europa, além dos amistosos das principais seleções, com **horário de Brasília**, **placar ao vivo** e **onde assistir no Brasil**.

🔗 **No ar:** https://futcentral.onrender.com

## O que o site faz

- Lista os jogos de qualquer data, com busca por time ou campeonato
- Abas **Brasil**, **América do Sul**, **Europa** e **Seleções**
- Mostra o placar durante e depois do jogo e o atualiza sozinho a cada 60 s quando a data é hoje ou há jogo em andamento (pausa com a aba do navegador escondida)
- Mostra quem fez os gols (com pênalti e gol contra) e quem levou cartão vermelho, embaixo de cada time
- Mostra os canais de TV e streaming de cada jogo, cadastrados à mão
- Avisa quando a fonte dos dados falha, em vez de mostrar "Nenhum jogo encontrado"

## Stack

| Parte | Tecnologia |
|---|---|
| Backend | Python 3.13 · FastAPI · Uvicorn · requests |
| Frontend | Um arquivo HTML com JavaScript puro; CSS do Tailwind 3 gerado no GitHub (`static/site.css`) e ícones do Font Awesome embutidos como SVG |
| Dados | API pública da ESPN (sem chave) |
| Hospedagem | Render, plano gratuito |
| Automação | GitHub Actions: deploy a cada push e monitor que mantém o site acordado |

## Rodar no computador (Windows / PowerShell)

```powershell
cd C:\Users\PauloRicardo\Documents\Site
.\.sitevirtual\Scripts\Activate.ps1           # ativa o ambiente virtual
uvicorn main:app --reload --port 8000         # --reload reinicia ao salvar arquivos
```

Abra http://127.0.0.1:8000

Para criar o ambiente do zero:

```powershell
uv venv .sitevirtual --python 3.13
.\.sitevirtual\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `main.py` | API: `GET /` entrega o site; `GET /api/jogos?data=AAAA-MM-DD` devolve os jogos |
| `site_esportivo.html` | A página: filtros, cards dos jogos, atualização automática |
| `canais.json` | Onde assistir: canais padrão por campeonato e canais de jogos específicos |
| `estilos/entrada.css` | Entrada do Tailwind (e o estilo dos cards fantasma). O CSS final `static/site.css` é gerado no GitHub a cada publicação — não edite à mão |
| `.github/workflows/medir-site.yml` | Mede o site no ar com o Lighthouse (Actions → Medir site → Run workflow) |
| `static/` | `og.jpg` (imagem da prévia ao compartilhar o link, 1200×630) e os ícones do site |
| `render.yaml` | Configuração do serviço no Render |
| `.github/workflows/publicar-render.yml` | Publica no Render a cada push na `main` |
| `.github/workflows/manter-acordado.yml` | Reserva: acessa o site a cada 10 min pelo GitHub (o agendamento do GitHub atrasa ou falha às vezes; o principal é a auto-visita no `main.py`) |
| `.github/workflows/listar-jogos.yml` | Lista os jogos de uma data no log; usada pela tarefa diária que cadastra os canais |

## Como mudar as coisas mais comuns

### Cadastrar onde passa um jogo
Edite o `canais.json` (não precisa reiniciar o servidor):

```json
"campeonatos": { "Premier League": ["Disney+"] },
"jogos": { "2026-11-14 Japão x Brasil": ["Globo", "SporTV", "ge tv"] }
```

- `campeonatos` vale para todos os jogos daquele campeonato.
- `jogos` vale para um jogo só e substitui o padrão. Use a chave `AAAA-MM-DD Mandante x Visitante`, com os nomes **como aparecem no site**.
- Lista vazia `[]` aparece como "Transmissão a confirmar".

### Incluir ou tirar um campeonato
Em `main.py`, no dicionário `LIGAS_PRINCIPAIS`, cada linha liga o código da ESPN ao nome, país e aba. Exemplo: `"eng.1": ("Premier League", "Inglaterra", "Europa")`. Cada campeonato custa 2 consultas à ESPN por data pesquisada.

### Escolher quais seleções aparecem nos amistosos
Em `main.py`, na lista `SELECOES_PRINCIPAIS`, separada por continente. Escreva o nome em **português e em inglês**, porque a ESPN às vezes devolve em inglês. Acentos e maiúsculas não importam.

### Prévia ao compartilhar o link
Título, descrição e imagem ficam nas tags `og:` e `twitter:` do `<head>` do `site_esportivo.html`. Os endereços usam `https://futcentral.onrender.com`: **se o domínio mudar, troque nessas tags**. Para trocar a imagem, substitua o `static/og.jpg` (1200×630, menos de 300 KB, com o logo **no centro**, porque o WhatsApp no computador mostra só um quadrado do meio) e aumente o `?v=` nos endereços da imagem para as redes buscarem a nova.

O WhatsApp e o Facebook guardam a prévia por alguns dias. Para forçar a atualização, use o [Sharing Debugger](https://developers.facebook.com/tools/debug/) → **Scrape Again**.

## API

`GET /api/jogos?data=2026-11-14`

| Resposta | Quando |
|---|---|
| `200 {"status": "sucesso", "dados": [...]}` | Tudo carregou |
| `200 {"status": "parcial", "dados": [...], "ligasComFalha": [...]}` | Alguns campeonatos falharam (o site mostra um aviso amarelo) |
| `400` | Data inválida |
| `503` | A ESPN não respondeu em nenhum campeonato |
| `500` | Erro interno |

Cada jogo traz `liga`, `pais`, `regiao`, `regioes` (abas em que aparece), `mandante`, `visitante`, `placarMandante`, `placarVisitante`, `estado` (`pre`, `in` ou `post`), `horario` (Brasília), `status`, `transmissao` e `lances` (gols e cartões vermelhos: `tipo` `gol`/`vermelho`, `lado` `mandante`/`visitante`, `jogador`, `minuto`, `penalti`, `contra`; o gol contra fica no lado do time que ganhou o gol).

## Testes
Ficam em `tests/` e rodam sem internet (com uma ESPN falsa, montada com jogos reais de 14/11/2026):
- `test_servidor.py`: gols/pênalti/gol contra/vermelho, horário de Brasília, filtro dos amistosos, ESPN fora do ar, cache, arquivos estáticos, compressão
- `test_canais.py`: formato do `canais.json`
- `test_pagina.py`: a página no navegador (cards alinhados no celular e no computador, gols, cards fantasma, mensagem de erro)

Rodar no PC (PowerShell, com o ambiente virtual ativado):
```powershell
pip install -r requirements.txt -r requirements-dev.txt
python -m playwright install chromium
pytest
```
No GitHub, eles rodam em todo Pull Request e antes de cada publicação: **se um teste falhar, o site não é publicado.** As regras do projeto para agentes de IA (e para o `/code-review`) estão no `CLAUDE.md`.

## Publicar

```powershell
git add <arquivos>
git commit -m "O que mudou"
git push
```

O GitHub Actions avisa o Render, que publica em 1 a 5 minutos. Acompanhe em **Actions → Publicar no Render** (no GitHub) e em **Events** (no Render).

- O link do Render fica no segredo `RENDER_DEPLOY_HOOK` do GitHub (**Settings → Secrets and variables → Actions**). Ele **nunca** deve ir para o código.
- O Auto-Deploy do Render fica desligado (**Off**) para não publicar duas vezes.
- Para publicar sem fazer um push novo, use **Actions → Publicar no Render → Run workflow**.

## CSS e desempenho
- O Tailwind não vem mais do CDN. A cada publicação, o GitHub gera `static/site.css` só com as classes que a página usa e salva no repositório (commit "CSS gerado (automático)").
- Rodando no PC, a página usa o `static/site.css` da última publicação: uma classe nova do Tailwind só ganha estilo depois do push. Para gerar na hora (precisa de Node): `npx tailwindcss@3.4.17 -i estilos/entrada.css -o static/site.css --content site_esportivo.html --minify`.
- As respostas são compactadas (GZip) e, no Render, uma tarefa de fundo deixa os jogos de hoje e de amanhã prontos no cache a cada 4 min.

## Cache

- Guardado em memória e em `.cache/espn.json`. Essa pasta fica fora do Git e é apagada a cada deploy no Render.
- Dias que já passaram ficam guardados para sempre. Dias futuros, por 3 h. Hoje, conforme cada campeonato: 60 s se tem jogo rolando ou começando em até 15 min, 10 min se ainda vai ter jogo, 6 h se já acabou tudo.
- Se a ESPN não responder, o site usa os últimos dados guardados daquele campeonato.
- Se mudar os campos que o servidor guarda de cada jogo, troque o `CACHE_VERSAO` em `main.py` para descartar o cache antigo.

## Limitações conhecidas

- A API da ESPN **não é oficial**: pode mudar ou sair do ar sem aviso.
- A ESPN só informa canais dos EUA, por isso os canais do Brasil são cadastrados à mão.
- No plano gratuito do Render, o site fica ligado cerca de 744 h por mês, das 750 h grátis.
- Para o site não "dormir", o `main.py` visita o próprio endereço a cada 10 min quando roda no Render (variável `RENDER_EXTERNAL_URL`, definida pelo Render). Se o serviço for reiniciado e ficar sem visitas, a primeira visita ainda demora uns 30 s.
- O monitor do GitHub é só reserva: o GitHub pode atrasar ou pular agendamentos e o pausa se o repositório ficar 60 dias sem commits.
