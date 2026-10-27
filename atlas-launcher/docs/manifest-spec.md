> Estado atual 0.4.0: autenticação, downloads e instalação foram implementados. As notas de fases anteriores abaixo são históricas. Consulte [instalação](installation.md), [cadastro Microsoft](microsoft-login.md) e [verificação](verification.md) para os limites atuais.

# Manifesto — proposta v1, ainda não aceito pelo aplicativo

A fundação da fase 3 começou na versão 0.3.0: há validação e testes criptográficos locais. Não existe manifesto de produção nem download autorizado.

Payload planejado: `schemaVersion`, `packId`, `version` imutável, `channel`, `minecraftVersion`, `modLoader.type/version`, `minimumLauncherVersion`, `minimumCompatibleVersion`, `files[]`, `removals[]`, `releaseNotes`, `publishedAt`. Cada arquivo terá caminho relativo, URL HTTPS de origem permitida, tamanho inteiro, SHA-256 e política explícita de substituição. Separar versão mais recente e mínima compatível.

Envelope: payload UTF-8 exato em base64, `keyId`, assinatura Ed25519 desses bytes. Verificar assinatura antes de interpretar o payload. Chave pública confiável incorporada no binário, privada somente no publicador. Não aceitar chave fornecida pelo mesmo manifesto. Limitar tamanho e rejeitar campos/tipos/duplicações inválidos. Formalizar JSON Schema e rotação de chaves na fase 3.

Bloquear caminhos absolutos, `..`, separadores ambíguos, UNC, drives Windows, ADS, nomes reservados, colisões de caixa e symlinks/junctions que escapem da instância. Autorizar apenas raízes gerenciadas explicitamente. Nunca remover `saves`, `screenshots`, `logs`, backups ou arquivos pessoais. Remoções precisam corresponder a um arquivo anteriormente gerenciado; nunca varrer e apagar arquivos desconhecidos.

Aplicar download em staging, hash/tamanho conferidos, lock exclusivo, diário de transação e ativação atômica com rollback. Recuperar após interrupção. Nunca aplicar enquanto o jogo está aberto. Download retomado exige validação de Content-Range e identidade do objeto; reiniciar se o objeto mudar. Impedir downgrade não autorizado e redirects para origem não permitida.

Testes previstos: assinatura inválida, hash divergente, manifesto inválido, diferenças reais apesar de mesma versão, travessia/symlink, arquivo pessoal, transferência interrompida, concorrência, falha de ativação e recuperação. Esses testes não são declarados concluídos na fase 1.

## Implementado na fundação 0.3.0

`main/modpack/manifest.ts` valida envelope com exatamente keyId/payload/signature. Chaves e origens precisam ser fornecidas por configuração confiável; não há valores de produção fictícios. Payload usa JSON compacto canônico (`JSON.stringify` do objeto), UTF-8 estrito, serialização base64 canônica e assinatura Ed25519 dos bytes exatos. Isso também rejeita propriedades JSON duplicadas.

Schema aceita apenas campos declarados e pack Atlas, canais stable/beta, Fabric, versões numéricas, UTC, arquivos com tamanho/hash válidos e origens HTTPS permitidas sem credenciais. Há limite de 2 MiB aproximado no payload e até 10 mil entradas. Caminhos limitados a mods/config/resourcepacks/shaderpacks, sem nomes Windows reservados, traversal, ADS ou colisões por caixa/ancestral. Remoções são apenas validadas; nenhuma remoção é executada. Verificação de symlinks/junctions no disco pertence à futura camada de instalação, ainda inexistente.

`integrity.ts` verifica tamanho/SHA-256 de bytes recebidos e planeja downloads por comparação de hashes/tamanhos reais. O chamador deverá calcular os hashes locais, sem confiar somente num índice ou na versão instalada. Ainda faltam leitura segura em streaming, downloads retomáveis, lock, diário, staging/ativação, rollback e conexão ao backend. Não há chaves privadas ou credenciais distribuídas.
