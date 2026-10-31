"""Veste os jogos do Cantinho descontraído com a identidade do perfil.

Uso no workflow:  python3 .github/scripts/jogos.py <pasta com as saídas brutas> <pasta de saída>
Autoteste:        python3 .github/scripts/jogos.py --teste

Os geradores (Platane/snk, abozanona/pacman-contribution-graph,
cyprieng/github-breakout e JuhaP2/contribution-tetris) desenham com as cores
do GitHub. Aqui cada cor vira um token do brand/tokens.json:
- os dias do gráfico (verde, Halloween ou inverno, claro ou escuro) viram a
  rampa dourada do perfil, nível por nível;
- as peças, a raquete e os textos de cada jogo viram tons da paleta.
O jogo em si (movimentos, placar, tempo) não muda. Grava <jogo>-{claro,escuro}.svg.
"""

import os
import re
import shutil
import sys

from agora import TEMAS, tokens
from estatisticas import NOITE

# As paletas do gráfico do GitHub, do dia vazio (0) ao mais cheio (4).
NIVEIS_GITHUB = [
    ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],  # claro
    ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],  # escuro
    ["#151b23", "#033a16", "#196c2e", "#2ea043", "#56d364"],  # escuro (2025)
    [None, "#ffee4a", "#ffc501", "#fe9600", "#03001c"],        # Halloween claro
    [None, "#631c03", "#bd561d", "#fa7a18", "#fddf68"],        # Halloween escuro
    [None, "#b6e3ff", "#54aeff", "#0969da", "#0a3069"],        # inverno claro
    [None, "#0a3069", "#0969da", "#54aeff", "#b6e3ff"],        # inverno escuro
]
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def paleta_do_jogo(T):
    """Tons para peças e detalhes: dourados e os azuis da Noite Estrelada."""
    r = T["calendario"]
    return [T["ouro_forma"], NOITE.get("cobalto", T["apoio"]), NOITE.get("brilho", T["suave"]),
            NOITE.get("estrela", r[2]), r[3], T["apoio"], NOITE.get("ultramar", T["tinta"])]


def mapa_do_jogo(jogo, tema):
    T = TEMAS[tema]
    r, p = T["calendario"], paleta_do_jogo(T)
    mapa = {cor: r[i] for linha in NIVEIS_GITHUB for i, cor in enumerate(linha) if cor}
    if jogo == "pacman":  # paredes do labirinto (pretas no claro, brancas no escuro) e nomes dos meses
        mapa.update({("#000000" if tema == "claro" else "#ffffff"): T["tinta"], "#57606a": T["apoio"], "#8b949e": T["apoio"]})
    elif jogo == "breakout":  # raquete e bola
        mapa["#1f6feb"] = T["ouro"]
    elif jogo == "tetris":
        pecas = (["#2f62d6", "#e8b33a", "#e8832a", "#7b4fe0", "#1fb8d6", "#18b886", "#e8455f"] if tema == "claro"
                 else ["#3f7cf5", "#ffd166", "#ff9f43", "#9b6cff", "#3fe0f5", "#2ee6a6", "#ff5c7a"])
        mapa.update({cor: p[i % len(p)] for i, cor in enumerate(pecas)})
        (c1, c2), a = T["caixa"], T["azulejo"]
        if tema == "claro":  # painel, tabuleiro, textos e título
            mapa.update({"#f4f9ff": c2, "#e3eef9": c1, "#d3e3f3": a, "#0b1e3a": T["tinta"], "#355a80": T["apoio"], "#1f6fa8": T["ouro"]})
        else:
            mapa.update({"#071428": c2, "#0b1e3a": c1, "#10284a": a, "#eaf6ff": T["tinta"], "#a9c7e8": T["apoio"]})
    return mapa


def fantasmas(svg, tema):
    """Os fantasmas do Pac-Man são PNG: um filtro os deixa num tom só da paleta,
    guardando a claridade de cada pixel (os olhos continuam visíveis)."""
    T = TEMAS[tema]
    cor = NOITE.get("brilho" if tema == "escuro" else "cobalto", T["ouro_forma"])
    r, g, b = (int(cor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    luz = (0.2126, 0.7152, 0.0722)
    linhas = [" ".join(f"{k * l:.4f}" for l in luz) + " 0 0" for k in (r, g, b)] + ["0 0 0 1 0"]
    filtro = (f'<filter id="fantasma" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="{" ".join(linhas)}"/></filter>'
              f'<style>image{{filter:url(#fantasma)}}</style>')
    # O Pac-Man é amarelo e pisca em vermelho, também nas animações (values="yellow;red;...").
    svg = re.sub(r"\byellow\b", T["ouro_forma"], svg)
    svg = re.sub(r"\bred\b", T["ouro"], svg)
    fim = svg.rindex("</svg>")
    return svg[:fim] + filtro + svg[fim:]


def veste(svg, jogo, tema):
    mapa = mapa_do_jogo(jogo, tema)
    svg = HEX.sub(lambda m: mapa.get(m.group(0).lower(), m.group(0)), svg)
    return fantasmas(svg, tema) if jogo == "pacman" else svg


ENTRADAS = {  # jogo: (arquivo claro, arquivo escuro) na pasta bruta
    "cobrinha": ("cobrinha-claro.svg", "cobrinha-escuro.svg"),
    "pacman": ("pacman-claro.svg", "pacman-escuro.svg"),
    "breakout": ("breakout/light.svg", "breakout/dark.svg"),
    "tetris": ("tetris/tetris-light.svg", "tetris/tetris-dark.svg"),
}


def teste():
    T = TEMAS["escuro"]
    # Halloween e verde caem no mesmo nível da rampa.
    assert veste('<rect fill="#FE9600"/><rect fill="#26a641"/>', "breakout", "escuro") == \
        f'<rect fill="{T["calendario"][3]}"/><rect fill="{T["calendario"][3]}"/>'
    assert T["ouro"] in veste('<rect fill="#1f6feb"/>', "breakout", "escuro")
    claro = veste('<rect fill="#2f62d6"/><text fill="#0b1e3a"/>', "tetris", "claro")
    assert "#2f62d6" not in claro and TEMAS["claro"]["tinta"] in claro
    pac = veste('<svg><g fill="#123456"/><path fill="yellow"/><rect fill="#ffffff"/></svg>', "pacman", "claro")
    assert '<g fill="#123456"/>' in pac and 'fill="#ffffff"' in pac  # cor desconhecida e fundo claro ficam
    assert 'id="fantasma"' in pac and "yellow" not in pac
    assert "red" not in veste('<svg><animate values="yellow;red"/></svg>', "pacman", "escuro").split("<filter")[0]
    print("ok")


if __name__ == "__main__":
    if "--teste" in sys.argv:
        teste()
        sys.exit()
    bruto, saida = sys.argv[1:3]
    os.makedirs(saida, exist_ok=True)
    for jogo, arquivos in ENTRADAS.items():
        for tema, nome in zip(("claro", "escuro"), arquivos):
            destino = os.path.join(saida, f"{jogo}-{tema}.svg")
            if jogo == "cobrinha":  # já sai nas cores do perfil (color_dots do snk)
                shutil.copy(os.path.join(bruto, nome), destino)
                continue
            with open(os.path.join(bruto, nome), encoding="utf-8") as f:
                svg = f.read()
            with open(destino, "w", encoding="utf-8", newline="\n") as f:
                f.write(veste(svg, jogo, tema))
            print(f"{destino}: {os.path.getsize(destino) // 1024} KB")
