import type { AuthState } from '../../main/auth/microsoft';
import { VideoBackground } from '../components/VideoBackground';
import { PROJECT } from '../../shared/project';
import { useState } from 'react';
import { Icon } from '../components/Icon';
export function Login({
  onExplore,
  onWebsite,
  auth,
  onSignIn,
  onOpenMicrosoft,
  onCancel,
}: {
  onExplore: () => void;
  onWebsite: () => void;
  auth?: AuthState;
  onSignIn: () => void;
  onOpenMicrosoft: () => void;
  onCancel: () => void;
}) {
  const [mode, setMode] = useState('official');
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
            Por nickname
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
              <input placeholder="Digite seu nick…" disabled />
            </label>
            <p className="login-explanation">
              Acesso por nickname ainda indisponível. Depende da política de autenticação do
              servidor.
            </p>
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
        <div className="divider">
          <span>enquanto isso</span>
        </div>
        <button className="primary wide" onClick={onExplore}>
          Conhecer o launcher <Icon name="arrow" size={17} />
        </button>
        <p className="login-note">Explore a interface sem iniciar uma sessão.</p>
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
