"""Painel de estatísticas do README: contribuições, sequências, commits, PRs e repositórios.

Uso no workflow:  python3 .github/scripts/estatisticas.py <pasta>   (com GH_TOKEN no ambiente)
Autoteste:        python3 .github/scripts/estatisticas.py --teste

Os números vêm do GitHub pelo GITHUB_TOKEN:
- contribuições do último ano e sequências: o mesmo calendário que o perfil
  mostra (GraphQL contributionCalendar). Com "Private contributions" ligado, ele
  já traz as privadas como números anônimos, com os dias no fuso do perfil.
  "Hoje" é o dia em Brasília: sem contribuição ainda hoje, a sequência vale até ontem;
- commits: soma de totalCommitContributions de todos os anos da conta;
- PRs e repositórios: pullRequests e repositoriesContributedTo (só públicos,
  incluindo os meus), as mesmas consultas do card antigo de estatísticas.
Cores, fonte e raio vêm do brand/tokens.json; o texto vira contorno da Mona
Sans (glifos.json). Grava painel-{claro,escuro}.svg (desktop, 820px) e
painel-celular-{claro,escuro}.svg (400px) em <pasta>.
"""

import datetime
import json
import math
import os
import sys
import urllib.request
from html import escape
from zoneinfo import ZoneInfo

from agora import RAIO, TEMAS, escreve, mede, tokens

# Tons da Noite Estrelada (azul-claro, cobalto, amarelo das estrelas) para as chamas fortes.
NOITE = tokens()["noite"]

USUARIO = "IsaacGomes260653"
BRASILIA = ZoneInfo("America/Sao_Paulo")
TEXTO, TITULO = 450, 620  # pesos da Mona Sans no glifos.json
CALENDARIO = """query($login: String!, $from: DateTime, $to: DateTime) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionYears
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}"""
CONTAS = """query($login: String!) {
  user(login: $login) {
    pullRequests(first: 1) { totalCount }
    repositoriesContributedTo(first: 1, includeUserRepositories: true, privacy: PUBLIC,
                              contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) { totalCount }
  }
}"""
# Ícones do Lucide (licença ISC), em traço, numa caixa de 24.
ICONES = {
    "commit": '<circle cx="12" cy="12" r="3"/><path d="M3 12h6"/><path d="M15 12h6"/>',
    "pr": '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><path d="M6 9v12"/>',
    "globo": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
}
# Um momento só: o anel enche e os números sobem, uma vez. Sem movimento para
# quem pede menos movimento; o estado final já é o desenho parado.
CSS = (".sobe{animation:sobe .9s cubic-bezier(.16,1,.3,1) both}"
       "@keyframes sobe{from{opacity:0;transform:translateY(8px)}}"
       ".anel{animation:enche 1.6s cubic-bezier(.16,1,.3,1) .25s both}"
       "@keyframes enche{from{stroke-dashoffset:var(--volta)}}"
       # A chama tremula pela base, o núcleo num ritmo próprio, faíscas sobem e estrelas piscam.
       ".tremula{transform-box:fill-box;transform-origin:50% 100%;animation:tremula 1.9s ease-in-out infinite}"
       ".nucleo{transform-box:fill-box;transform-origin:50% 100%;animation:tremula 1.3s ease-in-out -.4s infinite}"
       ".faisca{animation:faisca 2.4s ease-out infinite}.pisca{transform-box:fill-box;transform-origin:center;animation:pisca 2.8s ease-in-out infinite}"
       "@keyframes tremula{0%,100%{transform:scale(1,1) skewX(0)}30%{transform:scale(.96,1.05) skewX(-2deg)}65%{transform:scale(1.03,.97) skewX(1.5deg)}}"
       "@keyframes faisca{0%{transform:translateY(0);opacity:0}15%{opacity:1}100%{transform:translateY(-16px);opacity:0}}"
       "@keyframes pisca{50%{transform:scale(.55);opacity:.4}}"
       "@media (prefers-reduced-motion:reduce){.sobe,.anel,.tremula,.nucleo,.faisca,.pisca{animation:none}}")

# Chama em caixa de 1×1 com a base em (0,5, 1): corpo com duas línguas e um núcleo em gota.
CHAMA = ("M.5 1C.18 1 .06 .76 .14 .56C.2 .42 .32 .38 .34 .22C.42 .3 .46 .36 .48 .46C.56 .3 .6 .14 .52 0"
         "C.8 .16 .94 .44 .88 .66C.84 .86 .7 1 .5 1Z")
