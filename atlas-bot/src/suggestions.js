// A GuildMessages event is sufficient: voting does not inspect message content.
export const SUGGESTIONS_CHANNEL_ID = '1554830034542526495';
export async function addSuggestionVotes(message, guildId) {
  if (message.guildId !== guildId || message.channelId !== SUGGESTIONS_CHANNEL_ID
      || message.author?.bot || message.webhookId || message.system) return;
  await message.react('✅');
  await message.react('❌');
}
