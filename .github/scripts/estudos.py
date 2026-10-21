"""Reescreve o roadmap de estudos do README a partir do estudos.yml.

Uso no workflow:  yq -o=json estudos.yml | python3 .github/scripts/estudos.py
Autoteste local:  python3 .github/scripts/estudos.py --teste

Lê o estudos.yml já convertido em JSON pela entrada padrão (o yq vem
instalado nos runners do GitHub, então não precisa de pip) e troca só o
trecho entre os marcadores ESTUDOS:INICIO e ESTUDOS:FIM do README.md.
Campo vazio ou ausente simplesmente não aparece.
"""

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from html import escape
from xml.etree import ElementTree

INICIO = "<!-- ESTUDOS:INICIO -->"
FIM = "<!-- ESTUDOS:FIM -->"
AGORA_INICIO = "<!-- AGORA:INICIO -->"
AGORA_FIM = "<!-- AGORA:FIM -->"

# A ordem daqui é a ordem da legenda.
STATUS = {
    "estudando": "🟢 Estudando / Studying",
    "a_comecar": "⚪ A começar / Up next",
    "pausado": "⏸️ Pausado / Paused",
    "concluido": "✅ Concluído / Done",
}

# Imagens do roadmap: cada trilha vira um SVG desenhado aqui, em 4 versões
# (tema claro/escuro × largo/celular), trocadas pelo <picture> do README.
PASTA = "assets/estudos"
RAW = "https://raw.githubusercontent.com/IsaacGomes260653/IsaacGomes260653/main/"
# O GitHub não carrega fontes externas em imagens: pilha de fontes do sistema.
FONTE = '-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif'
MONO = 'ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace'
# Abaixo desta largura de tela a coluna do README fica estreita demais para a
# versão larga (o texto passaria a ter menos de 12px), e entra a de celular,
# que tem 280px: no celular a coluna do README tem ~260 a 300px, então ela
# aparece em tamanho natural ou quase.
QUEBRA = 1199

# Por status: (cor, borda do cartão, fundo do cartão, fundo do selo, texto do selo).
# Cores conferidas no validador de paleta (separação para daltonismo e
# contraste); o cinza do "a começar" é neutro de propósito. Cada status também
# tem um ícone próprio, para a cor nunca ser a única pista.
TEMAS = {
    "claro": {
        "caixa": ("#eef2ff", "#f5f3ff"), "contorno": "#c7d2fe", "sombra": ("#4f46e5", 0.14),
        "texto": "#1f2328", "suave": "#59636e", "trilho": "#d0d7de",
        "concluido": ("#1a7f37", "#1a7f37", "#f0fbf3", "#1a7f37", "#ffffff"),
        "estudando": ("#4f46e5", "#4f46e5", "#ffffff", "#4f46e5", "#ffffff"),
        "a_comecar": ("#6e7781", "#d0d7de", "#ffffff", "#6e7781", "#ffffff"),
        "pausado": ("#9a6700", "#9a6700", "#fffbea", "#9a6700", "#ffffff"),
    },
    "escuro": {
        "caixa": ("#151a33", "#1b1631"), "contorno": "#363b6e", "sombra": ("#000000", 0.45),
        "texto": "#e6edf3", "suave": "#9198a1", "trilho": "#30363d",
        "concluido": ("#3fb950", "#3fb950", "#12261b", "#3fb950", "#0d1117"),
        "estudando": ("#818cf8", "#818cf8", "#1e2142", "#818cf8", "#0d1117"),
        "a_comecar": ("#6e7681", "#30363d", "#161b22", "#484f58", "#e6edf3"),
        "pausado": ("#d29922", "#d29922", "#2b2311", "#d29922", "#0d1117"),
    },
}

# Só CSS, que o GitHub deixa rodar dentro de imagens: o brilho da etapa atual
# pulsa e as barras enchem uma vez. Sem animação para quem pede menos movimento.
CSS = (
    f"text{{font-family:{FONTE}}}.m{{font-family:{MONO}}}"
    ".pulso{animation:pulso 2.4s ease-in-out infinite alternate}"
    "@keyframes pulso{from{opacity:.2}to{opacity:.85}}"
    ".enche{transform-box:fill-box;transform-origin:0 50%;animation:enche 1.4s cubic-bezier(.2,.7,.2,1) .3s both}"
    "@keyframes enche{from{transform:scaleX(0)}}"
    "@media (prefers-reduced-motion:reduce){.pulso,.enche{animation:none}}"
)

