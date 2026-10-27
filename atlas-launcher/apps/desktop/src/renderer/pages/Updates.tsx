import type { RuntimeState } from '../../shared/contracts';
import { VideoBackground } from '../components/VideoBackground';
import { Icon } from '../components/Icon';
export function Updates({
  runtime,
  onInstall,
  onCancel,
}: {
  runtime?: RuntimeState;
  onInstall: () => void;
  onCancel: () => void;
}) {
  const state = runtime?.installation;
  const busy = state && ['checking', 'downloading-game', 'downloading-pack'].includes(state.status);
  const steps = [
    'Verificar versão oficial',
    'Baixar arquivos necessários',
    'Validar integridade',
    'Instalar o modpack',
    'Liberar o jogo',
  ];
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="overline">SEMPRE PRONTO PARA A AVENTURA</span>
          <h1>Atualizações do Atlas</h1>
          <p>Download e verificação dos arquivos oficiais do Atlas.</p>
        </div>
        <span className="badge neutral">
          {state?.status === 'ready'
            ? 'Verificado'
            : busy
              ? 'Em andamento'
              : 'Pronto para preparar'}
        </span>
      </div>
      <div className="updates-grid">
        <section className="panel">
          <h2>Preparação do modpack</h2>
          <p>{state?.label ?? 'Prepare sua instalação Atlas.'}</p>
          <div className="inactive-progress" role="status">
            {state?.total
              ? `${state.completed} / ${state.total} itens nesta etapa (${Math.round((state.completed / state.total) * 100)}%)`
              : 'Manifesto Atlas assinado disponível no aplicativo.'}
          </div>
          {busy && (
            <progress
              className="installation-progress"
              max={state.total || 1}
              value={state.total ? state.completed : undefined}
            />
          )}
          <div className="update-actions">
            <button
              className="primary"
              disabled={!runtime?.canInstall || !!busy || runtime.busy || runtime.gameRunning}
              onClick={onInstall}
            >
              {state?.status === 'ready' ? 'Verificar instalação' : 'Preparar Minecraft e modpack'}
            </button>
            {busy && (
              <button className="secondary" onClick={onCancel}>
                Cancelar
              </button>
            )}
          </div>
          <ol className="update-steps">
            {[
              'Verificar versão oficial',
              'Baixar arquivos necessários',
              'Validar integridade',
              'Instalar o modpack',
              'Liberar o jogo',
            ].map((step, index) => (
              <li key={step}>
                <span>{index + 1}</span>
                <strong>{step}</strong>
                <small>
                  {state?.status === 'ready'
                    ? index === 4 && runtime?.auth.status !== 'signed-in'
                      ? 'Aguardando login'
                      : 'Concluído'
                    : busy
                      ? 'Em preparação'
                      : 'Aguardando'}
                </small>
              </li>
            ))}
          </ol>
        </section>
        <aside className="updates-aside">
          <div className="update-art">
            <VideoBackground scene="lighthouse" />
          </div>
          <section className="panel">
            <Icon name="info" />
            <h3>Atualizações sem complicação</h3>
            <p>
              O launcher verifica os arquivos oficiais e mostra o progresso real aqui. A barra
              mostra o estado real da instalação; o jogo só é liberado após conferir os arquivos.
            </p>
          </section>
        </aside>
      </div>
    </>
  );
}
