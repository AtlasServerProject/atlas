# Warps Atlas

Implementação própria para Fabric 1.21.1, inspirada no comportamento documentado do EssentialsX, sem instalar Bukkit/Spigot ou copiar seu código.

Referências consultadas em 30/10/2026:
- [Comandos e permissões oficiais](https://github.com/EssentialsX/Essentials/blob/2.x/Essentials/src/main/resources/plugin.yml): warp, setwarp, delwarp.
- [Configuração oficial](https://github.com/EssentialsX/Essentials/blob/2.x/Essentials/src/main/resources/config.yml): per-warp-permission, teleport-safety, teleport-delay, teleport-cooldown.

## Jogadores

| Comando | Função |
| --- | --- |
| `/warp` ou `/warps` | Menu paginado com ícones dos destinos permitidos. |
| `/warp <nome>` | Viajar para um destino. Autocompletar mostra apenas os disponíveis. |
| `/warp cancelar` | Cancelar o preparo de uma viagem. |

Login e regras aceitas são obrigatórios. Saia do Hub de autenticação pelo NPC/bússola antes de usar warps. O Hub e mundos de desenvolvimento não podem ser cadastrados como destino.

O preparo dura 3 segundos. Movimento acima de 0,1 bloco, dano, morte, desconexão, mudança de dimensão, início de batalha, congelamento, StaffMode, montaria/cama ou outro teleporte pendente cancelam a viagem. Apenas um warp por jogador pode ficar pendente. O intervalo de 10 segundos começa somente após o teleporte confirmado; cancelamentos não cobram cooldown. Girar a câmera não cancela.

O destino exato é preferido. Se obstruído, procura uma posição segura até 3 blocos ao redor e 2 na vertical; sem local seguro, cancela. Verifica chão, altura, borda, colisões, líquidos, fogo e outros blocos perigosos. A direção da câmera é preservada conforme o cadastro. O serviço existente de `/back` recebe a posição de origem.

## Administração

ADM/Dono ou cargo com `atlas.warp.manage`, sempre autenticado e fora do Hub:

| Comando | Função |
| --- | --- |
| `/setwarp <nome>` | Criar ou atualizar a posição/direção onde você está. Atualizar mantém título, ícone, acesso e estado. |
| `/delwarp <nome>` | Excluir o destino. A versão anterior do arquivo fica no backup. |
| `/warpadmin <nome> nome <título>` | Alterar o título exibido no menu. |
| `/warpadmin <nome> icone <namespace:item>` | Usar um item existente como ícone. |
| `/warpadmin <nome> acesso publico` | Liberar aos jogadores autenticados. |
| `/warpadmin <nome> acesso vip` | Restringir a VIP ativo, administrador ou permissão específica. |
| `/warpadmin <nome> acesso staff` | Restringir a Staff, administrador ou permissão específica. |
| `/warpadmin <nome> acesso permissao` | Exigir `atlas.warps.<nome>` ou administração. |
| `/warpadmin <nome> estado desativado` | Ocultar e impedir viagens, inclusive as pendentes. |
| `/warpadmin <nome> estado ativado` | Reativar. |

Nomes: 1–24 letras/números ASCII, `_` ou `-`; são normalizados para minúsculas. `cancelar` é reservado. Títulos têm até 64 caracteres e não aceitam códigos de formatação. Editar, reposicionar, desativar ou excluir invalida solicitações antigas; o acesso é reconferido na conclusão. Operações administrativas são registradas no log do servidor com UUID do autor.

## Destinos iniciais

Apenas na primeira inicialização, cadastra `emerald`: atlas:emerald, X 1183.346, Y 81, Z 4094.55, yaw 180, pitch 0. Demais destinos devem ser marcados pela Staff na posição correta do lobby atual; não reutilizar coordenadas de construções antigas.

Exemplo, já posicionado na entrada de cada prédio:

```text
/setwarp caixas
/warpadmin caixas nome Caixas do Atlas
/warpadmin caixas icone minecraft:chest
/setwarp mercado
/warpadmin mercado nome Poké Mart
/warpadmin mercado icone minecraft:gold_ingot
/setwarp arena
/warpadmin arena nome Arena Atlas
/warpadmin arena icone minecraft:diamond_sword
/setwarp centro
/warpadmin centro nome Centro Pokémon
/warpadmin centro icone minecraft:beacon
/setwarp laboratorio
/warpadmin laboratorio nome Laboratório Pokémon
/warpadmin laboratorio icone minecraft:book
```

## Persistência e instalação

Arquivo: `config/atlas/warps.json` no diretório do Minecraft isolado. Leituras usam catálogo em memória. Alterações fazem escrita temporária + fsync + rename atômico, preservando `warps.json.bak`; erro de gravação não altera o catálogo. Arquivo inválido é preservado e desabilita o módulo, sem resetar dados. Limites: 1 MiB e 1000 destinos. Não há migração de banco nem mod novo para o cliente.

Instalação preparada em `infra/releases/atlas-warps-1.40.5-warp.1/`. Execute `sudo python3 infra/security/deploy-atlas-warps.py --apply` no diretório do projeto. Reinicia somente o Minecraft, faz backup do Core e do catálogo existente, preserva correções das caixas e não publica as alterações pendentes de autenticação. O script restaura o Core anterior se a checagem de inicialização falhar.

## Validação

`warpStoreTest`: nomes/coordenadas/dimensões inválidos, matriz de acesso público/VIP/Staff/permissão, desativação, persistência após reinício, revisão de destino, backup, JSON corrompido e falha de escrita. Regressão das caixas executada junto. A compilação verifica as APIs Fabric/Minecraft utilizadas. Testes reais de GUI, movimento, dano e teleporte ainda precisam ser feitos no servidor após instalar.
