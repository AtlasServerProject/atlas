# Configurar login Microsoft do Atlas

O código usa MSAL Node 7.1.2, aplicativo público e contas Microsoft pessoais. Não solicita senha no launcher, não usa Client Secret e não empresta o Client ID de outros launchers. O Client ID público foi configurado para a versão 0.7.5. O endpoint Microsoft de código de dispositivo aceitou o início da autorização (HTTP 200); a autorização completa Xbox/Minecraft com uma conta real ainda precisa ser testada.

## Cadastro

1. Abra [Microsoft Entra](https://entra.microsoft.com/) e entre com a conta administradora do Atlas.
2. Vá a **Identidade / Aplicativos / Registros de aplicativos → Novo registro** (os nomes podem variar conforme o idioma do painel).
3. Nome: **Atlas Cobblemon Launcher**.
4. Tipos de conta: **Somente contas pessoais da Microsoft**. O código usa a autoridade `consumers`, destinada a contas pessoais Xbox/Microsoft.
5. Para o fluxo de código de dispositivo usado aqui, deixe URI de redirecionamento vazia. Não crie um aplicativo Web confidencial nem um Client Secret.
6. Registre. Em **Autenticação → Configurações avançadas**, habilite **Permitir fluxos de cliente público** e salve.
7. Copie somente **ID do aplicativo (cliente) / Application (client) ID**, um UUID público. Não envie senha, token, código de autenticação ou Client Secret.

[Guia oficial de registro](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app) · [MSAL Node e código de dispositivo](https://learn.microsoft.com/en-us/entra/msal/javascript/node/acquire-token-requests#device-code-flow).

## Acesso Xbox/Minecraft

O registro no Entra não garante, sozinho, acesso do aplicativo aos serviços Minecraft. O fluxo solicita `XboxLive.signin` e `offline_access` e precisa ser aceito pelos serviços Microsoft/Xbox/Minecraft para o Client ID do Atlas. Se aparecer HTTP 403/registro de aplicativo inválido, verifique a revisão do aplicativo com Microsoft/Mojang; não substitua o ID por credenciais de outros launchers.

O endereço Microsoft [aka.ms/mce-reviewappid](https://aka.ms/mce-reviewappid) redirecionou para um formulário `forms.office.com` nesta verificação. O conteúdo final e a aprovação não foram confirmados nesta sessão; se o formulário não estiver disponível para sua conta, consulte o suporte oficial. Não há prazo de aprovação afirmado aqui.

## Configurar o código

Na pasta `atlas-launcher`, depois de obter o ID real:

```bash
npm run configure:microsoft -- SEU_CLIENT_ID_PUBLICO
npm run package:installer
```

`SEU_CLIENT_ID_PUBLICO` é uma indicação de preenchimento, nunca uma credencial válida. O comando só aceita UUID, modifica o campo público de configuração e preserva catálogo, assinatura e chave pública do modpack. Como o código de dispositivo é um fluxo público, nenhum segredo precisa ser distribuído.

O administrador também pode informar esse Client ID público na conversa para atualizar o próximo build. O jogador final não precisa de Node.js nem executar esse comando.

## Teste real após configurar

- Entrar com a Microsoft deve exibir um código temporário no launcher e abrir apenas o endereço Microsoft permitido.
- O jogador informa o código somente no site da Microsoft e autoriza sua própria conta com Minecraft Java disponível.
- O processo principal troca a sessão por Xbox/XSTS e Minecraft, consulta o perfil e disponibiliza somente nome/UUID à interface.
- Tokens Microsoft ficam no cache MSAL cifrado com `safeStorage` do Electron quando o cofre do SO é seguro. Em backend Linux `basic_text` ou sem criptografia, não há persistência de tokens; a sessão fica apenas na memória.
- Sair limpa o cache, inclusive gravações concorrentes. O código lógico invalida uma autorização cancelada para impedir atualização tardia do perfil.
- O fluxo Microsoft real e a criptografia DPAPI no Windows ainda não foram testados com uma conta nesta sessão. Os testes automatizados da cadeia de autorização usam respostas artificiais identificadas como fixtures.

O modo offline por nickname continua disponível. O login Microsoft do launcher não dispensa a autenticação local do servidor Atlas.

## Modo offline disponível

A versão 0.6.0 oferece perfil por nickname, com autenticação própria do servidor Atlas por /login ou /register. Não solicita senha Microsoft nem senha do servidor no launcher. A identidade é apresentada como offline, sem afirmar validação Microsoft. O cadastro Microsoft pode ser retomado depois.
