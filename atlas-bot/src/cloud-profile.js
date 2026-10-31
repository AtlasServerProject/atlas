import { Options } from 'discord.js';

export function cloudClientOptions(enabled = process.env.ATLAS_CLOUD_MODE === 'true') {
  if (!enabled) return {};
  return {
    makeCache: Options.cacheWithLimits({
      ...Options.DefaultMakeCacheSettings,
      MessageManager: 0,
      PresenceManager: 0,
      GuildMemberManager: { maxSize: 50, keepOverLimit: member => member.id === member.client.user?.id },
      GuildBanManager: 0,
      ReactionManager: 0,
      ReactionUserManager: 0,
      GuildScheduledEventManager: 0,
    }),
  };
}
