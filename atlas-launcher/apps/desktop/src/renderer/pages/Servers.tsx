import type { RuntimeState } from '../../shared/contracts';
import { VideoBackground } from '../components/VideoBackground';
import { PROJECT } from '../../shared/project';
import { Icon } from '../components/Icon';
export function Servers({ runtime, onPlay }: { runtime?: RuntimeState; onPlay: () => void }) {
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="overline">SUA AVENTURA NO ATLAS</span>
          <h1>Servidor Atlas</h1>
          <p>Entre no Atlas Cobblemon e comece sua jornada.</p>
        </div>
      </div>
      <div className="server-grid">
        {[
          {
            name: 'Atlas Cobblemon',
            description:
              'Explore o Atlas Cobblemon. O Lobby é seu ponto de encontro dentro do servidor.',
            image: 'atlas',
            address: PROJECT.serverAddress,
          },
        ].map((server) => (
          <article className="panel server-card" key={server.name}>
            <div className={'server-art ' + server.image}>
              <VideoBackground scene="surf" />
            </div>
            <div className="server-title">
              <h2>{server.name}</h2>
              <span className="badge neutral">Não consultado</span>
            </div>
            <p>{server.description}</p>
            <span className="server-address">
              <Icon name="server" size={15} />
              {server.address}
            </span>
            <button
              className="primary wide"
              disabled={
                runtime?.installation.status !== 'ready' ||
                runtime?.auth.status !== 'signed-in' ||
                runtime?.gameRunning
              }
              onClick={onPlay}
            >
              Jogar Atlas
            </button>
            <small>Disponível após preparar o jogo. Status online ainda não integrado.</small>
          </article>
        ))}
      </div>
    </>
  );
}
