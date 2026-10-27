"""Cards da seção Agora · Now do README: um SVG por item.

Cada item do campo agora do estudos.yml (o mesmo da issue do painel, uma linha
"português | inglês") vira um card:
- o emoji do começo escolhe o ícone (💼 maleta, 🐾 pata, 📘 livro; outro: faísca);
- o texto até a 1ª vírgula é o título, e o resto, a descrição;
- a 1ª palavra escolhe o selo: Estudando → ESTUDANDO · STUDYING,
  Construindo → EM CONSTRUÇÃO · BUILDING, qualquer outra → AGORA · NOW.

O GitHub não carrega fontes em imagens, então o texto vira contorno da Mona
Sans, lido do glifos.json. Ele é gerado uma vez a partir da fonte, com o
fontTools e o brotli (o workflow não precisa deles):
    python3 .github/scripts/agora.py --glifos mona-sans-latin-standard-normal.woff2 LICENSE
Autoteste:
    python3 .github/scripts/agora.py --teste
"""

import json
import os
import re
import sys
from html import escape
from xml.etree import ElementTree

GLIFOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glifos.json")
PESOS = (450, 620)  # apoio e título, como no banner
# ASCII, Latin-1 e a pontuação tipográfica: cobre português e inglês.
LETRAS = "".join(map(chr, [*range(0x20, 0x7F), *range(0xA0, 0x100)])) + "–—‘’“”…•"

# 3 cards de 264px cabem lado a lado na coluna do README no desktop (~820px);
# no celular cada um fica numa linha, em tamanho natural.
LARGURA, MARGEM, RESPIRO = 264, 6, 16
TEXTO = LARGURA - 2 * (MARGEM + RESPIRO)

# Tokens do linkedin-banner/DESIGN.md.
TEMAS = {
    "escuro": {
        "caixa": ("#0f1a30", "#0b1324"), "contorno": "#22314f", "sombra": ("#000000", 0.45),
        "azulejo": "#122039", "tinta": "#f3efe6", "apoio": "#aab5c7", "suave": "#8a96ab", "ouro": "#e8b84a",
    },
}

# Ícones do Lucide (licença ISC), em traço, numa caixa de 24.
ICONES = {
    "maleta": '<path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/><rect width="20" height="14" x="2" y="6" rx="2"/>',
    "pata": ('<circle cx="11" cy="4" r="2"/><circle cx="18" cy="8" r="2"/><circle cx="20" cy="16" r="2"/>'
             '<path d="M9 10a5 5 0 0 1 5 5v3.5a3.5 3.5 0 0 1-6.84 1.045Q6.52 17.48 4.46 16.84A3.5 3.5 0 0 1 5.5 10Z"/>'),
    "livro": ('<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5'
              'a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>'),
    "faisca": ('<path d="M9.94 15.5A2 2 0 0 0 8.5 14.06l-6.14-1.58a.5.5 0 0 1 0-.96L8.5 9.94A2 2 0 0 0 9.94 8.5'
               'l1.58-6.14a.5.5 0 0 1 .96 0L14.06 8.5A2 2 0 0 0 15.5 9.94l6.14 1.58a.5.5 0 0 1 0 .96L15.5 14.06'
               'a2 2 0 0 0-1.44 1.44l-1.58 6.14a.5.5 0 0 1-.96 0z"/>'),
}
EMOJIS = {"💼": "maleta", "🐾": "pata", **dict.fromkeys("📘📗📕📙📚📖📓📒", "livro")}

SELOS = {"estudando": ("ESTUDANDO", "STUDYING"), "construindo": ("EM CONSTRUÇÃO", "BUILDING"),
         "agora": ("AGORA", "NOW")}
VERBOS = {"estudando": "estudando", "aprendendo": "estudando", "cursando": "estudando",
          "construindo": "construindo", "criando": "construindo", "desenvolvendo": "construindo"}

LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


