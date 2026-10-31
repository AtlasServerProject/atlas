# Crate Hidden Abilities

Built on Core 1.40.5+crate.3. Adds the operator-selected 1/100 HA chance to newly generated rewards whose actual form lists a HiddenAbility. Same independent chance for normal/shiny and all crates, including monthly. Uses Cobblemon HiddenAbilityProperty to apply and verify the ability before reservation/JSON persistence. Unsupported forms keep their ordinary ability. Recovery/retries deserialize the saved Pokemon and never reroll HA. Existing pending prizes are unchanged.

Delivery chat marks HA wins. Preview describes the HA rate and retains weighted species/shiny odds. Reel alignment, private sounds and five-second auto-close preserved. No worlds/config/schema/authentication changes.

Policy and reel regression tests passed; compilation succeeded. Live HA draw/serialization confirmation still needs an in-game opening after installation. This 1% rate is an Atlas choice, not a claim about default wild spawns.
