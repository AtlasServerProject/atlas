import test from 'node:test';
import assert from 'node:assert/strict';
import { assignMemberRole } from '../src/member-role.js';

test('atribui somente o cargo configurado a novos humanos e preserva cargos existentes', async () => {
  const assigned = [];
  const role = { id: 'member', managed: false, editable: true };
  const cache = new Set(['vip']);
  const member = { user: { bot: false }, guild: { id: 'atlas', roles: { fetch: async id => { assert.equal(id, 'member'); return role; } } },
    roles: { cache, add: async r => { assigned.push(r.id); cache.add(r.id); } } };
  const settings = { guildId: 'atlas', memberRoleId: 'member' };
  await assignMemberRole(member, settings);
  await assignMemberRole(member, settings);
  assert.deepEqual(assigned, ['member']);
  assert.ok(cache.has('vip'));
  cache.delete('member');
  member.user.bot = true;
  await assignMemberRole(member, settings);
  member.user.bot = false;
  await assignMemberRole(member, { ...settings, guildId: 'other' });
  await assignMemberRole(member, { ...settings, memberRoleId: undefined });
  assert.equal(assigned.length, 1);
  role.editable = false;
  await assert.rejects(assignMemberRole(member, settings));
});