# Rótulos curtos dos cartões: 4 cartões lado a lado só cabem na imagem com
# nomes curtos. O estudos.yml só tem o título completo, então os apelidos
# ficam aqui, pela chave do título em português. Se um título mudar ou entrar
# uma etapa nova, o cartão mostra o título completo em vez de um apelido velho.
CURTOS = {
    "Lógica e sintaxe em Dart": ("Lógica", "Logic"),
    "Programação orientada a objetos": ("POO", "OOP"),
    "Projeto prático": ("Projeto", "Project"),
    "Git e GitHub": ("Git", "Git"),
    "Métodos ágeis e ferramentas": ("Ágil", "Agile"),
    "Do código à loja de apps": ("Publicação", "Release"),
    "Linguagens de apoio": ("Java + Ruby", "Java + Ruby"),
}

ESTRELA = "⭐ Exigido no plano da empresa / Required by the company plan"


def texto(valor):
    """Texto limpo, ou "" se vazio, ausente ou ainda um marcador PREENCHER."""
    s = "" if valor is None else str(valor).strip()
    return "" if s.strip("[]").upper() == "PREENCHER" else s


def junta(par, sep):
    """{"pt": ..., "en": ...} vira "PT<sep>EN", sem lado vazio nem repetido."""
    par = par or {}
    return sep.join(dict.fromkeys(t for t in (texto(par.get("pt")), texto(par.get("en"))) if t))


def bilingue(par):
    """Português e, logo abaixo, inglês em itálico."""
    par = par or {}
    pt, en = texto(par.get("pt")), texto(par.get("en"))
    return "<br>\n".join(filter(None, [pt, en and f"<em>{en}</em>"]))


def nome(item):
    """Título de etapa ou nome de subtema: texto simples ou {"pt": ..., "en": ...}."""
    valor = item.get("titulo") or item.get("nome")
    return junta(valor, " · ") if isinstance(valor, dict) else texto(valor)


def status(item, padrao=""):
    s = texto(item.get("status")) or padrao
    if s and s not in STATUS:
        raise SystemExit(f"status inválido {s!r} em {nome(item)!r}. Use: {' | '.join(STATUS)}")
    return s


def folhas(subtemas):
    """Subtemas sem itens: são eles que têm status próprio e entram na contagem."""
    for s in subtemas or []:
        if s.get("itens"):
            yield from folhas(s["itens"])
        else:
            yield s


def status_sub(s):
    """Subtema sem status está a começar. Grupo não tem status: sai dos itens."""
    if not s.get("itens"):
        return status(s, "a_comecar")
    todos = {status_sub(f) for f in folhas(s["itens"])}
    if todos == {"concluido"}:
        return "concluido"
    for x in ("estudando", "pausado"):
        if x in todos:
            return x
    return "estudando" if "concluido" in todos else "a_comecar"


def conta(subtemas, so_estrela=False):
    fs = [f for f in folhas(subtemas) if f.get("estrela") or not so_estrela]
    return sum(status_sub(f) == "concluido" for f in fs), len(fs)


def icone(s):
    return STATUS[s].split()[0]


def link(item):
    """[nome](url), com o preço entre parênteses quando houver."""
    rotulo = nome(item)
    url, preco = texto(item.get("url")), texto(item.get("preco"))
    if rotulo and url:
        rotulo = f"[{rotulo}]({url})"
    else:
        rotulo = rotulo or (url and f"<{url}>")
    return rotulo and " ".join(filter(None, [rotulo, preco and f"({preco})"]))


def lista(subtemas, recuo=""):
    linhas = []
    for s in subtemas or []:
        rotulo = link(s)
        if not rotulo:
            continue
        codigo = texto(s.get("codigo"))  # onde está o código do estudo, se já tiver
        codigo = f" · [código / code]({codigo})" if codigo else ""
        if s.get("itens"):
            feitos, total = conta(s["itens"])
            linhas.append(f"{recuo}- {icone(status_sub(s))} **{rotulo}** · {feitos}/{total}{codigo}")
            linhas.append(lista(s["itens"], recuo + "  "))
        else:
            estrela = "⭐ " if s.get("estrela") else ""
            linhas.append(f"{recuo}- {icone(status_sub(s))} {estrela}{rotulo}{codigo}")
    return "\n".join(filter(None, linhas))


def progresso(e):
    feitos, total = conta(e.get("subtemas"))
    if not total:
        return ""
    cheio = round(10 * feitos / total)
    linha = f"**Progresso / Progress:** `{'█' * cheio}{'░' * (10 - cheio)}` {round(100 * feitos / total)}% · {feitos}/{total} ✅"
    feitos, total = conta(e.get("subtemas"), so_estrela=True)
    return linha + (f" · ⭐ {feitos}/{total}" if total else "")


