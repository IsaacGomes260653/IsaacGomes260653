# Referências para o perfil do GitHub

Pesquisa feita em outubro de 2026 para guiar as mudanças no perfil. Os links ao vivo foram testados no dia 22/10/2026.

## 10 perfis de referência

| Perfil | O que faz de melhor | O que eu levo para o meu |
|---|---|---|
| [simonw](https://github.com/simonw) | README vivo: últimos releases, posts do blog e anotações se atualizam sozinhos por GitHub Actions, em três colunas. | Atualização automática que prova atividade real, gerada por Action e não por serviço de terceiros. |
| [tw93](https://github.com/tw93) | Uma frase de apresentação com os produtos que criou e números (seguidores, estrelas) atualizados por Action dentro do próprio texto. Logo abaixo, tabela com releases e posts recentes. | Dizer o que faço numa frase só, logo no topo. |
| [anuraghazra](https://github.com/anuraghazra) | Cabeçalho próprio, "sobre mim" com conquista concreta e repositórios fixados contando a mesma história (o github-readme-stats). | Banner próprio e coerência entre bio, README e fixados. |
| [cassidoo](https://github.com/cassidoo) | Texto curto com voz pessoal e uma lista de coisas que ela construiu, cada uma com link. Nenhum widget. | Projetos com link direto para abrir e testar. |
| [DenverCoder1](https://github.com/DenverCoder1) | Criador do readme-typing-svg e do streak-stats. Usa uma única animação de texto e põe a métrica mais forte logo depois da apresentação. | Uma animação só, com frases curtas. |
| [lowlighter](https://github.com/lowlighter) | Criador do metrics: painéis em SVG gerados por Action e guardados no próprio repositório. | Widgets que não caem porque não dependem de instância pública. |
| [Platane](https://github.com/Platane) | Criador do snk (a cobrinha): um único elemento animado, com versões clara e escura via `<picture>`. | Tema claro e escuro de verdade em cada imagem. |
| [felangel](https://github.com/felangel) | Referência de Flutter (Bloc, Dart Frog): poucos tópicos dizendo o que mantém e onde conversar com ele. | No mundo Dart/Flutter, o que você constrói fala mais do que badges. |
| [sindresorhus](https://github.com/sindresorhus) | README mínimo e bem-humorado. Funciona porque o trabalho público já convence. | Personalidade cabe, desde que o conteúdo sério esteja nos fixados. |
| [maykbrito](https://github.com/maykbrito) | Referência brasileira (Rocketseat): tópicos curtos com onde trabalha, o que publica e sobre o que perguntar. | Cargo e empresa atuais visíveis em uma linha. |

Também citados nas listas consultadas: [abhisheknaiidu](https://github.com/abhisheknaiidu) (curador da lista *awesome-github-profile-readme*), [MartinHeinz](https://github.com/MartinHeinz) (posts do blog puxados por Action) e [jh3y](https://github.com/jh3y) (projetos descritos pelo resultado, não pela tecnologia).

## Widgets e banners

### Valem a pena

| Widget | Por quê |
|---|---|
| Banner próprio em imagem, com versões clara e escura via `<picture>` | Identidade única e zero dependência externa: a imagem fica no repositório. |
| Cards gerados por GitHub Actions ([lowlighter/metrics](https://github.com/lowlighter/metrics), [github-profile-summary-cards](https://github.com/vn7n24fzkq/github-profile-summary-cards), [snk](https://github.com/Platane/snk)) | Rodam no meu repositório e salvam o SVG num branch. Não caem por limite de requisições. |
| Atividade recente automática | Mostra que o perfil está vivo sem eu precisar lembrar de atualizar. |
| Badges de contato do [shields.io](https://shields.io) numa cor só | Serviço estável, leve e legível no celular. |
| Um card de estatísticas e, no máximo, a sequência de contribuições | Para quem está começando, um card preenche espaço com dado real. Mais que isso vira painel. |
| Contador de visitas ([komarev](https://github.com/antonkomarev/github-profile-views-counter)) | Discreto e estável. Vale como curiosidade, não como argumento. |

### Poluem ou quebram

| Widget | Problema |
|---|---|
| Instâncias públicas na Vercel: [github-profile-trophy](https://github.com/ryo-ma/github-profile-trophy) e [github-readme-activity-graph](https://github.com/Ashutosh00710/github-readme-activity-graph) | Respondiam **402 Payment Required** no teste de 22/10/2026. Imagem quebrada é pior que nenhuma. |
| Instância pública do [github-readme-stats](https://github.com/anuraghazra/github-readme-stats) | O projeto original deixou de ser mantido e a instância pública já foi pausada antes. Só vale gerado por Action ou hospedado por conta própria. |
| Troféus em conta nova | Os níveis baixos chamam atenção para números pequenos. |
| Vários cards de estatística empilhados | Lê como template padrão e ocupa a primeira tela sem dizer nada sobre o trabalho. |
| Muro de badges de tecnologia sem projeto que comprove | Vira lista de palavras-chave. Recrutador procura o repositório que prova. |
| Animação de digitação com mais de 4 frases ou pausas curtas | Ninguém lê até o fim. |
| Spotify tocando agora, citações aleatórias, WakaTime | Não ajudam na decisão de quem está avaliando um júnior. |

## O que recrutadores mais valorizam

1. **Primeira tela clara em 15 a 30 segundos:** quem eu sou, cargo atual, stack principal e como falar comigo.
2. **Repositórios fixados com README de verdade:** o que o projeto faz, stack, como rodar, print ou demo ao vivo. A demo ao vivo é o maior ganho de credibilidade.
3. **Constância, não volume:** alguns commits por semana durante meses valem mais que um pico seguido de meses parados. Vale ativar a opção que mostra contribuições privadas no gráfico.
4. **Qualidade do processo:** mensagens de commit que explicam a mudança, pelo menos um teste e um workflow de CI.
5. **Ser encontrável:** localização, contato e tópicos nos repositórios (`flutter`, `dart`, `nextjs`...).
6. **Coerência:** bio, README, LinkedIn e fixados contando a mesma história.
7. **Nada de lixo em destaque:** forks sem contribuição, tutoriais clonados e projetos abandonados fora dos fixados.
8. **Seções atualizadas:** "aprendendo X" parado há meses e números sem data passam descuido.
9. **Contribuição em open source:** um PR aceito num projeto conhecido é difícil de falsificar e mostra aprovação de outros devs.
10. **Imagens que carregam no celular:** conferir o perfil numa tela estreita antes de considerar pronto.

## O que isso significa para o meu perfil

**Pontos fortes que já existem:** widgets gerados por Actions (não caem), roadmap de estudos feito sob medida, textos em português e inglês, temas claro e escuro.

**Lacunas encontradas:**

- Textos desatualizados (GONAR e RanchoControl como algo atual, ília como "em breve").
- Banner com gradiente roxo genérico, diferente da identidade do LinkedIn.
- Muitos widgets em sequência (estatísticas, sequência, linguagens, linhas de código, calendário, estrelas e o cantinho descontraído).
- Bio do GitHub antiga, sem empresa, localização e site.
- Repositórios que vão ser fixados sem tópicos, licença ou imagem de compartilhamento.

## Fontes

- [abhisheknaiidu/awesome-github-profile-readme](https://github.com/abhisheknaiidu/awesome-github-profile-readme)
- [Tópico awesome-github-profiles no GitHub](https://github.com/topics/awesome-github-profiles)
- [ReadmeDesign: Best GitHub Profile README Examples 2026](https://readmedesign.com/blog/best-github-profile-readme-examples) (atualizado em ago/2026)
- [ReadmeDesign: What Tech Recruiters Actually Look for in a GitHub Profile](https://readmedesign.com/blog/what-recruiters-look-for) (atualizado em ago/2026)
- [DevBio: GitHub Profile README Examples 2026](https://devbio.me/blogs/github-profile-readme-examples-2026) (jun/2026)
- [DEV Community: Top GitHub Profile Tools and Stats Generators (2026)](https://dev.to/_d7eb1c1703182e3ce1782/top-github-profile-tools-and-stats-generators-2026-2h3h)
- [Instahyre: GitHub Profile Checklist 2026](https://resources.instahyre.com/blog/github-profile-checklist/)
- [Placement Preparation: GitHub Profile & Portfolio Guide (2026)](https://www.placementpreparation.io/blog/github-profile-portfolio-guide/)
- [Issue #4747 do github-readme-stats sobre hospedar por Actions](https://github.com/anuraghazra/github-readme-stats/issues/4747)

Vários desses artigos são de empresas que vendem geradores de perfil. Por isso, as recomendações acima só entraram quando apareciam em mais de uma fonte ou quando deu para conferir direto no perfil citado.
