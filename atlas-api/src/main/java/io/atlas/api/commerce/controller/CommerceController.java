package io.atlas.api.commerce.controller;
import io.atlas.api.commerce.model.CommerceModels.*;
import io.atlas.api.commerce.service.*;
import io.atlas.api.auth.model.SessionIdentity;
import io.atlas.api.auth.service.RateLimiter;
import io.atlas.api.shared.web.RequestIdFilter;
import jakarta.validation.Valid;
import jakarta.servlet.http.HttpServletRequest;
import java.util.UUID;
import org.springframework.http.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api/v1")
public class CommerceController {
 private final IdentityService identity;private final OrderService orders;private final RateLimiter limits;
 public CommerceController(IdentityService identity,OrderService orders,RateLimiter limits){this.identity=identity;this.orders=orders;this.limits=limits;}
 private String request(HttpServletRequest r){return (String)r.getAttribute(RequestIdFilter.ATTRIBUTE);}
 private void limit(SessionIdentity p,String scope){limits.check(scope,p.id().toString(),10);}
 private <T> ResponseEntity<T> ok(T body){return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(body);}
 @GetMapping("/users/me/minecraft-link") ResponseEntity<LinkStatus> status(@AuthenticationPrincipal SessionIdentity p){return ok(identity.status(p.id()));}
 @PostMapping("/users/me/minecraft-link-challenges") ResponseEntity<ChallengeCreated> create(@AuthenticationPrincipal SessionIdentity p,HttpServletRequest r){limit(p,"LINK_CREATE");return ok(identity.create(p.id(),request(r)));}
 @PostMapping("/users/me/minecraft-link-confirmations") ResponseEntity<LinkView> confirm(@AuthenticationPrincipal SessionIdentity p,@Valid @RequestBody Confirmation body,HttpServletRequest r){limit(p,"LINK_CONFIRM");return ok(identity.confirm(p.id(),body,request(r)));}
 @PostMapping("/users/me/minecraft-unlink") ResponseEntity<Void> unlink(@AuthenticationPrincipal SessionIdentity p,@Valid @RequestBody Unlink body,HttpServletRequest r){limit(p,"LINK_UNLINK");identity.unlink(p.id(),body,request(r));return ResponseEntity.noContent().build();}
 @PostMapping("/orders/checkout") ResponseEntity<OrderView> checkout(@AuthenticationPrincipal SessionIdentity p,@RequestHeader(value="Idempotency-Key",required=false) String key,@Valid @RequestBody Checkout body,HttpServletRequest r){limit(p,"CHECKOUT");return ok(orders.checkout(p.id(),key,body,request(r)));}
 @GetMapping("/orders") ResponseEntity<OrdersPage> list(@AuthenticationPrincipal SessionIdentity p,@RequestParam(defaultValue="0") int page){return ok(orders.list(p.id(),page));}
 @GetMapping("/orders/{id}") ResponseEntity<OrderView> detail(@AuthenticationPrincipal SessionIdentity p,@PathVariable UUID id){return ok(orders.detail(p.id(),id));}
}
