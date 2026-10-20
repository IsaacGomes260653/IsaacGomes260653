"""Reescreve o roadmap de estudos do README a partir do estudos.yml.

Uso no workflow:  yq -o=json estudos.yml | python3 .github/scripts/estudos.py
Autoteste local:  python3 .github/scripts/estudos.py --teste

Lê o estudos.yml já convertido em JSON pela entrada padrão (o yq vem
instalado nos runners do GitHub, então não precisa de pip) e troca só o
trecho entre os marcadores ESTUDOS:INICIO e ESTUDOS:FIM do README.md.
Campo vazio ou ausente simplesmente não aparece.
"""

import datetime
import json
import re
import subprocess
import sys

INICIO = "<!-- ESTUDOS:INICIO -->"
FIM = "<!-- ESTUDOS:FIM -->"

# A ordem daqui é a ordem da legenda.
STATUS = {
    "estudando": "🟢 Estudando / Studying",
    "a_comecar": "⚪ A começar / Up next",
    "pausado": "⏸️ Pausado / Paused",
    "concluido": "✅ Concluído / Done",
}

# Cor dos nós no diagrama: o índigo do perfil para "estudando" e cinza para
# "a começar". Texto branco passa de 4.5:1 sobre todos os fundos, e cada
# fundo tem pelo menos 3:1 contra o fundo claro e o escuro do GitHub.
CORES = {
    "estudando": "fill:#4f46e5,stroke:#818cf8,color:#fff",
    "a_comecar": "fill:#6b7280,stroke:#6b7280,color:#fff",
    "pausado": "fill:#9a6700,stroke:#9a6700,color:#fff",
    "concluido": "fill:#1a7f37,stroke:#1a7f37,color:#fff",
}

# Rótulos curtos dos nós: 8 etapas lado a lado só cabem na largura do README
# com nomes curtos. O estudos.yml só tem o título completo, então os apelidos
# ficam aqui, pela chave do título em português. Se um título mudar ou entrar
# uma etapa nova, o nó mostra o título completo em vez de um apelido velho.
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
        if s.get("itens"):
            feitos, total = conta(s["itens"])
            linhas.append(f"{recuo}- {icone(status_sub(s))} **{rotulo}** · {feitos}/{total}")
            linhas.append(lista(s["itens"], recuo + "  "))
        else:
            estrela = "⭐ " if s.get("estrela") else ""
            linhas.append(f"{recuo}- {icone(status_sub(s))} {estrela}{rotulo}")
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
    """Número, português e inglês, um por linha. O visualizador de Mermaid do
    GitHub mostra o diagrama em tamanho natural (não encolhe para caber), e em
    três linhas as 8 etapas ficam com ~710px, dentro dos ~830px do README.
    A etapa em andamento ganha uma quarta linha com a porcentagem concluída."""
    titulo = etapa.get("titulo") or {}
    pt, en = CURTOS.get(texto(titulo.get("pt")), (titulo.get("pt"), titulo.get("en")))
    pt, en = texto(pt), texto(en)
    feitos, total = conta(etapa.get("subtemas"))
    pct = f"{round(100 * feitos / total)}%" if total and status(etapa) == "estudando" else ""
    linhas = [texto(etapa.get("numero")), pt, en if en != pt else "", pct]
    return "<br>".join(filter(None, linhas)).replace('"', "#quot;")


def diagrama(trilha, etapas):
    linhas = [
        "```mermaid",
        '%%{init: {"flowchart": {"rankSpacing": 15, "nodeSpacing": 20, "padding": 6, "diagramPadding": 8}}}%%',
        "flowchart LR",
    ]
    titulo = junta(trilha.get("titulo"), " · ")
    if titulo:
        linhas.append(f"  accTitle: {titulo}")
    linhas.append(
        "  accDescr: Etapas em sequência, a cor mostra o status / Stages in sequence, the color shows the status"
    )
    usados = []
    for i, e in enumerate(etapas, 1):
        s = status(e)
        linhas.append(f'  e{i}["{rotulo_curto(e)}"]' + (f":::{s}" if s else ""))
        usados.append(s)
    if len(etapas) > 1:
        linhas.append("  " + " --> ".join(f"e{i}" for i in range(1, len(etapas) + 1)))
    linhas += [f"  classDef {s} {CORES[s]}" for s in dict.fromkeys(usados) if s]
    linhas.append("```")
    return "\n".join(linhas)


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