# ---------------------------------------------------------------- texto do item

def limpa(md):
    """Markdown do item em texto puro: sem link, negrito nem crase."""
    return re.sub(r"\*\*|__|`", "", LINK.sub(r"\1", md)).strip()


def divide(t):
    """(título, descrição): corta na 1ª vírgula fora de parênteses."""
    nivel = 0
    for i, c in enumerate(t):
        nivel += (c in "([") - (c in ")]")
        if c == "," and not nivel:
            resto = t[i + 1:].strip()
            return t[:i].strip(), resto[:1].upper() + resto[1:]
    return t, ""


def card(item):
    """Os dados do card a partir de {"pt": ..., "en": ...}."""
    pt, en = item.get("pt") or "", item.get("en") or ""
    emoji, _, resto = pt.partition(" ")
    if re.search(r"\w", emoji):  # não começa com emoji
        emoji, resto = "", pt
    titulo, descricao = divide(limpa(resto))
    title, description = divide(limpa(en))
    return {
        "icone": EMOJIS.get(emoji.replace("️", ""), "faisca"),
        "titulo": (titulo, title), "descricao": (descricao, description),
        "selo": SELOS[VERBOS.get(titulo.split(" ", 1)[0].lower(), "agora")],
    }


# ---------------------------------------------------------------- contornos

_glifos = None


def glifos():
    global _glifos
    if _glifos is None:
        with open(GLIFOS, encoding="utf-8") as f:
            _glifos = json.load(f)
    return _glifos


def glifo(c, peso):
    tabela = glifos()["pesos"][str(peso)]
    if c not in tabela:
        raise SystemExit(f"O card não sabe desenhar o caractere {c!r}: troque-o no item do Agora")
    return tabela[c]


def mede(t, tam, peso, espaco=0):
    """Largura em px, com o avanço real de cada letra (sem kerning)."""
    return sum(glifo(c, peso)[0] for c in t) * tam / glifos()["upem"] + espaco * tam * max(len(t) - 1, 0)


def quebra(t, tam, peso, largura=TEXTO):
    """Linhas de até `largura` px, quebrando nos espaços."""
    linhas, atual = [], ""
    for palavra in t.split():
        tentativa = f"{atual} {palavra}".strip()
        if atual and mede(tentativa, tam, peso) > largura:
            linhas.append(atual)
            atual = palavra
        else:
            atual = tentativa
    return [*linhas, atual] if atual else linhas


def escreve(t, x, y, tam, peso, cor, usados, espaco=0):
    """Texto em contornos: cada letra é um <use> do glifo, que vai uma vez só no <defs>."""
    upem = glifos()["upem"]
    k, cx, letras = tam / upem, 0, []
    for c in t:
        avanco, d = glifo(c, peso)
        if d:
            nome = f"g{peso}-{ord(c):x}"
            usados[nome] = d
            letras.append(f'<use href="#{nome}" x="{round(cx)}"/>')
        cx += avanco + espaco * upem
    return f'<g fill="{cor}" transform="translate({x:g} {y:g}) scale({k:g} {-k:g})">{"".join(letras)}</g>'


# ---------------------------------------------------------------- desenho

def linhas_do_card(c):
    """[(texto, tamanho, peso, tinta, altura da linha)] do título e da descrição."""
    (titulo, title), (descricao, description) = c["titulo"], c["descricao"]
    saida = [(t, 16, 620, "tinta", 21) for t in quebra(titulo, 16, 620)]
    saida += [(t, 13, 450, "apoio", 18) for t in quebra(title, 13, 450)]
    if descricao or description:
        saida.append(("", 0, 0, "", 10))
        saida += [(t, 13, 450, "apoio", 18) for t in quebra(descricao, 13, 450)]
        saida += [(t, 13, 450, "suave", 18) for t in quebra(description, 13, 450)]
    return saida