NUCLEO = "M.5 1C.34 1 .28 .86 .32 .76C.36 .66 .44 .62 .46 .5C.58 .6 .7 .72 .66 .84C.63 .94 .58 1 .5 1Z"
NIVEIS = ["apagada", "pequena", "média", "grande", "intensa", "lendária"]


def nivel_da_chama(dias):
    """0 dias: brasa; 1–3: pequena; 4–7: média; 8–14: grande; 15–29: intensa; 30+: lendária."""
    return next(i for i, limite in enumerate((0, 3, 7, 14, 29)) if dias <= limite) if dias < 30 else 5


def chama(T, nivel, x, base):
    """A chama da sequência, com a base em (x, base), nas cores do tema."""
    if nivel == 0:  # brasa apagada: parada e cinza
        return (f'<ellipse cx="{x}" cy="{base - 3}" rx="9" ry="3.5" fill="{T["suave"]}" fill-opacity=".55"/>'
                f'<ellipse cx="{x}" cy="{base - 4}" rx="4" ry="1.6" fill="{T["apoio"]}" fill-opacity=".5"/>')
    altura = (0, 16, 22, 28, 34, 40)[nivel]
    largura = altura * 0.78
    caixa = f'transform="translate({x - largura / 2:.1f} {base - altura}) scale({largura:.1f} {altura})"'
    externa, interna = T["ouro_forma"], NOITE["estrela"]
    if nivel >= 4:
        interna = NOITE["brilho"]
    if nivel == 5:
        externa = NOITE["cobalto"]
    partes = []
    if nivel >= 3:  # brilho em volta
        partes.append(f'<circle class="pisca" style="animation-duration:3.4s" cx="{x}" cy="{base - altura * .45:.1f}" r="{altura * .62:.1f}"'
                      f' fill="{externa}" fill-opacity="{.10 if nivel < 5 else .16}"/>')
    partes.append(f'<g class="tremula"><path d="{CHAMA}" {caixa} fill="{externa}" stroke="{T["ouro"]}"'
                  f' stroke-width="{1.2 / altura:.3f}" stroke-opacity=".6"/></g>')
    if nivel >= 2:
        partes.append(f'<g class="nucleo"><path d="{NUCLEO}" {caixa} fill="{interna}"/></g>')
    if nivel >= 2:  # faíscas
        for i, (dx, atraso) in enumerate(((-6, 0), (5, -.9), (1, -1.7))[: 2 if nivel < 4 else 3]):
            partes.append(f'<circle class="faisca" style="animation-delay:{atraso}s" cx="{x + dx}" cy="{base - altura * .8:.1f}" r="1.3" fill="{T["ouro_forma"]}"/>')
    if nivel == 5:  # estrelas em volta
        for dx, dy, atraso in ((-17, -30, 0), (16, -34, -1), (19, -12, -1.9), (-18, -8, -.6)):
            partes.append(f'<circle class="pisca" style="animation-delay:{atraso}s" cx="{x + dx}" cy="{base + dy}" r="1.8" fill="{NOITE["estrela"]}"/>')
    return "".join(partes)



# ---------------------------------------------------------------- dados