def painel(dados, data):
    blocos = [" · ".join([*STATUS.values(), ESTRELA])]
    for trilha in dados.get("trilhas") or []:
        etapas = trilha.get("etapas") or []
        titulo = junta(trilha.get("titulo"), " · ")
        if titulo:
            blocos.append(f"#### {titulo}")
        numeradas = [e for e in etapas if texto(e.get("numero"))]
        if numeradas:
            blocos.append(diagrama(trilha, numeradas))
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


def substitui(readme, bloco):
    padrao = re.compile(re.escape(INICIO) + r".*?" + re.escape(FIM), re.S)
    if not padrao.search(readme):
        raise SystemExit(f"Marcadores {INICIO} / {FIM} não encontrados no README.md")
    return padrao.sub(lambda _: bloco, readme, count=1)


def data_do_estudos():
    saida = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", "estudos.yml"],
        capture_output=True, text=True,
    ).stdout.strip()
    return datetime.date.fromisoformat(saida) if saida else datetime.date.today()


def teste():
    dados = {"trilhas": [
        {"titulo": {"pt": "Trilha", "en": "Track"}, "etapas": [
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
                 {"nome": "Pronto", "itens": [{"nome": "A", "status": "concluido"}]},
             ]},
            {"numero": 2, "titulo": {"pt": "Tópico novo", "en": "New topic"}, "status": "a_comecar",
             "conteudo": {"pt": "Só em português"}, "onde": []},
            {"numero": 3, "titulo": {"pt": "Sem status", "en": ""}, "progresso": 40, "proximo": "PREENCHER"},
        ]},
        {"titulo": {"pt": "Dados", "en": "Data"}, "etapas": [
            {"titulo": {"pt": "Databricks", "en": "Databricks"}, "status": "pausado",
             "nota": {"pt": "Pausei.", "en": "Paused."}, "onde": []},
            {"titulo": {"pt": "AWS", "en": "AWS"}, "status": "a_comecar", "subtemas": [{"nome": "M1"}]},
        ]},
    ], "extras": [
        {"nome": "Udemy", "url": "https://u", "preco": "pago",
         "nota": {"pt": "Só em promoção", "en": "Only on sale"}},
    ]}
    md = painel(dados, datetime.date(2026, 9, 24))
    assert md.splitlines()[3] == " · ".join([*STATUS.values(), ESTRELA])
    assert "#### Trilha · Track" in md and "#### Dados · Data" in md
    assert "flowchart LR" in md
    assert 'e1["1<br>Lógica<br>Logic<br>50%"]:::estudando' in md  # apelido curto, PT, EN e % (em andamento)
    assert 'e2["2<br>Tópico novo<br>New topic"]:::a_comecar' in md  # sem apelido: título completo
    assert 'e3["3<br>Sem status"]\n' in md                        # sem status: sem cor
    assert "e1 --> e2 --> e3" in md
    assert "classDef estudando fill:#4f46e5" in md
    assert "classDef pausado" not in md                           # Databricks fica fora do diagrama
    assert md.count("<details open>") == 1 and md.count("<details>") == 3  # AWS: avulsa com subtemas
    assert "Dart logic and syntax</b> — 🟢 Estudando / Studying · 2/4 ✅</summary>" in md
    assert "**Progresso / Progress:** `█████░░░░░` 50% · 2/4 ✅ · ⭐ 1/2" in md
    assert "- 🟢 **[Variables](https://v)** · 1/2\n  - ✅ ⭐ [Null safety](https://v#n)\n  - 🟢 ⭐ Final and const" in md
    assert "- ⚪ Ramos · Branches\n- ✅ **Pronto** · 1/1\n  - ✅ A" in md
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
        painel({"trilhas": [{"etapas": [{"status": "estudnado"}]}]}, datetime.date.today())
    except SystemExit as erro:
        assert "estudnado" in str(erro)
    else:
        raise AssertionError("status inválido deveria falhar")
    try:
        painel({"trilhas": [{"etapas": [{"subtemas": [{"nome": "X", "status": "feito"}]}]}]}, datetime.date.today())
    except SystemExit as erro:
        assert "'feito' em 'X'" in str(erro)
    else:
        raise AssertionError("status inválido em subtema deveria falhar")
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
    # inválido, o README fica intacto em vez de ser apagado.
    novo = substitui(readme, painel(dados, data_do_estudos()))
    with open("README.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(novo)
