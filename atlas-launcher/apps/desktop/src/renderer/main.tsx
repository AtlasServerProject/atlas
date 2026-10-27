import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import type {
  AtlasBridge,
  Bootstrap,
  RuntimeState,
  Settings as Preferences,
} from '../shared/contracts';
import { PROJECT } from '../shared/project';
import { Icon } from './components/Icon';
import { WindowBar } from './components/WindowBar';
import { Login } from './pages/Login';
import { Home } from './pages/Home';
import { Modpack } from './pages/Modpack';
import { Servers } from './pages/Servers';
import { Account } from './pages/Account';
import { Updates } from './pages/Updates';
import { Settings } from './pages/Settings';
import './styles/app.css';
declare global {
  interface Window {
    atlas?: AtlasBridge;
  }
}
const navigation = [
  ['Início', 'home'],
  ['Modpack', 'box'],
  ['Servidor', 'server'],
  ['Conta', 'user'],
  ['Configurações', 'settings'],
] as const;
function App() {
  const [runtime, setRuntime] = useState<RuntimeState>();
  const [login, setLogin] = useState(true);
  const [tab, setTab] = useState('Início');
  const [data, setData] = useState<Bootstrap>();
  const [settings, setSettings] = useState<Preferences>();
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    window.atlas
      ?.bootstrap()
      .then((value) => {
        setData(value);
        setSettings(value.settings);
      })
      .catch(() =>
        setError('Não foi possível ler suas preferências. Feche e abra o launcher novamente.'),
      );
  }, []);
  useEffect(() => {
    if (!window.atlas) return;
    let disposed = false;
    let busy = false;
    let reported = false;
    const refresh = async () => {
      if (busy) return;
      busy = true;
      try {
        const state = await window.atlas!.runtimeState();
        if (!disposed) setRuntime(state);
      } catch {
        if (!disposed && !reported) {
          reported = true;
          setError('Não foi possível consultar o estado do launcher. Reinicie o aplicativo.');
        }
      } finally {
        busy = false;
      }
    };
    void refresh();
    const timer = setInterval(() => void refresh(), 1000);
    return () => {
      disposed = true;
      clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    if (runtime?.auth.status === 'signed-in') setLogin(false);
    else if (runtime?.auth.status === 'waiting') setLogin(true);
  }, [runtime?.auth.status]);
  async function action(
    name:
      | 'signInMicrosoft'
      | 'openMicrosoftVerification'
      | 'signOut'
      | 'installMinecraft'
      | 'cancelInstallation'
      | 'playMinecraft',
  ) {
    try {
      await window.atlas?.[name]();
    } catch (error) {
      setError(
        error instanceof Error ? error.message : 'Não foi possível concluir. Tente novamente.',
      );
    }
  }
  const preparing =
    runtime &&
    ['checking', 'downloading-game', 'downloading-pack'].includes(runtime.installation.status);
  const website = () =>
    window.atlas
      ?.openWebsite()
      .catch(() => setError('Não foi possível abrir o site oficial. Tente novamente mais tarde.'));
  async function save() {
    if (!window.atlas || !settings) return;
    setSaving(true);
    setMessage('');
    try {
      setSettings(await window.atlas.saveSettings(settings));
      setMessage('Preferências salvas.');
    } catch {
      setError('Não foi possível salvar. Confira os limites de RAM e resolução e tente novamente.');
    } finally {
      setSaving(false);
    }
  }
  return (
    <>
      <WindowBar />
      {login ? (
        <Login
          onExplore={() => setLogin(false)}
          onWebsite={website}
          auth={runtime?.auth}
          onSignIn={() => void action('signInMicrosoft')}
          onOpenMicrosoft={() => void action('openMicrosoftVerification')}
          onCancel={() => void action('signOut')}
        />
      ) : (
        <div className="app-shell">
          <aside className="sidebar">
            <button className="brand" onClick={() => setTab('Início')} aria-label="Início Atlas">
              <img src="assets/logo.png" alt="Logotipo Atlas" />
              <strong>ATLAS</strong>
            </button>
            <nav aria-label="Menu principal">
              {navigation.map(([label, icon]) => (
                <button
                  key={label}
                  className={tab === label ? 'nav-item selected' : 'nav-item'}
                  aria-current={tab === label ? 'page' : undefined}
                  onClick={() => {
                    setTab(label);
                    setMessage('');
                  }}
                >
                  <Icon name={icon} size={18} />
                  <span>{label}</span>
                </button>
              ))}
            </nav>
            <div className="sidebar-bottom">
              <button
                className="nav-item update-nav"
                aria-current={tab === 'Atualizações' ? 'page' : undefined}
                onClick={() => setTab('Atualizações')}
              >
                <Icon name="download" size={17} />
                <span>Atualizações</span>
              </button>
              <button className="profile" onClick={() => setTab('Conta')}>
                <span className="avatar">
                  <Icon name="user" size={21} />
                </span>
                <span>
                  {runtime?.auth.account?.name ?? 'Visitante'}
                  <small>{runtime?.auth.account ? 'Microsoft · Java Edition' : 'Sem sessão'}</small>
                </span>
              </button>
            </div>
          </aside>
          <main>
            {preparing && (
              <div className="installation-banner">
                <Icon name="download" size={18} />
                <div>
                  <strong>
                    {runtime.installation.status === 'checking'
                      ? 'Preparando instalação…'
                      : runtime.installation.status === 'downloading-game'
                        ? 'Minecraft, bibliotecas e Java 21'
                        : 'Instalando o modpack Atlas'}
                  </strong>
                  <small>{runtime.installation.label}</small>
                </div>
                <progress
                  max={runtime.installation.total || 1}
                  value={runtime.installation.total ? runtime.installation.completed : undefined}
                />
                <button className="text-button" onClick={() => void action('cancelInstallation')}>
                  Cancelar
                </button>
              </div>
            )}
            {runtime?.installation.status === 'error' && (
              <div className="installation-banner error">
                <Icon name="info" />
                <div>
                  <strong>{runtime.installation.label}</strong>
                  <small>{runtime.installation.message}</small>
                </div>
                <button className="secondary" onClick={() => void action('installMinecraft')}>
                  Tentar novamente
                </button>
              </div>
            )}

            {!window.atlas && (
              <div className="preview-notice">
                <Icon name="info" size={14} />
                Prévia no navegador · Preferências locais disponíveis no aplicativo desktop.
              </div>
            )}
            {tab === 'Início' ? (
              <Home
                onModpack={() => setTab('Modpack')}
                onUpdates={() => setTab('Atualizações')}
                runtime={runtime}
                onInstall={() => void action('installMinecraft')}
                onPlay={() => void action('playMinecraft')}
              />
            ) : tab === 'Modpack' ? (
              <Modpack
                directory={data?.installationDirectory}
                onSettings={() => setTab('Configurações')}
                runtime={runtime}
                onInstall={() => void action('installMinecraft')}
              />
            ) : tab === 'Servidor' ? (
              <Servers runtime={runtime} onPlay={() => void action('playMinecraft')} />
            ) : tab === 'Conta' ? (
              <Account
                onLogin={() => setLogin(true)}
                account={runtime?.auth.account}
                onSignOut={() => void action('signOut')}
              />
            ) : tab === 'Atualizações' ? (
              <Updates
                runtime={runtime}
                onInstall={() => void action('installMinecraft')}
                onCancel={() => void action('cancelInstallation')}
              />
            ) : (
              <Settings
                data={data}
                settings={settings}
                onChange={setSettings}
                onSave={save}
                message={message}
                saving={saving}
              />
            )}
            <footer>
              <span>Atlas Launcher {data?.version ?? '0.4.0'} · Prévia de desenvolvimento</span>
              <button className="text-button" onClick={website} disabled={!window.atlas}>
                Site oficial <Icon name="external" size={12} />
              </button>
            </footer>
          </main>
        </div>
      )}
      {error && (
        <div className="modal-backdrop">
          <section
            className="error-dialog"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="error-title"
          >
            <span className="error-icon">!</span>
            <h2 id="error-title">Algo não saiu como esperado</h2>
            <p>{error}</p>
            <button className="primary" autoFocus onClick={() => setError('')}>
              Entendi
            </button>
          </section>
        </div>
      )}
    </>
  );
}
createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
