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


def status(etapa):
    s = texto(etapa.get("status"))
    if s and s not in STATUS:
        raise SystemExit(
            f"status inválido {s!r} na etapa {junta(etapa.get('titulo'), ' / ')!r}."
            f" Use: {' | '.join(STATUS)}"
        )
    return s


def onde(links):
    itens = []
    for link in links or []:
        nome, url = texto(link.get("nome")), texto(link.get("url"))
        if nome and url:
            itens.append(f"[{nome}]({url})")
        elif nome or url:
            itens.append(nome or f"<{url}>")
    return f"**Onde / Where:** {' · '.join(itens)}" if itens else ""


def rotulo_curto(etapa):
    """ "1 · Lógica" em cima e "Logic" embaixo: em duas linhas o nó fica com
    metade da largura, e as 8 etapas cabem lado a lado sem encolher o texto."""
    titulo = etapa.get("titulo") or {}
    pt, en = CURTOS.get(texto(titulo.get("pt")), (titulo.get("pt"), titulo.get("en")))
    pt, en = texto(pt), texto(en)
    linhas = [" · ".join(filter(None, [texto(etapa.get("numero")), pt]))]
    if en and en != pt:
        linhas.append(en)
    return "<br>".join(linhas).replace('"', "#quot;")


def diagrama(trilha, etapas):
    linhas = [
        "```mermaid",
        '%%{init: {"flowchart": {"rankSpacing": 20, "nodeSpacing": 20, "padding": 10, "diagramPadding": 8}}}%%',
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
    nome = " · ".join(filter(None, [numero, junta(e.get("titulo"), " · ")]))
    rotulo = " — ".join(filter(None, [nome and f"<b>{nome}</b>", STATUS.get(s)]))
    corpo = [b for b in (bilingue(e.get("conteudo")), bilingue(e.get("nota")), onde(e.get("onde"))) if b]
    if not numero:  # etapa avulsa, fora da sequência (como o Databricks): bloco simples
        return "\n\n".join(filter(None, [rotulo, *corpo]))
    abre = " open" if s == "estudando" else ""
    return "\n\n".join([f"<details{abre}>\n<summary>{rotulo}</summary>", *corpo, "</details>"])


def painel(dados, data):
    blocos = [" · ".join(STATUS.values())]
    for trilha in dados.get("trilhas") or []:
        etapas = trilha.get("etapas") or []
        titulo = junta(trilha.get("titulo"), " · ")
        if titulo:
            blocos.append(f"#### {titulo}")
        numeradas = [e for e in etapas if texto(e.get("numero"))]
        if numeradas:
            blocos.append(diagrama(trilha, numeradas))
        blocos += [b for b in map(etapa, etapas) if b]
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
             "onde": [{"nome": "DartPad", "url": "https://dartpad.dev"}]},
            {"numero": 2, "titulo": {"pt": "Tópico novo", "en": "New topic"}, "status": "a_comecar",
             "conteudo": {"pt": "Só em português"}, "onde": []},
            {"numero": 3, "titulo": {"pt": "Sem status", "en": ""}, "progresso": 40, "proximo": "PREENCHER"},
        ]},
        {"titulo": {"pt": "Dados", "en": "Data"}, "etapas": [
            {"titulo": {"pt": "Databricks", "en": "Databricks"}, "status": "pausado",
             "nota": {"pt": "Pausei.", "en": "Paused."}, "onde": []},
        ]},
    ]}
    md = painel(dados, datetime.date(2026, 9, 24))
    assert md.splitlines()[3] == " · ".join(STATUS.values())
    assert "#### Trilha · Track" in md and "#### Dados · Data" in md
    assert "flowchart LR" in md
    assert 'e1["1 · Lógica<br>Logic"]:::estudando' in md          # apelido curto, EN na 2ª linha
    assert 'e2["2 · Tópico novo<br>New topic"]:::a_comecar' in md  # sem apelido: título completo
    assert 'e3["3 · Sem status"]\n' in md                         # sem status: sem cor
    assert "e1 --> e2 --> e3" in md
    assert "classDef estudando fill:#4f46e5" in md
    assert "classDef pausado" not in md                           # Databricks fica fora do diagrama
    assert md.count("<details open>") == 1 and md.count("<details>") == 2
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
