# Atlas Launcher 0.4.0

Aplicativo desktop independente para Atlas Cobblemon. Interface baseada na referência fornecida: login com arte lateral, menu compacto, Início, Modpack, Servidores, Conta, Configurações e Atualizações. Mantém a marca e os assets do Atlas.

## Executável Windows para teste

Pacote Windows x64: `/home/somente/downloads/Atlas-Launcher-0.4.0-Windows-x64.zip`.

Extraia **todo o ZIP** e abra `AtlasLauncher.exe`. Preserve as DLLs e a pasta `resources` ao lado do executável. Node.js não é necessário no computador do jogador. Este é um pacote executável de prévia, sem instalador, assinatura Authenticode ou atualizador do aplicativo. Não foi executado em Windows nesta sessão; a validação nativa ainda é necessária. Não desative proteções do Windows para abri-lo.

Download e instalação de Minecraft 1.21.1, Fabric 0.18.0, Java 21 e 57 mods estão integrados. O fluxo Microsoft e a inicialização estão implementados, mas o login real depende do Client ID próprio do Atlas e de validação em Windows. **Conhecer o launcher** abre a navegação sem criar sessão. Contagens de jogadores, notícias e versões instaladas não são simuladas. Emerald é apresentado como lobby do Atlas, sem inventar endereço de outro servidor.

## Desenvolvimento

Requisitos: Node.js 22.12+ e npm; Java 21 para o backend. Windows é a plataforma inicial de distribuição. Na pasta `atlas-launcher`:

```bash
npm ci
npm run dev
```

Vite usa `127.0.0.1:5179`. React tem recarga automática; alterações em main/preload exigem reiniciar. Electron 45 baixa seu binário no primeiro `npm run setup`; dev/start executam esse preparo automaticamente. Não use `--no-sandbox`.

Build local e geração Windows:

```bash
npm run build
npm start
npm run package:windows
```

O empacotamento usa `@electron/packager` 20.4.0, Electron 45.0.0, runtime Windows x64 com checksums verificados, código em ASAR e ícone Atlas. A saída fica em `artifacts/windows/Atlas Launcher-win32-x64`. Empacotar não cria uma assinatura de distribuição.

## Backend separado

O backend continua na fundação 0.1.0, sem alterações na API do site ou bancos do servidor:

```bash
cd services/backend
./mvnw spring-boot:run
```

No Windows use `mvnw.cmd`. Escuta somente `127.0.0.1:8091`, sem MySQL nesta fase. Não precisa estar aberto para explorar a interface.

## Verificação

```bash
npm run typecheck
npm test
npm run build
npm run format:check
npm audit
cd services/backend
./mvnw verify
```

Preferências RAM/resolução/tela cheia/minimização são persistidas localmente com validação no processo principal. São aplicadas ao iniciar o jogo. O renderer não acessa arquivos, credenciais, shell ou comandos arbitrários. Controles da janela usam IPC restrito.

## Documentação

- [Arquitetura](docs/architecture.md)
- [Execução e limitação do sandbox Linux](docs/development.md)
- [API](docs/api.md)
- [Manifestos futuros](docs/manifest-spec.md)
- [Segurança](docs/security.md)
- [Verificações](docs/verification.md)

Próximos passos: cadastrar o aplicativo Microsoft, validar login e jogo em Windows e preparar distribuição assinada. Sem conta oficial autenticada, Jogar permanece bloqueado.

## Versão 0.4.0

- Ícone Windows e favicon derivados da logo oficial Atlas, substituindo o favicon Angular herdado. A interface usa máscara circular e composição com o fundo para eliminar o quadrado da logo sem alterar a arte original.
- Site: https://www.atlascobblemon.com.br. Endereço Minecraft informado pelo administrador: `stapling-gpo.tun.ply.gg`.
- Vídeos locais Milotic, surf e farol reaproveitados de `atlas-web/public/media`. Loop sem áudio, posters de reserva, controles de pausa e respeito à redução de movimento/visibilidade. Vídeos incluídos no pacote: não dependem do site estar acessível. São cenas ilustrativas do Cobblemon, não capturas do servidor Atlas.
- Fundação da fase 3 em `src/main/modpack`: validação de envelope Ed25519, schema, origens, caminhos Windows, SHA-256 e planejamento por arquivo. Release real 1.0.2-beta.2 assinada, com 56 mods de fontes oficiais e Atlas Interface 1.1.1 incluído.

## Instalação e login 0.4.0

No Windows, use **Conhecer o launcher → Preparar Minecraft** para instalar sem autenticação. Para jogar, configure o cadastro próprio do Atlas e entre com uma conta Microsoft que possua Minecraft Java.

- [Cadastro Microsoft](docs/microsoft-login.md)
- [Instalação, requisitos e limites](docs/installation.md)

A API do site e o servidor Minecraft não foram implantados ou reiniciados nesta tarefa. O único ajuste adicional no mod cliente foi atualizar o endereço do botão Jogar Agora, gerando Atlas Interface 1.1.1.
