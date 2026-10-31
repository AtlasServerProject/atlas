import type { AuthState } from '../../main/auth/microsoft';
import { VideoBackground } from '../components/VideoBackground';
import { PROJECT } from '../../shared/project';
import { useState } from 'react';
import { Icon } from '../components/Icon';
export function Login({
  onWebsite,
  auth,
  onSignIn,
  onOpenMicrosoft,
  onCancel,
  onOffline,
}: {
  onWebsite: () => void;
  auth?: AuthState;
  onSignIn: () => void;
  onOpenMicrosoft: () => void;
  onCancel: () => void;
  onOffline: (nickname: string) => Promise<void>;
}) {
  const [mode, setMode] = useState('nickname');
  const [nickname, setNickname] = useState(() => {
    try {
      const saved = localStorage.getItem('atlas:last-offline-nickname') ?? '';
      return /^[A-Za-z0-9_]{3,16}$/.test(saved) ? saved : '';
    } catch {
      return '';
    }
  });
  const [offlineError, setOfflineError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  return (
    <div className="login-screen">
      <section className="login-panel">
        <div className="login-brand">
          <img src="assets/logo.png" alt="Atlas Cobblemon" />
          <h1>ATLAS</h1>
          <span>COBBLEMON</span>
        </div>
        <div className="segmented">
          <button
            className={mode === 'official' ? 'active' : ''}
            onClick={() => setMode('official')}
          >
            Conta original
          </button>
          <button
            className={mode === 'nickname' ? 'active' : ''}
            onClick={() => setMode('nickname')}
          >
            Modo offline
          </button>
        </div>
        {mode === 'official' ? (
          <>
            <button
              className="microsoft"
              disabled={!auth?.configured || ['connecting', 'waiting'].includes(auth.status)}
              onClick={onSignIn}
            >
              <span className="ms-icon">
                <i />
                <i />
                <i />
                <i />
              </span>
              Entrar com a Microsoft
            </button>
            <p className="login-explanation">
              {auth?.configured
                ? 'A autorização acontece no site da Microsoft. Sua senha nunca é digitada no Atlas.'
                : 'O aplicativo Microsoft do Atlas ainda precisa ser cadastrado para habilitar o login.'}
            </p>
          </>
        ) : (
          <>
            <label className="field">
              Nick
              <input
                value={nickname}
                onChange={(event) => setNickname(event.target.value)}
                placeholder="Seu nick no Minecraft"
                minLength={3}
                maxLength={16}
                autoComplete="username"
                spellCheck={false}
              />
            </label>
            <p className="login-explanation">
              Use seu nick do Atlas. Ao entrar no servidor, autentique-se com /login ou crie sua
              conta com /register. Sua senha é informada apenas dentro do Minecraft.
            </p>
            <button
              className="primary wide"
              disabled={!/^[A-Za-z0-9_]{3,16}$/.test(nickname) || submitting || !window.atlas}
              onClick={async () => {
                setSubmitting(true);
                setOfflineError('');
                try {
                  await onOffline(nickname);
                  try {
                    localStorage.setItem('atlas:last-offline-nickname', nickname);
                  } catch {
                    // Storage availability must not prevent entry into the launcher.
                  }
                } catch {
                  setOfflineError(
                    'Não foi possível usar esse nick. Aguarde a operação atual terminar e tente novamente.',
                  );
                } finally {
                  setSubmitting(false);
                }
              }}
            >
              {submitting ? 'Preparando perfil…' : 'Entrar no modo offline'}
            </button>
            {offlineError && (
              <p role="alert" className="auth-error">
                {offlineError}
              </p>
            )}
          </>
        )}
        {auth?.status === 'waiting' && (
          <section className="device-code" role="status">
            <p>Informe este código somente no site da Microsoft:</p>
            <code>{auth.userCode}</code>
            <button className="primary wide" onClick={onOpenMicrosoft}>
              Abrir Microsoft
            </button>
            <button className="text-button" onClick={onCancel}>
              Cancelar login
            </button>
          </section>
        )}
        {auth?.status === 'connecting' && (
          <p role="status" className="login-explanation">
            Validando sua conta Microsoft e o perfil Minecraft…
          </p>
        )}
        {auth?.status === 'error' && (
          <p role="alert" className="login-explanation auth-error">
            {auth.message}
          </p>
        )}
        <button className="text-button" onClick={onWebsite} disabled={!window.atlas}>
          Conheça o Atlas <Icon name="external" size={14} />
        </button>
      </section>
      <section className="login-art">
        <VideoBackground scene="milotic" />
        <div className="login-welcome">
          <span className="overline">SUA PRÓXIMA AVENTURA COMEÇA AQUI</span>
          <h2>BEM-VINDO AO ATLAS</h2>
          <p>Explore · Capture · Construa · Viva</p>
          <small>Um mundo de aventuras no universo Cobblemon.</small>
        </div>
        <div className="login-facts">
          <article>
            <Icon name="server" />
            <div>
              Atlas Cobblemon<small>{PROJECT.serverAddress}</small>
            </div>
          </article>
          <article>
            <Icon name="box" />
            <div>
              Minecraft 1.21.1<small>Fabric · Java 21</small>
            </div>
          </article>
        </div>
      </section>
    </div>
  );
}
