import {TicketStore} from '../src/tickets/store.js';
import {expireTicketContent} from '../src/tickets/retention.js';
const apply=process.argv.includes('--apply');const value=process.argv.find(x=>x.startsWith('--days='));const days=value?Number(value.split('=')[1]):90;
const store=new TicketStore();try{const count=expireTicketContent(store,{days,dryRun:!apply});console.log(JSON.stringify({mode:apply?'applied':'dry-run',expiredClosedTickets:count,retentionDays:days}));}finally{store.close();}
