"""Calendário 3D das contribuições (yoshi389111/github-profile-3d-contrib) nas cores do perfil.

Uso no workflow:
  python3 .github/scripts/calendario3d.py --config <settings.json>   antes da Action
  python3 .github/scripts/calendario3d.py <pasta>                     depois dela
Autoteste:  python3 .github/scripts/calendario3d.py --teste

A Action aceita as cores do calendário, do texto e do radar num JSON, que sai
aqui do brand/tokens.json: a rampa dourada nos dias, tinta, apoio e ouro no
resto. Só as fatias das linguagens vêm com as cores do GitHub; depois da Action,
cada linguagem ganha um tom da paleta, na ordem em que aparece.
"""

import json
import os
import re
import sys

from agora import RAIO, TEMAS, tokens

ARQUIVO = "calendario-3d-{}.svg"
COR = re.compile(r"#[0-9a-fA-F]{6}\b")
FUNDO = re.compile(r'<rect x="0" y="0" width="(\d+)" height="(\d+)" class="fill-bg"></rect>')
ESCALA = 1280 / 880  # o SVG tem 1280 de largura e aparece com cerca de 880 no README


def config():
    """Um gráfico por tema, cada um com as cores dele."""
    saida = []
    for tema, T in TEMAS.items():
        saida.append({
            "type": "normal",
            "fileName": ARQUIVO.format(tema),
            "backgroundColor": T["caixa"][0],
            "foregroundColor": T["tinta"],
            "strongColor": T["ouro"],
            "weakColor": T["apoio"],
            "radarColor": T["ouro_forma"],
            "growingAnimation": True,
            # O dia vazio é o azulejo do card, como no calendário do recolore.py.
            "contribColors": [T["azulejo"], *T["calendario"][1:]],
        })
    return saida


def serie(T):
    """A mesma sequência de tons das linguagens do recolore.py."""
    rampa = T["calendario"]
    return [T["ouro"], rampa[3], rampa[2], T["tinta"], T["apoio"], T["suave"]]


def veste(svg, tema):
    """Troca as cores das linguagens (as únicas que não vêm da config) pela série do
    tema, põe a fonte do sistema e dá ao fundo o raio e o contorno dos outros cards."""
    T = TEMAS[tema]
    svg = svg.replace('"Ubuntu", "Helvetica", "Arial", sans-serif', tokens()["fonte"]["sistema"])
    r, borda = round(RAIO * ESCALA), round(ESCALA, 1)
    svg = FUNDO.sub(lambda m: f'<rect x="{borda / 2}" y="{borda / 2}" width="{int(m.group(1)) - borda}" height="{int(m.group(2)) - borda}"'
                    f' rx="{r}" class="fill-bg" stroke="{T["contorno"]}" stroke-width="{borda}"></rect>', svg, count=1)
    conhecidas = {c.lower() for c in (T["caixa"][0], T["tinta"], T["ouro"], T["apoio"], T["ouro_forma"], T["contorno"], T["azulejo"],
                                       *T["calendario"])}
    estranhas = [c for c in dict.fromkeys(m.lower() for m in COR.findall(svg)) if c not in conhecidas]
    tons = serie(T)
    mapa = {c: tons[i % len(tons)] for i, c in enumerate(estranhas)}
    return COR.sub(lambda m: mapa.get(m.group(0).lower(), m.group(0)), svg)


def teste():
    cfg = config()
    assert [c["fileName"] for c in cfg] == ["calendario-3d-claro.svg", "calendario-3d-escuro.svg"]
    assert all(len(c["contribColors"]) == 5 for c in cfg)
    T = TEMAS["claro"]
    svg = ('<style>* { font-family: "Ubuntu", "Helvetica", "Arial", sans-serif; }</style>'
           '<rect x="0" y="0" width="1280" height="850" class="fill-bg"></rect>'
           f'<rect fill="{T["calendario"][2]}"/><path fill="#3178c6"/><path fill="#00b4ab"/><path fill="#3178C6"/>')
    out = veste(svg, "claro")
    assert T["calendario"][2] in out and "#3178c6" not in out.lower() and "#00b4ab" not in out
    assert "Ubuntu" not in out and f'rx="{round(RAIO * ESCALA)}"' in out and T["contorno"] in out
    assert out.count(serie(T)[0]) == 2  # a mesma linguagem fica com o mesmo tom
    print("calendario3d: ok")


if __name__ == "__main__":
    if sys.argv[1] == "--teste":
        teste()
    elif sys.argv[1] == "--config":
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            json.dump(config(), f, indent=2)
    else:
        for tema in TEMAS:
            caminho = os.path.join(sys.argv[1], ARQUIVO.format(tema))
            with open(caminho, encoding="utf-8") as f:
                svg = f.read()
            with open(caminho, "w", encoding="utf-8", newline="\n") as f:
                f.write(veste(svg, tema))
