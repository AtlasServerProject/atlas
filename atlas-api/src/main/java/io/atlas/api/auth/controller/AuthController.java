package io.atlas.api.auth.controller;
import io.atlas.api.auth.model.Account.UserView;
import io.atlas.api.auth.model.AuthRequests;
import io.atlas.api.auth.model.SessionIdentity;
import io.atlas.api.auth.service.AuthService;
import io.atlas.api.auth.service.AuthProperties;
import io.atlas.api.auth.service.RateLimiter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import java.time.Clock;
import java.util.List;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.security.web.csrf.CsrfTokenRepository;
import org.springframework.security.web.authentication.session.ChangeSessionIdAuthenticationStrategy;
import org.springframework.web.bind.annotation.*;
@RestController
@RequestMapping("/api/v1")
public class AuthController {
    private final AuthProperties properties;private final AuthService auth;private final RateLimiter limits;private final Clock clock;private final SecurityContextRepository contexts;private final CsrfTokenRepository csrf;
    public AuthController(AuthProperties properties,AuthService auth,RateLimiter limits,Clock clock,SecurityContextRepository contexts,CsrfTokenRepository csrf) {this.properties=properties;this.auth=auth;this.limits=limits;this.clock=clock;this.contexts=contexts;this.csrf=csrf;}
    private void limit(String scope,String email,HttpServletRequest request) {
        // Remote address only: do not trust X-Forwarded-For until an explicit proxy trust policy exists.
        limits.check(scope+":ip",request.getRemoteAddr(),properties.ipAttempts());limits.check(scope+":account",auth.normalize(email),properties.accountAttempts());
    }
    @PostMapping("/auth/register")
    ResponseEntity<Void> register(@Valid @RequestBody AuthRequests.Register body,HttpServletRequest request) {
        limit("REGISTER",body.email(),request);auth.register(body);return ResponseEntity.accepted().build();
    }
    @PostMapping("/auth/login")
    ResponseEntity<UserView> login(@Valid @RequestBody AuthRequests.Login body,HttpServletRequest request,HttpServletResponse response) {
        limit("LOGIN",body.email(),request);var account=auth.login(body);
        var identity=new SessionIdentity(account.id(),account.authVersion(),clock.instant());
        var authentication=UsernamePasswordAuthenticationToken.authenticated(identity,null,List.of(new SimpleGrantedAuthority("ROLE_"+account.role())));
        request.getSession(true);new ChangeSessionIdAuthenticationStrategy().onAuthentication(authentication,request,response);
        csrf.saveToken(null,request,response);
        var context=SecurityContextHolder.createEmptyContext();context.setAuthentication(authentication);SecurityContextHolder.setContext(context);contexts.saveContext(context,request,response);
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(account.view());
    }
    @PostMapping("/auth/logout") ResponseEntity<Void> logout(HttpServletRequest request,HttpServletResponse response) {
        SecurityContextHolder.clearContext();var session=request.getSession(false);if(session!=null) session.invalidate();csrf.saveToken(null,request,response);return ResponseEntity.noContent().build();
    }
    @GetMapping("/users/me") ResponseEntity<UserView> me(@org.springframework.security.core.annotation.AuthenticationPrincipal SessionIdentity principal) {
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(auth.current(principal.id()).view());
    }
    @PostMapping("/auth/resend-verification") ResponseEntity<Void> resend(@Valid @RequestBody AuthRequests.EmailRequest body,HttpServletRequest request) {limit("RESEND",body.email(),request);auth.resend(body.email());return ResponseEntity.accepted().build();}
    @PostMapping("/auth/forgot-password") ResponseEntity<Void> forgot(@Valid @RequestBody AuthRequests.EmailRequest body,HttpServletRequest request) {limit("FORGOT",body.email(),request);auth.forgot(body.email());return ResponseEntity.accepted().build();}
    @PostMapping("/auth/verify-email") ResponseEntity<Void> verify(@Valid @RequestBody AuthRequests.Token body,HttpServletRequest request) {limits.check("VERIFY:ip",request.getRemoteAddr(),properties.ipAttempts());auth.verify(body.token());return ResponseEntity.noContent().build();}
    @PostMapping("/auth/reset-password") ResponseEntity<Void> reset(@Valid @RequestBody AuthRequests.Reset body,HttpServletRequest request) {limits.check("RESET:ip",request.getRemoteAddr(),properties.ipAttempts());auth.reset(body.token(),body.password());return ResponseEntity.noContent().build();}
}