def altura(cards):
    """A mesma altura para todos: lado a lado, eles ficam alinhados."""
    corpo = max(sum(l[4] for l in linhas_do_card(c)) for c in cards)
    return MARGEM + RESPIRO + 40 + 16 + corpo + 18 + 26 + RESPIRO + MARGEM


def desenha(c, tema, alto):
    T = TEMAS[tema]
    usados = {}
    x0, y = MARGEM + RESPIRO, MARGEM + RESPIRO
    w, h = LARGURA - 2 * MARGEM, alto - 2 * MARGEM
    base = alto - MARGEM
    partes = [
        f'<rect x="{x0}" y="{y}" width="40" height="40" rx="10" fill="{T["azulejo"]}"/>',
        f'<g transform="translate({x0 + 9} {y + 9}) scale(.9167)" fill="none" stroke="{T["ouro"]}" stroke-width="2"'
        f' stroke-linecap="round" stroke-linejoin="round">{ICONES[c["icone"]]}</g>',
    ]
    y += 40 + 16
    for t, tam, peso, tinta, alt in linhas_do_card(c):
        if t:
            partes.append(escreve(t, x0, y + round(tam * 0.8, 2), tam, peso, T[tinta], usados))
        y += alt
    # Selo no pé do card: fica na mesma altura em todos.
    rotulo = " · ".join(c["selo"])
    sy = base - RESPIRO - 26
    sw = 25 + mede(rotulo, 11, 620, 0.06) + 12
    partes.append(
        f'<rect x="{x0}" y="{sy}" width="{sw:.1f}" height="26" rx="13" fill="{T["ouro"]}" fill-opacity=".1"'
        f' stroke="{T["ouro"]}" stroke-opacity=".4"/>'
        f'<circle cx="{x0 + 13}" cy="{sy + 13}" r="4" fill="{T["ouro"]}"/>'
        + escreve(rotulo, x0 + 25, sy + 17, 11, 620, T["ouro"], usados, 0.06)
    )
    (c1, c2), (sombra, opacidade) = T["caixa"], T["sombra"]
    alt = texto_alt(c)
    defs = "".join(f'<path id="{n}" d="{d}"/>' for n, d in usados.items())
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{LARGURA}" height="{alto}" viewBox="0 0 {LARGURA} {alto}"'
        f' role="img" aria-label="{escape(alt)}"><title>{escape(alt)}</title><defs>'
        f'<linearGradient id="caixa" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/>'
        f'<stop offset="1" stop-color="{c2}"/></linearGradient>'
        f'<filter id="sombra" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="0" dy="1.5"'
        f' stdDeviation="2.5" flood-color="{sombra}" flood-opacity="{opacidade}"/></filter>'
        f'{defs}</defs><rect x="{MARGEM}" y="{MARGEM}" width="{w}" height="{h}" rx="16" fill="url(#caixa)"'
        f' stroke="{T["contorno"]}" filter="url(#sombra)"/>{"".join(partes)}</svg>\n'
    )


def texto_alt(c):
    """Título, descrição e selo, em PT e EN, para o alt da imagem."""
    (titulo, title), (descricao, description), (pt, en) = c["titulo"], c["descricao"], c["selo"]
    lado = lambda t, d, s: t + (f": {d}" if d else "") + f" ({s.capitalize()})"
    return f"{lado(titulo, descricao, pt)} / {lado(title or titulo, description, en)}"


def cartoes(itens):
    """([dados de cada card], {(número, tema): svg}). Item sem português fica de fora."""
    cards = [card(i) for i in itens if (i.get("pt") or "").strip()]
    alto = round(altura(cards)) if cards else 0
    return cards, {(n, tema): desenha(c, tema, alto) for n, c in enumerate(cards, 1) for tema in TEMAS}


# ---------------------------------------------------------------- tabela de glifos