def onde(links):
    itens = list(filter(None, map(link, links or [])))
    return f"**Onde / Where:** {' · '.join(itens)}" if itens else ""


def extras(lista_extras):
    linhas = []
    for x in lista_extras or []:
        nota = x.get("nota") or {}
        pt, en = texto(nota.get("pt")), texto(nota.get("en"))
        rotulo = link(x)
        if rotulo:
            nota = " · ".join(filter(None, [pt, en and f"<em>{en}</em>"]))
            linhas.append(f"- {rotulo}" + (f" — {nota}" if nota else ""))
    return "#### Extras\n\n" + "\n".join(linhas) if linhas else ""


def rotulo_curto(etapa):
    """(português, inglês) do cartão; o inglês some quando é igual."""
    titulo = etapa.get("titulo") or {}
    pt, en = CURTOS.get(texto(titulo.get("pt")), (titulo.get("pt"), titulo.get("en")))
    pt, en = texto(pt), texto(en)
    return pt, en if en != pt else ""


def mede(t, tam, mono=False):
    """Largura aproximada do texto. Folgada de propósito: a fonte do sistema
    muda de aparelho para aparelho, e no Linux ela costuma ser mais larga."""
    return len(t) * tam * (0.6 if mono else 0.56)


def simbolo(s, x, y, cor):
    """Ícone do status centrado em (x, y): a cor nunca é a única pista."""
    if s == "concluido":
        return (f'<path d="M{x - 4.5:g} {y:g}l3 3.2 6-6.6" fill="none" stroke="{cor}"'
                ' stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>')
    if s == "estudando":
        return (f'<circle cx="{x:g}" cy="{y:g}" r="7.5" fill="none" stroke="{cor}" stroke-opacity=".4"'
                f' stroke-width="1.5"/><circle cx="{x:g}" cy="{y:g}" r="4" fill="{cor}"/>')
    if s == "pausado":
        return "".join(f'<rect x="{x + dx:g}" y="{y - 5:g}" width="3.2" height="10" rx="1" fill="{cor}"/>'
                       for dx in (-4.5, 1.3))
    return f'<circle cx="{x:g}" cy="{y:g}" r="5.5" fill="none" stroke="{cor}" stroke-width="1.8"/>'


def dados_cartao(e):
    s = status(e, "a_comecar")
    feitos, total = conta(e.get("subtemas"))
    numero = texto(e.get("numero"))
    if numero:
        pt, en = rotulo_curto(e)
        linhas = [(pt, 15, "texto"), (en, 13, "suave")]
    else:  # cartão avulso (Outros estudos): o status vai escrito, em PT e EN
        st_pt, st_en = STATUS[s].split(" ", 1)[1].split(" / ")
        linhas = [(nome(e), 15, "texto"), (st_pt, 13, "suave"), (st_en, 13, "suave")]
    return {"numero": numero, "status": s, "feitos": feitos, "total": total,
            "linhas": [l for l in linhas if l[0]]}


def altura_cartao(c):
    return 14 + (34 if c["numero"] else 0) + sum(t + 6 for _, t, _ in c["linhas"]) + 34


def cartao(c, x, y, w, h, T):
    s = c["status"]
    cor, borda, fundo, selo, selo_txt = T[s]
    partes = []
    if s == "estudando":
        partes.append(f'<rect class="pulso" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="12" fill="none"'
                      f' stroke="{cor}" stroke-width="5" opacity=".6" filter="url(#brilho)"/>')
    partes.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="12" fill="{fundo}"'
                  f' stroke="{borda}" stroke-width="{2 if s == "estudando" else 1.2}"/>')
    a = 12 if w < 130 else 14   # respiro interno: menor no cartão estreito do celular
    direita, topo = x + w - a, y + a
    pct = f"{round(100 * c['feitos'] / c['total'])}%" if c["total"] and s == "estudando" else ""
    if c["numero"]:
        partes.append(f'<circle cx="{x + a + 12:g}" cy="{topo + 12:g}" r="12" fill="{selo}"/>'
                      f'<text class="m" x="{x + a + 12:g}" y="{topo + 16.5:g}" font-size="13" font-weight="700"'
                      f' text-anchor="middle" fill="{selo_txt}">{escape(c["numero"])}</text>')
        if pct:
            partes.append(f'<text class="m" x="{direita:g}" y="{topo + 16.5:g}" font-size="13" font-weight="700"'
                          f' text-anchor="end" fill="{T["texto"]}">{pct}</text>')
        partes.append(simbolo(s, direita - 7 - (mede(pct, 13, True) + 8 if pct else 0), topo + 12, cor))
        topo += 34
    for i, (t, tam, tinta) in enumerate(c["linhas"]):
        topo += tam + 2
        peso = ' font-weight="600"' if i == 0 else ""
        partes.append(f'<text x="{x + a:g}" y="{topo:g}" font-size="{tam}"{peso} fill="{T[tinta]}">{escape(t)}</text>')
        if i == 1 and not c["numero"]:  # no cartão avulso, o ícone fica ao lado do status
            partes.append(simbolo(s, direita - 7, topo - tam * 0.35, cor))
        topo += 4
    if c["total"]:  # barra e contador sempre no pé do cartão, alinhados entre si
        base, bw = y + h - 20, w - 2 * a - 46
        partes.append(f'<rect x="{x + a:g}" y="{base:g}" width="{bw:g}" height="6" rx="3" fill="{T["trilho"]}"/>')
        if c["feitos"]:
            partes.append(f'<rect class="enche" x="{x + a:g}" y="{base:g}" width="{bw * c["feitos"] / c["total"]:.1f}"'
                          f' height="6" rx="3" fill="{cor}"/>')
        partes.append(f'<text class="m" x="{direita:g}" y="{base + 6:g}" font-size="13" text-anchor="end"'
                      f' fill="{T["suave"]}">{c["feitos"]}/{c["total"]}</text>')
    return "".join(partes)