def graphql(consulta, variaveis):
    corpo = json.dumps({"query": consulta, "variables": {"login": USUARIO, **variaveis}}).encode()
    pedido = urllib.request.Request("https://api.github.com/graphql", data=corpo, headers={
        "Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        resposta = json.load(r)
    if resposta.get("errors"):
        sys.exit(f"GraphQL: {resposta['errors']}")
    return resposta["data"]["user"]


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


def coleta(hoje):
    """Os números do painel, lidos do GitHub."""
    ultimo_ano = graphql(CALENDARIO, {})["contributionsCollection"]  # sem datas = o período do perfil
    contagem, commits = dias(ultimo_ano), 0
    for ano in ultimo_ano["contributionYears"]:  # a maior sequência e os commits olham a conta inteira
        colecao = graphql(CALENDARIO, {"from": f"{ano}-01-01T00:00:00Z", "to": f"{ano}-12-31T23:59:59Z"})["contributionsCollection"]
        contagem = {**dias(colecao), **contagem}
        commits += colecao["totalCommitContributions"]
    contas = graphql(CONTAS, {})
    atual, maior = sequencias(contagem, hoje)
    # O log mostra o que o GITHUB_TOKEN enxerga, para conferir com o perfil.
    print(f"último ano: {ultimo_ano['contributionCalendar']['totalContributions']} "
          f"(privadas anônimas {ultimo_ano['restrictedContributionsCount']}) | hoje em Brasília: {hoje} = {contagem.get(hoje.isoformat(), 0)}")
    print(f"últimos dias: {' '.join([f'{k[5:]}={v}' for k, v in sorted(contagem.items()) if k <= hoje.isoformat()][-6:])}")
    print(f"sequência atual: {atual[2]} ({atual[0]} a {atual[1]}) | maior: {maior[2]} ({maior[0]} a {maior[1]})")
    print(f"commits: {commits} | PRs: {contas['pullRequests']['totalCount']} | repositórios públicos: {contas['repositoriesContributedTo']['totalCount']}")
    return {
        "total": ultimo_ano["contributionCalendar"]["totalContributions"],
        "desde": datetime.date.fromisoformat(min(dias(ultimo_ano))),
        "atual": atual, "maior": maior, "commits": commits,
        "prs": contas["pullRequests"]["totalCount"], "repos": contas["repositoriesContributedTo"]["totalCount"],
    }


# ---------------------------------------------------------------- texto

def numero(n):
    return f"{n:,}".replace(",", ".")


def periodo(inicio, fim, hoje):
    if not inicio:
        return "sem sequência"
    f = lambda d: d.strftime("%d/%m") if d.year == hoje.year else d.strftime("%d/%m/%Y")
    return f(inicio) if inicio == fim else f"{f(inicio)} – {f(fim)}"


def dias_pt(n):
    return "1 dia" if n == 1 else f"{n} dias"


def dias_en(n):
    return "1 day" if n == 1 else f"{n} days"


def resumo(d, hoje):
    """Texto do alt: tudo o que o painel mostra, em PT e EN."""
    a, m = d["atual"], d["maior"]
    return (f"{numero(d['total'])} contribuições no último ano ({periodo(d['desde'], hoje, hoje)}); "
            f"sequência atual de {dias_pt(a[2])} ({periodo(a[0], a[1], hoje)}); maior sequência de {dias_pt(m[2])}; "
            f"{numero(d['commits'])} commits desde 2025; {d['prs']} pull requests; {d['repos']} repositórios públicos com contribuição"
            f" / {numero(d['total'])} contributions in the last year; current streak {dias_en(a[2])}; longest streak {dias_en(m[2])}; "
            f"{numero(d['commits'])} commits since 2025; {d['prs']} pull requests; {d['repos']} public repos contributed to")


# ---------------------------------------------------------------- desenho

class Tela:
    """Junta as partes do SVG e confere que nenhum texto passa da largura dada."""

    def __init__(self, tema):
        self.T, self.usados, self.partes, self.n = TEMAS[tema], {}, [], 0

    def texto(self, t, x, y, tam, peso, tinta, largura=None, centro=False, sobe=True):
        w = mede(t, tam, peso)
        if largura is not None and w > largura + 0.5:
            raise SystemExit(f"o texto {t!r} ({w:.0f}px) não cabe em {largura}px")
        x = x - w / 2 if centro else x
        g = escreve(t, round(x, 1), y, tam, peso, self.T[tinta], self.usados)
        if sobe:  # os números e rótulos sobem um depois do outro, em 60ms
            g = f'<g class="sobe" style="animation-delay:{self.n * 0.06:.2f}s">{g}</g>'
            self.n += 1
        self.partes.append(g)

    def icone(self, nome, x, y):
        T = self.T
        self.partes.append(
            f'<rect x="{x}" y="{y}" width="36" height="36" rx="9" fill="{T["azulejo"]}"/>'
            f'<g transform="translate({x + 9} {y + 9}) scale(.75)" fill="none" stroke="{T["ouro"]}" stroke-width="2"'
            f' stroke-linecap="round" stroke-linejoin="round">{ICONES[nome]}</g>')

    def anel(self, cx, cy, r, fracao):
        volta = 2 * math.pi * r
        self.partes.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{self.T["contorno"]}" stroke-width="7"/>'
            f'<circle class="anel" cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{self.T["ouro"]}" stroke-width="7"'
            f' stroke-linecap="round" stroke-dasharray="{volta:.2f}" stroke-dashoffset="{volta * (1 - fracao):.2f}"'
            f' style="--volta:{volta:.2f}" transform="rotate(-90 {cx} {cy})"/>')

    def chama(self, dias, x, base):
        self.partes.append(chama(self.T, nivel_da_chama(dias), x, base))

    def linha(self, x1, y, x2):
        self.partes.append(f'<path d="M{x1} {y}H{x2}" stroke="{self.T["contorno"]}"/>')

    def svg(self, largura, altura, alt):
        T, m = self.T, 6  # margem para a sombra, como nos cards do Agora
        w, h = largura - 2 * m, altura - 2 * m
        (c1, c2), (sombra, opacidade), (acento, opac_acento) = T["caixa"], T["sombra"], T["acento"]
        defs = "".join(f'<path id="{n}" d="{d}"/>' for n, d in self.usados.items())
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" viewBox="0 0 {largura} {altura}"'
            f' role="img" aria-label="{escape(alt)}"><title>{escape(alt)}</title><style>{CSS}</style><defs>'
            f'<linearGradient id="caixa" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/>'
            f'<stop offset="1" stop-color="{c2}"/></linearGradient>'
            f'<filter id="sombra" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="0" dy="1.5"'
            f' stdDeviation="2.5" flood-color="{sombra}" flood-opacity="{opacidade}"/></filter>'
            f'<clipPath id="cartao"><rect x="{m}" y="{m}" width="{w}" height="{h}" rx="{RAIO}"/></clipPath>{defs}</defs>'
            f'<rect x="{m}" y="{m}" width="{w}" height="{h}" rx="{RAIO}" fill="url(#caixa)" stroke="{T["contorno"]}" filter="url(#sombra)"/>'
            # Quarto de círculo no canto, à maneira dos azulejos de Athos Bulcão, como nos cards do Agora.
            f'<path d="M{largura - m - 72} {m}A72 72 0 0 0 {largura - m} {m + 72}V{m}Z" fill="{acento}"'
            f' fill-opacity="{opac_acento}" clip-path="url(#cartao)"/>'
            f'{"".join(self.partes)}</svg>\n'
        )


