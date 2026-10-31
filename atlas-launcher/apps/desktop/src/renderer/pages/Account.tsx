import type { PublicAccount } from '../../main/auth/microsoft';
import { Icon } from '../components/Icon';
export function Account({
  onLogin,
  account,
  onSignOut,
}: {
  onLogin: () => void;
  account?: PublicAccount;
  onSignOut: () => void;
}) {
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="overline">SUA IDENTIDADE</span>
          <h1>Conta e perfil</h1>
          <p>
            {account
              ? account.kind === 'offline'
                ? 'Perfil offline selecionado para acessar o Atlas.'
                : 'Sua conta Microsoft está conectada ao Atlas.'
              : 'Conecte sua conta para iniciar sua jornada.'}
          </p>
        </div>
      </div>
      <section className="panel account-panel">
        <span className="profile-placeholder">
          <Icon name="user" size={38} />
        </span>
        <div>
          <h2>{account?.name ?? 'Nenhuma conta conectada'}</h2>
          <p>
            {account
              ? account.kind === 'offline'
                ? 'Nickname local. A identidade será verificada pelo /login do servidor.'
                : 'Perfil Minecraft Java validado pela Microsoft.'
              : 'Não há sessão, nickname verificado ou dados de jogador salvos.'}
          </p>
        </div>
        <div className="account-summary">
          <article>
            Tempo de jogo<strong>—</strong>
          </article>
          <article>
            Última sessão<strong>—</strong>
          </article>
          <article>
            Perfil Minecraft
            <strong>
              {account
                ? account.kind === 'offline'
                  ? 'Offline · Atlas'
                  : 'Microsoft · Java'
                : 'Não conectado'}
            </strong>
          </article>
        </div>
        <button className="secondary wide" onClick={account ? onSignOut : onLogin}>
          <Icon name="user" size={16} />
          {account ? 'Sair da conta neste launcher' : 'Ver opções de acesso'}
        </button>
        <p className="muted">
          O launcher nunca solicita sua senha Microsoft diretamente. Tokens ficam somente no
          processo principal e no cache cifrado do sistema, quando disponível.
        </p>
      </section>
    </>
  );
}
