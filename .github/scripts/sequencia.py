"""Card de sequência do README: total do último ano, sequência atual e maior sequência.

Uso no workflow:  python3 .github/scripts/sequencia.py <pasta>   (com GH_TOKEN no ambiente)
Autoteste:        python3 .github/scripts/sequencia.py --teste

Lê o mesmo calendário de contribuições que o GitHub mostra no perfil (GraphQL
contributionCalendar). Com "Private contributions" ligado, ele já traz as
contribuições privadas como números anônimos, e os dias vêm contados no fuso do
perfil. Assim o card bate com o gráfico. "Hoje" é o dia em Brasília: se ainda
não houve contribuição hoje, a sequência atual vale até ontem, como no GitHub.
Grava <pasta>/github/sequencia.svg (tema claro) e <pasta>/github_dark/sequencia.svg.
"""

import datetime
import json
import os
import sys
import urllib.request
from zoneinfo import ZoneInfo

USUARIO = "IsaacGomes260653"
BRASILIA = ZoneInfo("America/Sao_Paulo")
CONSULTA = """query($login: String!, $from: DateTime, $to: DateTime) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionYears
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}"""
# Mesmas cores do card antigo (streak-stats com o dourado do perfil).
TEMAS = {
    "github": {"texto": "#151515", "apoio": "#464646", "destaque": "#8a6210", "linha": "#e4e2e2"},
    "github_dark": {"texto": "#fefefe", "apoio": "#9e9e9e", "destaque": "#e8b84a", "linha": "#30363d"},
}


