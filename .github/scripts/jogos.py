"""Veste os jogos do Cantinho descontraído com a identidade do perfil.

Uso no workflow:  python3 .github/scripts/jogos.py <pasta com as saídas brutas> <pasta de saída>
Autoteste:        python3 .github/scripts/jogos.py --teste

Os geradores (Platane/snk, abozanona/pacman-contribution-graph, que também faz
o Galaga, o Bomberman, o Campo Minado e o Puzzle Bobble, cyprieng/github-breakout
e JuhaP2/contribution-tetris) desenham com as cores do GitHub. Aqui cada cor
vira um token do brand/tokens.json:
- os dias do gráfico (verde, Halloween ou inverno, claro ou escuro) viram a
  rampa dourada do perfil, nível por nível;
- as peças, a raquete, as bolhas, os números e os textos viram tons da paleta;
- os bonecos em PNG ganham um filtro que os pinta num tom só da paleta.
Os SVGs do abozanona também emagrecem: números com casas demais são
arredondados e as imagens repetidas viram uma só, reusada com <use>.
O jogo em si (movimentos, placar, tempo) não muda. Grava <jogo>-{claro,escuro}.svg.
"""

import os
import re
import shutil
import sys

from agora import TEMAS
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
ABOZANONA = ("pacman", "galaga", "bomberman", "minesweeper", "puzzle-bobble")


def paleta_do_jogo(T):
    """Tons para peças e detalhes: dourados e os azuis da Noite Estrelada."""
    r = T["calendario"]
    return [T["ouro_forma"], NOITE["cobalto"], NOITE["brilho"], NOITE["estrela"], r[3], T["apoio"], NOITE["ultramar"]]


def mapa_do_jogo(jogo, tema):
    T = TEMAS[tema]
    claro = tema == "claro"
    # O Galaga é no espaço: fundo e rampa do tema escuro também na versão clara.
    r, p = TEMAS["escuro" if jogo == "galaga" else tema]["calendario"], paleta_do_jogo(T)
    mapa = {cor: r[i] for linha in NIVEIS_GITHUB for i, cor in enumerate(linha) if cor}
    mapa.update({"#57606a": T["apoio"], "#8b949e": T["apoio"]})  # nomes dos meses
    if jogo == "pacman":  # paredes do labirinto (pretas no claro, brancas no escuro)
        mapa["#000000" if claro else "#ffffff"] = T["tinta"]
    elif jogo == "galaga":  # céu e nomes dos meses
        E = TEMAS["escuro"]
        mapa.update({"#000000": E["fundo"], "#aaaaaa": E["apoio"]})
    elif jogo == "minesweeper":
        numeros = ["#1f4acc", "#1b7f37", "#b01e1e", "#5b2ca3", "#7d1a1a", "#00838f", "#111111"]
        tons = ([NOITE["cobalto"], T["ouro"], NOITE["ultramar"], T["apoio"], T["tinta"], NOITE["cobalto"], T["tinta"]] if claro
                else [NOITE["brilho"], T["ouro_forma"], NOITE["estrela"], T["apoio"], T["tinta"], NOITE["brilho"], T["tinta"]])
        mapa.update(zip(numeros, tons))
        mapa.update({"#d7dde5" if claro else "#2b3642": T["contorno"],  # casa aberta
                     "#000000" if claro else "#ffffff": T["tinta"],    # bordas das casas e mastro da bandeira
                     "#495057": T["apoio"], "#202124": T["tinta"],     # zeros e minas
                     "#d94841": T["ouro_forma"], "#f28b82": r[2]})     # bandeira e mina que explodiu
    elif jogo == "puzzle-bobble":  # bolhas e lançador
        bolhas = [NOITE["cobalto"], T["ouro_forma"], T["ouro"]] if claro else [NOITE["brilho"], T["ouro_forma"], NOITE["cobalto"]]
        mapa.update(zip(["#2ecc71", "#f1c40f", "#e74c3c"], bolhas))
        mapa["#cccccc"] = T["apoio"]
    elif jogo == "breakout":  # raquete e bola
        mapa["#1f6feb"] = T["ouro"]
    elif jogo == "tetris":
        pecas = (["#2f62d6", "#e8b33a", "#e8832a", "#7b4fe0", "#1fb8d6", "#18b886", "#e8455f"] if claro
                 else ["#3f7cf5", "#ffd166", "#ff9f43", "#9b6cff", "#3fe0f5", "#2ee6a6", "#ff5c7a"])
        mapa.update({cor: p[i % len(p)] for i, cor in enumerate(pecas)})
        (c1, c2), a = T["caixa"], T["azulejo"]
        if claro:  # painel, tabuleiro, textos e título
            mapa.update({"#f4f9ff": c2, "#e3eef9": c1, "#d3e3f3": a, "#0b1e3a": T["tinta"], "#355a80": T["apoio"], "#1f6fa8": T["ouro"]})
        else:
            mapa.update({"#071428": c2, "#0b1e3a": c1, "#10284a": a, "#eaf6ff": T["tinta"], "#a9c7e8": T["apoio"]})
    return mapa


