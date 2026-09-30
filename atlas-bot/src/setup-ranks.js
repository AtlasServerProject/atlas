import { Client, GatewayIntentBits, Routes } from 'discord.js';
import { config } from './config.js';
const ranks = [['DONO',0xaa0000],['ADM',0xff5555],['MOD',0x5555ff],['SUP',0x55ff55],['VIP',0xffaa00],['BETA',0xaa00aa],['Membro',0xffffff]];
const settings=config();
const client=new Client({intents:[GatewayIntentBits.Guilds]});
try {
 await client.login(settings.token);
 const guild=await client.guilds.fetch(settings.guildId);
 await guild.roles.fetch(); await guild.members.fetchMe();
 const selected=[];
 for(const [name,color] of ranks){
  let role=guild.roles.cache.find(r=>(r.name===name||(name==='SUP'&&r.name==='AJD'))&&!r.managed);
  if(!role) role=await guild.roles.create({name,colors:{primaryColor:color},hoist:true,mentionable:false,permissions:[],reason:'Cargos Atlas semelhantes ao Minecraft solicitados pelo dono'});
  else {if(!role.editable) throw new Error('ROLE_HIERARCHY');await role.edit({name,colors:{primaryColor:color},hoist:true,mentionable:false});}
  selected.push(role);
 }
 await guild.roles.fetch();
 const ceiling=guild.members.me.roles.highest.position;
 if(ceiling<=selected.length) throw new Error('ROLE_HIERARCHY');
 const current = [...selected].sort((a,b)=>b.position-a.position);
 if(current.map(r=>r.id).join(',') !== selected.map(r=>r.id).join(',')) await client.rest.patch(Routes.guildRoles(guild.id), { body: selected.map((role,i)=>({id:role.id,position:selected.length-i})) });
 await guild.roles.fetch();
 const result=selected.map(r=>guild.roles.cache.get(r.id)).sort((a,b)=>b.position-a.position);
 console.log(JSON.stringify(result.map(r=>({name:r.name,color:r.hexColor,position:r.position,permissions:r.permissions.toArray()}))));
 if(result.map(r=>r.name).join(',')!==ranks.map(r=>r[0]).join(',')) throw new Error('ORDER_VERIFICATION');
}catch(error){console.error('Falha ao configurar cargos:',error.code||error.message);process.exitCode=1;}finally{client.destroy();}
