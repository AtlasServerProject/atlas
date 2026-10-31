import {PermissionFlagsBits as P,SlashCommandBuilder} from 'discord.js';
export const ticketCommand=new SlashCommandBuilder().setName('ticketfinalizar').setDescription('Concluir o ticket deste canal e registrar o atendimento.').addStringOption(o=>o.setName('resumo').setDescription('Resumo do resultado, sem dados sensíveis.').setRequired(true).setMinLength(5).setMaxLength(500)).toJSON();
export const emptyMentions={parse:[]};
export function panel(disabled=false){return {embeds:[{title:'🎫 Suporte Atlas',description:'Precisa falar com a equipe?\n\nClique abaixo e descreva sua dúvida. O suporte receberá seu pedido. Um staff já está vindo ajudar você!\n\n**Um ticket ativo por jogador.** Não envie senhas ou códigos de acesso.',color:0x239bd3,footer:{text:'Atlas Cobblemon • Atendimento'}}],components:[{type:1,components:[{type:2,style:1,label:'Iniciar Atendimento',emoji:{name:'💬'},custom_id:'atlas:ticket:open',disabled}]}],allowedMentions:emptyMentions};}
export function queueCard(t,config,total){const active=t.status!=='OPEN';const closed=t.status==='CLOSED';return {content:t.status==='OPEN'?`<@&${config.roles.support}>`: '',embeds:[{title:`🎫 Ticket #${t.id}`,description:`**Jogador:** <@${t.requester}>\n**Pedido:**\n${t.reason}\n\n**Estado:** ${closed?'Concluído':t.status==='OPEN'?'Aguardando atendimento':t.status==='CLOSING'?'Encerrando':'Assumido'}${t.assignee?`\n**Atendente:** <@${t.assignee}>`:''}${closed?`\n✅ +1 atendimento para o responsável. Total: **${total ?? 0}**.`:''}`,color:closed?0x32965a:0x239bd3}],components:[{type:1,components:[{type:2,style:3,label:closed?'Concluído':active?'Assumido':'Aceitar atendimento',custom_id:`atlas:ticket:claim:${t.id}`,disabled:active}]}],allowedMentions:emptyMentions};}
export function channelPermissions(guild,bot,t,roles){
 const access=P.ViewChannel|P.ReadMessageHistory|P.SendMessages|P.AttachFiles|P.EmbedLinks;
 return [
  {id:guild,type:0,deny:P.ViewChannel,allow:0n},
  {id:roles.support,type:0,deny:P.ViewChannel,allow:0n},
  ...[...new Set([roles.owner,roles.admin,roles.mod])].map(id=>({id,type:0,allow:access,deny:0n})),
  ...[...new Set([bot,t.requester,t.assignee])].map(id=>({id,type:1,allow:access,deny:0n})),
 ];
}

export const staffRankingCommand=new SlashCommandBuilder().setName('rankstaff').setDescription('Consultar os pontos de atendimentos concluídos pela Staff.').addIntegerOption(o=>o.setName('pagina').setDescription('Página do ranking (10 atendentes por página).').setMinValue(1).setMaxValue(100000)).toJSON();
export function rankingCard(result){
 const lines=result.rows.map(row=>`**${row.position}º** — <@${row.assignee}> · **${row.points} ${row.points===1?'ponto':'pontos'}**`);
 return {embeds:[{title:'🏆 Ranking de Atendimentos — Staff Atlas',description:lines.length?lines.join('\n'):(result.total?'Esta página não tem resultados.':'Nenhum atendimento concluído registrado ainda.'),color:0xf1c40f,footer:{text:`Página ${result.page}/${result.pages} • +1 por ticket concluído para quem assumiu • Empates compartilham a posição`}}],allowedMentions:emptyMentions};
}