def bonecos(jogo, tema):
    """[(seletor CSS, cor, ganho)] para os bonecos em PNG de cada jogo. O ganho
    clareia sprites escuros (a nave do Galaga é vermelha e azul)."""
    T = TEMAS[tema]
    azul = NOITE["brilho" if tema == "escuro" else "cobalto"]
    return {
        "pacman": [("image", azul, 1)],                                  # fantasmas
        "galaga": [("image", T["ouro_forma"], 2.2)],                     # nave e tiros
        "bomberman": [("image", azul, 1), (".heroi", T["ouro_forma"], 1.6)],  # bombas e itens; jogador
    }.get(jogo, [])


def tinge(svg, regras):
    """Um filtro por cor deixa cada boneco num tom só, guardando a claridade de cada
    pixel (os olhos continuam visíveis)."""
    luz = (0.2126, 0.7152, 0.0722)
    filtros, estilo = "", ""
    for i, (seletor, cor, ganho) in enumerate(regras):
        r, g, b = (int(cor[j:j + 2], 16) / 255 for j in (1, 3, 5))
        linhas = [" ".join(f"{k * l * ganho:.4f}" for l in luz) + " 0 0" for k in (r, g, b)] + ["0 0 0 1 0"]
        filtros += (f'<filter id="tinta{i}" color-interpolation-filters="sRGB">'
                    f'<feColorMatrix type="matrix" values="{" ".join(linhas)}"/></filter>')
        estilo += f"{seletor}{{filter:url(#tinta{i})}}"
    fim = svg.rindex("</svg>")
    return svg[:fim] + filtros + f"<style>{estilo}</style>" + svg[fim:]


ANIMACAO = re.compile(r'<animate(?:Transform|Motion)?\b[^>]*>')


def poda(tag):
    """Num quadro-chave cercado por dois iguais a ele, nada muda (nem em
    interpolação linear, nem em discreta): sai o quadro e o seu tempo."""
    if "keySplines" in tag:
        return tag
    v, t = re.search(r'\svalues="([^"]*)"', tag), re.search(r'\skeyTimes="([^"]*)"', tag)
    if not (v and t):
        return tag
    valores, tempos = v.group(1).split(";"), t.group(1).split(";")
    if len(valores) != len(tempos) or len(valores) < 3:
        return tag
    fica = [i for i in range(len(valores))
            if i in (0, len(valores) - 1) or not (valores[i - 1].strip() == valores[i].strip() == valores[i + 1].strip())]
    if len(fica) == len(valores):
        return tag
    tag = tag.replace(v.group(0), f' values="{";".join(valores[i] for i in fica)}"', 1)
    return tag.replace(t.group(0), f' keyTimes="{";".join(tempos[i] for i in fica)}"', 1)


ESCONDIDO = re.compile(r'<(g|text)\b[^>]*\sopacity="0"[^>]*>(?:(?!<g\b|</g>|<text\b|</text>).)*</\1>', re.S)


def invisiveis(svg):
    """Tira o que nunca aparece: grupos e textos com opacidade 0 cuja animação de
    opacidade (se houver) fica em 0 o tempo todo, como as minas e bandeiras de
    casas que o Campo Minado nunca abre."""
    def tira(m):
        bloco = m.group(0)
        if "<set" in bloco:
            return bloco
        for tag in ANIMACAO.findall(bloco):
            if 'attributeName="opacity"' not in tag:
                continue
            v = re.search(r'\svalues="([^"]*)"', tag)
            if not v or any(float(x) for x in v.group(1).split(";")):
                return bloco  # aparece em algum momento (ou anima de um jeito que não sei ler)
        return ""
    return ESCONDIDO.sub(tira, svg)


IMAGEM = re.compile(r"<image\b([^>]*?)(/?)>|</image>")
GEOMETRIA = re.compile(r'\s(x|y|width|height|href|preserveAspectRatio)="([^"]*)"')


