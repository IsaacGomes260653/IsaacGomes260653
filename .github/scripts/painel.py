"""Issue do painel de estudos: as caixinhas da issue <-> o estudos.yml.

Corpo da issue a partir do yml:
    yq -o=json estudos.yml | python3 .github/scripts/painel.py --issue > corpo.md
Aplica a issue editada no estudos.yml (mexe só nas linhas que mudam):
    yq -o=json estudos.yml | python3 .github/scripts/painel.py --aplica corpo.md
Autoteste:
    python3 .github/scripts/painel.py --teste

Cada caixinha e cada título de etapa levam um código escondido, como
<!-- s:flutter:1:4 --> (4º subtema da etapa 1 da trilha flutter), que liga a
linha da issue ao subtema do yml. Regras de status ao aplicar:
- caixinha marcada = concluído;
- numa trilha em sequência, o 1º subtema não marcado da 1ª etapa incompleta
  (e não pausada) fica estudando, e a etapa também;
- numa trilha avulsa (Outros estudos), cada etapa está estudando quando já
  tem algo marcado, e o 1º subtema não marcado dela fica estudando;
- [pausado] no título da etapa pausa a etapa e o 1º subtema não marcado dela;
- o resto fica a começar (sem status no yml).
"""

import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

from estudos import junta, link, nome, status, texto

ARQUIVO = "estudos.yml"
YQ = os.environ.get("YQ", "yq")

MARCA = "<!-- painel-estudos: gerado a partir do estudos.yml pelo workflow painel-estudos.yml -->"
MARCA_AGORA = "<!-- agora -->"
AJUDA = """> **Como usar:** marque a caixinha de cada subtema que você terminar e o roadmap do perfil se \
atualiza sozinho em cerca de 1 minuto. O 1º subtema não marcado da etapa atual vira "estudando". \
Para pausar uma etapa, escreva `[pausado]` no título dela. A seção **Agora**, no fim, é texto: \
edite a issue e escreva um item por linha, `português | inglês`. Não apague os códigos \
`<!-- ... -->` escondidos no fim das linhas.
>
> **How to use:** tick each subtopic you finish and the profile roadmap updates itself in about \
a minute. The first unticked subtopic of the current stage becomes "studying". To pause a stage, \
write `[pausado]` in its title. The **Now** section, at the end, is plain text: edit the issue and \
write one item per line, `Portuguese | English`. Don't delete the hidden `<!-- ... -->` codes at \
the end of the lines."""
AJUDA_AGORA = ("<!-- Um item por linha: \"português | inglês\". Para um item com data, comece com "
               "[até AAAA-MM-DD] ou [desde AAAA-MM-DD]. Apague a linha para tirar o item. -->")

CODIGO = re.compile(r"<!--\s*([es]:[^\s>]+)\s*-->")
CAIXA = re.compile(r"^\s*[-*+]\s+\[([ xX])\]")
PAUSA = re.compile(r"\[(pausad[oa]|paused)\]", re.I)
ITEM = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
DATA = re.compile(r"^\[(até|ate|desde)\s+(\d{4}-\d{2}-\d{2})\]\s*", re.I)


def trilhas(dados):
    """Por trilha: [(código, caminho no yml, etapa, [(código, caminho, subtema)])]."""
    for ti, trilha in enumerate(dados.get("trilhas") or []):
        tid = texto(trilha.get("id")) or f"t{ti + 1}"
        etapas = []
        for ei, e in enumerate(trilha.get("etapas") or [], 1):
            caminho = f".trilhas[{ti}].etapas[{ei - 1}]"
            fs = []

            def anda(subtemas, base):
                for k, s in enumerate(subtemas or []):
                    if s.get("itens"):
                        anda(s["itens"], f"{base}[{k}].itens")
                    else:
                        fs.append((f"s:{tid}:{ei}:{len(fs) + 1}", f"{base}[{k}]", s))

            anda(e.get("subtemas"), f"{caminho}.subtemas")
            etapas.append((f"e:{tid}:{ei}", caminho, e, fs))
        yield trilha, etapas


