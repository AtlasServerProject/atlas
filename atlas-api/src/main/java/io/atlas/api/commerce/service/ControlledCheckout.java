package io.atlas.api.commerce.service;
import java.time.Clock;
import java.time.Instant;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
/** Time-limited account and product permission for validating checkout before public sales open. */
@Component
public class ControlledCheckout {
 private final UUID account;private final String slug;private final Instant expires;private final Clock clock;
 public ControlledCheckout(@Value("${atlas.commerce.controlled-account:}") String account,@Value("${atlas.commerce.controlled-product:}") String slug,@Value("${atlas.commerce.controlled-until:}") String until,Clock clock){this.account=account.isBlank()?null:UUID.fromString(account);this.slug=slug;this.expires=until.isBlank()?Instant.MIN:Instant.parse(until);this.clock=clock;}
 public boolean allows(UUID user,String product){return account!=null&&account.equals(user)&&!slug.isBlank()&&slug.equals(product)&&clock.instant().isBefore(expires);}
}
