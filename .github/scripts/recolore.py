"""Veste os SVGs do lowlighter/metrics (linguagens e calendário) com a identidade do perfil.

Uso no workflow:  python3 .github/scripts/recolore.py <entrada.svg> <saída sem extensão>
Autoteste:        python3 .github/scripts/recolore.py --teste

Grava <saída>-claro.svg e <saída>-escuro.svg com as cores do brand/tokens.json:
- calendário: as cores dos dias (que o GitHub muda em datas especiais, como o
  Halloween) viram a rampa dourada do perfil, do dia vazio ao mais cheio;
- linguagens: cada linguagem, na ordem da barra, ganha um tom da paleta;
- títulos e ícones em dourado, texto em tinta e apoio;
- o mesmo quadro dos outros cards: caixa em degradê, contorno, sombra e raio.
Os números e o desenho do metrics não mudam; o texto dele é HTML, então segue
na fonte do sistema.
"""

import re
import sys

from agora import RAIO, TEMAS

PREENCHE = re.compile(r'fill="(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})"')
RAIZ = re.compile(r'<svg\b[^>]*\bwidth="(\d+)"[^>]*\bheight="(\d+)"[^>]*>')
FOLGA = 14  # respiro entre o quadro e o conteúdo do metrics


NIVEL = re.compile(r"--color-calendar(?:-\w+)?-graph-day-(?:L(\d)-)?bg:\s*(#[0-9a-fA-F]{3,6})")


def cores_do_calendario(svg, rampa, vazio):
    """{cor original: cor da rampa}. O próprio SVG declara o nível de cada cor do
    GitHub (dia vazio e L1 a L4, inclusive nas paletas de Halloween e de inverno),
    então cada cor vai para o mesmo nível da rampa dourada."""
    mapa = {}
    for nivel, cor in NIVEL.findall(svg):
        mapa[cor.lower()] = rampa[int(nivel)] if nivel else vazio
    return mapa


def cores_das_linguagens(svg, serie):
    """{cor da linguagem: tom da paleta}, na ordem em que aparecem na barra."""
    barra = re.findall(r'<rect[^>]*mask="url\(#languages-bar\)"[^>]*fill="(#[0-9a-fA-F]{3,6})"', svg)
    ordem = list(dict.fromkeys(barra))
    return {cor.lower(): serie[i % len(serie)] for i, cor in enumerate(ordem)}


def troca(svg, mapa):
    return PREENCHE.sub(lambda m: f'fill="{mapa.get(m.group(1).lower(), m.group(1))}"', svg)


def veste(svg, tema, tipo):
    T = TEMAS[tema]
    rampa = T["calendario"]
    serie = [T["ouro"], rampa[3], rampa[2], T["tinta"], T["apoio"], T["suave"]]
    # O dia vazio é o azulejo do card, para o plano do calendário assentar no fundo.
    mapa = cores_do_calendario(svg, rampa, T["azulejo"]) if tipo == "calendario" else cores_das_linguagens(svg, serie)
    corpo = troca(svg, mapa)
    raiz = RAIZ.search(corpo)
    largura, altura = int(raiz.group(1)), int(raiz.group(2))
    estilo = (f"<style>svg{{color:{T['tinta']} !important}}h2,h3{{color:{T['ouro']} !important}}"
              f".field svg{{fill:{T['ouro']} !important}}small{{color:{T['apoio']} !important}}</style>")
    fim = corpo.rindex("</svg>")
    corpo = corpo[:fim] + estilo + corpo[fim:]  # depois do CSS do metrics, para valer sobre ele
    m = 6  # margem para a sombra, como nos cards do Agora
    W, H = largura + 2 * (m + FOLGA), altura + 2 * (m + FOLGA)
    (c1, c2), (sombra, opacidade) = T["caixa"], T["sombra"]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><defs>'
        f'<linearGradient id="caixa-metrics" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/>'
        f'<stop offset="1" stop-color="{c2}"/></linearGradient>'
        f'<filter id="sombra-metrics" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="0" dy="1.5"'
        f' stdDeviation="2.5" flood-color="{sombra}" flood-opacity="{opacidade}"/></filter></defs>'
        f'<rect x="{m}" y="{m}" width="{W - 2 * m}" height="{H - 2 * m}" rx="{RAIO}" fill="url(#caixa-metrics)"'
        f' stroke="{T["contorno"]}" filter="url(#sombra-metrics)"/>'
        f'<svg x="{m + FOLGA}" y="{m + FOLGA}" width="{largura}" height="{altura}" overflow="visible">'
        f'{corpo[raiz.end():].rsplit("</svg>", 1)[0]}</svg></svg>\n'
    )


def teste():
    cal = ('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="330" class=""><style>h2{color:#0366d6}'
           ':root{--color-calendar-graph-day-bg:#ebedf0;--color-calendar-graph-day-L1-bg:#9be9a8;'
           '--color-calendar-halloween-graph-day-L1-bg:#ffee4a;--color-calendar-halloween-graph-day-L4-bg:#03001c;'
           '--color-calendar-winter-graph-day-L1-bg:#0a3069;--color-calendar-winter-graph-day-L4-bg:#b6e3ff}</style>'
           + '<path fill="#ebedf0"/>' * 9 + '<path fill="#03001c"/><path fill="#ffee4a"/><path fill="#0A3069"/>'
           '<path fill="#b6e3ff"/></svg>')
    for tema, T in TEMAS.items():
        saida = veste(cal, tema, "calendario")
        r = T["calendario"]
        assert saida.count(f'fill="{T["azulejo"]}"') == 9, saida  # dia vazio
        # Halloween e inverno: o nível vem do nome da variável, não da claridade.
        assert saida.count(f'fill="{r[1]}"') == 2 and saida.count(f'fill="{r[4]}"') == 2, saida
        assert "#03001c" not in saida.split("</style>")[-1] and "#b6e3ff" not in saida.split("</style>")[-1]
        assert saida.rindex(f"h2,h3{{color:{T['ouro']}") > saida.index("h2{color:#0366d6}")  # vale sobre o original
        assert f'stroke="{T["contorno"]}"' in saida
        assert saida.startswith('<svg xmlns="http://www.w3.org/2000/svg" width="520" height="370"')
    lang = ('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="146" class="">'
            '<rect mask="url(#languages-bar)" x="0" fill="#e34c26"/><rect mask="url(#languages-bar)" x="9" fill="#3178c6"/>'
            '<path fill="#e34c26"/><path fill="#3178c6"/></svg>')
    saida = veste(lang, "escuro", "linguagens")
    assert "#e34c26" not in saida and saida.count(f'fill="{TEMAS["escuro"]["ouro"]}"') == 2
    print("ok")


if __name__ == "__main__":
    if "--teste" in sys.argv:
        teste()
        sys.exit()
    entrada, saida = sys.argv[1:3]
    tipo = "calendario" if "isocalendar" in entrada else "linguagens"
    with open(entrada, encoding="utf-8") as f:
        original = f.read()
    for tema in TEMAS:
        with open(f"{saida}-{tema}.svg", "w", encoding="utf-8", newline="\n") as f:
            f.write(veste(original, tema, tipo))