def tres_numeros(t, d, xs, y, largura):
    """Commits, PRs e repositórios: azulejo com ícone, número e rótulos PT e EN."""
    itens = [("commit", numero(d["commits"]), "commits desde 2025", "commits since 2025"),
             ("pr", numero(d["prs"]), "pull requests criados", "pull requests opened"),
             ("globo", numero(d["repos"]), "repos públicos com contribuição", "public repos contributed to")]
    for (icone, valor, pt, en), (x, yy) in zip(itens, xs(y)):
        t.icone(icone, x, yy)
        t.texto(valor, x + 50, yy + 18, 20, TITULO, "tinta", largura)
        t.texto(pt, x + 50, yy + 36, 12, TEXTO, "apoio", largura)
        t.texto(en, x + 50, yy + 52, 11, TEXTO, "suave", largura)


def painel(tema, d, hoje, agora):
    """SVG desktop: 820 de largura, três faixas (destaque, números, atualização)."""
    t, W, x0 = Tela(tema), 820, 34
    a, m = d["atual"], d["maior"]
    t.texto("Atividade no GitHub", x0, 48, 16, TITULO, "ouro", sobe=False)
    t.texto("· GitHub activity", x0 + mede("Atividade no GitHub ", 16, TITULO), 48, 13, TEXTO, "apoio", sobe=False)
    # Destaque: o total do último ano e, ao lado, o anel da sequência atual.
    t.texto(numero(d["total"]), x0, 128, 54, TITULO, "tinta", 300)
    t.texto("contribuições no último ano", x0, 156, 14, TEXTO, "apoio", 300)
    t.texto("contributions in the last year", x0, 174, 12, TEXTO, "suave", 300)
    t.texto(periodo(d["desde"], hoje, hoje), x0, 196, 12, TITULO, "ouro", 300)
    t.anel(410, 140, 46, a[2] / m[2] if m[2] else 0)
    t.texto(str(a[2]), 410, 151, 32, TITULO, "tinta", 70, centro=True)
    t.texto("dias" if a[2] != 1 else "dia", 410, 166, 11, TEXTO, "apoio", 70, centro=True)
    xd = 484
    t.texto("Sequência atual", xd, 104, 16, TITULO, "tinta", 302)
    t.chama(a[2], xd + mede("Sequência atual", 16, TITULO) + 22, 108)
    t.texto(f"current streak · {dias_en(a[2])}", xd, 121, 12, TEXTO, "suave", 302)
    t.texto(periodo(a[0], a[1], hoje), xd, 140, 12, TITULO, "ouro", 302)
    t.texto(f"Maior sequência: {dias_pt(m[2])}", xd, 170, 13, TEXTO, "apoio", 302)
    t.texto(f"longest streak · {dias_en(m[2])}", xd, 187, 12, TEXTO, "suave", 302)
    t.texto(periodo(m[0], m[1], hoje), xd, 205, 12, TITULO, "ouro", 302)
    t.linha(x0, 230, W - x0)
    tres_numeros(t, d, lambda y: [(x0, y), (x0 + 254, y), (x0 + 508, y)], 254, 194)
    t.texto(f"atualizado em {agora.strftime('%d/%m/%Y %H:%M')} (Brasília) · mesmo calendário do perfil", x0, 340, 11, TEXTO, "suave", sobe=False)
    return t.svg(W, 358, resumo(d, hoje))


