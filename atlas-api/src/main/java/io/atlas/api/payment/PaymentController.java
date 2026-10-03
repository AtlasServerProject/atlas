package io.atlas.api.payment;
import java.util.UUID;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import io.atlas.api.auth.model.SessionIdentity;
import io.atlas.api.auth.service.RateLimiter;
@RestController
public class PaymentController {
 private final PaymentService service;private final RateLimiter limits;
 public PaymentController(PaymentService service,RateLimiter limits){this.service=service;this.limits=limits;}
 @PostMapping("/api/v1/orders/{id}/payment") public ResponseEntity<PaymentService.Checkout> checkout(@AuthenticationPrincipal SessionIdentity account,@PathVariable UUID id){limits.check("PAYMENT_CREATE",account.id().toString(),10);return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(service.checkout(account.id(),id));}
 @PostMapping("/api/v1/webhooks/mercadopago") public ResponseEntity<Void> webhook(@RequestHeader(value="x-signature",required=false) String signature,@RequestHeader(value="x-request-id",required=false) String request,@RequestParam(value="data.id",required=false) String id,@RequestParam(value="type",required=false) String type){service.webhook(signature,request,id,type);return ResponseEntity.ok().build();}
}
