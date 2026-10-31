# Crate reel correction

Built on the exact deployed Core 1.40.5 archive. Only crate menu/service/timeline classes and the version metadata changed. Pending local-login changes are not deployed by this hotfix.

The reel now uses the persisted reward to align the last step, decelerates at 2/4/7/10-tick intervals, keeps the row and winning center unchanged throughout the reveal/delivery, and waits 40 ticks before allowing delivery. Selection weights, key reservation and durable delivery are unchanged. Exact properties distinguish normal/shiny rewards.

Validated 20,100 outcome/pool-size combinations, every visible movement, final center and hold. In-game confirmation after restart is still required.
