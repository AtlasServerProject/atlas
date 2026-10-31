import test from 'node:test';
import assert from 'node:assert/strict';
import { addSuggestionVotes, SUGGESTIONS_CHANNEL_ID } from '../src/suggestions.js';
test('adds both votes to a member suggestion without reading content', async () => {
  const reactions = [];
  await addSuggestionVotes({ guildId: 'atlas', channelId: SUGGESTIONS_CHANNEL_ID, author: { bot: false }, react: async e => reactions.push(e) }, 'atlas');
  assert.deepEqual(reactions, ['✅', '❌']);
});
test('ignores other servers, other channels, bots, system messages and webhooks', async () => {
  for (const override of [{ guildId: 'other' }, { channelId: 'other' }, { author: { bot: true } }, { system: true }, { webhookId: 'hook' }]) {
    await addSuggestionVotes({ guildId: 'atlas', channelId: SUGGESTIONS_CHANNEL_ID, author: { bot: false }, react: () => assert.fail('unexpected vote'), ...override }, 'atlas');
  }
});