def painel_celular(tema, d, hoje, agora):
    """SVG para o celular: 400 de largura, tudo empilhado e em tamanho de leitura."""
    t, W, x0 = Tela(tema), 400, 30
    larg = W - 2 * x0
    a, m = d["atual"], d["maior"]
    t.texto("Atividade no GitHub", x0, 46, 16, TITULO, "ouro", sobe=False)
    t.texto("GitHub activity", x0, 64, 13, TEXTO, "apoio", sobe=False)
    t.texto(numero(d["total"]), x0, 128, 50, TITULO, "tinta", larg)
    t.texto("contribuições no último ano", x0, 154, 14, TEXTO, "apoio", larg)
    t.texto("contributions in the last year", x0, 172, 12, TEXTO, "suave", larg)
    t.texto(periodo(d["desde"], hoje, hoje), x0, 194, 12, TITULO, "ouro", larg)
    t.linha(x0, 216, W - x0)
    t.anel(x0 + 44, 272, 40, a[2] / m[2] if m[2] else 0)
    t.texto(str(a[2]), x0 + 44, 282, 28, TITULO, "tinta", 60, centro=True)
    t.texto("dias" if a[2] != 1 else "dia", x0 + 44, 296, 11, TEXTO, "apoio", 60, centro=True)
    xd = x0 + 108
    t.texto("Sequência atual", xd, 254, 16, TITULO, "tinta", W - x0 - xd)
    t.chama(a[2], xd + mede("Sequência atual", 16, TITULO) + 22, 258)
    t.texto(f"current streak · {dias_en(a[2])}", xd, 272, 12, TEXTO, "suave", W - x0 - xd)
    t.texto(periodo(a[0], a[1], hoje), xd, 292, 12, TITULO, "ouro", W - x0 - xd)
    t.texto(f"Maior sequência: {dias_pt(m[2])} · {periodo(m[0], m[1], hoje)}", x0, 346, 13, TEXTO, "apoio", larg)
    t.texto(f"longest streak · {dias_en(m[2])}", x0, 364, 12, TEXTO, "suave", larg)
    t.linha(x0, 388, W - x0)
    tres_numeros(t, d, lambda y: [(x0, y), (x0, y + 66), (x0, y + 132)], 410, larg - 50)
    t.texto(f"atualizado em {agora.strftime('%d/%m/%Y %H:%M')} (Brasília)", x0, 628, 11, TEXTO, "suave", larg, sobe=False)
    return t.svg(W, 648, resumo(d, hoje))


# ---------------------------------------------------------------- teste

