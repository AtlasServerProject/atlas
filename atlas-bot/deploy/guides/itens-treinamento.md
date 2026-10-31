## 🎒 Itens — usar, segurar e consumir
**Cobblemon 1.8.2 • referência de 24/10/2026**
**Item de uso:** aplicado ao Pokémon ou escolhido pelo fluxo do item; não precisa funcionar só por ficar na mochila.
**Item segurado:** precisa estar equipado no exemplar. Levar Leftovers no inventário não cura o Pokémon como se estivesse segurando.
**Consumível:** pode desaparecer ao cumprir seu efeito. Não trate consumo esperado como perda por bug.

Um item existir no cadastro não garante receita, venda ou drop disponível no Atlas. Confira o item exato, a origem e o que a interface permite. Complementos de Mega, TM e reprodução não devem ser explicados como se todos os seus efeitos fossem do Cobblemon base.

**Pergunta inicial:** “Qual item você usou, em qual Pokémon, equipado ou por interação, e qual mensagem apareceu?”
Itens de evolução já têm catálogo próprio na conversa de Evoluções específicas. Este módulo aborda atributos, experiência e combate.

## 📊 Nível, IV, EV e Nature não são a mesma coisa
**Nível:** progressão por experiência. No Atlas, o limite configurado é 100. Mesmo nível não significa mesmos atributos.
**IVs:** valores de origem de cada atributo, normalmente entre 0 e 31. **6×31** significa seis IVs originais máximos; **F3** não significa 6×31.
**EVs:** treinamento por atributo; limite padrão validado no competitivo: **252 por atributo e 510 no total**. Não é possível colocar 252 nos seis.
**Nature:** normalmente aumenta um atributo em 10% e reduz outro em 10%; Natures neutras não mudam esses atributos. Não altera HP por Nature.
**Estágios de batalha:** aumentos/reduções temporários, diferentes dos EVs. Swords Dance não acrescenta EV permanente.

O motor também distingue IV original de IV efetivo de treinamento. Não diga que um ajuste efetivo reescreveu os IVs de origem ou que será herdado por reprodução sem conferir. A presença desse mecanismo não certifica a disponibilidade de todo item de Hyper Training no modpack.

## 🌿 Mints — efeito e exemplo
A mint define a **Nature efetiva dos atributos**, separada da Nature original registrada no Pokémon. Não prometa que muda gênero, habilidade, IVs, shiny ou forma evolutiva.
**Adamant:** favorece Ataque e reduz Ataque Especial.
**Modest:** favorece Ataque Especial e reduz Ataque.
**Jolly:** favorece Velocidade e reduz Ataque Especial.
**Timid:** favorece Velocidade e reduz Ataque.
**Bold:** favorece Defesa e reduz Ataque.
**Calm:** favorece Defesa Especial e reduz Ataque.
**Serious:** efeito neutro.

Não escolha uma Nature só pelo Pokémon “ser forte”; considere golpes e função. O arquivo anexado traz os **25 perfis de Nature**; isso não quer dizer que existam 25 itens diferentes de mint.
A base possui, por exemplo, receita da Adamant Mint com **três Red Mint Leaf e uma Cyan Mint Leaf**, em arranjo 2×2. Confira a receita em jogo, pois posição e item importam.
**Caso:** Toxel pode ter requisito da Nature original para a evolução; uma mint não deve ser prometida como troca automática dessa condição.

## 💪 Vitaminas, penas, bagas e Power Items
**Vitaminas da base:** HP Up → HP; Protein → Ataque; Iron → Defesa; Calcium → Ataque Especial; Zinc → Defesa Especial; Carbos → Velocidade. As descrições indicam **+10 EVs**, respeitando limites e condições de uso.
**Penas de treino:** Health, Muscle, Resist, Genius, Clever e Swift correspondem aos mesmos seis atributos; descrições indicam **+1 EV**. Fairy Feather é um item de combate diferente, não uma dessas penas de EV.
**Bagas de redução:** Pomeg/Kelpsy/Qualot/Hondew/Grepa/Tamato reduzem EVs de HP/Ataque/Defesa/Ataque Especial/Defesa Especial/Velocidade, respectivamente. Confira o efeito e se o uso ainda é válido.
**Power Items:** são segurados; a descrição de Power Weight, por exemplo, prevê EVs extras de HP ao ganhar experiência em batalha. Não basta carregá-lo na mochila.