def atuais(dados):
    """{caminho: status} como está no yml. Subtema a começar = None (sem status)."""
    saida = {}
    for _, etapas in trilhas(dados):
        for _, caminho, e, fs in etapas:
            saida[caminho] = status(e)
            for _, p, s in fs:
                saida[p] = None if status(s, "a_comecar") == "a_comecar" else status(s)
    return saida


def novos_status(dados, marcado, pausada):
    """{caminho: status} pelas regras do topo do arquivo."""
    novo = {}
    for _, etapas in trilhas(dados):
        sequencia = len(etapas) > 1 and all(texto(e.get("numero")) for _, _, e, _ in etapas)
        tem_atual = False
        for chave, caminho, e, fs in etapas:
            if not fs:  # etapa sem subtemas: não tem caixinha, fica como está
                continue
            marcas = [marcado(k, s) for k, _, s in fs]
            if all(marcas):
                st = "concluido"
            elif pausada(chave, e):
                st = "pausado"
            elif sequencia:
                st = "a_comecar" if tem_atual else "estudando"
                tem_atual = True
            else:
                st = "estudando" if any(marcas) else "a_comecar"
            novo[caminho] = st
            primeiro = st in ("estudando", "pausado")
            for (k, p, s), feito in zip(fs, marcas):
                if feito:
                    novo[p] = "concluido"
                elif primeiro:
                    novo[p], primeiro = st, False
                else:
                    novo[p] = None
    return novo


# ---------------------------------------------------------------- yml -> issue

def caixas(subtemas, chaves, recuo=""):
    linhas = []
    for s in subtemas or []:
        rotulo = link(s) or "?"
        if s.get("itens"):
            linhas.append(f"{recuo}- **{rotulo}**")
            linhas += caixas(s["itens"], chaves, recuo + "  ")
        else:
            x = "x" if status(s, "a_comecar") == "concluido" else " "
            estrela = "⭐ " if s.get("estrela") else ""
            linhas.append(f"{recuo}- [{x}] {estrela}{rotulo} <!-- {next(chaves)} -->")
    return linhas


def linha_agora(item):
    item = normaliza(item)
    data = (f"[até {item['ate']}] " if "ate" in item else "") + (f"[desde {item['desde']}] " if "desde" in item else "")
    return f"- {data}{item['pt']}" + (f" | {item['en']}" if item["en"] else "")


def corpo_issue(dados):
    partes = [MARCA, AJUDA]
    for trilha, etapas in trilhas(dados):
        partes.append(f"## {junta(trilha.get('titulo'), ' · ')}")
        for chave, _, e, fs in etapas:
            titulo = " · ".join(filter(None, [texto(e.get("numero")), nome(e)]))
            pausa = " [pausado]" if status(e) == "pausado" else ""
            partes.append(f"### {titulo}{pausa} <!-- {chave} -->")
            if fs:
                partes.append("\n".join(caixas(e.get("subtemas"), iter([k for k, _, _ in fs]))))
    partes.append(f"## 📌 Agora · Now {MARCA_AGORA}")
    partes.append("\n".join([AJUDA_AGORA, *map(linha_agora, dados.get("agora") or [])]))
    return "\n\n".join(partes) + "\n"


# ---------------------------------------------------------------- issue -> yml

def normaliza(item):
    """Item do Agora com só os campos que importam, na ordem pt, en, ate, desde."""
    saida = {"pt": texto(item.get("pt")), "en": texto(item.get("en"))}
    for campo in ("ate", "desde"):
        valor = texto(item.get(campo))
        if valor:
            try:
                datetime.date.fromisoformat(valor)
            except ValueError:
                raise SystemExit(f"Data inválida {valor!r} no item do Agora {saida['pt']!r}: use AAAA-MM-DD")
            saida[campo] = valor
    return saida


def le_item(t):
    item = {}
    m = DATA.match(t)
    if m:
        item["desde" if m.group(1).lower() == "desde" else "ate"] = m.group(2)
        t = t[m.end():]
    pt, _, en = t.partition(" | ")
    return normaliza({"pt": pt, "en": en, **item})