def graphql(variaveis):
    corpo = json.dumps({"query": CONSULTA, "variables": {"login": USUARIO, **variaveis}}).encode()
    pedido = urllib.request.Request("https://api.github.com/graphql", data=corpo, headers={
        "Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        resposta = json.load(r)
    if resposta.get("errors"):
        sys.exit(f"GraphQL: {resposta['errors']}")
    return resposta["data"]["user"]["contributionsCollection"]


def dias(colecao):
    return {d["date"]: d["contributionCount"]
            for w in colecao["contributionCalendar"]["weeks"] for d in w["contributionDays"]}


def sequencias(contagem, hoje):
    """(início, fim, dias) da sequência atual e da maior, a partir de {data ISO: contagem}."""
    um = datetime.timedelta(days=1)
    dia = hoje if contagem.get(hoje.isoformat()) else hoje - um  # hoje ainda pode ganhar contribuição
    fim = dia
    while contagem.get(dia.isoformat()):
        dia -= um
    atual = (dia + um, fim, (fim - dia).days)
    maior, inicio = (None, None, 0), None
    for data in sorted(contagem):
        d = datetime.date.fromisoformat(data)
        if d > hoje:
            break
        if contagem[data]:
            inicio = inicio or d
            if (d - inicio).days + 1 > maior[2]:
                maior = (inicio, d, (d - inicio).days + 1)
        else:
            inicio = None
    return atual, maior


def numero(n):
    return f"{n:,}".replace(",", ".")


def periodo(inicio, fim, hoje):
    if not inicio:
        return "—"
    f = lambda d: d.strftime("%d/%m") if d.year == hoje.year else d.strftime("%d/%m/%Y")
    return f(inicio) if inicio == fim else f"{f(inicio)} – {f(fim)}"


def svg(tema, total, desde, atual, maior, hoje, agora):
    c = TEMAS[tema]
    fonte = "font-family=\"'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif\""

    def coluna(x, valor, rotulo, rotulo_en, datas, cor_valor, cor_rotulo):
        return (f'<text x="{x}" y="{78 if cor_valor == c["destaque"] else 70}" text-anchor="middle" {fonte} font-size="28" font-weight="700" fill="{cor_valor}">{valor}</text>'
                f'<text x="{x}" y="118" text-anchor="middle" {fonte} font-size="14" font-weight="600" fill="{cor_rotulo}">{rotulo}</text>'
                f'<text x="{x}" y="135" text-anchor="middle" {fonte} font-size="11" fill="{c["apoio"]}">{rotulo_en}</text>'
                f'<text x="{x}" y="156" text-anchor="middle" {fonte} font-size="12" fill="{c["apoio"]}">{datas}</text>')

    titulo = (f"Contribuições no último ano: {numero(total)}. Sequência atual: {atual[2]} dias ({periodo(atual[0], atual[1], hoje)}). "
              f"Maior sequência: {maior[2]} dias ({periodo(maior[0], maior[1], hoje)}).")
    dias_txt = lambda n: f"{n} day" if n == 1 else f"{n} days"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="190" viewBox="0 0 600 190" role="img" aria-label="{titulo}">
<title>{titulo}</title>
<line x1="200" y1="16" x2="200" y2="160" stroke="{c["linha"]}"/>
<line x1="400" y1="16" x2="400" y2="160" stroke="{c["linha"]}"/>
{coluna(100, numero(total), "Contribuições", "no último ano · in the last year", periodo(desde, hoje, hoje), c["texto"], c["texto"])}
<circle cx="300" cy="64" r="40" fill="none" stroke="{c["destaque"]}" stroke-width="5"/>
{coluna(300, atual[2], "Sequência atual", "current streak · " + dias_txt(atual[2]), periodo(atual[0], atual[1], hoje), c["destaque"], c["destaque"])}
{coluna(500, maior[2], "Maior sequência", "longest streak · " + dias_txt(maior[2]), periodo(maior[0], maior[1], hoje), c["texto"], c["texto"])}
<text x="300" y="182" text-anchor="middle" {fonte} font-size="10" fill="{c["apoio"]}">calendário do perfil · atualizado em {agora.strftime("%d/%m/%Y %H:%M")} (Brasília)</text>
</svg>
"""


def teste():
    d = datetime.date
    cal = {"2026-10-16": 0, "2026-10-17": 3, "2026-10-18": 1, "2026-10-19": 0,
           "2026-10-20": 2, "2026-10-21": 5, "2026-10-22": 1, "2026-10-23": 0}
    # Hoje sem contribuição ainda: a sequência vale até ontem.
    cal["2026-10-24"] = 0
    atual, maior = sequencias({**cal, "2026-10-23": 4}, d(2026, 10, 24))
    assert atual == (d(2026, 10, 20), d(2026, 10, 23), 4), atual
    assert maior == (d(2026, 10, 20), d(2026, 10, 23), 4), maior
    # Ontem e hoje sem contribuição: sequência zerada; a maior continua.
    atual, maior = sequencias(cal, d(2026, 10, 24))
    assert atual[2] == 0 and maior == (d(2026, 10, 20), d(2026, 10, 22), 3), (atual, maior)
    # Hoje com contribuição conta, e dia futuro (fuso) é ignorado.
    atual, _ = sequencias({**cal, "2026-10-23": 1, "2026-10-24": 2, "2026-10-25": 9}, d(2026, 10, 24))
    assert atual == (d(2026, 10, 20), d(2026, 10, 24), 5), atual
    assert numero(1459) == "1.459" and periodo(d(2026, 10, 18), d(2026, 10, 30), d(2026, 10, 30)) == "18/10 – 30/10"
    assert periodo(d(2025, 10, 26), d(2026, 10, 30), d(2026, 10, 30)) == "26/10/2025 – 30/10"
    texto = svg("github_dark", 1459, d(2025, 10, 26), (d(2026, 10, 18), d(2026, 10, 30), 13), (d(2026, 10, 18), d(2026, 10, 30), 13),
                d(2026, 10, 30), datetime.datetime(2026, 10, 30, 12, 5, tzinfo=BRASILIA))
    assert "1.459" in texto and "18/10 – 30/10" in texto and "13 days" in texto and "13 dias (" in texto and "#e8b84a" in texto
    print("ok")


if __name__ == "__main__":
    if "--teste" in sys.argv:
        teste()
        sys.exit()
    agora = datetime.datetime.now(BRASILIA)
    hoje = agora.date()
    ultimo_ano = graphql({})  # sem datas = o mesmo período do gráfico do perfil
    contagem = dias(ultimo_ano)
    for ano in ultimo_ano["contributionYears"]:  # a maior sequência olha a conta inteira
        contagem = {**dias(graphql({"from": f"{ano}-01-01T00:00:00Z", "to": f"{ano}-12-31T23:59:59Z"})), **contagem}
    total = ultimo_ano["contributionCalendar"]["totalContributions"]
    desde = datetime.date.fromisoformat(min(dias(ultimo_ano)))
    atual, maior = sequencias(contagem, hoje)
    # O log mostra o que o GITHUB_TOKEN enxerga, para conferir com o perfil.
    print(f"total no último ano: {total} (commits {ultimo_ano['totalCommitContributions']}, "
          f"privadas anônimas {ultimo_ano['restrictedContributionsCount']}) | hoje em Brasília: {hoje} = {contagem.get(hoje.isoformat(), 0)}")
    print(f"últimos dias: {' '.join([f'{k[5:]}={v}' for k, v in sorted(contagem.items()) if k <= hoje.isoformat()][-6:])}")
    print(f"sequência atual: {atual[2]} ({atual[0]} a {atual[1]}) | maior: {maior[2]} ({maior[0]} a {maior[1]})")
    for tema in TEMAS:
        os.makedirs(os.path.join(sys.argv[1], tema), exist_ok=True)
        with open(os.path.join(sys.argv[1], tema, "sequencia.svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(svg(tema, total, desde, atual, maior, hoje, agora))