Se o item não subir um atributo visivelmente, verifique limite de EV, Nature, nível e arredondamentos antes de afirmar falha. Não recomende repetição cega que gaste todo o estoque do jogador.

## 🍬 Experiência e PP
**Rare Candy:** aumenta um nível quando o uso é válido; não promete seis IVs perfeitos nem uma habilidade específica.
**Exp. Candy:** XS **100**, S **800**, M **3.000**, L **10.000**, XL **30.000** pontos de experiência nas descrições da base. Isso não é uma quantidade fixa de níveis para qualquer espécie/nível.
**Exp. Share:** item segurado para receber parcela da experiência sem participar. Não prometa que qualquer membro no PC receberá ou que todos ganham a mesma parcela.
**PP Up:** aumenta em 20% o PP-base do golpe escolhido, até o limite de 60%.
**PP Max:** leva ao máximo permitido, não soma outros 60% sobre um PP já maximizado. Arredondamento e golpes com restrição podem influenciar.

Restaurar PP atual e aumentar PP máximo são ações diferentes. **Ether/Elixir** não são automaticamente a mesma coisa que PP Up. Confira golpe, PP atual/máximo e item antes de orientar novo gasto.

## 🛡️ Itens segurados — situações frequentes
**Leftovers:** recuperação gradual em batalha.
**Life Orb:** aumenta dano de golpes e normalmente cobra HP; é diferente de golpe que causa recoil por si só e há exceções.
**Choice Band/Specs/Scarf:** favorecem Ataque/Ataque Especial/Velocidade, mas normalmente prendem a escolha de golpe enquanto o efeito se aplica. “Não consigo escolher outro golpe” pode ser esperado.
**Focus Sash:** depende de HP cheio para sobreviver a um golpe que nocautearia; múltiplos acertos e dano residual podem derrubar depois. Não é proteção permanente.
**Eviolite:** beneficia defesas quando a espécie pode evoluir; não é um bônus universal.
**Assault Vest:** aumenta Defesa Especial, mas limita escolha de golpes de status.
**Oran/Sitrus:** curam sob condição de HP; **Lum** interage com status/confusão. Não espere ativação de toda baga no mesmo contexto.

**Everstone:** impede evolução enquanto seu efeito vale. **Exp. Share** não é item de cura. No caso de bug, registre o item que estava realmente equipado no início e no momento do efeito.

## 🧾 Item não funcionou ou desapareceu
**SUP:** identifica item exato, Pokémon, uso/equipamento, batalha, mensagem, quantidade anterior/depois e o efeito esperado.
**MOD:** confere consumo normal, condição de ativação, troca de item e regras da batalha antes de suspeitar de abuso.
**ADM:** investiga problema reproduzível ou complemento/receita envolvido; restauração somente com decisão e registro.

No competitivo protegido do Atlas, itens de mochila são bloqueados pela regra da batalha. Item segurado e item usado da mochila são mecanismos diferentes. Não recomende contornar a trava com outro comando ou mudar a equipe durante o confronto.

Não anuncie como disponível uma receita de outro modpack. Não prometa que toda cápsula reverte HA, que mint altera Nature original, que PP Max dá PP infinito ou que item consumido sempre voltará após a batalha.
**Fontes:** descrições, receitas e classes de itens do Cobblemon instalado, simulador e regras atuais do Atlas. Referência oficial: https://gitlab.com/cable-mc/cobblemon
