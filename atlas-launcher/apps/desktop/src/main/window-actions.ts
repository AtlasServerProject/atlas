import type { WindowAction } from '../shared/contracts';
export function validateWindowAction(value: unknown): WindowAction {
  if (value !== 'minimize' && value !== 'maximize' && value !== 'close')
    throw new Error('Ação de janela inválida.');
  return value;
}
