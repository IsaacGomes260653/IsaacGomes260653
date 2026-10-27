"""Atividade recente do README: as últimas ações públicas no GitHub, em lista.

Uso no workflow:  python3 .github/scripts/atividade.py   (com GH_TOKEN no ambiente)
Autoteste:        python3 .github/scripts/atividade.py --teste

Lê a API de eventos públicos (só o que já é público, nada de repositório
privado) e troca o trecho entre ATIVIDADE:INICIO e ATIVIDADE:FIM do README.md.
Entram PRs mesclados, repositórios criados ou publicados, commits enviados e
issues abertas ou fechadas. Desde 2025 a API manda eventos enxutos (o PR vem
sem título, e o push, sem a lista de commits), então o título é buscado à parte.
"""

import datetime
import json
import os
import sys
import urllib.request

from estudos import substitui

USUARIO = "IsaacGomes260653"
API = "https://api.github.com"
INICIO = "<!-- ATIVIDADE:INICIO -->"
FIM = "<!-- ATIVIDADE:FIM -->"
LIMITE = 8
BRASILIA = datetime.timezone(datetime.timedelta(hours=-3))  # sem horário de verão desde 2019
MERGE = datetime.timedelta(seconds=60)  # o merge gera um push no branch de destino logo depois


def api(caminho):
    url = caminho if caminho.startswith("http") else f"{API}/{caminho}"
    cabecalhos = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if os.environ.get("GH_TOKEN"):
        cabecalhos["Authorization"] = f"Bearer {os.environ['GH_TOKEN']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=cabecalhos), timeout=30) as r:
        return json.load(r)


def hora(e):
    return datetime.datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))


def md(t):
    """Texto vindo de fora (título de PR ou issue) seguro dentro do Markdown."""
    for c in "\\`*_[]<>":
        t = t.replace(c, f"\\{c}")
    return t


def nome_repo(repo):
    dono, _, nome = repo.partition("/")
    return nome if dono == USUARIO else repo


def itens(eventos, busca=api):
    """Até LIMITE itens, do mais novo para o mais antigo:
    (ícone, ação PT, ação EN, título, link, repositório ou "", data)."""
    eventos = sorted(eventos, key=hora, reverse=True)
    merges = [(e["repo"]["name"], e["payload"]["pull_request"]["base"]["ref"], hora(e)) for e in eventos
              if e["type"] == "PullRequestEvent" and e["payload"].get("action") == "merged"]
    saida, vistos = [], set()
    for e in eventos:
        tipo, p, repo = e["type"], e["payload"], e["repo"]["name"]
        dia, url_repo = hora(e).astimezone(BRASILIA).date(), f"https://github.com/{repo}"
        acao = p.get("action")
        if tipo == "PullRequestEvent" and (acao == "merged" or acao == "closed" and p["pull_request"].get("merged")):
            pr = p["pull_request"]
            pr = pr if "title" in pr and "html_url" in pr else busca(pr["url"])
            chave = ("pr", repo, pr["number"])
            item = ("🔀", "PR mesclado", "Merged pull request", md(pr["title"]), pr["html_url"], repo)
        elif tipo == "CreateEvent" and p.get("ref_type") == "repository":
            chave = ("repo", repo)
            item = ("📦", "Repositório criado", "Created repository", md(nome_repo(repo)), url_repo, "")
        elif tipo == "PublicEvent":
            chave = ("publico", repo)
            item = ("🌐", "Repositório publicado", "Made public", md(nome_repo(repo)), url_repo, "")
        elif tipo == "PushEvent":
            ramo = p.get("ref", "").removeprefix("refs/heads/")
            if any(r == repo and b == ramo and datetime.timedelta(0) <= hora(e) - t <= MERGE for r, b, t in merges):
                continue  # é o push do próprio merge, que já aparece como PR mesclado
            chave = ("push", repo, ramo, dia)  # vários pushes no mesmo dia viram um item
            item = ("⬆️", "Commits enviados", "Pushed commits", f"`{md(ramo)}`",
                    f"{url_repo}/commit/{p['head']}", repo)
        elif tipo == "IssuesEvent" and acao in ("opened", "closed"):
            issue = p["issue"]
            issue = issue if "title" in issue and "html_url" in issue else busca(issue["url"])
            chave = ("issue", repo, issue["number"], acao)
            item = ("📝", "Issue aberta", "Opened issue") if acao == "opened" else ("✅", "Issue fechada", "Closed issue")
            item = (*item, md(f"#{issue['number']} {issue['title']}"), issue["html_url"], repo)
        else:
            continue
        if chave not in vistos:
            vistos.add(chave)
            saida.append((*item, dia))
        if len(saida) == LIMITE:
            break
    return saida


