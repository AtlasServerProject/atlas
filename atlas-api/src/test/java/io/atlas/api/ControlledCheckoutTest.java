package io.atlas.api;
import io.atlas.api.commerce.service.ControlledCheckout;
import java.time.*;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;
class ControlledCheckoutTest {
 @Test void permissionRequiresAccountProductAndUnexpiredDeadline(){var user=UUID.randomUUID();var deadline=Instant.parse("2030-01-01T12:00:00Z");var gate=new ControlledCheckout(user.toString(),"vip-3",deadline.toString(),Clock.fixed(deadline.minusSeconds(1),ZoneOffset.UTC));assertThat(gate.allows(user,"vip-3")).isTrue();assertThat(gate.allows(null,"vip-3")).isFalse();assertThat(gate.allows(UUID.randomUUID(),"vip-3")).isFalse();assertThat(gate.allows(user,"vip-1")).isFalse();assertThat(new ControlledCheckout(user.toString(),"vip-3",deadline.toString(),Clock.fixed(deadline,ZoneOffset.UTC)).allows(user,"vip-3")).isFalse();}
 @Test void incompleteConfigurationNeverEnablesCheckout(){var user=UUID.randomUUID();var clock=Clock.systemUTC();assertThat(new ControlledCheckout("","vip-3","2030-01-01T12:00:00Z",clock).allows(user,"vip-3")).isFalse();assertThat(new ControlledCheckout(user.toString(),"vip-3","",clock).allows(user,"vip-3")).isFalse();assertThat(new ControlledCheckout(user.toString(),"","2030-01-01T12:00:00Z",clock).allows(user,"")).isFalse();}
}
