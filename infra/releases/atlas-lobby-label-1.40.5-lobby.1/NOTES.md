# Lobby naming

Player-facing Lobby Emerald is now Lobby: HUD/sidebar/bossbar, welcome/travel/purchases/RTP/respawn messages, and default warp title. `/lobby` now works directly; `/lobby emerald` remains compatible. Canonical warp is lobby; `/warp emerald` forwards to it. Deployment migrates the existing emerald warp record preserving coordinates/access/state and all unrelated destinations. Spawn NPC and compass destination retain Emerald as the region name. Internal world IDs and all unrelated code, crate rewards/lighting/account data are unchanged.
