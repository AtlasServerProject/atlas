export type AuthStage =
  | 'Microsoft'
  | 'Xbox Live'
  | 'Xbox dispositivo'
  | 'Xbox XSTS'
  | 'Minecraft autorização'
  | 'Minecraft perfil';
/** Only locally constructed messages reach the renderer; remote bodies/tokens are never echoed. */
export class AuthFlowError extends Error {
  constructor(
    readonly stage: AuthStage,
    readonly status?: number,
    xerr?: number,
  ) {
    let detail = 'Tente novamente; se persistir, informe esta etapa à equipe.';
    if (stage === 'Minecraft autorização' && status === 403)
      detail =
        'O serviço Minecraft recusou a autorização do Atlas. O Client ID pode precisar de aprovação da Mojang; informe esta etapa à equipe para confirmar.';
    if (stage === 'Minecraft perfil' && status === 404)
      detail =
        'Esta conta não tem um perfil Minecraft Java disponível. Confira se escolheu a conta que possui o jogo.';
    if (stage === 'Xbox XSTS' && xerr === 2148916233)
      detail =
        'Entre no site do Xbox e conclua a criação do seu perfil Xbox antes de tentar novamente.';
    if (stage === 'Xbox XSTS' && xerr === 2148916238)
      detail = 'Confira as configurações da família Microsoft e as permissões da conta Xbox.';
    super(`${stage}${status ? ` — HTTP ${status}` : ''}: ${detail}`);
    this.name = 'AuthFlowError';
  }
}
export function publicAuthError(error: unknown): string {
  if (error instanceof AuthFlowError) return error.message;
  const code =
    error && typeof error === 'object' && 'errorCode' in error ? error.errorCode : undefined;
  if (code === 'invalid_client' || code === 'unauthorized_client')
    return 'Microsoft: confira se Permitir fluxos de cliente público está habilitado no aplicativo Atlas.';
  if (
    ['authorization_declined', 'access_denied', 'user_cancelled', 'user_canceled'].includes(
      String(code),
    )
  )
    return 'A autorização Microsoft foi cancelada. Você pode tentar novamente.';
  if (
    ['expired_token', 'code_expired', 'device_code_expired', 'user_timeout'].includes(String(code))
  )
    return 'O código Microsoft expirou. Inicie uma nova autorização.';
  return 'Microsoft: não foi possível concluir a autorização. Tente novamente e confira o cadastro do aplicativo Atlas.';
}
