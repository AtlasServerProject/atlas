import { createServer } from 'node:http';
import { timingSafeEqual } from 'node:crypto';

export function authorized(header, secret) {
  if (!secret) return false;
  const actual = Buffer.from(header || '');
  const expected = Buffer.from(`Bearer ${secret}`);
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}
export function eventMessage(body) {
  const titles = { started: 'Servidor iniciado', stopping: 'Servidor encerrando', maintenance: 'Manutenção', announcement: 'Aviso do Minecraft' };
  if (!body || !Object.hasOwn(titles, body.type) || typeof body.message !== 'string' || !body.message.trim() || body.message.length > 1500) {
    throw new Error('Evento inválido.');
  }
  return `**${titles[body.type]}**\n${body.message}`;
}
export function createBridge(secret, send) {
  let lastAccepted = 0;
  return createServer({ requestTimeout: 10000, headersTimeout: 10000 }, async (req, res) => {
    const end = (status, text) => { res.writeHead(status, { 'Content-Type': 'text/plain; charset=utf-8' }); res.end(text); };
    if (req.method !== 'POST' || req.url !== '/events') return end(404, 'Não encontrado');
    if (!authorized(req.headers.authorization, secret)) return end(401, 'Não autorizado');
    if (!(req.headers['content-type'] || '').startsWith('application/json')) return end(415, 'Use application/json');
    if (Date.now() - lastAccepted < 2000) return end(429, 'Aguarde antes do próximo evento');
    const chunks = [];
    let size = 0;
    try {
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 8192) return end(413, 'Evento muito grande');
        chunks.push(chunk);
      }
      let message;
      try { message = eventMessage(JSON.parse(Buffer.concat(chunks).toString('utf8'))); } catch { return end(400, 'Evento inválido'); }
      if (Date.now() - lastAccepted < 2000) return end(429, 'Aguarde antes do próximo evento');
      lastAccepted = Date.now();
      await send(message);
      end(202, 'Enviado');
    } catch { if (!res.headersSent) end(503, 'Não foi possível publicar'); }
  });
}
