import {lstatSync,realpathSync,unlinkSync,existsSync} from 'node:fs';
import {resolve,dirname,basename} from 'node:path';
/** Erase only expired CLOSED-ticket content. Keep ticket IDs/assignees for staff totals. */
export function expireTicketContent(store,{directory='.runtime/ticket-transcripts',days=90,now=Date.now(),dryRun=false}={}) {
 if(!Number.isInteger(days)||days<30||days>365)throw Error('Retenção de tickets deve ser entre 30 e 365 dias.');
 const cutoff=now-days*86400000,root=resolve(directory);let count=0;
 for(const ticket of store.expiredContent(cutoff)) {
  if(ticket.transcript&&existsSync(ticket.transcript)) {
   const path=resolve(ticket.transcript);
   // Reject symlinks, nested directories and any database path outside this archive.
   if(lstatSync(path).isSymbolicLink()||dirname(realpathSync(path))!==realpathSync(root)||basename(path)!==`ticket-${ticket.id}.jsonl`)throw Error('Caminho de transcrição inesperado; revisão necessária.');
   if(!dryRun)unlinkSync(path);
  }
  if(!dryRun)store.expireContent(ticket.id,cutoff);
  count++;
 }
 return count;
}