def le(corpo):
    """Da issue: {código: marcado}, {código da etapa: pausada} e os itens do Agora
    (None se a seção não estiver lá, para não apagar o Agora por engano)."""
    marcas, pausas, agora = {}, {}, None
    for linha in corpo.splitlines():
        if MARCA_AGORA in linha:
            agora = []
            continue
        m = CODIGO.search(linha)
        if m:
            chave = m.group(1)
            if chave.startswith("s:"):
                caixa = CAIXA.match(linha)
                if caixa:
                    marcas[chave] = caixa.group(1) != " "
            else:
                pausas[chave] = bool(PAUSA.search(linha))
        elif agora is not None:
            if linha.startswith("#"):  # outro título depois do Agora: a seção acabou
                break
            item = ITEM.match(linha)
            if item and not CAIXA.match(linha) and le_item(item.group(1))["pt"]:
                agora.append(le_item(item.group(1)))
    return marcas, pausas, agora


def yq(expr, conteudo):
    with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False, encoding="utf-8", newline="\n") as f:
        f.write(conteudo)
    try:
        saida = subprocess.run([YQ, "-o=json", "-I=0", expr, f.name], check=True,
                               capture_output=True, text=True, encoding="utf-8")
        return json.loads(saida.stdout)
    finally:
        os.unlink(f.name)


def troca_em_linha(linha, novo):
    """Ajusta o status dentro de um subtema escrito numa linha só: { nome: ..., status: ... }."""
    if re.search(r"\bstatus:", linha):
        if novo:
            return re.sub(r"\bstatus:\s*[a-z_]+", f"status: {novo}", linha, count=1)
        return re.sub(r",\s*status:\s*[a-z_]+|\bstatus:\s*[a-z_]+\s*,\s*", "", linha, count=1)
    if not novo:
        return linha
    for chave in (", estrela:", ", url:", ", preco:"):  # o status entra logo depois do nome
        if chave in linha:
            return linha.replace(chave, f", status: {novo}{chave}", 1)
    fim = linha.rindex("}")
    return f"{linha[:fim].rstrip()}, status: {novo} {linha[fim:]}"


def troca_status(conteudo, mudancas):
    """Muda só as linhas de status, para não desfazer a formatação feita à mão
    (o yq reformataria o arquivo inteiro). O yq só diz em que linha está cada nó."""
    if not mudancas:
        return conteudo
    caminhos = list(mudancas)
    infos = yq("[" + ", ".join(f'({p} | {{"l": line, "c": column, "f": style, "s": (.status | line)}})'
                               for p in caminhos) + ", (.trilhas | key | line)]", conteudo)
    linhas = conteudo.split("\n")
    # O yq conta as linhas sem o comentário do topo do arquivo: acha a diferença.
    desvio = next(i for i, l in enumerate(linhas) if l.startswith("trilhas:")) + 1 - infos.pop()
    for p, info in sorted(zip(caminhos, infos), key=lambda x: -max(x[1]["l"], x[1]["s"])):
        novo, i = mudancas[p], info["l"] + desvio - 1
        if info["f"] == "flow":
            if info["s"] not in (0, info["l"]) or "{" not in linhas[i]:
                raise SystemExit(f"Não sei editar {p}: escreva cada subtema numa linha só, {{ nome: ... }}")
            linhas[i] = troca_em_linha(linhas[i], novo)
        elif info["s"]:
            j = info["s"] + desvio - 1
            if not re.match(r"\s*status:", linhas[j]):
                raise SystemExit(f"A linha {j + 1} do {ARQUIVO} não é o status de {p}")
            if novo:
                linhas[j] = re.sub(r"(status:\s*)[a-z_]+", rf"\g<1>{novo}", linhas[j], count=1)
            else:
                del linhas[j]
        elif novo:
            linhas.insert(i + 1, " " * (info["c"] - 1) + f"status: {novo}")
    return "\n".join(linhas)


