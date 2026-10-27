import type { RuntimeState } from '../../shared/contracts';
import { useState } from 'react';
import { Icon } from '../components/Icon';
export function Modpack({
  directory,
  onSettings,
  runtime,
  onInstall,
}: {
  directory?: string;
  onSettings: () => void;
  runtime?: RuntimeState;
  onInstall: () => void;
}) {
  const [tab, setTab] = useState('Mods');
  const [query, setQuery] = useState('');
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="overline">SUA INSTALAÇÃO</span>
          <h1>Modpack</h1>
          <p>Atlas Cobblemon · Minecraft 1.21.1 · Fabric</p>
        </div>
        <span className="badge neutral">
          {runtime?.installation.status === 'ready' ? 'Verificado' : 'Não instalado'}
        </span>
      </div>
      <section className="panel">
        <div className="tabs">
          {['Mods', 'Resource packs', 'Configurações'].map((label) => (
            <button
              key={label}
              className={tab === label ? 'active' : ''}
              onClick={() => setTab(label)}
            >
              {label}
            </button>
          ))}
        </div>
        {tab === 'Configurações' ? (
          <div className="pack-directory">
            <h3>Diretório reservado para o Atlas</h3>
            <code>{directory ?? 'Disponível no aplicativo desktop'}</code>
            <p>Mundos locais, capturas e outras instalações não serão removidos.</p>
            <button className="secondary" onClick={onSettings}>
              Preferências do Minecraft
            </button>
          </div>
        ) : (
          <>
            <div className="search-placeholder">
              <Icon name="search" size={16} />
              <input
                disabled={tab !== 'Mods' || !runtime?.mods.length}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={tab === 'Mods' ? 'Buscar mod…' : 'Buscar resource pack…'}
                aria-label={tab === 'Mods' ? 'Buscar mod' : 'Buscar resource pack'}
              />
            </div>
            {tab === 'Mods' && runtime?.mods.length ? (
              <>
                <div className="pack-toolbar">
                  <span>
                    {runtime.mods.length} mods · Atlas {runtime.packVersion}
                  </span>
                  <button
                    className="primary"
                    disabled={
                      !runtime.canInstall ||
                      runtime.busy ||
                      !['not-installed', 'ready', 'error', 'cancelled'].includes(
                        runtime.installation.status,
                      ) ||
                      runtime.gameRunning
                    }
                    onClick={onInstall}
                  >
                    {runtime.installation.status === 'ready'
                      ? 'Verificar arquivos'
                      : 'Instalar Minecraft e modpack'}
                  </button>
                </div>
                <ul className="mod-list">
                  {runtime.mods
                    .filter((mod) => mod.name.toLowerCase().includes(query.toLowerCase()))
                    .map((mod) => (
                      <li key={mod.name}>
                        <Icon name="box" size={17} />
                        <span>{mod.name}</span>
                        <small>
                          {(mod.size / 1048576).toLocaleString('pt-BR', {
                            maximumFractionDigits: 1,
                          })}{' '}
                          MB
                        </small>
                      </li>
                    ))}
                </ul>
              </>
            ) : (
              <div className="empty-state">
                <Icon name="box" size={42} />
                <h2>
                  {tab === 'Mods' ? 'Nenhum mod sincronizado' : 'Nenhum resource pack sincronizado'}
                </h2>
                <p>
                  O catálogo será carregado a partir do manifesto oficial assinado.
                  <br />
                  Nenhum arquivo foi baixado ou alterado.
                </p>
              </div>
            )}
          </>
        )}
      </section>
    </>
  );
}
