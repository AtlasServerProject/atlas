package io.atlas.api.commerce.controller;
import io.atlas.api.commerce.model.CommerceModels.Proof;
import io.atlas.api.commerce.service.IdentityService;
import io.atlas.api.auth.service.RateLimiter;
import io.atlas.api.shared.error.ApiFailure;
import io.atlas.api.shared.web.RequestIdFilter;
import jakarta.validation.Valid;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;
@RestController
public class CoreIdentityController {
 private final IdentityService identity;private final RateLimiter limits;private final byte[] key;
 public CoreIdentityController(IdentityService identity,RateLimiter limits,@Value("${atlas.core.key:}") String key){this.identity=identity;this.limits=limits;this.key=key.getBytes(StandardCharsets.UTF_8);if(this.key.length>0&&this.key.length<43)throw new IllegalArgumentException("Core integration key must contain at least 256 bits.");}
 @PostMapping("/internal/v1/minecraft/proofs") ResponseEntity<Void> proof(@RequestHeader(value="X-Atlas-Key",defaultValue="") String supplied,@Valid @RequestBody Proof proof,HttpServletRequest r){if(key.length<43||!java.util.List.of("127.0.0.1","0:0:0:0:0:0:0:1","::1").contains(r.getRemoteAddr())||!MessageDigest.isEqual(key,supplied.getBytes(StandardCharsets.UTF_8)))throw new ApiFailure(HttpStatus.FORBIDDEN,"CORE_AUTH_REQUIRED","Acesso não autorizado.");limits.check("CORE_PROOF",proof.subject().toString(),10);identity.prove(proof,(String)r.getAttribute(RequestIdFilter.ATTRIBUTE));return ResponseEntity.noContent().build();}
}