def legenda(x, y, largura, T):
    """Uma linha só quando cabe; senão, grade de 2 colunas com PT em cima e EN embaixo."""
    itens = [(s, *STATUS[s].split(" ", 1)[1].split(" / ")) for s in STATUS]
    larguras = [18 + mede(f"{pt} / {en}", 13) for _, pt, en in itens]
    partes = []
    if sum(larguras) + 20 * (len(itens) - 1) <= largura:
        for (s, pt, en), w in zip(itens, larguras):
            partes.append(simbolo(s, x + 6, y + 8, T[s][0]) +
                          f'<text x="{x + 18:g}" y="{y + 12.5:g}" font-size="13" fill="{T["texto"]}">'
                          f'{escape(pt)}<tspan fill="{T["suave"]}"> / {escape(en)}</tspan></text>')
            x += w + 20
        return "".join(partes), 18
    for i, (s, pt, en) in enumerate(itens):
        cx, cy = x + (i % 2) * largura / 2, y + (i // 2) * 38
        partes.append(simbolo(s, cx + 6, cy + 8, T[s][0]) +
                      f'<text x="{cx + 18:g}" y="{cy + 12.5:g}" font-size="13" fill="{T["texto"]}">{escape(pt)}</text>'
                      f'<text x="{cx + 18:g}" y="{cy + 29:g}" font-size="13" fill="{T["suave"]}">{escape(en)}</text>')
    return "".join(partes), 38 * ((len(itens) + 1) // 2) - 4


def desenha(titulo, cartoes, colunas, largura, tema, texto_alt, caminho):
    """Caixa com título, legenda (só no caminho) e cartões. No caminho, a ordem
    é em "S": a 2ª fileira volta da direita para a esquerda, e a linha que liga
    os cartões fica colorida até a etapa atual."""
    T = TEMAS[tema]
    m, p = (12, 20) if largura > 400 else (8, 12)   # m: folga para a sombra da caixa
    x0, y, iw = m + p, m + p, largura - 2 * (m + p)
    pt, en = titulo
    corpo = []
    if mede(f"{pt} · {en}", 18) * 1.05 <= iw:
        corpo.append(f'<text x="{x0}" y="{y + 18}" font-size="18" font-weight="700" fill="{T["texto"]}">{escape(pt)}'
                     f'<tspan font-weight="400" fill="{T["suave"]}"> · {escape(en)}</tspan></text>')
        y += 18
    else:
        corpo.append(f'<text x="{x0}" y="{y + 18}" font-size="18" font-weight="700" fill="{T["texto"]}">{escape(pt)}</text>'
                     f'<text x="{x0}" y="{y + 40}" font-size="15" fill="{T["suave"]}">{escape(en)}</text>')
        y += 40
    if caminho:
        trecho, alto = legenda(x0, y + 14, iw, T)
        corpo.append(trecho)
        y += 14 + alto
    y += 20
    gx, gy = (24 if colunas > 2 else 12), 22
    cw, ch = (iw - (colunas - 1) * gx) / colunas, max(map(altura_cartao, cartoes))
    pos = []
    for i in range(len(cartoes)):
        fileira, k = divmod(i, colunas)
        col = colunas - 1 - k if caminho and fileira % 2 else k
        pos.append((x0 + col * (cw + gx), y + fileira * (ch + gy)))
    if caminho and len(cartoes) > 1:
        centros = [f"{px + cw / 2:g},{py + ch / 2:g}" for px, py in pos]
        andamento = [i for i, c in enumerate(cartoes) if c["status"] == "estudando"]
        feitas = [i for i, c in enumerate(cartoes) if c["status"] == "concluido"]
        atual = (andamento or feitas[-1:] or [0])[0]
        linha = ('<polyline points="{}" fill="none" stroke="{}" stroke-width="3"'
                 ' stroke-linejoin="round" stroke-linecap="round"/>')
        corpo.append(linha.format(" ".join(centros), T["trilho"]))
        if atual:
            corpo.append(linha.format(" ".join(centros[:atual + 1]), T["estudando"][0]))
    corpo += [cartao(c, px, py, cw, ch, T) for c, (px, py) in zip(cartoes, pos)]
    fileiras = -(-len(cartoes) // colunas)
    altura = round(y + fileiras * ch + (fileiras - 1) * gy + p + m)
    (c1, c2), (sombra, opacidade) = T["caixa"], T["sombra"]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" viewBox="0 0 {largura} {altura}"'
        f' role="img" aria-label="{escape(texto_alt)}"><title>{escape(texto_alt)}</title><style>{CSS}</style><defs>'
        f'<linearGradient id="caixa" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/>'
        f'<stop offset="1" stop-color="{c2}"/></linearGradient>'
        f'<filter id="sombra" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="0" dy="2"'
        f' stdDeviation="5" flood-color="{sombra}" flood-opacity="{opacidade}"/></filter>'
        '<filter id="brilho" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5"/></filter>'
        f'</defs><rect x="{m}" y="{m}" width="{largura - 2 * m}" height="{altura - 2 * m}" rx="16" fill="url(#caixa)"'
        f' stroke="{T["contorno"]}" filter="url(#sombra)"/>{"".join(corpo)}</svg>\n'
    )


def resumo(trilha):
    """Texto alternativo: o status e a contagem de cada etapa, em PT e EN."""
    pt, en = [], []
    for e in trilha.get("etapas") or []:
        c = dados_cartao(e)
        numero = c["numero"]
        nome_pt, nome_en = rotulo_curto(e) if numero else (nome(e), "")
        st_pt, st_en = STATUS[c["status"]].split(" ", 1)[1].split(" / ")
        conta_pt = f", {c['feitos']} de {c['total']} subtemas" if c["total"] else ""
        conta_en = f", {c['feitos']} of {c['total']} subtopics" if c["total"] else ""
        pt.append(" ".join(filter(None, [numero, nome_pt])) + f": {st_pt.lower()}{conta_pt}")
        en.append(" ".join(filter(None, [numero, nome_en or nome_pt])) + f": {st_en.lower()}{conta_en}")
    titulo = junta(trilha.get("curto") or trilha.get("titulo"), " · ")
    return f"{titulo}. " + "; ".join(pt) + ". / " + "; ".join(en) + "."


def imagens(dados):
    """{caminho do arquivo: svg} de todas as trilhas, nas 4 versões."""
    saida = {}
    for trilha in dados.get("trilhas") or []:
        etapas = trilha.get("etapas") or []
        if not etapas:
            continue
        cartoes = list(map(dados_cartao, etapas))
        caminho = len(etapas) > 1 and all(c["numero"] for c in cartoes)
        par = trilha.get("curto") or trilha.get("titulo") or {}
        titulo = (texto(par.get("pt")), texto(par.get("en")))
        texto_alt = resumo(trilha)
        versoes = (("", 4 if caminho else 2, 800 if caminho else 520), ("-celular", 2, 280))
        for tema in TEMAS:
            for sufixo, colunas, largura in versoes:
                arquivo = f"{PASTA}/{texto(trilha.get('id')) or 'trilha'}{sufixo}-{tema}.svg"
                if arquivo in saida:
                    raise SystemExit(f"Duas trilhas gerariam {arquivo}: dê um id diferente a cada trilha")
                saida[arquivo] =desenha(titulo, cartoes, colunas, largura, tema, texto_alt, caminho)
    return saida


def figura(trilha, svgs):
    """<picture> com as 4 versões. O ?v= muda quando a imagem muda, para o
    cache do GitHub não mostrar uma versão velha."""
    base = f"{PASTA}/{texto(trilha.get('id')) or 'trilha'}"

    def url(sufixo):
        arquivo = f"{base}{sufixo}.svg"
        return f"{RAW}{arquivo}?v={hashlib.sha1(svgs[arquivo].encode()).hexdigest()[:8]}"

    return "\n".join([
        "<picture>",
        f'  <source media="(max-width: {QUEBRA}px) and (prefers-color-scheme: dark)" srcset="{url("-celular-escuro")}">',
        f'  <source media="(max-width: {QUEBRA}px)" srcset="{url("-celular-claro")}">',
        f'  <source media="(prefers-color-scheme: dark)" srcset="{url("-escuro")}">',
        f'  <img src="{url("-claro")}" alt="{escape(resumo(trilha))}">',
        "</picture>",
    ])


def etapa(e):
    s = status(e)
    numero = texto(e.get("numero"))
    titulo = " · ".join(filter(None, [numero, nome(e)]))
    rotulo = " — ".join(filter(None, [titulo and f"<b>{titulo}</b>", STATUS.get(s)]))
    feitos, total = conta(e.get("subtemas"))
    if total:
        rotulo += f" · {feitos}/{total} ✅"
    corpo = [b for b in (
        bilingue(e.get("conteudo")), bilingue(e.get("nota")),
        progresso(e), lista(e.get("subtemas")), onde(e.get("onde")),
    ) if b]
    if not numero and not total:  # etapa avulsa e sem subtemas: bloco simples
        return "\n\n".join(filter(None, [rotulo, *corpo]))
    abre = " open" if s == "estudando" else ""
    return "\n\n".join([f"<details{abre}>\n<summary>{rotulo}</summary>", *corpo, "</details>"])


def painel(dados, data, svgs):
    blocos = [" · ".join([*STATUS.values(), ESTRELA])]
    for trilha in dados.get("trilhas") or []:
        etapas = trilha.get("etapas") or []
        titulo = junta(trilha.get("titulo"), " · ")
        if titulo:
            blocos.append(f"#### {titulo}")
        if etapas:
            blocos.append(figura(trilha, svgs))
            if texto(dados.get("painel")) and trilha is dados["trilhas"][0]:
                blocos.append(f'<sub>✏️ <a href="{escape(dados["painel"])}">Atualizar progresso · Update progress</a></sub>')
        blocos += [b for b in map(etapa, etapas) if b]
    blocos += list(filter(None, [extras(dados.get("extras"))]))
    blocos.append(
        f"<sub>Atualizado em / Updated on {data:%d/%m/%Y} · gerado automaticamente a partir do"
        ' <a href="estudos.yml">estudos.yml</a> / auto-generated from <a href="estudos.yml">estudos.yml</a></sub>'
    )
    return "\n".join([
        INICIO,
        "<!-- Gerado a partir do estudos.yml pelo workflow painel-estudos.yml."
        " Não edite aqui: edite o estudos.yml. -->",
        "",
        "\n\n".join(blocos),
        FIM,
    ])


def hoje_brasilia():
    # O Brasil não tem horário de verão desde 2019: UTC-3 o ano todo.
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).date()


def vale(item, hoje):
    """O item do Agora aparece hoje? "ate" e "desde" são opcionais (AAAA-MM-DD)."""
    ate, desde = texto(item.get("ate")), texto(item.get("desde"))
    return (not ate or hoje <= datetime.date.fromisoformat(ate)) and (
        not desde or hoje >= datetime.date.fromisoformat(desde))


def agora(dados, hoje):
    """Seção Agora · Now: português e, logo abaixo, inglês em itálico."""
    itens = []
    for item in dados.get("agora") or []:
        pt, en = texto(item.get("pt")), texto(item.get("en"))
        if pt and vale(item, hoje):
            itens.append(f"- {pt}" + (f"<br>\n  <em>{en}</em>" if en else ""))
    return "\n".join([AGORA_INICIO, "<!-- Gerado a partir do estudos.yml (campo agora). -->", "", *itens, AGORA_FIM])


def substitui(readme, bloco, inicio=INICIO, fim=FIM):
    padrao = re.compile(re.escape(inicio) + r".*?" + re.escape(fim), re.S)
    if not padrao.search(readme):
        raise SystemExit(f"Marcadores {inicio} / {fim} não encontrados no README.md")
    return padrao.sub(lambda _: bloco, readme, count=1)


def data_do_estudos():
    # Mudança ainda não commitada (a issue do painel acabou de mexer no yml): é de hoje.
    if subprocess.run(["git", "diff", "--quiet", "--", "estudos.yml"]).returncode:
        return hoje_brasilia()
    saida = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", "estudos.yml"],
        capture_output=True, text=True,
    ).stdout.strip()
    return datetime.date.fromisoformat(saida) if saida else datetime.date.today()


