"""Cards da seção Agora · Now do README: um SVG por item.

O GitHub não carrega fontes em imagens, então o texto vira contorno da Mona
Sans, lido do glifos.json. Ele é gerado uma vez a partir da fonte, com o
fontTools e o brotli (o workflow não precisa deles):
    python3 .github/scripts/agora.py --glifos mona-sans-latin-standard-normal.woff2 LICENSE
"""

import json
import os
import sys

GLIFOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glifos.json")
PESOS = (450, 620)  # apoio e título, como no banner
# ASCII, Latin-1 e a pontuação tipográfica: cobre português e inglês.
LETRAS = "".join(map(chr, [*range(0x20, 0x7F), *range(0xA0, 0x100)])) + "–—‘’“”…•"


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


if __name__ == "__main__":
    if sys.argv[1:2] == ["--glifos"]:
        gera_glifos(*sys.argv[2:4])
