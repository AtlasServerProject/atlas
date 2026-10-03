# Atlas-bot

Base do bot oficial do Discord Atlas, em Node.js 24.17+ e discord.js. Usa comandos de barra e o intent `Guilds` e, para boas-vindas, `GuildMembers`; não precisa ler mensagens dos membros. A conexão usa Gateway e não exige porta pública.

## Funcionalidades

| Comando | Função |
| --- | --- |
| `/ping` | Latência do bot, sem afirmar que o Minecraft está online |
| `/ajuda` | Lista de comandos |
| `/servidor` | Endereço configurado do Minecraft |
| `/como-jogar` | Orientação inicial e link do modpack; guia ainda em rascunho |
| `/estrutura` | Prévia dos canais e cargos |
| `/estrutura confirmar:true` | DONO cria elementos ausentes |
| `/aviso texto:...` | DONO publica no canal de avisos configurado |

A estrutura propõe categorias de informações e comunidade, canais de boas-vindas, regras, avisos, como-jogar, geral, dúvidas e sugestões. Cria os cargos `Treinador` e `Avisos Atlas`, sem privilégios ou atribuição automática. Reaproveita e renomeia as categorias padrão e os canais geral/Geral para a identidade Atlas, preservando suas permissões; não exclui canais. Canais alheios à estrutura são preservados. Os canais novos de informação impedem mensagens e threads de membros comuns. A criação parcial pode ser retomada com o mesmo comando. Executar uma única instância do bot evita criações concorrentes.

Mensagens não notificam `@everyone`, cargos ou usuários. Os comandos administrativos exigem o ID exato do DONO e o ID do canal exclusivo em cada execução. Outros administradores são recusados. Todos os comandos ficam restritos ao servidor configurado. Sem esses dois IDs, a administração fica desabilitada.

## Configurar e instalar no Discord

