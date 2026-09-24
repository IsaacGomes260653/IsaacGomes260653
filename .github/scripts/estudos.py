"""Reescreve o painel "Estudando agora" do README a partir do estudos.yml.

Uso no workflow:  yq -o=json estudos.yml | python3 .github/scripts/estudos.py
Autoteste local:  python3 .github/scripts/estudos.py --teste

Lê o estudos.yml já convertido em JSON pela entrada padrão (o yq vem
instalado nos runners do GitHub, então não precisa de pip) e troca só o
trecho entre os marcadores ESTUDOS:INICIO e ESTUDOS:FIM do README.md.
"""

import datetime
import json
import re
import subprocess
import sys

INICIO = "<!-- ESTUDOS:INICIO -->"
FIM = "<!-- ESTUDOS:FIM -->"

STATUS = {
    "estudando": "🟢 Estudando",
    "retomando": "🔄 Retomando",
    "pausado": "⏸️ Pausado",
    "concluido": "✅ Concluído",
    "concluído": "✅ Concluído",
}


def texto(valor):
    if valor is None or str(valor).strip() == "":
        return "[PREENCHER]"
    return str(valor).replace("PREENCHER", "[PREENCHER]").replace("[[PREENCHER]]", "[PREENCHER]")


def barra(progresso):
    try:
        p = max(0, min(100, float(progresso)))
    except (TypeError, ValueError):
        return "progresso [PREENCHER]"
    cheios = round(p / 10)
    return f"`{'▰' * cheios}{'▱' * (10 - cheios)}` {p:g}%"


def status(valor):
    chave = str(valor or "").strip().lower()
    return STATUS.get(chave, f"⚪ {texto(valor)}")


def painel(estudos, data):
    linhas = [
        INICIO,
        "<!-- Gerado a partir do estudos.yml pelo workflow painel-estudos.yml."
        " Não edite aqui: edite o estudos.yml. -->",
        "",
    ]
    trilha_atual = None
    for item in estudos:
        trilha = item.get("trilha")
        if trilha and trilha != trilha_atual:
            linhas += [f"**{texto(trilha)}**", ""]
        trilha_atual = trilha

        detalhe = f"<sub>Próximo passo: {texto(item.get('proximo'))}"
        if item.get("certificado"):
            detalhe += f" · 🎓 [Certificado]({item['certificado']})"
        linhas += [
            f"- **{texto(item.get('nome'))}** · {texto(item.get('plataforma'))}<br>",
            f"  {barra(item.get('progresso'))} · {status(item.get('status'))}<br>",
            f"  {detalhe}</sub>",
            "",
        ]
    linhas += [
        f"<sub>Atualizado em {data:%d/%m/%Y} · gerado automaticamente a partir do"
        ' <a href="estudos.yml">estudos.yml</a></sub>',
        FIM,
    ]
    return "\n".join(linhas)


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
    assert barra(60) == "`▰▰▰▰▰▰▱▱▱▱` 60%"
    assert barra(150) == "`▰▰▰▰▰▰▰▰▰▰` 100%"
    assert barra("PREENCHER") == "progresso [PREENCHER]"
    assert status("Retomando") == "🔄 Retomando"
    assert status("PREENCHER") == "⚪ [PREENCHER]"
    assert texto("Databricks · PREENCHER") == "Databricks · [PREENCHER]"
    readme = f"antes\n{INICIO}\nvelho\n{FIM}\ndepois"
    bloco = painel([{"nome": "Dart", "status": "estudando", "progresso": 40,
                     "certificado": "https://exemplo.com"}], datetime.date(2026, 9, 24))
    novo = substitui(readme, bloco)
    assert novo.startswith("antes\n") and novo.endswith("\ndepois")
    assert "velho" not in novo and "24/09/2026" in novo and "[Certificado](https://exemplo.com)" in novo
    try:
        substitui("sem marcadores", bloco)
    except SystemExit:
        pass
    else:
        raise AssertionError("deveria falhar sem marcadores")
    print("ok")


if __name__ == "__main__":
    if "--teste" in sys.argv:
        teste()
        sys.exit()
    estudos = json.load(sys.stdin)["estudos"]
    with open("README.md", encoding="utf-8") as f:
        readme = f.read()
    # Monta tudo antes de abrir para escrita: se faltar um marcador, o
    # README fica intacto em vez de ser apagado.
    novo = substitui(readme, painel(estudos, data_do_estudos()))
    with open("README.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(novo)
