import { PROJECT } from '../../shared/project';
import { useState } from 'react';
import type { Bootstrap, RuntimeState, Settings as Preferences } from '../../shared/contracts';
import { Icon } from '../components/Icon';
export function Settings({
  data,
  runtime,
  settings,
  onChange,
  onSave,
  message,
  saving,
}: {
  data?: Bootstrap;
  runtime?: RuntimeState;
  settings?: Preferences;
  onChange: (value: Preferences) => void;
  onSave: () => void;
  message: string;
  saving: boolean;
}) {
  const [tab, setTab] = useState('Geral');
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="overline">DO SEU JEITO</span>
          <h1>Configurações</h1>
          <p>Prepare o Minecraft para este computador.</p>
        </div>
      </div>
      <section className="panel settings-panel">
        <div className="tabs">
          {['Geral', 'Minecraft', 'Desempenho', 'Avançado'].map((label) => (
            <button
              key={label}
              className={tab === label ? 'active' : ''}
              onClick={() => setTab(label)}
            >
              {label}
            </button>
          ))}
        </div>
        {tab === 'Avançado' ? (
          <>
            <h3>Diagnóstico</h3>
            <button
              className="secondary"
              disabled={!window.atlas}
              onClick={() => void window.atlas?.openDiagnostics()}
            >
              Abrir diagnósticos
            </button>
            <p>
              Os diagnósticos de inicialização do Minecraft ficam nesta pasta. Tokens são ocultados
              no registro do launcher.
            </p>
            <p className="muted">
              Launcher {data?.version ?? PROJECT.version} ·{' '}
              {data?.platform ?? 'Prévia no navegador'}
            </p>
          </>
        ) : tab === 'Geral' ? (
          <>
            <label className="field">
              Diretório reservado de instalação
              <code>{data?.installationDirectory ?? 'Disponível no aplicativo desktop'}</code>
            </label>
            <p className="muted">
              Nesta versão, a pasta é definida pelo launcher para manter a instalação separada.
            </p>
            {settings && (
              <label className="toggle">
                <span>
                  Minimizar o launcher ao iniciar o jogo
                  <small>O launcher volta a aparecer quando o Minecraft for encerrado.</small>
                </span>
                <input
                  type="checkbox"
                  checked={settings.minimizeOnLaunch}
                  onChange={(e) => onChange({ ...settings, minimizeOnLaunch: e.target.checked })}
                />
              </label>
            )}
          </>
        ) : settings && data && data.maxRamMb >= 512 ? (
          tab === 'Minecraft' ? (
            <>
              <div className="resolution">
                <label className="field">
                  Largura
                  <input
                    type="number"
                    min={854}
                    max={7680}
                    value={settings.width}
                    onChange={(e) => onChange({ ...settings, width: Number(e.target.value) })}
                  />
                </label>
                <label className="field">
                  Altura
                  <input
                    type="number"
                    min={480}
                    max={4320}
                    value={settings.height}
                    onChange={(e) => onChange({ ...settings, height: Number(e.target.value) })}
                  />
                </label>
              </div>
              <label className="toggle">
                <span>Iniciar o Minecraft em tela cheia</span>
                <input
                  type="checkbox"
                  checked={settings.fullscreen}
                  onChange={(e) => onChange({ ...settings, fullscreen: e.target.checked })}
                />
              </label>
            </>
          ) : (
            <div>
              <p className="muted">
                RAM é um limite máximo, não memória liberada. O launcher ajusta o limite desta
                sessão se necessário, sem exigir que todo o limite esteja livre de uma vez. O jogo
                inicia com 512 MB de heap e pode crescer até o limite escolhido.
              </p>
              {runtime?.memory && (
                <p role="status">
                  Disponível agora:{' '}
                  {(runtime.memory.availableMb / 1024).toLocaleString('pt-BR', {
                    maximumFractionDigits: 1,
                  })}{' '}
                  GB · Total:{' '}
                  {(runtime.memory.totalMb / 1024).toLocaleString('pt-BR', {
                    maximumFractionDigits: 1,
                  })}{' '}
                  GB
                </p>
              )}
              {runtime?.memory?.recommendedMb ? (
                <button
                  className="secondary"
                  onClick={() => onChange({ ...settings, ramMb: runtime.memory!.recommendedMb })}
                >
                  Usar valor recomendado (
                  {(runtime.memory.recommendedMb / 1024).toLocaleString('pt-BR')} GB)
                </button>
              ) : (
                runtime?.memory && (
                  <p className="muted">
                    4 GB são recomendados, mas você pode tentar iniciar com menos memória.
                  </p>
                )
              )}
              <label className="field ram-field">
                Memória RAM máxima
                <strong>
                  {(settings.ramMb / 1024).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} GB
                </strong>
                <input
                  type="range"
                  min={512}
                  max={data.maxRamMb}
                  step={256}
                  value={settings.ramMb}
                  onChange={(e) => onChange({ ...settings, ramMb: Number(e.target.value) })}
                />
                <small>
                  Limite: {data.maxRamMb.toLocaleString('pt-BR')} MB, mantendo uma reserva de
                  memória para o sistema.
                </small>
              </label>
            </div>
          )
        ) : (
          <p>Configurações locais disponíveis no aplicativo desktop, com memória suficiente.</p>
        )}
        {settings && tab !== 'Avançado' && (
          <div className="settings-actions">
            <button
              className="primary"
              disabled={saving || !data || data.maxRamMb < 512}
              onClick={onSave}
            >
              <Icon name="check" size={16} />
              {saving ? 'Salvando…' : 'Salvar preferências'}
            </button>
            <span role="status">{message}</span>
          </div>
        )}
        <p className="settings-note">
          As preferências ficam salvas neste computador e são aplicadas na próxima inicialização do
          Minecraft.
        </p>
      </section>
    </>
  );
}
