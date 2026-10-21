package io.atlas.api.support;
import java.util.UUID;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.http.*;
import io.atlas.api.auth.model.SessionIdentity;
import io.atlas.api.auth.service.RateLimiter;
@RestController
public class SupportController {
 public record Create(@NotNull UUID orderId,@NotBlank @Size(max=120) String title,@NotBlank @Size(max=4000) String body){}
 public record Reply(@NotBlank @Size(max=4000) String body){}
 public record Status(@NotBlank String status){}
 private final SupportService service;private final RateLimiter limits;
 public SupportController(SupportService service,RateLimiter limits){this.service=service;this.limits=limits;}
 private <T> ResponseEntity<T> ok(T body){return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(body);}
 @GetMapping("/api/v1/admin/team") public ResponseEntity<?> team(@AuthenticationPrincipal SessionIdentity u,@RequestParam(defaultValue="0") int page){return ok(service.team(u.id(),page));}
 @PostMapping("/api/v1/support/tickets") public ResponseEntity<?> create(@AuthenticationPrincipal SessionIdentity u,@Valid @RequestBody Create b){limits.check("SUPPORT_CREATE",u.id().toString(),10);return ok(service.create(u.id(),b.orderId(),b.title(),b.body()));}
 @GetMapping("/api/v1/support/tickets") public ResponseEntity<?> list(@AuthenticationPrincipal SessionIdentity u,@RequestParam(defaultValue="0") int page){return ok(service.list(u.id(),false,page));}
 @GetMapping("/api/v1/admin/support/tickets") public ResponseEntity<?> queue(@AuthenticationPrincipal SessionIdentity u,@RequestParam(defaultValue="0") int page){return ok(service.list(u.id(),true,page));}
 @GetMapping({"/api/v1/support/tickets/{id}","/api/v1/admin/support/tickets/{id}"}) public ResponseEntity<?> detail(@AuthenticationPrincipal SessionIdentity u,@PathVariable UUID id,@RequestParam(defaultValue="0") int after,jakarta.servlet.http.HttpServletRequest request){return ok(service.detail(u.id(),id,request.getRequestURI().startsWith("/api/v1/admin/"),after));}
 @PostMapping({"/api/v1/support/tickets/{id}/messages","/api/v1/admin/support/tickets/{id}/messages"}) public ResponseEntity<?> reply(@AuthenticationPrincipal SessionIdentity u,@PathVariable UUID id,@Valid @RequestBody Reply b,jakarta.servlet.http.HttpServletRequest request){limits.check("SUPPORT_REPLY",u.id().toString(),30);service.reply(u.id(),id,request.getRequestURI().startsWith("/api/v1/admin/"),b.body());return ResponseEntity.noContent().build();}
 @PostMapping("/api/v1/admin/support/tickets/{id}/status") public ResponseEntity<?> status(@AuthenticationPrincipal SessionIdentity u,@PathVariable UUID id,@Valid @RequestBody Status b){limits.check("SUPPORT_STATUS",u.id().toString(),30);service.status(u.id(),id,b.status());return ResponseEntity.noContent().build();}
}
