package io.atlas.api.system.controller;

import io.atlas.api.system.model.SystemInfo;
import io.atlas.api.system.service.SystemService;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class SystemController {
    private final SystemService service;
    public SystemController(SystemService service) { this.service = service; }
    @GetMapping("/api/v1/system")
    ResponseEntity<SystemInfo> system() { return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(service.info()); }
    @GetMapping("/api/v1/auth/csrf")
    ResponseEntity<CsrfInfo> csrf(CsrfToken token) {
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(new CsrfInfo(token.getToken(), token.getHeaderName()));
    }
    public record CsrfInfo(String token, String headerName) { }
}