1. No [Discord Developer Portal](https://discord.com/developers/applications), crie a aplicação **Atlas-bot** e obtenha o token na seção Bot. Não envie o token pelo chat ou coloque no Git.
2. Copie o Application ID. Ative o modo desenvolvedor do Discord e copie o ID do seu servidor.
3. Em Installation/OAuth2, gere o link de instalação para servidor com os escopos `bot` e `applications.commands`. Permissões: **View Channels**, **Send Messages**, **Manage Channels** e **Manage Roles**. Não é necessário conceder Administrator ao bot. Mantenha o cargo do bot acima dos cargos que ele deverá criar/gerenciar.
4. Abra o link e instale no seu servidor usando uma conta com permissão. O convite comum `discord.gg` não instala bots.
5. Prepare o arquivo local protegido:

```bash
cd /home/somente/dev/atlas/atlas-bot
npm ci
mkdir -p /home/somente/.config/atlas
install -m 600 .env.example /home/somente/.config/atlas/discord-bot.env
```

O comando `install` acima é apenas para a primeira configuração: não sobrescreva um arquivo já preenchido. Edite esse arquivo localmente com token, Application ID e Guild ID. Endereço e link do modpack são opcionais; valores ausentes aparecem como não configurados.

Registre os comandos e inicie:

```bash
node --env-file=/home/somente/.config/atlas/discord-bot.env src/register.js
node --env-file=/home/somente/.config/atlas/discord-bot.env src/index.js
```

O registro atualiza os oito comandos por nome apenas no servidor configurado, sem apagar comandos de outros módulos. Para desenvolvimento, pode usar `.env` (ignorado pelo Git) e `npm run register` / `npm start`.

Execute `/estrutura` para revisar e `/estrutura confirmar:true` quando quiser criá-la. Depois copie o ID do canal `avisos` para `DISCORD_ANNOUNCEMENTS_CHANNEL_ID` e reinicie o bot. Texto de regras/boas-vindas e atribuição de cargos ainda dependem da definição da equipe.

## Avisos do Minecraft

Integração opcional via `POST http://127.0.0.1:8787/events`. Só é iniciada quando `ATLAS_BRIDGE_SECRET` (32 caracteres ou mais) e o canal de avisos estão configurados. Gere a chave localmente, por exemplo com `openssl rand -hex 32`, e armazene no arquivo protegido. Não é o token do Discord.

O endpoint exige `Authorization: Bearer <chave>` e `Content-Type: application/json`, limita corpo a 8 KiB, mensagem a 1.500 caracteres e aceita no máximo um evento a cada dois segundos. Retorna 202 após publicar; 400 para evento inválido, 401 sem autenticação, 413 para corpo excessivo, 429 para limite e 503 se não publicar. Não possui fila persistente ou retentativas automáticas.

Formato: `{"type":"started","message":"O Survival está disponível."}`. Tipos aceitos: `started`, `stopping`, `maintenance`, `announcement`.

Um script local de operação do Minecraft pode chamar:

```bash
node --env-file=/home/somente/.config/atlas/discord-bot.env src/notify.js announcement 'Manutenção programada às 22h.'
```

Para processos separados, forneça ao emissor apenas `ATLAS_BRIDGE_SECRET` e `ATLAS_BRIDGE_PORT`. Não exponha o endpoint publicamente. Esta entrega prepara o receptor e o emissor; ainda não conecta automaticamente os eventos do atlas-core nem altera o serviço Minecraft. Não executa comandos administrativos no jogo e não espelha o chat.

## Serviço e validação

Modelo de serviço **do usuário**, ajustado para o host atual, em `deploy/atlas-bot.service`. Depois de configurar e testar a conexão:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/atlas-bot.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now atlas-bot
journalctl --user -u atlas-bot -n 50
```

Para iniciar mesmo sem sessão aberta, o usuário precisa ter linger habilitado no host. Serviço instalado e habilitado neste host em 30/09/2026; conexão ao Discord confirmada.

Validação local: `npm run check` e `npm test`. Os testes não conectam ao Discord. Aceite pendente no servidor: instalação, comandos, permissões reais, estrutura sem duplicações e publicação de aviso. Não existe banco de dados nesta versão.

## Console exclusivo do DONO

Crie manualmente um canal de texto privado, por exemplo `atlas-controle`: negue **View Channel** a `@everyone` e permita acesso à sua conta e ao bot (View Channel e Send Messages). Administradores do Discord sempre podem ignorar restrições de visibilidade; mesmo assim, o bot recusa comandos de qualquer outra conta. Configure `DISCORD_OWNER_ID` com o ID da sua conta e `DISCORD_OWNER_CHANNEL_ID` com o ID desse canal e reinicie o bot. Nenhum outro cargo é considerado dono.

No canal exclusivo:

- `/dono canal nome:bate-papo tipo:Texto` cria canal de texto.
- `/dono canal nome:Equipe tipo:Voz` cria canal de voz.
- A opção `categoria` faz o novo canal herdar as permissões da categoria. Sem categoria, vale o acesso padrão do servidor.
- `/dono cargo nome:Moderador` cria cargo sem privilégios iniciais.
- `/dono atribuir membro:@Pessoa cargo:@Moderador` atribui um cargo existente.
- `/dono permissao cargo:@Moderador permissao:ManageMessages permitir:true` concede a permissão ao cargo.
- Com `canal`, a mesma operação altera uma sobrescrita apenas naquele canal. `permitir:false` nega nesse canal; sem canal, remove o bit do cargo, mas outros cargos ainda podem concedê-lo.

As alterações são imediatas após o envio do comando. O registro de auditoria do Discord identifica o bot e inclui o ID do dono como motivo nas operações de `/dono`. Não há exclusão de canais/cargos, banimentos, execução de código ou interpretação de linguagem natural nesta versão. O bot não concede `Administrator` pelo comando de permissões. Para delegar uma permissão, o próprio bot precisa tê-la e respeitar a hierarquia dos cargos; habilite somente as permissões que pretende administrar. O canal do dono e sua categoria não podem ser alterados diretamente pelo comando de sobrescritas.

`/estrutura` e `/aviso` também exigem a conta do DONO no canal exclusivo. O rascunho de estrutura não cria o canal privado automaticamente, pois ele é o ponto inicial de controle. A interação inicial é totalmente por comandos de barra e respostas privadas; conversa livre será uma etapa separada.

## Organização aplicada em 30/09/2026

Bot instalado no Atlas Cobblemon, oito comandos registrados e canal do dono protegido. Categorias: 📌 ATLAS • INFORMAÇÕES, 🌿 ATLAS • COMUNIDADE e 🔊 ATLAS • VOZ. Canais de texto: boas-vindas, regras, avisos, como-jogar, geral, duvidas, sugestoes, aventuras e trocas. Voz: Praça Emerald, Exploração e Batalhas. Cargos criados sem privilégios: Treinador (verde) e Avisos Atlas (amarelo). Canal de avisos configurado no arquivo externo. Segunda execução confirmou ausência de duplicações. Nenhuma mensagem de regras, anúncio ou boas-vindas foi publicada automaticamente. Integração de eventos Minecraft continua opcional.

## Boas-vindas automáticas

`DISCORD_WELCOME_CHANNEL_ID` seleciona o canal. Ao entrar um membro humano no Discord configurado, o bot publica uma mensagem verde com avatar, menção apenas ao novo membro e links de regras/como-jogar. Bots são ignorados; membros existentes não recebem mensagens retroativas. Requer Server Members Intent habilitado no Developer Portal → Bot → Privileged Gateway Intents e reinício do serviço após habilitar. Sem essa autorização, o bot mantém os comandos ativos e registra que boas-vindas estão pendentes. Não corresponde à entrada no Minecraft. Teste local validado; intent já ativado; teste de entrada real pendente.

## Cargo automático

`DISCORD_MEMBER_ROLE_ID` aponta para o cargo Membro. Novos membros humanos recebem esse cargo no evento de entrada, independentemente do envio das boas-vindas. Não remove cargos existentes, ignora bots e não aplica retroativamente a membros antigos. Requer GuildMembers e cargo abaixo do Atlas-bot. Configurado e implantado em 30/09/2026; testes locais passaram, entrada real ainda precisa ser observada.

## Contador Minecraft

O status do Atlas-bot mostra `Minecraft: N/50 online`, consultado a cada 30 segundos (mais o tempo de consulta). `/online` responde em privado com a contagem e horário da consulta; cache de 10 segundos e consultas simultâneas compartilhadas. Falhas mostram indisponível, nunca zero fictício. Usa o status TCP Java em `MINECRAFT_STATUS_HOST` (padrão 127.0.0.1) e `MINECRAFT_STATUS_PORT` (25565), timeout de 5 segundos; não usa RCON nem modifica o Minecraft. Conta jogadores de todos os mundos dessa instância. Não agrega servidores separados. A atividade some quando o bot está offline. Dependência minecraft-server-util 5.4.4 fixada (projeto sem manutenção upstream); troca futura deve preservar consulta local. Implantado em 30/09/2026, consulta real 0/50; 12 testes passaram.

## Categoria STATUS

Categoria STATUS acima de Informações, com três canais de voz visíveis e conexão negada a @everyone: membros do Discord (inclui bots), endereço público configurado e jogadores Minecraft. Atualização serial a cada 310 segundos, renomeando somente quando muda, para reduzir alterações de nomes e respeitar limites da API. `/online` e a atividade do bot continuam disponíveis com maior frequência. Falha na consulta Minecraft mostra indisponível; se o bot parar, os nomes permanecem na última leitura. Endereço omitido por decisão do dono. Não publica mensagens no chat.

## Estado de entrega e publicação

Em 30/09/2026, o bot está ativo no serviço de usuário atlas-bot.service. Server Members Intent foi ativado e a conexão confirmada. Entradas humanas recebem boas-vindas e cargo Membro, sem processamento retroativo. Cargos visuais DONO, ADM, MOD, SUP, VIP, BETA e Membro criados, sem poderes administrativos adicionais. SUP usa o verde do Minecraft e BETA usa roxo.

STATUS está acima de Informações, com contadores Discord e Minecraft. Por decisão do dono, o canal de endereço deve ser retirado enquanto o site não está pronto (remoção via API recusada com Missing Access; pendente no Discord); a configuração vazia não recria esse canal. Nenhum domínio público foi presumido.

Validações: 13 testes locais, consulta Minecraft real e bot conectado. Aceite em entrada real e interação dos comandos pelo dono permanece pendente. Não há conversa livre, sincronização de ranks Minecraft/Discord, atribuição retroativa ou eventos Minecraft conectados automaticamente. O serviço usa systemd do usuário e linger ainda não está habilitado; execução após encerrar todas as sessões depende da configuração do host.

O código está em atlas-bot/ dentro do repositório principal atlas, não em um submódulo separado. Credenciais ficam exclusivamente em ~/.config/atlas/discord-bot.env, com modo 600.
