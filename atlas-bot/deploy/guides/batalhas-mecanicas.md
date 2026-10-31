## ⚔️ Batalhas — referência da Staff
**Cobblemon 1.8.2 / regras competitivas atuais do Atlas • 24/10/2026**
Uma batalha depende de tipos, atributos, golpes, habilidades, itens, clima, terreno e formato. Antes de chamar algo de bug, identifique o contexto completo.
**Selvagem, NPC, jogador casual, torneio e desafio ranqueado não são automaticamente o mesmo formato.** Pokémon de raid e formas de complementos podem ter outras regras.

O Atlas usa formatos competitivos **Gen 9** para OU, UU, Monotype, Ubers e AG, com validação automática no fluxo protegido. Isso não significa que todo encontro casual aplique essas cláusulas nem que o servidor inteiro seja idêntico a um site externo.

A tabela de 18 tipos anexada foi gerada do simulador instalado. Tipos da espécie e forma importam; Mega/Terastal e efeitos podem mudar o contexto. Material de atendimento conferido em dados/código, sem teste manual de todas as combinações.

## 🔥 Tipos e multiplicadores
**Super efetivo:** normalmente 2× contra um tipo; dois fatores favoráveis podem produzir 4×.
**Resistido:** normalmente 0,5×; duas resistências podem produzir 0,25×.
**Imune:** 0× pela relação de tipos quando nenhuma exceção a altera.

Exemplos básicos:
• Fogo contra Grama/Inseto → 4×.
• Elétrico contra Água/Terra → imunidade por Terra, não 2× só por ser Água.
• Terra contra Voador → imunidade por tipo, sujeita a efeitos que alterem o contexto.
• Normal e Lutador contra Fantasma → imunidade normal, com exceções de habilidades/efeitos.
• Dragão contra Fada → imunidade normal.

**STAB:** usar golpe do próprio tipo costuma dar bônus de 1,5×; habilidades e Terastal podem alterar a regra. Não é o mesmo bônus de super efetivo.
A tabela indica interação de tipos, não quantos HP serão perdidos: poder do golpe, atributos, clima, crítico e variação de dano ainda importam. “Mesmo golpe” não garante dano idêntico em todas as tentativas.

## 🥊 Físico, especial e golpes de status
**Físico:** geralmente usa Ataque contra Defesa.
**Especial:** geralmente usa Ataque Especial contra Defesa Especial.
**Status:** aplica efeito, preparação ou mudança de estado; não é definido por causar dano.
Há golpes com regras especiais, então consulte o golpe específico em caso de exceção. O tipo do golpe não determina sozinho se é físico ou especial.

**Estágios:** modificadores temporários de batalha, normalmente entre −6 e +6; são diferentes de EVs e IVs. Habilidades como Unaware e golpes críticos têm interações próprias.
**Accuracy/Evasion:** um golpe pode errar por precisão, evasão, condição, proteção ou imunidade. “100 de precisão” não é licença para ignorar todos os efeitos.
**Protect/Substitute:** não bloqueiam de forma idêntica todo golpe ou efeito. Não aplique uma regra genérica a ataques que têm exceções declaradas.

## ⏱️ Ordem de ação
A ordem não é só nível ou Velocidade exibida. Considere **prioridade do golpe**, Velocidade efetiva, habilidades, item, clima, paralisia, Tailwind e Trick Room.
**Prioridade:** um golpe com prioridade pode agir antes de um adversário mais rápido; habilidades e bloqueios podem interferir.
**Trick Room:** altera a ordem de Velocidade dentro das condições da mecânica; não coloca automaticamente todos os golpes de prioridade por último.
**Empate de Velocidade:** pode produzir resultados diferentes; um turno isolado não prova erro.
**Choice Scarf**, clima e habilidades podem explicar por que um Pokémon aparentemente lento agiu antes.

**Coleta para SUP:** ambos os Pokémon/formas, golpes usados naquele turno, itens, habilidades e efeitos ativos. Não peça apenas o nível.
**Resposta útil:** “Vamos comparar prioridade e Velocidade efetiva, incluindo item e efeitos, antes de concluir que a ordem estava incorreta.”

