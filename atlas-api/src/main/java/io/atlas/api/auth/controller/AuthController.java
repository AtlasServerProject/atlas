package io.atlas.api.auth.controller;

import io.atlas.api.auth.model.*;
import io.atlas.api.auth.model.Account.UserView;
import io.atlas.api.auth.service.*;
import io.atlas.api.shared.error.ApiFailure;
import io.atlas.api.shared.web.RequestIdFilter;
import jakarta.servlet.http.*;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.io.Serializable;
import java.time.*;
import java.util.*;
import org.springframework.http.*;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.security.web.csrf.CsrfTokenRepository;
import org.springframework.web.bind.annotation.*;

@RestController @RequestMapping("/api/v1")
public class AuthController {
    // Retain the serialized pre-0.9 type so old pending challenges expire cleanly instead of failing session deserialization.
    private record Challenge(UUID id,long version,Instant at,boolean setup) implements Serializable {}
    public record MfaRequired(boolean mfaRequired,boolean setupRequired) {}
    public record SetupRequest(@Size(max=128) String password){@Override public String toString(){return "SetupRequest[redacted]";}}
    public record Code(@NotBlank @Size(min=6,max=32) String code){@Override public String toString(){return "MfaCode[redacted]";}}
    public record Completion(UserView user,List<String> recoveryCodes){@Override public String toString(){return "MfaCompletion[redacted]";}}
    public record Reauthentication(@NotBlank @Size(max=128) String password,@Size(max=32) String code){@Override public String toString(){return "Reauthentication[redacted]";}}
    private final LoginSessions sessions;private final ClientIpResolver clientIp;private final AuthProperties properties;private final AuthService auth;private final RateLimiter limits;
    private final Clock clock;private final SecurityContextRepository contexts;private final CsrfTokenRepository csrf;private final MfaService mfa;private final SecurityEvents events;
    public AuthController(AuthProperties properties,AuthService auth,RateLimiter limits,Clock clock,SecurityContextRepository contexts,CsrfTokenRepository csrf,ClientIpResolver clientIp,MfaService mfa,SecurityEvents events,LoginSessions sessions){this.sessions=sessions;this.properties=properties;this.auth=auth;this.limits=limits;this.clock=clock;this.contexts=contexts;this.csrf=csrf;this.clientIp=clientIp;this.mfa=mfa;this.events=events;}
    private String requestId(HttpServletRequest r){return (String)r.getAttribute(RequestIdFilter.ATTRIBUTE);}
    private void limit(String scope,String email,HttpServletRequest request){limits.check(scope+":ip",clientIp.resolve(request),properties.ipAttempts());limits.check(scope+":account",auth.normalize(email),properties.accountAttempts());}
    @PostMapping("/auth/register") ResponseEntity<Void> register(@Valid @RequestBody AuthRequests.Register body,HttpServletRequest request){limit("REGISTER",body.email(),request);auth.register(body);events.event(null,"REGISTER_REQUEST","ACCEPTED",requestId(request));return ResponseEntity.accepted().build();}
    @PostMapping("/auth/login") ResponseEntity<?> login(@Valid @RequestBody AuthRequests.Login body,HttpServletRequest request,HttpServletResponse response){
        limit("LOGIN",body.email(),request);Account account;
        try{account=auth.login(body);}catch(ApiFailure failure){events.event(null,"LOGIN","FAILURE",requestId(request));throw failure;}
        Object result=sessions.begin(account,request,response);events.event(account.id(),result instanceof LoginSessions.MfaRequired?"LOGIN_MFA_REQUIRED":"LOGIN",result instanceof LoginSessions.MfaRequired?"PENDING":"SUCCESS",requestId(request));return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(result);
    }
    @PostMapping("/auth/mfa/setup") ResponseEntity<MfaService.Setup> setup(@Valid @RequestBody SetupRequest body,@org.springframework.security.core.annotation.AuthenticationPrincipal SessionIdentity principal,HttpServletRequest request){
        Account account;
        if(principal==null){var c=sessions.challenge(request);if(!c.setup())throw new ApiFailure(HttpStatus.CONFLICT,"MFA_ALREADY_ENABLED","Use seu autenticador para entrar.");account=auth.current(c.id());}
        else{
            account=auth.current(principal.id());limit("MFA_SETUP",account.email(),request);
            if(body.password()==null||!auth.login(new AuthRequests.Login(account.email(),body.password())).id().equals(account.id()))throw new ApiFailure(HttpStatus.UNAUTHORIZED,"INVALID_CREDENTIALS","Confirme sua senha.");
            sessions.enrollment(account,request);
        }
        limits.check("MFA_SETUP:account",account.id().toString(),5);var result=mfa.setup(account);events.event(account.id(),"MFA_ENROLLMENT","STARTED",requestId(request));return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(result);
    }
    @PostMapping("/auth/mfa/verify") ResponseEntity<Completion> verifyMfa(@Valid @RequestBody Code body,HttpServletRequest request,HttpServletResponse response){
        var c=sessions.challenge(request);limits.check("MFA:ip",clientIp.resolve(request),properties.ipAttempts());limits.check("MFA:account",c.id().toString(),5);
        List<String> recovery;
        try{recovery=mfa.verify(auth.current(c.id()),body.code(),c.setup());}catch(ApiFailure error){events.event(c.id(),"MFA_VERIFY","FAILURE",requestId(request));throw error;}
        var user=sessions.establish(auth.current(c.id()),request,response,c.at(),clock.instant());events.event(c.id(),c.setup()?"MFA_ENABLED":"LOGIN_MFA","SUCCESS",requestId(request));return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(new Completion(user,recovery));
    }
    @PostMapping("/auth/reauthenticate") ResponseEntity<Void> reauthenticate(@org.springframework.security.core.annotation.AuthenticationPrincipal SessionIdentity principal,@Valid @RequestBody Reauthentication body,HttpServletRequest request,HttpServletResponse response){
        if(principal==null)throw new ApiFailure(HttpStatus.UNAUTHORIZED,"AUTHENTICATION_REQUIRED","Entre novamente.");var account=auth.current(principal.id());limit("REAUTH",account.email(),request);
        try{auth.login(new AuthRequests.Login(account.email(),body.password()));if(mfa.required(account))mfa.verify(account,body.code(),false);}catch(ApiFailure error){events.event(account.id(),"REAUTH","FAILURE",requestId(request));throw error;}
        var updated=new SessionIdentity(account.id(),account.authVersion(),principal.authenticatedAt(),mfa.required(account)?clock.instant():principal.mfaVerifiedAt(),clock.instant());
        var context=SecurityContextHolder.createEmptyContext();context.setAuthentication(UsernamePasswordAuthenticationToken.authenticated(updated,null,List.of(new SimpleGrantedAuthority("ROLE_"+account.role()))));SecurityContextHolder.setContext(context);contexts.saveContext(context,request,response);events.event(account.id(),"REAUTH","SUCCESS",requestId(request));return ResponseEntity.noContent().build();
    }
    @PostMapping("/auth/logout") ResponseEntity<Void> logout(@org.springframework.security.core.annotation.AuthenticationPrincipal SessionIdentity principal,HttpServletRequest request,HttpServletResponse response){sessions.clear(request,response);events.event(principal==null?null:principal.id(),"LOGOUT","SUCCESS",requestId(request));return ResponseEntity.noContent().build();}
    @GetMapping("/users/me") ResponseEntity<UserView> me(@org.springframework.security.core.annotation.AuthenticationPrincipal SessionIdentity principal){return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(auth.current(principal.id()).view());}
    @PostMapping("/auth/resend-verification") ResponseEntity<Void> resend(@Valid @RequestBody AuthRequests.EmailRequest body,HttpServletRequest request){limit("RESEND",body.email(),request);auth.resend(body.email());events.event(null,"VERIFICATION_REQUEST","ACCEPTED",requestId(request));return ResponseEntity.accepted().build();}
    @PostMapping("/auth/forgot-password") ResponseEntity<Void> forgot(@Valid @RequestBody AuthRequests.EmailRequest body,HttpServletRequest request){limit("FORGOT",body.email(),request);auth.forgot(body.email());events.event(null,"RECOVERY_REQUEST","ACCEPTED",requestId(request));return ResponseEntity.accepted().build();}
    @PostMapping("/auth/verify-email") ResponseEntity<Void> verify(@Valid @RequestBody AuthRequests.Token body,HttpServletRequest request){limits.check("VERIFY:ip",clientIp.resolve(request),properties.ipAttempts());auth.verify(body.token());events.event(null,"EMAIL_VERIFIED","SUCCESS",requestId(request));return ResponseEntity.noContent().build();}
    @PostMapping("/auth/reset-password") ResponseEntity<Void> reset(@Valid @RequestBody AuthRequests.Reset body,HttpServletRequest request){limits.check("RESET:ip",clientIp.resolve(request),properties.ipAttempts());auth.reset(body.token(),body.password());events.event(null,"PASSWORD_RESET","SUCCESS",requestId(request));return ResponseEntity.noContent().build();}
}