def gera_glifos(fonte, licenca):
    """{peso: {letra: [avanço, contorno]}} em unidades da fonte, com o aviso de
    copyright e o texto da licença (SIL OFL 1.1) junto, como a licença pede."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.ttLib import TTFont

    f = TTFont(fonte)
    cmap = f.getBestCmap()
    saida = {"fonte": f["name"].getDebugName(0), "licenca": open(licenca, encoding="utf-8").read(),
             "upem": f["head"].unitsPerEm, "pesos": {}}
    for peso in PESOS:
        conjunto = f.getGlyphSet(location={"wght": peso, "wdth": 100})
        tabela = saida["pesos"][str(peso)] = {}
        for c in LETRAS:
            nome = cmap.get(ord(c))
            if nome:
                caneta = SVGPathPen(conjunto, ntos=lambda v: str(round(v)))
                conjunto[nome].draw(caneta)
                tabela[c] = [round(conjunto[nome].width), caneta.getCommands()]
    with open(GLIFOS, "w", encoding="utf-8", newline="\n") as arq:
        json.dump(saida, arq, ensure_ascii=False, indent=0)
        arq.write("\n")


# ---------------------------------------------------------------- autoteste

def teste():
    item = {"pt": "💼 Construindo o **[Íris](https://x)**, site (Next.js, GSAP e WebGL) imersivo",
            "en": "Building **[Íris](https://x)**, an immersive site"}
    c = card(item)
    assert c["titulo"] == ("Construindo o Íris", "Building Íris"), c
    assert c["descricao"] == ("Site (Next.js, GSAP e WebGL) imersivo", "An immersive site"), c
    assert card({"pt": "Sem emoji, nem link"})["titulo"] == ("Sem emoji", "")
    assert c["icone"] == "maleta" and card({"pt": "📚 Lendo"})["icone"] == "livro"
    assert card({"pt": "🎓 Formando"})["icone"] == card({"pt": "Sem emoji"})["icone"] == "faisca"
    assert c["selo"] == ("EM CONSTRUÇÃO", "BUILDING")
    assert card({"pt": "📘 Estudando Dart"})["selo"] == ("ESTUDANDO", "STUDYING")
    assert card({"pt": "💼 Estagiário na ília"})["selo"] == ("AGORA", "NOW")
    assert mede("EM CONSTRUÇÃO · BUILDING", 11, 620, 0.06) + 37 <= TEXTO  # o selo mais longo cabe
    assert divide("Sem vírgula") == ("Sem vírgula", "")
    frase = "uma frase bem comprida que precisa quebrar em mais de uma linha dentro do card"
    linhas = quebra(frase, 13, 450)
    assert len(linhas) > 1 and " ".join(linhas) == frase
    assert all(mede(l, 13, 450) <= TEXTO for l in linhas)
    cards, svgs = cartoes([item, {"pt": "📘 Só PT"}, {"pt": "", "en": "Só EN"}])
    assert len(cards) == 2 and sorted(svgs) == [(n, t) for n in (1, 2) for t in TEMAS]
    assert len({re.search(r'height="(\d+)"', s).group(1) for s in svgs.values()}) == 1  # mesma altura
    for svg in svgs.values():
        raiz = ElementTree.fromstring(svg)
        ids = {e.get("id") for e in raiz.iter() if e.get("id")}
        assert all(u.get("href")[1:] in ids for u in raiz.iter("{http://www.w3.org/2000/svg}use"))
        assert "None" not in svg and len(svg.encode()) < 60_000
    assert ('aria-label="Construindo o Íris: Site (Next.js, GSAP e WebGL) imersivo (Em construção) /'
            ' Building Íris: An immersive site (Building)"') in svgs[(1, "escuro")]
    try:
        cartoes([{"pt": "Estudando 漢字"}])
    except SystemExit as erro:
        assert "漢" in str(erro)
    else:
        raise AssertionError("caractere fora da fonte deveria falhar")
    print("ok")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--glifos"]:
        gera_glifos(*sys.argv[2:4])
    elif "--teste" in sys.argv:
        teste()