def troca_agora(conteudo, itens):
    def campos(item):
        return "{ " + ", ".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in item.items()) + " }"

    bloco = ["agora:", *(f"  - {campos(i)}" for i in itens)] if itens else ["agora: []"]
    linhas = conteudo.split("\n")
    ini = next((i for i, l in enumerate(linhas) if re.match(r"agora:", l)), None)
    if ini is None:
        while linhas and not linhas[-1]:
            linhas.pop()
        return "\n".join([*linhas, "", *bloco, ""])
    fim = ini + 1
    while fim < len(linhas) and (linhas[fim][:1] in (" ", "\t") or not linhas[fim]):
        fim += 1
    while fim > ini + 1 and not linhas[fim - 1]:
        fim -= 1
    linhas[ini:fim] = bloco
    return "\n".join(linhas)


def aplica(dados, corpo, conteudo):
    """Novo texto do estudos.yml com o estado da issue. Confere o resultado
    relendo com o yq antes de devolver: na dúvida, falha sem estragar o arquivo."""
    marcas, pausas, agora = le(corpo)
    alvo = novos_status(
        dados,
        lambda k, s: marcas.get(k, status(s, "a_comecar") == "concluido"),  # linha sumiu da issue: fica como está
        lambda k, e: pausas.get(k, status(e) == "pausado"),
    )
    antes = atuais(dados)
    novo = troca_status(conteudo, {p: v for p, v in alvo.items() if v != antes[p]})
    agora_antes = [normaliza(i) for i in dados.get("agora") or []]
    if agora is not None and agora != agora_antes:
        novo = troca_agora(novo, agora)
    if novo != conteudo:
        relido = yq(".", novo)
        depois = atuais(relido)
        errados = [p for p, v in alvo.items() if depois.get(p) != v]
        agora_final = agora if agora is not None else agora_antes
        if errados or [normaliza(i) for i in relido.get("agora") or []] != agora_final:
            raise SystemExit(f"A edição do {ARQUIVO} não saiu como esperado ({errados[:3]}); nada foi gravado")
    return novo


# ---------------------------------------------------------------- autoteste

EXEMPLO = """# cabeçalho
# outra linha do cabeçalho

trilhas:
  - id: t
    titulo: { pt: "Trilha", en: "Track" }
    etapas:
      - numero: 1
        titulo: { pt: "Um", en: "One" }
        status: estudando
        subtemas:
          - nome: "Grupo"
            itens:
              - { nome: "A", status: concluido, url: "https://a" }
              - { nome: "B", status: estudando, estrela: true }
          - { nome: "C" }

      - numero: 2
        titulo: { pt: "Dois", en: "Two" }
        status: a_comecar
        subtemas:
          - { nome: "D", url: "https://d" }
          - { nome: "E" }

  - id: o
    titulo: { pt: "Outros", en: "Other" }
    etapas:
      - titulo: { pt: "X", en: "X" }
        status: pausado
        subtemas:
          - { nome: "X1", status: pausado }
          - { nome: "X2" }

# Agora
agora:
  - { pt: "📱 A partir de 26/10", en: "Starting Oct 26", ate: "2026-10-25" }
  - { pt: "🛠️ Mantendo", en: "Keeping" }

extras:
  - nome: "Extra"
"""