def contraste(a, b):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted([lum(a), lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def teste():
    d = datetime.date
    cal = {"2026-10-16": 0, "2026-10-17": 3, "2026-10-18": 1, "2026-10-19": 0,
           "2026-10-20": 2, "2026-10-21": 5, "2026-10-22": 1, "2026-10-23": 0, "2026-10-24": 0}
    # Hoje sem contribuição ainda: a sequência vale até ontem.
    atual, maior = sequencias({**cal, "2026-10-23": 4}, d(2026, 10, 24))
    assert atual == (d(2026, 10, 20), d(2026, 10, 23), 4) and maior == atual, (atual, maior)
    # Ontem e hoje sem contribuição: sequência zerada; a maior continua.
    atual, maior = sequencias(cal, d(2026, 10, 24))
    assert atual[2] == 0 and maior == (d(2026, 10, 20), d(2026, 10, 22), 3), (atual, maior)
    # Hoje com contribuição conta, e dia futuro (fuso) é ignorado.
    atual, _ = sequencias({**cal, "2026-10-23": 1, "2026-10-24": 2, "2026-10-25": 9}, d(2026, 10, 24))
    assert atual == (d(2026, 10, 20), d(2026, 10, 24), 5), atual
    assert numero(1459) == "1.459" and periodo(d(2026, 10, 18), d(2026, 10, 30), d(2026, 10, 30)) == "18/10 – 30/10"
    assert periodo(d(2025, 10, 26), d(2026, 10, 30), d(2026, 10, 30)) == "26/10/2025 – 30/10"
    # Todo texto com contraste AA (4,5:1) contra as duas pontas do fundo do card.
    for tema, T in TEMAS.items():
        for tinta in ("tinta", "apoio", "suave", "ouro"):
            for fundo in T["caixa"]:
                assert contraste(T[tinta], fundo) >= 4.5, (tema, tinta, fundo, contraste(T[tinta], fundo))
    # Números grandes e sequências longas ainda cabem (Tela.texto falha se não couber).
    dados = {"total": 12345, "desde": d(2025, 10, 31), "commits": 12345, "prs": 1234, "repos": 123,
             "atual": (d(2026, 8, 1), d(2026, 10, 30), 91), "maior": (d(2025, 12, 1), d(2026, 10, 30), 334)}
    agora = datetime.datetime(2026, 10, 30, 12, 5, tzinfo=BRASILIA)
    for tema in TEMAS:
        for desenho in (painel, painel_celular):
            svg = desenho(tema, dados, d(2026, 10, 30), agora)
            assert "12.345" in svg and "None" not in svg and "prefers-reduced-motion" in svg and len(svg.encode()) < 120_000
            assert TEMAS[tema]["ouro"] in svg and svg.count('class="anel"') == 1
    # Faixas da chama e o que cada uma desenha.
    assert [nivel_da_chama(n) for n in (0, 1, 3, 4, 7, 8, 14, 15, 29, 30, 400)] == [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    T = TEMAS["escuro"]
    assert "tremula" not in chama(T, 0, 10, 40) and chama(T, 1, 10, 40).count('class="faisca"') == 0
    assert chama(T, 2, 10, 40).count('class="faisca"') == 2 and chama(T, 4, 10, 40).count('class="faisca"') == 3
    if NOITE:
        assert NOITE["brilho"] in chama(T, 4, 10, 40) and NOITE["cobalto"] in chama(T, 5, 10, 40)
        assert chama(T, 5, 10, 40).count('class="pisca"') == 5  # brilho e quatro estrelas
    print("ok")


def folha_de_chamas(tema):
    """Os seis níveis lado a lado, com a faixa de dias de cada um (prévia)."""
    t = Tela(tema)
    faixas = ["0 dias", "1 a 3", "4 a 7", "8 a 14", "15 a 29", "30 ou mais"]
    for i, (dias, faixa) in enumerate(zip((0, 2, 5, 10, 20, 40), faixas)):
        x = 34 + 60 + i * 120
        t.chama(dias, x, 96)
        t.texto(NIVEIS[nivel_da_chama(dias)], x, 128, 13, TITULO, "tinta", 110, centro=True, sobe=False)
        t.texto(faixa, x, 146, 12, TEXTO, "apoio", 110, centro=True, sobe=False)
    return t.svg(820, 176, "Os seis níveis da chama da sequência")


if __name__ == "__main__":
    if "--teste" in sys.argv:
        teste()
        sys.exit()
    if "--chamas" in sys.argv:
        pasta = sys.argv[sys.argv.index("--chamas") + 1]
        os.makedirs(pasta, exist_ok=True)
        for tema in TEMAS:
            with open(os.path.join(pasta, f"chamas-{tema}.svg"), "w", encoding="utf-8", newline="\n") as f:
                f.write(folha_de_chamas(tema))
        sys.exit()
    agora = datetime.datetime.now(BRASILIA)
    hoje = agora.date()
    dados = coleta(hoje)
    os.makedirs(sys.argv[1], exist_ok=True)
    for tema in TEMAS:
        for nome, desenho in (("painel", painel), ("painel-celular", painel_celular)):
            with open(os.path.join(sys.argv[1], f"{nome}-{tema}.svg"), "w", encoding="utf-8", newline="\n") as f:
                f.write(desenho(tema, dados, hoje, agora))
