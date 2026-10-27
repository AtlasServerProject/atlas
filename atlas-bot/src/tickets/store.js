import {migration1,migration2} from './migrations.js';
import {DatabaseSync} from 'node:sqlite';
import {mkdirSync,chmodSync} from 'node:fs';
import {dirname} from 'node:path';

export class TicketStore {
  constructor(path='.runtime/tickets.sqlite') {
    if(path!==':memory:'){mkdirSync(dirname(path),{recursive:true,mode:0o700});}
    this.db=new DatabaseSync(path);
    if(path!==':memory:')chmodSync(path,0o600);
    this.db.exec('PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;');
    const version=this.db.prepare('PRAGMA user_version').get().user_version;
    if(version>2)throw new Error('Versão de tickets mais recente que este bot.');
    for(const [index,migration] of [migration1,migration2].entries())if(version<index+1){
      this.db.exec('BEGIN IMMEDIATE');
      try{this.db.exec(migration);this.db.exec(`PRAGMA user_version=${index+1}`);this.db.exec('COMMIT');}
      catch(e){this.db.exec('ROLLBACK');throw e;}
    }
  }
  get(id){return this.db.prepare('SELECT * FROM tickets WHERE id=?').get(id);}
  byChannel(id){return this.db.prepare('SELECT * FROM tickets WHERE channel=? AND status IN (\'ACTIVE\',\'CLOSING\')').get(id);}
  active(user){return this.db.prepare("SELECT * FROM tickets WHERE requester=? AND status NOT IN ('CLOSED','CANCELLED')").get(user);}
  open(user,reason){
    try {return this.get(Number(this.db.prepare('INSERT INTO tickets(requester,reason,created) VALUES(?,?,?)').run(user,reason,Date.now()).lastInsertRowid));}
    catch(e){if(this.active(user))return null;throw e;}
  }
  claim(id,user){return this.db.prepare("UPDATE tickets SET status='CLAIMING',assignee=? WHERE id=? AND status='OPEN'").run(user,id).changes===1;}
  activate(id,channel){return this.db.prepare("UPDATE tickets SET status='ACTIVE',channel=? WHERE id=? AND status='CLAIMING'").run(channel,id).changes===1;}
  release(id){this.db.prepare("UPDATE tickets SET status='OPEN',assignee=NULL WHERE id=? AND status='CLAIMING' AND channel IS NULL").run(id);}
  queue(id,message){this.db.prepare('UPDATE tickets SET queue_message=? WHERE id=?').run(message,id);}
  beginClose(id,summary,actor){return this.db.prepare("UPDATE tickets SET status='CLOSING',close_summary=?,closed_by=? WHERE id=? AND status='ACTIVE'").run(summary,actor,id).changes===1;}
  transcript(id,path){this.db.prepare("UPDATE tickets SET transcript=? WHERE id=? AND status='CLOSING'").run(path,id);}
  finish(id){return this.db.prepare("UPDATE tickets SET status='CLOSED',closed=? WHERE id=? AND status='CLOSING' AND transcript IS NOT NULL").run(Date.now(),id).changes===1;}
  expiredContent(cutoff){return this.db.prepare("SELECT id,transcript FROM tickets WHERE status='CLOSED' AND closed<? AND (transcript IS NOT NULL OR reason!='' OR close_summary!='')").all(cutoff);}
  expireContent(id,cutoff){return this.db.prepare("UPDATE tickets SET transcript=NULL,reason='',close_summary='' WHERE id=? AND status='CLOSED' AND closed<?").run(id,cutoff).changes===1;}
  total(user){return this.db.prepare("SELECT count(*) AS count FROM tickets WHERE assignee=? AND status='CLOSED'").get(user).count;}
  ranking(page=1){
    if(!Number.isInteger(page)||page<1||page>100000)throw new Error('Página inválida.');
    const total=this.db.prepare("SELECT count(DISTINCT assignee) AS count FROM tickets WHERE status='CLOSED' AND assignee IS NOT NULL").get().count;
    const rows=this.db.prepare(`WITH scores AS (
      SELECT assignee, count(*) AS points FROM tickets WHERE status='CLOSED' AND assignee IS NOT NULL GROUP BY assignee
    ) SELECT assignee,points,RANK() OVER (ORDER BY points DESC) AS position FROM scores
    ORDER BY points DESC,assignee ASC LIMIT 10 OFFSET ?`).all((page-1)*10);
    return {rows,total,pages:Math.max(1,Math.ceil(total/10)),page};
  }
  synced(id,status){this.db.prepare('UPDATE tickets SET queue_synced=? WHERE id=?').run(status,id);}
  pending(){return this.db.prepare("SELECT * FROM tickets WHERE status IN ('OPEN','CLAIMING','CLOSING') OR (status IN ('ACTIVE','CLOSED') AND (queue_synced IS NULL OR queue_synced!=status)) ORDER BY id").all();}
  close(){this.db.close();}
}