## 😴 Status, clima e terreno
**Paralisia:** normalmente reduz Velocidade e pode impedir uma ação.
**Queimadura:** causa dano residual e normalmente reduz dano físico; habilidades/golpes têm exceções.
**Veneno/veneno grave:** causam dano residual; o grave tem progressão própria.
**Sono/congelamento:** afetam a capacidade de agir, com duração e saídas próprias. Não prometa que dormir significa perder um número fixo de turnos em todos os formatos.

**Clima e terreno são diferentes.** Chuva de batalha não é a mesma condição que chuva no mundo para uma evolução. Terrain normalmente tem relação com estar no chão; não assuma que afeta igualmente todo Pokémon.
Imunidades por tipo, habilidade, item ou efeito podem impedir status; um golpe recusado não é necessariamente falha.
No competitivo, cláusulas de sono variam por tier: OU/UU usam a regra de golpes de sono do snapshot instalado; não aplique uma única explicação de Sleep Clause a todos os formatos. Se o sistema bloquear, preserve a mensagem e confira a tier.

## 🏆 Torneio versus ranking no Atlas
**Torneio:** inscrições de 8 ou 16, prazo definido pela staff e chaves no Challonge. Resultados e organização externa têm operação própria; não prometa atualização automática de toda vitória no site.
**Ranking:** desafio entre jogadores por `/ranked desafiar <jogador> <tier>` e aceite com `/ranked aceitar <jogador>`. Apenas esse fluxo aceito pontua no ranking PvP; casual, NPC, selvagem e torneio não ganham Elo por serem batalhas.
**`/rankstaff` é outro ranking:** conta atendimentos de tickets, não vitórias de Pokémon.

No protegido Gen 9, o servidor valida a equipe e mantém cláusulas durante o combate. Há bloqueios para mecânicas proibidas, itens de mochila e alterações externas. Monotype tem restrição de Terastal no formato instalado. Não generalize a disponibilidade de Mega/Z/Dynamax de complementos para esses confrontos.

Uma forma existir no mod não garante que seja legal em OU. Ubers/AG não significam “qualquer dado inventado” ou dispensa de toda validação. Siga a resposta do formato e a mensagem emitida pelo sistema.

## 🚫 Equipe recusada, batalha anulada ou sem pontos
**Antes de iniciar:** confirme tier, espécie/forma, habilidade, golpes, itens, nível e distribuição de EVs/IVs. Dados desconhecidos ou combinação incompatível podem bloquear o confronto. Não troque apenas o nome da tier para contornar uma regra.
**Durante:** não altere a equipe original, item ou atributos por ferramenta externa. Efeitos legítimos dentro da batalha são tratados pelo combate; mudanças externas podem anular o confronto protegido.
**Sem Elo:** confira se era desafio ranqueado aceito e se houve resultado nativo confirmado. Parada administrativa, anulação ou resultado sem confirmação não deve virar vitória manual por suposição.

O sistema de validação não aplica automaticamente punição disciplinar nem declara WO em toda falha. Se houver suspeita de abuso, a moderação analisa com evidências e segundo avaliador.
**SUP:** reúne os dados e mensagens; **MOD:** confere contexto e regras; **ADM/organização:** decide encaminhamento técnico ou revisão. Não prometa pontos ou prêmio antes da verificação.

## 🧾 Modelo para investigar uma batalha
**Contexto:** casual, NPC, selvagem, raid, torneio ou ranked; tier se houver.
**Momento:** horário com fuso e turno aproximado.
**Equipes envolvidas:** espécies/formas relevantes, níveis, golpes, habilidade e item. Não publique equipes privadas fora do espaço necessário à análise.
**Estado:** HP, status, modificadores, clima, terreno e proteções.
**Esperado versus observado:** descreva o efeito e a mensagem exata, sem acusação.
**Evidência:** imagem ou vídeo do trecho; evite divulgar dados pessoais.

Não peça senha nem use comandos para alterar Pokémon como teste. Se reproduzir, use ambiente controlado e autorização adequada, preservando o original do jogador.

**Fontes:** simulador e dados do Cobblemon instalados, regras competitivas atuais do Atlas. Referência oficial do mod: https://gitlab.com/cable-mc/cobblemon
Esta referência não representa teste em jogo de cada habilidade, golpe, item, formato ou complemento.
