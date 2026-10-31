import { useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';
type Scene = 'milotic' | 'surf' | 'lighthouse';
const clips: Record<Scene, string> = {
  milotic: 'atlas-milotic-loop-hq',
  surf: 'atlas-surf-hq',
  lighthouse: 'atlas-lighthouse-hq',
};
export function VideoBackground({ scene }: { scene: Scene }) {
  const video = useRef<HTMLVideoElement>(null);
  const container = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(
    () => matchMedia('(prefers-reduced-motion: reduce)').matches,
  );
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const element = video.current;
    const host = container.current;
    if (!element || !host) return;
    let visible = false;
    let disposed = false;
    const update = () => {
      if (!paused && !document.hidden && visible) {
        void element.play().catch(() => {
          if (!disposed) setReady(false);
        });
      } else element.pause();
    };
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      update();
    });
    observer.observe(host);
    document.addEventListener('visibilitychange', update);
    return () => {
      disposed = true;
      observer.disconnect();
      document.removeEventListener('visibilitychange', update);
      element.pause();
    };
  }, [paused]);
  useEffect(() => {
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setPaused(media.matches);
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  const path = 'assets/media/' + clips[scene];
  return (
    <div ref={container} className="video-background">
      <video
        ref={video}
        src={path + '.mp4'}
        poster={path + '.jpg'}
        muted
        loop
        playsInline
        preload="metadata"
        aria-hidden="true"
        className={ready ? 'playing' : ''}
        onPlaying={() => setReady(true)}
        onError={() => {
          setFailed(true);
          setReady(false);
        }}
      />
      <img src={path + '.jpg'} alt="" className={ready ? 'video-poster hidden' : 'video-poster'} />
      <button
        className="video-toggle"
        disabled={failed}
        aria-label={
          failed
            ? 'Vídeo indisponível'
            : paused
              ? 'Reproduzir vídeo de fundo'
              : 'Pausar vídeo de fundo'
        }
        title={
          failed ? 'Exibindo imagem de reserva' : paused ? 'Reproduzir animação' : 'Pausar animação'
        }
        onClick={() => setPaused(!paused)}
      >
        <Icon name={paused ? 'play' : 'pause'} size={12} />
      </button>
    </div>
  );
}