def teste():
    dados = {"trilhas": [
        {"id": "t", "titulo": {"pt": "Trilha", "en": "Track"}, "etapas": [
            {"numero": 1, "titulo": {"pt": "Lógica e sintaxe em Dart", "en": "Dart logic and syntax"},
             "status": "estudando", "conteudo": {"pt": "Conteúdo", "en": "Content"},
             "onde": [{"nome": "DartPad", "url": "https://dartpad.dev"},
                      {"nome": "Curso", "url": "https://c", "preco": "US$ 99"}],
             "subtemas": [
                 {"nome": "Variables", "url": "https://v", "itens": [
                     {"nome": "Null safety", "status": "concluido", "estrela": True, "url": "https://v#n"},
                     {"nome": "Final and const", "status": "estudando", "estrela": True},
                 ]},
                 {"nome": {"pt": "Ramos", "en": "Branches"}},
                 {"nome": "Pronto", "codigo": "https://g", "itens": [
                     {"nome": "A", "status": "concluido", "codigo": "https://g/a"}]},
             ]},
            {"numero": 2, "titulo": {"pt": "Tópico novo", "en": "New topic"}, "status": "a_comecar",
             "conteudo": {"pt": "Só em português"}, "onde": []},
            {"numero": 3, "titulo": {"pt": "Sem status", "en": ""}, "progresso": 40, "proximo": "PREENCHER"},
        ]},
        {"id": "dados", "titulo": {"pt": "Dados", "en": "Data"}, "etapas": [
            {"titulo": {"pt": "Databricks", "en": "Databricks"}, "status": "pausado",
             "nota": {"pt": "Pausei.", "en": "Paused."}, "onde": []},
            {"titulo": {"pt": "AWS", "en": "AWS"}, "status": "a_comecar", "subtemas": [{"nome": "M1"}]},
        ]},
    ], "extras": [
        {"nome": "Udemy", "url": "https://u", "preco": "pago",
         "nota": {"pt": "Só em promoção", "en": "Only on sale"}},
    ]}
    svgs = imagens(dados)
    md = painel(dados, datetime.date(2026, 9, 24), svgs)
    assert md.splitlines()[3] == " · ".join([*STATUS.values(), ESTRELA])
    assert "#### Trilha · Track" in md and "#### Dados · Data" in md
    assert "mermaid" not in md and md.count("<picture>") == 2
    assert (f'<source media="(max-width: {QUEBRA}px) and (prefers-color-scheme: dark)"'
            f' srcset="{RAW}{PASTA}/t-celular-escuro.svg?v=') in md
    assert f'<img src="{RAW}{PASTA}/t-claro.svg?v=' in md
    assert 'alt="Trilha · Track. 1 Lógica: estudando, 2 de 4 subtemas; 2 Tópico novo: a começar;' in md
    assert "/ 1 Logic: studying, 2 of 4 subtopics;" in md
    assert sorted(svgs) == sorted(f"{PASTA}/{t}{v}-{tema}.svg" for t in ("t", "dados")
                                  for v in ("", "-celular") for tema in TEMAS)
    for arquivo, svg in svgs.items():
        ElementTree.fromstring(svg)                               # XML válido
        assert len(svg.encode()) < 40_000, arquivo
        assert min(map(float, re.findall(r'font-size="([\d.]+)"', svg))) >= 13, arquivo
        assert "prefers-reduced-motion" in svg and "None" not in svg, arquivo
    t, cel = svgs[f"{PASTA}/t-claro.svg"], svgs[f"{PASTA}/t-celular-claro.svg"]
    avulsa = svgs[f"{PASTA}/dados-claro.svg"]
    assert 'width="800"' in t and 'width="280"' in cel
    assert t.count("<polyline") == 1                              # a etapa 1 é a atual: nada pintado
    assert t.count('class="pulso"') == 1 and ">50%</text>" in t and ">2/4</text>" in t
    assert "> / Studying</tspan>" in t and ">Studying</text>" in cel  # legenda: 1 linha × grade
    assert "<polyline" not in avulsa and 'class="pulso"' not in avulsa and "Concluído" not in avulsa
    assert ">Pausado</text>" in avulsa and ">Paused</text>" in avulsa and ">0/1</text>" in avulsa
    tres = {"id": "u", "etapas": [{"numero": n, "status": s}
                                  for n, s in ((1, "concluido"), (2, "concluido"), (3, "estudando"))]}
    pintada = imagens({"trilhas": [tres]})[f"{PASTA}/u-claro.svg"]
    assert pintada.count("<polyline") == 2 and 'stroke="#4f46e5" stroke-width="3"' in pintada
    try:
        imagens({"trilhas": [{"etapas": [{"numero": 1}]}, {"etapas": [{"numero": 1}]}]})
    except SystemExit as erro:
        assert "id" in str(erro)
    else:
        raise AssertionError("duas trilhas sem id deveriam falhar")
    assert md.count("<details open>") == 1 and md.count("<details>") == 3  # AWS: avulsa com subtemas
    assert "Dart logic and syntax</b> — 🟢 Estudando / Studying · 2/4 ✅</summary>" in md
    assert "**Progresso / Progress:** `█████░░░░░` 50% · 2/4 ✅ · ⭐ 1/2" in md
    assert "- 🟢 **[Variables](https://v)** · 1/2\n  - ✅ ⭐ [Null safety](https://v#n)\n  - 🟢 ⭐ Final and const" in md
    assert ("- ⚪ Ramos · Branches\n- ✅ **Pronto** · 1/1 · [código / code](https://g)\n"
            "  - ✅ A · [código / code](https://g/a)") in md
    assert "[Curso](https://c) (US$ 99)" in md
    assert "<b>AWS</b> — ⚪ A começar / Up next · 0/1 ✅</summary>" in md and "- ⚪ M1" in md
    assert "⭐ 0/" not in md                                       # sem ⭐ na etapa: sem contador de ⭐
    assert "#### Extras\n\n- [Udemy](https://u) (pago) — Só em promoção · <em>Only on sale</em>" in md
    assert "Conteúdo<br>\n<em>Content</em>" in md
    assert "Só em português\n" in md and "<em></em>" not in md
    assert "**Onde / Where:** [DartPad](https://dartpad.dev)" in md and md.count("Onde / Where") == 1
    assert "<b>Databricks</b> — ⏸️ Pausado / Paused" in md
    assert "Pausei.<br>\n<em>Paused.</em>" in md
    assert "Updated on 24/09/2026" in md
    for proibido in ("PREENCHER", "progresso", "None", "[]", "{}", "<b></b>"):
        assert proibido not in md, proibido
    try:
        imagens({"trilhas": [{"etapas": [{"status": "estudnado"}]}]})
    except SystemExit as erro:
        assert "estudnado" in str(erro)
    else:
        raise AssertionError("status inválido deveria falhar")
    try:
        imagens({"trilhas": [{"etapas": [{"subtemas": [{"nome": "X", "status": "feito"}]}]}]})
    except SystemExit as erro:
        assert "'feito' em 'X'" in str(erro)
    else:
        raise AssertionError("status inválido em subtema deveria falhar")
    assert "Atualizar progresso" not in md
    com_link = painel({**dados, "painel": "https://x/issues/1"}, datetime.date(2026, 9, 24), svgs)
    assert com_link.count('<a href="https://x/issues/1">Atualizar progresso · Update progress</a>') == 1
    lista_agora = {"agora": [
        {"pt": "📱 A partir de **26/10**", "en": "Starting **Oct 26**", "ate": "2026-10-25"},
        {"pt": "📱 Dev na **ília**", "en": "Dev at **ília**", "desde": "2026-10-26"},
        {"pt": "Só PT", "en": ""},
    ]}
    antes, depois = (agora(lista_agora, datetime.date(2026, 10, dia)) for dia in (25, 26))
    assert "- 📱 A partir de **26/10**<br>\n  <em>Starting **Oct 26**</em>" in antes and "ília" not in antes
    assert "Dev na **ília**" in depois and "A partir de" not in depois
    assert "- Só PT\n" in antes and "<em></em>" not in antes
    trocado = substitui(f"a\n{AGORA_INICIO}\nvelho\n{AGORA_FIM}\nb", depois, AGORA_INICIO, AGORA_FIM)
    assert "velho" not in trocado and trocado.startswith("a\n") and trocado.endswith("\nb")
    readme = f"antes\n{INICIO}\nvelho\n{FIM}\ndepois"
    novo = substitui(readme, md)
    assert novo.startswith("antes\n") and novo.endswith("\ndepois") and "velho" not in novo
    try:
        substitui("sem marcadores", md)
    except SystemExit:
        pass
    else:
        raise AssertionError("deveria falhar sem marcadores")
    print("ok")


if __name__ == "__main__":
    if "--teste" in sys.argv:
        teste()
        sys.exit()
    dados = json.load(sys.stdin)
    with open("README.md", encoding="utf-8") as f:
        readme = f.read()
    # Monta tudo antes de abrir para escrita: se o yml tiver um status
    # inválido, o README e as imagens ficam intactos em vez de serem apagados.
    svgs = imagens(dados)
    novo = substitui(readme, painel(dados, data_do_estudos(), svgs))
    if "agora" in dados:
        novo = substitui(novo, agora(dados, hoje_brasilia()), AGORA_INICIO, AGORA_FIM)
    os.makedirs(PASTA, exist_ok=True)
    for arquivo, svg in svgs.items():
        with open(arquivo, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
    with open("README.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(novo)
