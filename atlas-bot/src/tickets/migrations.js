// SQLite migration 1: durable tickets and one active request per player.
export const migration1 = `
      CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY AUTOINCREMENT, requester TEXT NOT NULL,
      reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN', assignee TEXT, channel TEXT, queue_message TEXT,
      created INTEGER NOT NULL, closed INTEGER, transcript TEXT, close_summary TEXT, closed_by TEXT, queue_synced TEXT);
      CREATE UNIQUE INDEX IF NOT EXISTS one_active_ticket ON tickets(requester) WHERE status NOT IN ('CLOSED','CANCELLED');
`;

export const migration2 = `CREATE INDEX IF NOT EXISTS tickets_closed_assignee
 ON tickets(assignee) WHERE status='CLOSED' AND assignee IS NOT NULL;`;