def lista(itens):
    linhas = []
    for icone, pt, en, titulo, url, repo, dia in itens:
        onde = f" · [{md(nome_repo(repo))}](https://github.com/{repo})" if repo else ""
        linhas.append(f"- {icone} **[{titulo}]({url})**{onde}<br>\n"
                      f"  <sub>{pt} · <em>{en}</em> · {dia:%d/%m/%Y}</sub>")
    if not linhas:
        linhas = ["Nenhuma atividade pública recente.<br>\n<em>No recent public activity.</em>"]
    return "\n".join([INICIO, "<!-- Gerado pelo workflow atividade.yml a partir dos eventos públicos do GitHub."
                              " Não edite aqui. -->", "", *linhas, FIM])


def teste():
    def ev(tipo, quando, payload, repo=f"{USUARIO}/perfil"):
        return {"type": tipo, "created_at": quando, "payload": payload, "repo": {"name": repo}}

    pr = lambda n, base="main": {"url": f"{API}/repos/x/pulls/{n}", "number": n, "base": {"ref": base}}
    buscados = []

    def busca(url):
        buscados.append(url)
        n = int(url.rsplit("/", 1)[1])
        return {"number": n, "title": f"Título *{n}* [x]", "html_url": f"https://github.com/x/pull/{n}"}

    eventos = [
        ev("PullRequestEvent", "2026-10-27T11:21:40Z", {"action": "merged", "number": 25, "pull_request": pr(25)}),
        ev("PullRequestEvent", "2026-10-27T11:21:24Z", {"action": "opened", "number": 25, "pull_request": pr(25)}),
        ev("PushEvent", "2026-10-27T11:21:41Z", {"ref": "refs/heads/main", "head": "m1"}),       # push do merge
        ev("PushEvent", "2026-10-27T01:22:29Z", {"ref": "refs/heads/passeio", "head": "p3"}),    # 26/10 em Brasília
        ev("PushEvent", "2026-10-26T14:20:26Z", {"ref": "refs/heads/passeio", "head": "p1"}),    # mesmo dia: junta
        ev("PushEvent", "2026-10-25T13:17:14Z", {"ref": "refs/heads/main", "head": "c9"}),
        ev("CreateEvent", "2026-10-24T14:00:31Z", {"ref": "x", "ref_type": "branch"}),
        ev("DeleteEvent", "2026-10-24T14:02:37Z", {"ref": "x", "ref_type": "branch"}),
        ev("CreateEvent", "2026-10-23T10:00:00Z", {"ref": None, "ref_type": "repository"}, "outra/lib"),
        ev("IssuesEvent", "2026-10-22T10:00:00Z", {"action": "opened", "issue": {
            "number": 14, "title": "Painel <de> estudos", "html_url": "https://github.com/x/issues/14"}}),
        ev("IssuesEvent", "2026-10-22T09:00:00Z", {"action": "labeled", "issue": {"number": 14}}),
    ]
    saida = itens(eventos, busca)
    assert [i[0] for i in saida] == ["🔀", "⬆️", "⬆️", "📦", "📝"], saida
    assert buscados == [f"{API}/repos/x/pulls/25"]
    assert saida[1][4].endswith("/commit/p3") and str(saida[1][6]) == "2026-10-26"
    texto = lista(saida)
    assert texto.startswith(INICIO + "\n") and texto.endswith("\n" + FIM)
    assert ("- 🔀 **[Título \\*25\\* \\[x\\]](https://github.com/x/pull/25)**"
            f" · [perfil](https://github.com/{USUARIO}/perfil)<br>\n"
            "  <sub>PR mesclado · <em>Merged pull request</em> · 27/10/2026</sub>") in texto
    assert "- ⬆️ **[`passeio`](" in texto and "Commits enviados · <em>Pushed commits</em> · 26/10/2026" in texto
    assert "- 📦 **[outra/lib](https://github.com/outra/lib)**<br>" in texto  # repositório de outra pessoa: nome inteiro
    assert "**[#14 Painel \\<de\\> estudos](https://github.com/x/issues/14)**" in texto
    muitos = [ev("PushEvent", f"2026-10-{d:02d}T12:00:00Z", {"ref": "refs/heads/main", "head": str(d)}) for d in range(1, 20)]
    assert len(itens(muitos, busca)) == LIMITE
    assert "Nenhuma atividade" in lista([])
    print("ok")


if __name__ == "__main__":
    if "--teste" in sys.argv:
        teste()
        sys.exit()
    bloco = lista(itens(api(f"users/{USUARIO}/events/public?per_page=100")))
    with open("README.md", encoding="utf-8") as f:
        readme = f.read()
    novo = substitui(readme, bloco, INICIO, FIM)
    with open("README.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(novo)
