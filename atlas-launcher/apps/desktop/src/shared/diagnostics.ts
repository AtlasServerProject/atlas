/** Public diagnostics contain only curated text: never remote responses, paths or tokens. */
export interface Diagnostic {
  code: string;
  title: string;
  explanation: string;
  steps: string[];
  responsibility: 'Jogador' | 'Equipe Atlas' | 'Jogador ou equipe Atlas';
}
const issue = (
  code: string,
  title: string,
  explanation: string,
  steps: string[],
  responsibility: Diagnostic['responsibility'] = 'Jogador',
): Diagnostic => ({ code, title, explanation, steps, responsibility });
export function gameDiagnostic(text: string, offline = false): Diagnostic | undefined {
  // Chat from other players is not a trusted error signal.
  if (/\[CHAT\]|<[^>]+>/.test(text)) return;
  if (
    /reservar mem[oó]ria|OutOfMemoryError|Could not reserve enough space|insufficient memory for the Java Runtime Environment|Native memory allocation.*failed|os::commit_memory.*failed|paging file is too small|Failed to map memory/i.test(
      text,
    )
  )
    return issue(
      'ATL-JAVA-001',
      'O Minecraft ficou sem memória',
      'O Java informou uma falha real ao reservar ou usar memória.',
      [
        'Feche aplicativos que consomem memória.',
        'Em Configurações → Desempenho, ajuste a RAM sem reservar toda a memória do computador.',
        'Se persistir, envie o diagnóstico à equipe.',
      ],
    );
  if (
    /AUTH_INVALID_SESSION|invalid session|sess[aã]o inv[aá]lida|invalid token|Failed to log in:.*Invalid|disconnect\.loginFailedInfo\.invalidSession/i.test(
      text,
    )
  )
    return issue(
      'ATL-AUTH-001',
      'O servidor recusou a sessão do Minecraft',
      offline
        ? 'A conexão em modo offline foi recusada na validação de sessão. O servidor pode estar exigindo uma conta Microsoft para esse nick; o registro não confirma a causa exata.'
        : 'A sessão apresentada ao servidor não foi aceita. Ela pode ter expirado ou ter sido encerrada em outro lugar.',
      offline
        ? [
            'Não altere o nick para tentar recuperar outra conta.',
            'Informe à equipe Atlas que entrou em modo offline, o horário e este código.',
            'A equipe precisa conferir a política de autenticação do servidor. Reinstalar o modpack não corrige essa validação.',
          ]
        : [
            'Feche o Minecraft.',
            'No launcher, saia da conta Microsoft e entre novamente na conta que possui Minecraft Java.',
            'Abra o jogo de novo. Se persistir, envie este código e o horário à equipe.',
          ],
      offline ? 'Equipe Atlas' : 'Jogador ou equipe Atlas',
    );
  if (
    /SERVER_FLIGHT_DISABLED|Flying is not enabled on this server|n[aã]o [eé] permitido voar|multiplayer\.disconnect\.flying/i.test(
      text,
    )
  )
    return issue(
      'ATL-SRV-001',
      'O servidor bloqueou o voo',
      'O servidor expulsou o jogador pela verificação de voo. Isso também pode ocorrer com montarias ou movimento de mods.',
      [
        'Informe à equipe o que fazia antes da expulsão.',
        'A equipe deve conferir allow-flight e as regras de movimento; esta configuração fica no servidor.',
      ],
      'Equipe Atlas',
    );
  if (
    /MOD_REGISTRY_MISMATCH|Unknown registry|unknown.*registr(?:y|ies)|registry.*unknown|entradas de registro.*desconhecidas|incompatible mod set|Incompatible mods found|Mod resolution encountered an incompatible mod set/i.test(
      text,
    )
  )
    return issue(
      'ATL-MOD-001',
      'Mods incompatíveis ou ausentes',
      'O cliente ou o servidor anunciou conteúdo que a outra instalação não reconhece.',
      [
        'Feche o Minecraft e use Atualizações → Verificar instalação.',
        'Não misture mods de outros perfis com a instalação Atlas.',
        'Se continuar, envie o diagnóstico: a equipe deve comparar as versões do cliente e do servidor.',
      ],
      'Jogador ou equipe Atlas',
    );
  if (
    /NETWORK_UNREACHABLE|Connection refused|Connection timed out|connect timed out|UnknownHostException|Unknown host|No route to host/i.test(
      text,
    )
  )
    return issue(
      'ATL-NET-001',
      'Não foi possível alcançar o servidor',
      'A tentativa de conexão falhou antes de concluir a entrada. Isso pode ser rede, endereço indisponível ou servidor desligado.',
      [
        'Confira sua conexão com a internet e tente novamente.',
        'Use o endereço oficial do Atlas.',
        'Se outros jogadores também não conseguem entrar, informe à equipe.',
      ],
      'Jogador ou equipe Atlas',
    );
  if (/NETWORK_RESET|Connection reset|SocketException.*reset/i.test(text))
    return issue(
      'ATL-NET-002',
      'A conexão foi interrompida',
      'A conexão foi encerrada durante a comunicação. Esse registro sozinho não identifica quem a interrompeu.',
      [
        'Tente reconectar uma vez.',
        'Se repetir, informe o horário e envie o diagnóstico à equipe.',
      ],
      'Jogador ou equipe Atlas',
    );
  if (
    /GLFW error 65542|does not support OpenGL|Failed to create.*OpenGL|Pixel format not accelerated/i.test(
      text,
    )
  )
    return issue(
      'ATL-GPU-001',
      'Não foi possível iniciar os gráficos',
      'O Minecraft encontrou uma falha de compatibilidade OpenGL ou do driver de vídeo.',
      [
        'Atualize o driver pelo fabricante da placa de vídeo.',
        'Reinicie o computador. Se persistir, envie o diagnóstico e o modelo da placa à equipe.',
      ],
    );
  if (/UnsupportedClassVersionError|requires Java (?:21|version)|class file version 65/i.test(text))
    return issue(
      'ATL-JAVA-002',
      'Versão do Java incompatível',
      'O jogo não iniciou com a versão de Java exigida pelo modpack.',
      [
        'Use Atualizações → Verificar instalação para conferir o Java gerenciado pelo Atlas.',
        'Inicie pelo Atlas Launcher, sem substituir seus arquivos de Java.',
      ],
    );
  if (/\[AtlasDiagnostic\] code=DISCONNECT_UNKNOWN/.test(text))
    return issue(
      'ATL-SRV-002',
      'O Minecraft foi desconectado',
      'A tela de desconexão não apresentou uma causa reconhecida pelo Atlas.',
      [
        'Anote a mensagem mostrada no Minecraft e o horário.',
        'Abra os diagnósticos e envie à equipe junto com a mensagem.',
      ],
      'Jogador ou equipe Atlas',
    );
  if (
    /Failed to (?:download|reload).*resource|resource.*pack.*(?:failed|error)|Erro ao recarregar recursos/i.test(
      text,
    )
  )
    return issue(
      'ATL-PACK-001',
      'Falha no pacote de recursos',
      'O Minecraft registrou falha ao baixar ou carregar um pacote de recursos.',
      [
        'Confira a conexão e use Verificar instalação.',
        'Se persistir ao entrar no Atlas, envie este código à equipe para conferir o pacote do servidor.',
      ],
      'Jogador ou equipe Atlas',
    );
}
export function launcherDiagnostic(error: unknown): Diagnostic {
  const raw = error instanceof Error ? error.message : typeof error === 'string' ? error : '';
  const text = raw.replace(/^Error invoking remote method '[^']+': (?:Error: )?/, '');
  const game = gameDiagnostic(text);
  if (game) return game;
  if (/Minecraft autoriza.*403/i.test(text))
    return issue(
      'ATL-MS-403',
      'Minecraft recusou a autorização do Atlas',
      'A Microsoft concluiu a etapa de login, mas o serviço Minecraft retornou HTTP 403.',
      [
        'Informe este código à equipe Atlas.',
        'A equipe precisa conferir a aprovação do aplicativo e as permissões exigidas pelo serviço Minecraft.',
      ],
      'Equipe Atlas',
    );
  if (/Minecraft perfil.*404/i.test(text))
    return issue(
      'ATL-MS-404',
      'Perfil Minecraft Java não encontrado',
      'A conta autorizada não apresentou um perfil Minecraft Java disponível.',
      [
        'Confira se escolheu a conta que possui Minecraft Java.',
        'Abra o launcher oficial para conferir o perfil da conta.',
      ],
    );
  if (/Microsoft|Xbox|autoriza[cç][aã]o|conta foi desconectada/i.test(text))
    return issue(
      'ATL-AUTH-002',
      'Não foi possível concluir o login',
      'A autorização da conta não foi concluída ou a sessão precisa ser renovada.',
      [
        'Inicie novamente o login Microsoft e conclua a autorização no navegador.',
        'Se persistir, confira a mensagem na tela Conta e informe a etapa à equipe.',
      ],
      'Jogador ou equipe Atlas',
    );
  if (/ENOSPC|not enough space|espa[cç]o.*(?:insuficiente|disco)/i.test(text))
    return issue(
      'ATL-DISK-001',
      'Espaço em disco insuficiente',
      'Não há espaço disponível para concluir a operação.',
      [
        'Libere espaço na unidade da instalação do Atlas.',
        'Tente novamente sem apagar seus mundos ou dados pessoais.',
      ],
    );
  if (/ENOTDIR|not a directory/i.test(text))
    return issue(
      'ATL-FILE-001',
      'Um arquivo está ocupando o lugar de uma pasta',
      'A instalação encontrou um caminho com tipo incompatível.',
      [
        'Atualize o launcher e use Verificar instalação.',
        'Se persistir, envie o diagnóstico. Não apague a pasta inteira do jogo.',
      ],
      'Jogador ou equipe Atlas',
    );
  if (/EACCES|EPERM|EBUSY|permission denied|access.*denied|em uso/i.test(text))
    return issue(
      'ATL-FILE-002',
      'Arquivo bloqueado ou sem permissão',
      'O Windows não permitiu acessar um arquivo necessário.',
      [
        'Feche o Minecraft e outros launchers e tente novamente.',
        'Confira se o antivírus colocou arquivos do Atlas em quarentena. Não desative a proteção do computador.',
        'Envie o diagnóstico se o bloqueio continuar.',
      ],
    );
  if (
    /n[aã]o gerenciado|unmanaged|fora.*(?:diret[oó]rio|instala[cç][aã]o)|symlink|symbolic link/i.test(
      text,
    )
  )
    return issue(
      'ATL-FILE-003',
      'A instalação foi interrompida para preservar seus arquivos',
      'A proteção de caminhos encontrou um arquivo que não pode ser alterado automaticamente.',
      [
        'Atualize o launcher e tente Verificar instalação.',
        'Se persistir, envie o diagnóstico à equipe antes de apagar ou mover arquivos.',
      ],
      'Jogador ou equipe Atlas',
    );
  if (/assinatura|signature|hash|checksum|integridade/i.test(text))
    return issue(
      'ATL-INTEGRITY-001',
      'A verificação dos arquivos falhou',
      'Um arquivo ou catálogo não passou na validação de integridade. Ele não será executado.',
      [
        'Confira a conexão e tente baixar novamente.',
        'Se persistir, informe à equipe para conferir a publicação oficial. Não ignore a validação.',
      ],
      'Jogador ou equipe Atlas',
    );
  if (/fetch|HTTP|ENOTFOUND|ECONN|ETIMEDOUT|network|download/i.test(text))
    return issue(
      'ATL-DOWNLOAD-001',
      'Falha ao acessar o serviço de download',
      'O launcher não conseguiu concluir a transferência ou recebeu uma resposta de erro.',
      [
        'Confira a internet e tente novamente.',
        'Se persistir, informe à equipe o horário da tentativa.',
      ],
      'Jogador ou equipe Atlas',
    );
  if (/Java n[aã]o iniciou|iniciar o Java/i.test(text))
    return issue(
      'ATL-JAVA-003',
      'O Java não iniciou',
      'O sistema operacional não conseguiu abrir o Java gerenciado pelo Atlas.',
      [
        'Feche o jogo e use Verificar instalação.',
        'Confira se o antivírus bloqueou o Java e envie o diagnóstico se continuar.',
      ],
    );
  if (/Aguarde|processo atual|jogo ou a instala[cç][aã]o/i.test(text))
    return issue(
      'ATL-BUSY-001',
      'Outra operação está em andamento',
      'O jogo ou uma operação de instalação ainda está ativo.',
      ['Aguarde a operação terminar ou feche o Minecraft antes de tentar novamente.'],
    );
  return issue(
    'ATL-UNKNOWN-001',
    'Não foi possível concluir a operação',
    'Ainda não há evidência suficiente para identificar a causa com segurança.',
    [
      'Tente novamente uma vez.',
      'Se persistir, abra os diagnósticos e informe à equipe este código, a ação realizada e o horário.',
    ],
    'Jogador ou equipe Atlas',
  );
}
export function diagnosticText(d: Diagnostic): string {
  return `${d.code} — ${d.title}\n${d.explanation}\nResponsável pela verificação: ${d.responsibility}\n${d.steps.map((s, i) => `${i + 1}. ${s}`).join('\n')}`;
}
