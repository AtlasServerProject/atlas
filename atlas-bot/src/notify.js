// Utilitário executado no mesmo host do bot; não recebe token Discord.
const [type, ...words] = process.argv.slice(2);
const secret = process.env.ATLAS_BRIDGE_SECRET;
if (!secret || !type || !words.length) {
  console.error('Configure ATLAS_BRIDGE_SECRET e use: npm run notify -- started "Mensagem"');
  process.exit(1);
}
try {
  const response = await fetch(`http://127.0.0.1:${Number(process.env.ATLAS_BRIDGE_PORT || 8787)}/events`, {
    method: 'POST', headers: { Authorization: `Bearer ${secret}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, message: words.join(' ') }), signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) throw new Error();
  console.log('Aviso entregue ao Discord.');
} catch { console.error('Falha no envio. Verifique o bot, a chave, o evento e o canal configurado.'); process.exitCode = 1; }
