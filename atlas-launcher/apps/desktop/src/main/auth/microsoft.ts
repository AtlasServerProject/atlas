import { MicrosoftAuthenticator } from '@xmcl/user';
import { PublicClientApplication, type DeviceCodeRequest } from '@azure/msal-node';
import { TokenVault } from './vault';
export interface PublicAccount {
  id: string;
  name: string;
  kind: 'microsoft';
}
export interface AuthState {
  configured: boolean;
  status: 'signed-out' | 'waiting' | 'connecting' | 'signed-in' | 'error';
  account?: PublicAccount;
  userCode?: string;
  verificationUri?: string;
  message?: string;
}
interface GameSession {
  profile: PublicAccount;
  accessToken: string;
  expiresAt: number;
  xuid: string;
}
export function validClientId(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value) &&
    value !== '00000000-0000-0000-0000-000000000000'
  );
}
export function validateVerificationUri(value: string): string {
  const url = new URL(value);
  if (
    ![
      'https://microsoft.com/devicelogin',
      'https://www.microsoft.com/link',
      'https://www.microsoft.com/devicelogin',
    ].includes(url.href.replace(/\/$/, ''))
  )
    throw new Error('Endereço Microsoft não autorizado.');
  return url.href;
}
export async function exchangeMinecraftToken(
  accessToken: string,
  request: typeof fetch = fetch,
): Promise<GameSession> {
  const json = async (url: string, body?: unknown, bearer?: string) => {
    const response = await request(url, {
      method: body ? 'POST' : 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(bearer ? { Authorization: 'Bearer ' + bearer } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
      redirect: 'error',
      signal: AbortSignal.timeout(30000),
    });
    if (!response.ok)
      throw new Error(
        response.status === 404
          ? 'Esta conta não tem um perfil Minecraft Java disponível.'
          : 'A Microsoft/Xbox não concluiu a autorização. Verifique as permissões da conta e do aplicativo Atlas.',
      );
    return response.json();
  };
  const xboxClient = new MicrosoftAuthenticator({
    fetch: (input, init) =>
      request(input, {
        ...init,
        redirect: 'error',
        signal: init?.signal ?? AbortSignal.timeout(30000),
      }),
  });
  let xsts;
  try {
    const xbox = await xboxClient.authenticateXboxLive(accessToken);
    const device = await xboxClient.authenticateXboxDevice();
    xsts = await xboxClient.authorizeXboxLive(
      xbox.Token,
      'rp://api.minecraftservices.com/',
      undefined,
      device.Token,
    );
  } catch {
    throw new Error(
      'A Microsoft/Xbox não concluiu a autorização. Verifique as permissões da conta e do aplicativo Atlas.',
    );
  }
  const uhs = xsts.DisplayClaims?.xui?.[0]?.uhs;
  if (typeof uhs !== 'string' || typeof xsts.Token !== 'string')
    throw new Error('Resposta Xbox inválida.');
  const game = await json('https://api.minecraftservices.com/authentication/login_with_xbox', {
    identityToken: `XBL3.0 x=${uhs};${xsts.Token}`,
  });
  if (
    typeof game.access_token !== 'string' ||
    !Number.isFinite(game.expires_in) ||
    game.expires_in <= 0
  )
    throw new Error('Sessão Minecraft inválida.');
  const profile = await json(
    'https://api.minecraftservices.com/minecraft/profile',
    undefined,
    game.access_token,
  );
  if (!/^[0-9a-f]{32}$/i.test(profile.id) || !/^\w{3,16}$/.test(profile.name))
    throw new Error('Perfil Minecraft inválido.');
  return {
    profile: { id: profile.id, name: profile.name, kind: 'microsoft' },
    xuid: /^\d{1,24}$/.test(String(xsts.DisplayClaims?.xui?.[0]?.xid ?? ''))
      ? String(xsts.DisplayClaims.xui[0].xid)
      : '',
    accessToken: game.access_token,
    expiresAt: Date.now() + Math.min(game.expires_in, 86400) * 1000,
  };
}
export class MicrosoftLogin {
  private generation = 0;
  private session?: GameSession;
  private state: AuthState;
  private client?: PublicClientApplication;
  constructor(
    private clientId: string | null,
    private vault: TokenVault,
  ) {
    this.state = { configured: validClientId(clientId), status: 'signed-out' };
  }
  publicState(): AuthState {
    return structuredClone(this.state);
  }
  private createClient(generation: number) {
    if (!validClientId(this.clientId))
      throw new Error('O Client ID Microsoft do Atlas ainda não foi configurado.');
    return new PublicClientApplication({
      auth: { clientId: this.clientId, authority: 'https://login.microsoftonline.com/consumers' },
      system: { loggerOptions: { piiLoggingEnabled: false, loggerCallback: () => {} } },
      cache: {
        cachePlugin: {
          beforeCacheAccess: async (context) => {
            if (generation !== this.generation) return;
            const saved = await this.vault.read();
            if (saved) context.tokenCache.deserialize(saved);
          },
          afterCacheAccess: async (context) => {
            if (generation === this.generation && context.cacheHasChanged)
              await this.vault.write(context.tokenCache.serialize());
          },
        },
      },
    });
  }
  async signIn(): Promise<void> {
    if (!this.state.configured)
      throw new Error('Cadastre o aplicativo Microsoft do Atlas para habilitar o login.');
    if (['waiting', 'connecting'].includes(this.state.status)) return;
    const generation = ++this.generation;
    this.state = { configured: true, status: 'connecting' };
    try {
      const client = this.createClient(generation);
      this.client = client;
      const accounts = await client.getTokenCache().getAllAccounts();
      let token;
      if (accounts[0]) {
        try {
          token = await client.acquireTokenSilent({
            scopes: ['XboxLive.signin', 'offline_access'],
            account: accounts[0],
          });
        } catch {}
      }
      if (!token) {
        const request: DeviceCodeRequest = {
          scopes: ['XboxLive.signin', 'offline_access'],
          timeout: 900,
          deviceCodeCallback: (response) => {
            if (generation !== this.generation) return;
            this.state = {
              configured: true,
              status: 'waiting',
              userCode: response.userCode,
              verificationUri: validateVerificationUri(response.verificationUri),
              message: 'Abra o site da Microsoft e informe este código somente lá.',
            };
          },
        };
        token = await client.acquireTokenByDeviceCode(request);
      }
      if (generation !== this.generation) return;
      if (!token) throw new Error('Login cancelado ou expirado.');
      this.state = { configured: true, status: 'connecting' };
      const session = await exchangeMinecraftToken(token.accessToken);
      if (generation !== this.generation) return;
      this.session = session;
      this.state = { configured: true, status: 'signed-in', account: session.profile };
    } catch (error) {
      if (generation === this.generation) {
        this.session = undefined;
        this.state = {
          configured: true,
          status: 'error',
          message:
            error instanceof Error && error.message.startsWith('Esta conta')
              ? error.message
              : 'Não foi possível autenticar. Confira o cadastro do aplicativo Atlas, o acesso Xbox/Minecraft e tente novamente.',
        };
      }
    }
  }
  async signOut() {
    this.generation++;
    this.session = undefined;
    this.state = { configured: this.state.configured, status: 'signed-out' };
    await this.vault.clear();
    this.client = undefined;
  }
  async forGame(): Promise<GameSession> {
    if (!this.session || this.session.expiresAt < Date.now() + 120000) {
      await this.signIn();
    }
    if (!this.session || this.session.expiresAt < Date.now() + 30000)
      throw new Error('Entre novamente na sua conta Microsoft.');
    return this.session;
  }
}
