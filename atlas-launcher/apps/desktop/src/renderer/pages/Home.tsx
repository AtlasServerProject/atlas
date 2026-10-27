import type { RuntimeState } from '../../shared/contracts';
import { VideoBackground } from '../components/VideoBackground';
import { Icon } from '../components/Icon';
export function Home({
  onModpack,
  onUpdates,
  runtime,
  onInstall,
  onPlay,
}: {
  onModpack: () => void;
  onUpdates: () => void;
  runtime?: RuntimeState;
  onInstall: () => void;
  onPlay: () => void;
}) {
  const ready = runtime?.installation.status === 'ready';
  const busy =
    runtime?.busy ||
    runtime?.gameRunning ||
    (runtime &&
      ['checking', 'downloading-game', 'downloading-pack', 'running'].includes(
        runtime.installation.status,
      ));
  return (
    <>
      <section className="home-hero">
        <VideoBackground scene="milotic" />
        <div className="hero-copy">
          <span className="overline">SEU UNIVERSO. SUA HISTÓRIA.</span>
          <h1>ATLAS COBBLEMON</h1>
          <p>Um mundo de aventuras inspirado em Pokémon, totalmente no Minecraft.</p>
          <div className="installation-state">
            <span className="state-icon">
              <Icon name="download" />
            </span>
            <div>
              <strong>
                {ready
                  ? 'Instalação verificada'
                  : runtime?.gameRunning
                    ? 'Minecraft em execução'
                    : 'Prepare sua aventura'}
              </strong>
              <small>
                {ready
                  ? `Atlas ${runtime?.packVersion} · arquivos conferidos`
                  : (runtime?.installation.label ??
                    'Prepare o Minecraft e o modpack para começar.')}
              </small>
            </div>
          </div>
          <div className="play-group">
            <button
              disabled={
                !!busy || (ready ? runtime?.auth.status !== 'signed-in' : !runtime?.canInstall)
              }
              onClick={ready ? onPlay : onInstall}
            >
              <Icon name="play" size={22} />
              {ready ? 'JOGAR ATLAS' : 'PREPARAR MINECRAFT'}
            </button>
            <button aria-label="Ver instalação do modpack" onClick={onModpack}>
              ⌄
            </button>
          </div>
          <span className="play-caption">
            {ready && runtime?.auth.status !== 'signed-in'
              ? 'Conecte sua conta Microsoft para jogar.'
              : runtime?.canInstall
                ? 'Minecraft, Java 21 e modpack em uma pasta exclusiva.'
                : 'Instalação disponível no pacote Windows x64.'}
          </span>
        </div>
      </section>
      <div className="stat-grid">
        {[
          ['server', '—', 'Jogadores online', 'Sem fonte conectada'],
          [
            'box',
            ready ? runtime!.packVersion : 'Não instalado',
            'Versão do modpack',
            'Catálogo assinado',
          ],
          ['box', '1.21.1', 'Minecraft', 'Java Edition'],
          ['settings', 'Fabric', 'Modloader', runtime?.fabricVersion ?? '0.18.0'],
        ].map(([icon, value, label, note]) => (
          <article className="stat" key={label}>
            <Icon name={icon} />
            <div>
              <strong>{value}</strong>
              <span>{label}</span>
              <small>{note}</small>
            </div>
          </article>
        ))}
      </div>
      <div className="section-heading">
        <h2>Novidades</h2>
        <button className="text-button" onClick={onUpdates}>
          Ver atualizações <Icon name="arrow" size={14} />
        </button>
      </div>
      <div className="news-grid">
        <article className="news-feature">
          <div>
            <VideoBackground scene="surf" />
          </div>
          <section>
            <span className="overline">SUA JORNADA NO ATLAS</span>
            <h3>Um lugar para começar.</h3>
            <p>Seu modpack, sua conta e as novidades da comunidade em um só lugar.</p>
          </section>
        </article>
        <article className="panel news-empty">
          <span className="empty-symbol">
            <Icon name="clock" size={27} />
          </span>
          <h3>Aguardando novidades</h3>
          <p>As publicações oficiais vão aparecer aqui quando o serviço estiver conectado.</p>
          <span className="badge neutral">Sem publicações sincronizadas</span>
        </article>
        <article className="panel ready-card">
          <Icon name="shield" size={28} />
          <h3>Uma instalação só sua</h3>
          <p>O Atlas terá uma pasta própria, separada dos seus outros mundos e modpacks.</p>
          <button className="text-button" onClick={onModpack}>
            Ver modpack <Icon name="arrow" size={14} />
          </button>
        </article>
      </div>
    </>
  );
}