def enxuga(svg):
    """Menos bytes, o mesmo desenho: números com no máximo 3 casas, sem ".0" à toa,
    e cada imagem repetida guardada uma vez só nos <defs>."""
    svg = re.sub(r"\d+\.\d{4,}", lambda m: f"{float(m.group(0)):.3f}".rstrip("0").rstrip("."), svg)
    svg = re.sub(r"(?<![\d.])(\d+)\.0(?![\d])", r"\1", svg)
    svg = ANIMACAO.sub(lambda m: poda(m.group(0)), svg)
    svg = invisiveis(svg)
    if "xml:space" not in svg:  # o SVG já junta os espaços em branco ao desenhar
        svg = re.sub(r"\s+", " ", re.sub(r">\s+<", "><", svg))
    repetidas = {h for h in re.findall(r'href="(data:[^"]+)"', svg) if svg.count(h) > 1}
    if not repetidas:
        return svg
    defs, ids, abertas = [], {}, []  # abertas: se cada <image> aberta virou <use>

    def troca(m):
        if m.group(0) == "</image>":
            return "</use>" if abertas.pop() else m.group(0)
        geo = dict(GEOMETRIA.findall(m.group(1)))
        vira = geo.get("href") in repetidas
        if not m.group(2):
            abertas.append(vira)
        if not vira:
            return m.group(0)
        chave = tuple(sorted(geo.items()))
        if chave not in ids:
            ids[chave] = f"img{len(ids)}"
            defs.append(f'<image id="{ids[chave]}"' + "".join(f' {k}="{v}"' for k, v in chave) + "/>")
        return f'<use href="#{ids[chave]}"{GEOMETRIA.sub("", m.group(1))}{m.group(2)}>'

    svg = IMAGEM.sub(troca, svg)
    corpo = svg.index(">", svg.index("<svg")) + 1
    return svg[:corpo] + f"<defs>{''.join(defs)}</defs>" + svg[corpo:]


def veste(svg, jogo, tema):
    T = TEMAS[tema]
    mapa = mapa_do_jogo(jogo, tema)
    svg = HEX.sub(lambda m: mapa.get(m.group(0).lower(), m.group(0)), svg)
    if jogo == "pacman":  # amarelo e pisca em vermelho, também nas animações (values="yellow;red;...")
        svg = re.sub(r"\byellow\b", T["ouro_forma"], svg)
        svg = re.sub(r"\bred\b", T["ouro"], svg)
    elif jogo == "galaga":  # estrelas do céu
        svg = svg.replace('"white"', f'"{NOITE["brilho"]}"')
    elif jogo == "bomberman":  # o jogador ganha uma classe: dentro de <use> o navegador não vê o <symbol>
        svg = re.sub(r'(<symbol id="bm-player[^"]*"[^>]*>\s*<image)\b', r'\1 class="heroi"', svg)
    if jogo in ABOZANONA:
        svg = enxuga(svg)
    regras = bonecos(jogo, tema)
    return tinge(svg, regras) if regras else svg


ENTRADAS = {  # jogo: (arquivo claro, arquivo escuro) na pasta bruta
    "cobrinha": ("cobrinha-claro.svg", "cobrinha-escuro.svg"),
    **{j: (f"dist/{j}-contribution-graph.svg", f"dist/{j}-contribution-graph-dark.svg") for j in ABOZANONA},
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
    assert 'id="tinta0"' in pac and "yellow" not in pac
    assert "red" not in veste('<svg><animate values="yellow;red"/></svg>', "pacman", "escuro").split("<filter")[0]
    # Galaga: céu do tema escuro também na versão clara; jogador do Bomberman num tom e o resto em outro.
    assert f'fill="{T["fundo"]}"' in veste('<svg><rect fill="#000000"/></svg>', "galaga", "claro")
    bm = veste('<svg><symbol id="bm-player-1-down-0"><image href="x"/></symbol><symbol id="bm-bomb"><image href="y"/></symbol></svg>',
               "bomberman", "claro")
    assert bm.count("<filter") == 2 and bm.count('class="heroi"') == 1
    mina = veste('<svg><text fill="#1f4acc"/><circle fill="#202124"/></svg>', "minesweeper", "escuro")
    assert NOITE["brilho"] in mina and T["tinta"] in mina
    # Enxuga: arredonda, tira ".0" e guarda a imagem repetida uma vez só.
    img = '<image x="-5" y="-13" width="10" height="13" href="data:image/png;base64,AAAA" opacity="0">'
    svg = f'<svg><g><animate values="1.0 2.0;479.6666666666667 3"/>{img}<animate/></image>{img}</image><image href="data:x"/></g></svg>'
    menor = enxuga(svg)
    assert '"1 2;479.667 3"' in menor and menor.count("base64,AAAA") == 1
    assert menor.count('<use href="#img0" opacity="0">') == 2 and menor.count("</use>") == 2
    assert "</image>" not in menor and '<image href="data:x"/>' in menor
    # Poda: os quadros do meio de uma sequência igual saem; os das pontas ficam.
    assert poda('<animate values="a;a;a;a;b;b" keyTimes="0;.2;.4;.6;.8;1"/>') == '<animate values="a;a;b;b" keyTimes="0;.6;.8;1"/>'
    curva = '<animate values="a;a;a" keyTimes="0;.5;1" keySplines="x"/>'
    assert poda(curva) == curva
    # Invisíveis: sai o que fica em opacidade 0 para sempre; o que aparece um dia fica.
    nunca = '<g opacity="0"><animate attributeName="opacity" values="0;0"/><line/></g>'
    um_dia = '<g opacity="0"><animate attributeName="opacity" values="0;1"/><line/></g>'
    texto = '<text opacity="0">0<animate attributeName="opacity" values="0;0"/></text>'
    assert invisiveis(f"<g>{nunca}{um_dia}{texto}</g>") == f"<g>{um_dia}</g>"
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
