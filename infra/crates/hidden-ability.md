# Hidden Ability nas caixas

Chance escolhida pelo Dono: **1% (1 em 100)** por prêmio elegível, independentemente de ser normal ou shiny, nas nove gerações e na caixa mensal. A forma real deve ter uma habilidade do tipo HiddenAbility; espécies sem HA continuam com habilidade comum. A habilidade é sorteada antes de serializar/reservar o prêmio; recuperação e novas tentativas de entrega preservam o mesmo Pokémon e habilidade. Prêmios já salvos não são alterados.

## Referência conferida

Cobblemon instalado: 1.8.2. A geração padrão via PokemonProperties.create usa AbilityPool.select; HiddenAbility.isSatisfiedBy retorna false. Portanto esse caminho não tem uma taxa geral de HA. O arquivo original `data/cobblemon/spawn_bait_effects/berries/enigma_berry.json` declara `chance: 0.05` para `cobblemon:ha_chance`; é uma condição de isca, não uma taxa geral. A wiki oficial confirma 5% para Enigma Berry: https://wiki.cobblemon.com/index.php?title=Seasoning . Após essa distinção, o Dono escolheu explicitamente **1%** para as caixas.

## Verificação

`crateAbilityPolicyTest` verifica exatamente um resultado vencedor entre os 100 possíveis, todos os resultados inelegíveis e limites inválidos. `crateSpinTimelineTest` mantém as garantias da roleta e do fechamento automático. Compilação/remapeamento conferem a API da versão instalada. Instalação exige o script `infra/security/deploy-crate-ha.py --apply`; teste real em jogo ainda necessário.
