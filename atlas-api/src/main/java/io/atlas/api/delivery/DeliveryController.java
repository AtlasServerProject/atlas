package io.atlas.api.delivery;
import io.atlas.api.delivery.DeliveryModels.*;
import io.atlas.api.shared.error.ApiFailure;
import io.atlas.api.auth.model.SessionIdentity;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;
import java.util.*;
@RestController
public class DeliveryController {
 private final DeliveryService service;private final byte[] key;
 public DeliveryController(DeliveryService service,@Value("${atlas.core.key:}") String key){this.service=service;this.key=key.getBytes(StandardCharsets.UTF_8);}
 private void auth(String supplied,HttpServletRequest r){if(key.length<43||!List.of("127.0.0.1","::1","0:0:0:0:0:0:0:1").contains(r.getRemoteAddr())||!MessageDigest.isEqual(key,supplied.getBytes(StandardCharsets.UTF_8)))throw new ApiFailure(HttpStatus.FORBIDDEN,"CORE_AUTH_REQUIRED","Acesso não autorizado.");}
 @PostMapping("/internal/v1/deliveries/claim") public List<Delivery> claim(@RequestHeader(value="X-Atlas-Key",defaultValue="") String key,@Valid @RequestBody Claim input,HttpServletRequest r){auth(key,r);return service.claim();}
 @PostMapping("/internal/v1/deliveries/{id}/ack") public ResponseEntity<Void> ack(@RequestHeader(value="X-Atlas-Key",defaultValue="") String key,@PathVariable UUID id,@Valid @RequestBody Ack input,HttpServletRequest r){auth(key,r);service.ack(id,input);return ResponseEntity.noContent().build();}
 @PostMapping("/internal/v1/deliveries/{id}/failed") public ResponseEntity<Void> failed(@RequestHeader(value="X-Atlas-Key",defaultValue="") String key,@PathVariable UUID id,@Valid @RequestBody Failed input,HttpServletRequest r){auth(key,r);service.failed(id,input);return ResponseEntity.noContent().build();}
 @PostMapping("/internal/v1/vip/statuses") public ResponseEntity<Void> statuses(@RequestHeader(value="X-Atlas-Key",defaultValue="") String key,@Valid @RequestBody List<@Valid Balance> input,HttpServletRequest r){auth(key,r);service.sync(input);return ResponseEntity.noContent().build();}
 @GetMapping("/api/v1/users/me/vip") public ResponseEntity<VipView> vip(@AuthenticationPrincipal SessionIdentity user){return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(service.vip(user.id()));}
 @GetMapping("/api/v1/admin/deliveries") public List<Attempt> attempts(@RequestParam(defaultValue="0") int page){return service.attempts(page);}
 @PostMapping("/api/v1/admin/deliveries/{id}/retry") public ResponseEntity<Void> retry(@AuthenticationPrincipal SessionIdentity user,@PathVariable UUID id,@Valid @RequestBody Retry input){service.retry(id,user.id(),input.reason());return ResponseEntity.noContent().build();}
}
