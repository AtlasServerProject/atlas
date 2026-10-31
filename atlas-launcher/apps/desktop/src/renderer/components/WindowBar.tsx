import { PROJECT } from '../../shared/project';
import { Icon } from './Icon';
export function WindowBar() {
  return (
    <div className="window-bar">
      <span>
        ATLAS LAUNCHER <b>PRÉVIA {PROJECT.version}</b>
      </span>
      <div>
        {(['minimize', 'maximize', 'close'] as const).map((action) => (
          <button
            key={action}
            aria-label={
              {
                minimize: 'Minimizar',
                maximize: 'Maximizar ou restaurar',
                close: 'Fechar launcher',
              }[action]
            }
            disabled={!window.atlas}
            onClick={() => window.atlas?.windowAction(action).catch(() => {})}
          >
            <Icon
              name={{ minimize: 'minus', maximize: 'square', close: 'close' }[action]}
              size={14}
            />
          </button>
        ))}
      </div>
    </div>
  );
}