def teste():
    dados = yq(".", EXEMPLO)
    corpo = corpo_issue(dados)
    assert corpo.startswith(MARCA) and corpo.count("- [x]") == 1 and corpo.count("- [ ]") == 6
    assert "- **Grupo**\n  - [x] [A](https://a) <!-- s:t:1:1 -->\n  - [ ] ⭐ B <!-- s:t:1:2 -->\n- [ ] C <!-- s:t:1:3 -->" in corpo
    assert "### 1 · Um · One <!-- e:t:1 -->" in corpo and "### X [pausado] <!-- e:o:1 -->" in corpo
    assert "- [até 2026-10-25] 📱 A partir de 26/10 | Starting Oct 26\n- 🛠️ Mantendo | Keeping\n" in corpo

    def edita(*trocas):
        c = corpo
        for a, b in trocas:
            assert a in c, a
            c = c.replace(a, b)
        novo = aplica(dados, c, EXEMPLO)
        return [(x, y) for x, y in zip(EXEMPLO.split("\n"), novo.split("\n")) if x != y], novo

    assert aplica(dados, corpo, EXEMPLO) == EXEMPLO                       # ida e volta: nada muda
    assert aplica(dados, corpo.replace("\n", "\r\n"), EXEMPLO) == EXEMPLO  # app do celular manda \r\n
    diff, _ = edita(("- [ ] ⭐ B", "- [x] ⭐ B"))                          # marca B: C vira estudando
    assert diff == [('              - { nome: "B", status: estudando, estrela: true }',
                     '              - { nome: "B", status: concluido, estrela: true }'),
                    ('          - { nome: "C" }', '          - { nome: "C", status: estudando }')], diff
    diff, novo = edita(("- [ ] ⭐ B", "- [x] ⭐ B"), ("- [ ] C", "- [x] C"))  # fecha a etapa 1
    assert ('        status: estudando', '        status: concluido') in diff
    assert ('        status: a_comecar', '        status: estudando') in diff
    assert ('          - { nome: "D", url: "https://d" }', '          - { nome: "D", status: estudando, url: "https://d" }') in diff
    assert novo.count("\n\n") == EXEMPLO.count("\n\n") and novo.startswith("# cabeçalho")  # linhas em branco e comentários ficam
    diff, _ = edita(("- [x] [A]", "- [ ] [A]"))                            # desmarca A: A vira o atual, B volta
    assert ('              - { nome: "A", status: concluido, url: "https://a" }',
            '              - { nome: "A", status: estudando, url: "https://a" }') in diff
    assert ('              - { nome: "B", status: estudando, estrela: true }',
            '              - { nome: "B", estrela: true }') in diff and len(diff) == 2
    diff, _ = edita(("### X [pausado]", "### X"))                          # tira a pausa: X volta a começar
    assert diff == [('        status: pausado', '        status: a_comecar'),
                    ('          - { nome: "X1", status: pausado }', '          - { nome: "X1" }')], diff
    diff, _ = edita(("- [ ] X2", "- [x] X2"), ("### X [pausado]", "### X"))  # avulsa com algo feito: estudando
    assert ('        status: pausado', '        status: estudando') in diff
    assert ('          - { nome: "X1", status: pausado }', '          - { nome: "X1", status: estudando }') in diff
    _, novo = edita(("- 🛠️ Mantendo | Keeping\n", "- 🐾 Novo **x** | New \"y\"\n- [desde 2026-10-26] Dev | Dev\n"))
    assert ('agora:\n  - { pt: "📱 A partir de 26/10", en: "Starting Oct 26", ate: "2026-10-25" }\n'
            '  - { pt: "🐾 Novo **x**", en: "New \\"y\\"" }\n  - { pt: "Dev", en: "Dev", desde: "2026-10-26" }\n\nextras:') in novo
    _, novo = edita(("<!-- s:t:1:3 -->", ""))                               # linha sem código: ignorada
    assert novo == EXEMPLO
    assert aplica(dados, corpo.split(MARCA_AGORA)[0], EXEMPLO) == EXEMPLO     # sem a seção Agora: Agora intacto
    try:
        edita(("[até 2026-10-25]", "[até 2026-13-40]"))
    except SystemExit as erro:
        assert "2026-13-40" in str(erro)
    else:
        raise AssertionError("data inválida deveria falhar")
    print("ok")


if __name__ == "__main__":
    if "--teste" in sys.argv:
        teste()
        sys.exit()
    dados = json.load(sys.stdin)
    if "--issue" in sys.argv:
        sys.stdout.write(corpo_issue(dados))
    elif "--aplica" in sys.argv:
        with open(sys.argv[sys.argv.index("--aplica") + 1], encoding="utf-8") as f:
            corpo = f.read()
        with open(ARQUIVO, encoding="utf-8") as f:
            conteudo = f.read()
        novo = aplica(dados, corpo, conteudo)
        if novo != conteudo:
            with open(ARQUIVO, "w", encoding="utf-8", newline="\n") as f:
                f.write(novo)
    else:
        raise SystemExit(__doc__)
