# Automatic crate result closing

Built on deployed Core 1.40.5+crate.2. The rolling menu closes five seconds after the final reward is shown. A monotonic deadline is set only on the first reveal; delivery completion does not reset it. The server checks only the currently open crate-result menu, leaving previews and other screens untouched. Closing does not cancel or duplicate delivery.

Exact reward alignment and private click/level-up sounds preserved. No worlds, configuration, database records or authentication behavior changed. Timeline tests include the five-second boundary, late ticks and monotonic counter wrap. In-game confirmation still required.
