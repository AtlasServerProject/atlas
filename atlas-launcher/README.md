# Atlas Launcher 0.7.1

Launcher desktop do Atlas Cobblemon para Windows x64. Minecraft 1.21.1, Fabric 0.18.0, Java 21 e modpack Atlas 1.0.2-beta.4 (58 mods). Site: https://www.atlascobblemon.com.br. Servidor: stapling-gpo.tun.ply.gg.

## Instalar uma vez

Baixe o instalador na seção [Como jogar](https://www.atlascobblemon.com.br/how-to-play), feche versões antigas do launcher e execute `Atlas-Launcher-0.7.1-Setup-x64.exe`. Use o atalho Atlas Launcher depois de instalar. Não é necessário extrair ZIP, instalar Node.js ou preparar Java manualmente.

A instalação é por usuário, sem administrador, no destino fixo `LOCALAPPDATA/Programs/AtlasLauncher`. Mundos, modpack, configurações e cache permanecem no mesmo userData do aplicativo, fora da pasta substituída. Quem usa uma prévia em ZIP precisa fazer essa migração uma única vez.

Modo offline por nickname: use seu nick do Atlas e autentique-se com `/login` ou `/register` dentro do Minecraft. Não há coleta da senha do servidor no launcher. Login Microsoft permanece preparado, mas depende do Client ID próprio do Atlas e de teste real da autorização.

## Atualizações

- O aplicativo instalado consulta versões ao abrir e a cada cinco minutos, baixa instaladores assinados e aplica ao fechar quando o jogo e as operações terminaram.
- **Reiniciar e atualizar** permite aplicar uma atualização pronta imediatamente.
- Se o jogador fechar a janela com Minecraft aberto, o launcher permanece oculto até o jogo terminar e então conclui o fechamento/atualização.
- O instalador espera a saída do PID pai, usa staging e conserva a versão anterior; a ativação é revertida se a troca de diretórios falhar.
- Desinstalar remove programa e atalhos; não remove os dados locais do jogo.

Fontes no site oficial:

- `/launcher/windows/latest.json`: manifesto Ed25519 dos instaladores Windows.
- `/launcher/modpack.json`: manifesto Ed25519 do modpack.
- `/launcher/latest.json`: último ZIP legado, mantido para compatibilidade de distribuição.

Partes e pacote completo têm SHA-256; o executável é reconferido imediatamente antes de iniciar. A chave privada de publicação fica fora do repositório e dos pacotes. Não há certificado Authenticode configurado; a confiança do atualizador usa a assinatura Ed25519 fixada no aplicativo. ASAR não é criptografia.

## Desenvolvimento e distribuição

Node.js 22.12+ e npm. Java 21 somente para o backend independente.

```bash
npm ci
npm run dev
npm run typecheck
npm test
npm run build
npm run format:check
npm audit
```

Vite: 127.0.0.1:5179. Dev/start preparam Electron automaticamente. Não desative o sandbox. Main/preload exigem reinício após mudanças; React usa recarga de desenvolvimento. Não existem APIs genéricas de filesystem/shell/URLs no renderer.

Para gerar o instalador em Linux, disponibilize NSIS 3.10 em `artifacts/nsis-tools/root/usr`. Nesta VM foram baixados os pacotes oficiais Ubuntu `nsis` e `nsis-common` com `apt download` e extraídos com `dpkg-deb -x`, sem instalação de sistema.

```bash
npm run package:installer
node scripts/publish-installer.mjs /caminho/Atlas-Launcher-VERSAO-Setup-x64.exe
```

O publicador produz metadados assinados em `atlas-web/public/launcher/windows` e partes estáticas de até 20 MiB em `atlas-web/.launcher-distribution`, ignoradas pelo Git. Em atlas-web, execute `npm run build:pages` e publique o diretório compilado no Cloudflare Pages. O preparo confere os hashes e inclui as partes por hardlink/cópia. Em checkout novo, gere/restaure todas as partes referenciadas antes de publicar; o build falha se faltarem arquivos. Publique manifesto e arquivos no mesmo deploy.

O backend Java em services/backend continua independente, sem acesso às credenciais de produção do Atlas. Nenhum serviço Minecraft/API é reiniciado para atualizar o launcher.

## Validação e limites

61 testes automatizados passaram, incluindo identidade da instalação, bloqueio durante jogo/operações, assinatura, corrupção, preparação do instalador e argumentos fixos sem shell. Build Electron e NSIS passaram. Os bytes do executável e do ASAR extraídos do instalador foram comparados ao pacote original. A instalação e atualização entre duas versões em Windows real ainda precisam de validação; nenhum binário Windows foi executado nesta VM Linux.

Documentação: [instalação](docs/installation.md), [Microsoft](docs/microsoft-login.md), [segurança](docs/security.md), [verificações](docs/verification.md), [arquitetura](docs/architecture.md).
