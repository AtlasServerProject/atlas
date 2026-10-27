import {ChannelType,MessageFlags} from 'discord.js';
import {mkdirSync,writeFileSync,appendFileSync,renameSync,existsSync,openSync,fsyncSync,closeSync} from 'node:fs';
import {expireTicketContent} from './retention.js';
import {TicketStore} from './store.js';
import {panel,queueCard,channelPermissions,emptyMentions,ticketCommand,staffRankingCommand,rankingCard} from './ui.js';
import ticketConfig from '../ticket-config.json' with {type:'json'};

export function createTickets(client,settings,options={}) {
 const cfg=options.config||ticketConfig,store=options.store||new TicketStore(),running=new Set();let timer,lastRetention=0;
 const enabled=cfg.guildId===settings.guildId;
 const staff=m=>[cfg.roles.support,cfg.roles.mod,cfg.roles.admin,cfg.roles.owner].some(r=>m.roles.cache.has(r));
 const senior=m=>[cfg.roles.mod,cfg.roles.admin,cfg.roles.owner].some(r=>m.roles.cache.has(r));
 async function guild(){return client.guilds.fetch(cfg.guildId);}
 async function queue(){return (await guild()).channels.fetch(cfg.queueChannelId);}
 async function refresh(t){
  if(t.queue_synced===t.status)return;
  if(!t.queue_message)return;
  await (await queue()).messages.edit(t.queue_message,queueCard(t,cfg,t.assignee?store.total(t.assignee):0));
  store.synced(t.id,t.status);
 }
 async function publish(t){
  const q=await queue();
  if(!t.queue_message){
   // Stable nonce protects short retries after a successful send but failed local acknowledgement.
   const message=await q.send({...queueCard(t,cfg),nonce:`ticket-${t.id}`,enforceNonce:true,allowedMentions:{parse:[],roles:[cfg.roles.support]}});
   store.queue(t.id,message.id);store.synced(t.id,t.status);
  }else await refresh(t);
 }
 async function getChannel(id){try{return await (await guild()).channels.fetch(id);}catch(e){if(e.code===10003)return null;throw e;}}
 async function adopt(t){
  const channels=await (await guild()).channels.fetch();
  return channels.find(c=>c.parentId===cfg.categoryId&&c.topic===`Atlas ticket #${t.id}`);
 }
 async function archive(t){
  const dir=options.archiveDir||'.runtime/ticket-transcripts';mkdirSync(dir,{recursive:true,mode:0o700});
  const path=`${dir}/ticket-${t.id}.jsonl`,temp=path+'.pending';
  if(t.transcript&&existsSync(t.transcript))return;
  const ch=await getChannel(t.channel);if(!ch)throw Error('Canal ausente sem transcrição; revisão administrativa necessária.');
  writeFileSync(temp,JSON.stringify({ticket:t.id,requester:t.requester,assignee:t.assignee,closedBy:t.closed_by,summary:t.close_summary,created:t.created})+'\n',{mode:0o600});
  let before;
  for(;;){const messages=await ch.messages.fetch({limit:100,...(before?{before}:{})});if(!messages.size)break;
   for(const m of messages.values())appendFileSync(temp,JSON.stringify({id:m.id,author:m.author.id,date:m.createdTimestamp,content:m.content,embeds:m.embeds.map(e=>e.toJSON()),attachments:[...m.attachments.values()].map(a=>({name:a.name,url:a.url}))})+'\n');
   before=messages.last().id;
  }
  const fd=openSync(temp,'r');try{fsyncSync(fd);}finally{closeSync(fd);}
  renameSync(temp,path);store.transcript(t.id,path);
 }
 async function complete(t){
  if(running.has(t.id))return;running.add(t.id);
  try {
   await archive(t);t=store.get(t.id);
   const channel=await getChannel(t.channel);if(channel)await channel.delete(`Ticket #${t.id} concluído`);
   store.finish(t.id);t=store.get(t.id);await refresh(t);
  } finally {running.delete(t.id);}
 }
 async function claim(t,member){
  if(running.has(t.id)||!store.claim(t.id,member.id))return false;
  running.add(t.id);
  try{
   const g=await guild();await g.members.fetch(t.requester);
   let channel=await adopt(t);
   if(!channel)channel=await g.channels.create({name:`ticket-${t.id}`,type:ChannelType.GuildText,parent:cfg.categoryId,topic:`Atlas ticket #${t.id}`,permissionOverwrites:channelPermissions(g.id,client.user.id,{...t,assignee:member.id},cfg.roles),reason:`Aceite do ticket #${t.id}`});
   store.activate(t.id,channel.id);t=store.get(t.id);
   await channel.send({content:`🎫 **Atendimento #${t.id}**\n<@${t.requester}>, seu atendimento foi assumido por <@${member.id}>.\n\n**Pedido:**\n${t.reason}\n\nO canal é exclusivo para vocês e MOD/ADM/DONO. Ao concluir, o atendente usa \`/ticketfinalizar resumo:<resultado>\`.`,allowedMentions:{parse:[],users:[t.requester,member.id]}});
   await refresh(t);return true;
  }catch(e){
   // On an uncertain creation response, retain CLAIMING so reconciliation can adopt the channel.
   if(!store.get(t.id).channel){let found;try{found=await adopt(t);}catch{throw e;}if(found)store.activate(t.id,found.id);else store.release(t.id);}
   throw e;
  }finally{running.delete(t.id);}
 }
 async function handle(i){
  const command=i.isChatInputCommand()&&['ticketfinalizar','rankstaff'].includes(i.commandName);
  const component=(i.isButton()||i.isModalSubmit())&&i.customId.startsWith('atlas:ticket:');
  if(!command&&!component)return false;
  if(!enabled||i.guildId!==cfg.guildId){await i.reply({content:'Atendimento indisponível neste servidor.',flags:MessageFlags.Ephemeral});return true;}
  try{
   if(command&&i.commandName==='rankstaff'){
    if(![cfg.commandsPublicChannelId,cfg.commandsStaffChannelId].includes(i.channelId)){
      await i.reply({content:`Use /rankstaff em <#${cfg.commandsPublicChannelId}>.`,flags:MessageFlags.Ephemeral,allowedMentions:emptyMentions});return true;
    }
    if(i.channelId===cfg.commandsStaffChannelId&&!staff(await i.guild.members.fetch(i.user.id)))throw Error('Canal exclusivo da equipe.');
    await i.deferReply({flags:MessageFlags.Ephemeral});
    await i.editReply(rankingCard(store.ranking(i.options.getInteger('pagina')||1)));return true;
   }
   if(i.isButton()&&i.customId==='atlas:ticket:open'){
    if(i.channelId!==cfg.publicChannelId)throw Error('Abra seu atendimento pelo painel de Tickets.');
    const t=store.active(i.user.id);if(t){await i.reply({content:`Você já tem o ticket #${t.id}${t.channel?` em <#${t.channel}>`:' aguardando atendimento'}.`,flags:MessageFlags.Ephemeral});return true;}
    await i.showModal({custom_id:'atlas:ticket:submit',title:'Iniciar atendimento',components:[{type:1,components:[{type:4,custom_id:'reason',label:'Como podemos ajudar? Não envie senhas.',style:2,min_length:10,max_length:1000,required:true}]}]});return true;
   }
   await i.deferReply({flags:MessageFlags.Ephemeral});
   if(i.isModalSubmit()){
    if(i.customId!=='atlas:ticket:submit'||i.channelId!==cfg.publicChannelId)throw Error('Pedido inválido. Abra pelo painel de Tickets.');
    const reason=i.fields.getTextInputValue('reason').trim();if(reason.length<10||reason.length>1000)throw Error('Descreva sua dúvida em 10 a 1.000 caracteres.');
    const t=store.open(i.user.id,reason);if(!t)throw Error('Você já possui um ticket ativo.');
    try{await publish(t);}catch{await i.editReply(`Ticket #${t.id} registrado. O encaminhamento ao suporte será repetido automaticamente.`);return true;}
    await i.editReply(`🎫 Ticket #${t.id} aberto! O SUP foi avisado. Aguarde um atendente assumir.`);return true;
   }
   const member=await i.guild.members.fetch(i.user.id);if(!staff(member))throw Error('Somente a equipe pode realizar esta ação.');
   if(i.isButton()){
    const match=/^atlas:ticket:claim:(\d+)$/.exec(i.customId);if(!match||i.channelId!==cfg.queueChannelId)throw Error('Ação de ticket inválida.');
    const t=store.get(Number(match[1]));if(!t||t.queue_message!==i.message.id)throw Error('Ticket não encontrado.');
    if(t.requester===i.user.id)throw Error('Outro staff precisa assumir seu atendimento.');
    if(!await claim(t,member))throw Error('Este ticket já foi assumido por outro staff.');
    await i.editReply(`Você assumiu o ticket #${t.id}: <#${store.get(t.id).channel}>.`);return true;
   }
   const t=store.byChannel(i.channelId);if(!t)throw Error('Use /ticketfinalizar dentro do canal de atendimento.');
   if(t.assignee!==member.id&&!senior(member))throw Error('Somente o atendente responsável ou MOD/ADM/DONO pode finalizar.');
   if(t.status==='CLOSING'){await i.editReply('Este atendimento já está sendo encerrado; não haverá pontuação duplicada.');return true;}
   const summary=i.options.getString('resumo',true).trim();if(summary.length<5||summary.length>500)throw Error('Informe um resumo de 5 a 500 caracteres.');
   if(!store.beginClose(t.id,summary,member.id))throw Error('O atendimento já está sendo encerrado.');
   await i.editReply('Atendimento concluído. O registro será preservado e este canal será excluído.');
   try{await complete(store.get(t.id));}catch{await i.editReply('O encerramento ficou pendente. O bot tentará novamente; nenhum ponto será contado antes da exclusão do canal.');}
   return true;
  }catch(e){const text=e.message?.startsWith('Missing')||e.code?'Não foi possível concluir. O estado foi preservado; a equipe deve verificar permissões e tentar novamente.':e.message;try{if(i.deferred||i.replied)await i.editReply({content:text,allowedMentions:emptyMentions});else await i.reply({content:text,flags:MessageFlags.Ephemeral,allowedMentions:emptyMentions});}catch{}return true;}
 }
 let reconciling=false;
 async function reconcile(){if(!enabled||reconciling)return;reconciling=true;try{for(let t of store.pending())try{
   if(running.has(t.id))continue;
   if(t.status==='CLAIMING'){const found=await adopt(t);if(found)store.activate(t.id,found.id);else store.release(t.id);t=store.get(t.id);}
   if(t.status==='OPEN')await publish(t);
   else if(t.status==='CLOSING')await complete(t);
   else if(t.status==='CLOSED'||t.status==='ACTIVE')await refresh(t);
  }catch{console.error(`Tickets: recuperação pendente para #${t.id}.`);}}finally{reconciling=false;}}
 function retain(){if(Date.now()-lastRetention<3600000)return;const days=Number(process.env.ATLAS_TICKET_RETENTION_DAYS||90);const count=expireTicketContent(store,{directory:options.archiveDir||'.runtime/ticket-transcripts',days});lastRetention=Date.now();if(count)console.log(`Tickets: conteúdo local expirado em ${count} atendimento(s) concluído(s).`);}
 async function start(){if(!enabled)return;await (await guild()).commands.create(ticketCommand);await (await guild()).commands.create(staffRankingCommand);const ch=await getChannel(cfg.publicChannelId);await ch.messages.edit(cfg.panelId,panel(false));await reconcile();retain();timer=setInterval(()=>{try{retain();}catch{console.error('Tickets: retenção requer revisão administrativa.');}return reconcile().catch(()=>console.error('Tickets: falha na recuperação.'));},60000);timer.unref();console.log('Tickets habilitados.');}
 function stop(){clearInterval(timer);store.close();}
 return {handle,start,stop,reconcile};
}
