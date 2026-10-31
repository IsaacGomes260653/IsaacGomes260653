"""Escolhe o jogo da vez do Cantinho descontraído e escreve a legenda dele.

Uso no workflow:  python3 .github/scripts/jogo_da_vez.py <pasta dos jogos> <pasta de saída>
Autoteste:        python3 .github/scripts/jogo_da_vez.py --teste

A cada 4 horas entra um jogo. Os 8 passam em ordem embaralhada, sem repetir até
mostrar todos; depois a ordem é embaralhada de novo. A ordem sai só do relógio:
cada bloco de 8 janelas de 4 h é um ciclo, e o número do ciclo é a semente do
embaralhamento. Assim não há estado para guardar, e uma execução atrasada ou
perdida do Actions não bagunça a sequência.

Grava na saída, sempre com os mesmos nomes (o README não muda):
- jogo-{claro,escuro}.svg: o jogo da vez, copiado da pasta dos jogos;
- legenda-{claro,escuro}.svg e legenda-celular-{claro,escuro}.svg: "Jogo da vez:
  [nome] · Now playing: [name] — troca a cada 4 h entre 8 jogos", em contornos
  da Mona Sans e nas cores do brand/tokens.json;
- vez.json: qual jogo está no ar e até quando.
"""

import datetime
import hashlib
import json
import os
import shutil
import sys

from agora import TEMAS, escreve, mede

JOGOS = {  # arquivo: (nome em português, nome em inglês)
    "cobrinha": ("Cobrinha dourada", "Golden snake"),
    "pacman": ("Pac-Man", "Pac-Man"),
    "galaga": ("Galaga", "Galaga"),
    "bomberman": ("Bomberman", "Bomberman"),
    "minesweeper": ("Campo Minado", "Minesweeper"),
    "puzzle-bobble": ("Puzzle Bobble", "Puzzle Bobble"),
    "breakout": ("Quebra-tijolos", "Breakout"),
    "tetris": ("Tetris", "Tetris"),
}
JANELA = 4 * 3600  # segundos de cada jogo no ar
INICIO = datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc)
TAM, TEXTO, NOME = 14, 450, 620  # tamanho e pesos da Mona Sans, como as legendas <sub> do README


def ordem(ciclo):
    """Os 8 jogos embaralhados para o ciclo (Fisher-Yates com SHA-256, igual em
    qualquer versão do Python). O 1º nunca repete o último do ciclo anterior."""
    def embaralha(n):
        lista = list(JOGOS)
        for i in range(len(lista) - 1, 0, -1):
            j = int(hashlib.sha256(f"{n}:{i}".encode()).hexdigest(), 16) % (i + 1)
            lista[i], lista[j] = lista[j], lista[i]
        return lista
    atual = embaralha(ciclo)
    if atual[0] == embaralha(ciclo - 1)[-1]:
        atual[0], atual[1] = atual[1], atual[0]
    return atual


def da_vez(agora):
    """(jogo, fim da janela) para o instante `agora`."""
    janela = int((agora - INICIO).total_seconds() // JANELA)
    ciclo, posicao = divmod(janela, len(JOGOS))
    return ordem(ciclo)[posicao], INICIO + datetime.timedelta(seconds=(janela + 1) * JANELA)


def legenda(jogo, tema, celular):
    """No desktop numa linha; no celular, o nome em cima e a troca embaixo."""
    T, (pt, en) = TEMAS[tema], JOGOS[jogo]
    pedacos = [("Jogo da vez: ", TEXTO, "apoio"), (pt, NOME, "ouro"), (" · Now playing: ", TEXTO, "apoio"), (en, NOME, "ouro")]
    resto = [("troca a cada 4 h entre 8 jogos", TEXTO, "apoio")]
    linhas = [pedacos, resto] if celular else [pedacos + [(" — ", TEXTO, "apoio")] + resto]
    usados, partes, larguras = {}, [], [sum(mede(t, TAM, p) for t, p, _ in linha) for linha in linhas]
    largura, altura = round(max(larguras)) + 4, 22 * len(linhas)
    for n, (linha, w) in enumerate(zip(linhas, larguras)):
        x = (largura - w) / 2
        for t, peso, cor in linha:
            partes.append(escreve(t, round(x, 1), 16 + 22 * n, TAM, peso, T[cor], usados))
            x += mede(t, TAM, peso)
    defs = "".join(f'<path id="{n}" d="{d}"/>' for n, d in usados.items())
    rotulo = f"Jogo da vez: {pt} · Now playing: {en} — troca a cada 4 h entre 8 jogos"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" viewBox="0 0 {largura} {altura}"'
            f' role="img" aria-label="{rotulo}"><title>{rotulo}</title><defs>{defs}</defs>{"".join(partes)}</svg>\n')


def teste():
    vistos, inicio = [], INICIO + datetime.timedelta(minutes=5)
    for n in range(8 * 6):
        jogo, fim = da_vez(inicio + datetime.timedelta(seconds=n * JANELA))
        vistos.append(jogo)
        assert fim == INICIO + datetime.timedelta(seconds=(n + 1) * JANELA)
    for c in range(6):  # cada ciclo mostra os 8, sem repetir
        assert sorted(vistos[c * 8:(c + 1) * 8]) == sorted(JOGOS)
    assert all(a != b for a, b in zip(vistos, vistos[1:]))  # nem na virada de um ciclo para o outro
    assert vistos[:8] != vistos[8:16]  # e a ordem muda de um ciclo para o outro
    svg = legenda("minesweeper", "escuro", False)
    assert "Campo Minado" in svg and "Minesweeper" in svg and TEMAS["escuro"]["ouro"] in svg
    assert legenda("pacman", "claro", True).count('height="44"') == 1
    print("ok")


if __name__ == "__main__":
    if sys.argv[1] == "--teste":
        teste()
        sys.exit()
    jogos, saida = sys.argv[1:3]
    os.makedirs(saida, exist_ok=True)
    jogo, fim = da_vez(datetime.datetime.now(datetime.timezone.utc))
    for tema in TEMAS:
        shutil.copy(os.path.join(jogos, f"{jogo}-{tema}.svg"), os.path.join(saida, f"jogo-{tema}.svg"))
        for celular, sufixo in ((False, ""), (True, "-celular")):
            with open(os.path.join(saida, f"legenda{sufixo}-{tema}.svg"), "w", encoding="utf-8", newline="\n") as f:
                f.write(legenda(jogo, tema, celular))
    with open(os.path.join(saida, "vez.json"), "w", encoding="utf-8") as f:
        json.dump({"jogo": jogo, "nome": JOGOS[jogo][0], "name": JOGOS[jogo][1], "ate": fim.isoformat()}, f, ensure_ascii=False)
    print(f"jogo da vez: {jogo} (até {fim:%d/%m %H:%M} UTC)")
