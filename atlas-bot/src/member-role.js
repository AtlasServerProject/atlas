export async function assignMemberRole(member, settings) {
  if (member.guild.id !== settings.guildId || member.user.bot || !settings.memberRoleId) return;
  if (member.roles.cache.has(settings.memberRoleId)) return;
  const role = await member.guild.roles.fetch(settings.memberRoleId);
  if (!role || role.id === member.guild.id || role.managed || !role.editable) {
    throw new Error('Cargo Membro indisponível para atribuição.');
  }
  await member.roles.add(role, 'Cargo Membro automático na entrada no Atlas');
}
