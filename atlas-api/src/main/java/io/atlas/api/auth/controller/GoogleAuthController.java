package io.atlas.api.auth.controller;
import io.atlas.api.auth.repository.GoogleChallengeRepository;import io.atlas.api.auth.model.*;import io.atlas.api.auth.service.*;import io.atlas.api.shared.error.ApiFailure;import io.atlas.api.shared.web.RequestIdFilter;
import jakarta.servlet.http.*;import jakarta.validation.Valid;import jakarta.validation.constraints.*;
import java.io.Serializable;import java.time.*;import java.util.*;
import org.springframework.http.*;import org.springframework.security.core.annotation.AuthenticationPrincipal;import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api/v1/auth/google")
public class GoogleAuthController {
 private static final String FLOW="atlas.google.flow";
 private record Flow(String nonce,Instant at,UUID user,long authVersion) implements Serializable{@Override public String toString(){return "GoogleFlow[redacted]";}}
 public record Start(boolean link){}
 public record Credential(@NotBlank @Size(max=8192) String credential){@Override public String toString(){return "GoogleCredential[redacted]";}}
 public record Provider(boolean enabled,String clientId,boolean linked){}
 public record Challenge(String nonce){}
 private final GoogleChallengeRepository challenges;private final GoogleProperties properties;private final GoogleTokenVerifier verifier;private final GoogleIdentityService google;private final AuthService auth;private final LoginSessions sessions;private final RateLimiter limits;private final ClientIpResolver clientIp;private final TokenCodec tokens;private final Clock clock;private final SecurityEvents events;
 public GoogleAuthController(GoogleProperties properties,GoogleTokenVerifier verifier,GoogleIdentityService google,AuthService auth,LoginSessions sessions,RateLimiter limits,ClientIpResolver clientIp,TokenCodec tokens,Clock clock,SecurityEvents events,GoogleChallengeRepository challenges){this.challenges=challenges;this.properties=properties;this.verifier=verifier;this.google=google;this.auth=auth;this.sessions=sessions;this.limits=limits;this.clientIp=clientIp;this.tokens=tokens;this.clock=clock;this.events=events;}
 private void enabled(){if(!properties.enabled())throw new ApiFailure(HttpStatus.SERVICE_UNAVAILABLE,"GOOGLE_DISABLED","O acesso pelo Google ainda não está disponível.");}
 private String requestId(HttpServletRequest r){return (String)r.getAttribute(RequestIdFilter.ATTRIBUTE);}
 @GetMapping("/provider") public ResponseEntity<Provider> provider(@AuthenticationPrincipal SessionIdentity principal){return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(new Provider(properties.enabled(),properties.enabled()?properties.clientId():null,principal!=null&&google.linked(principal.id())));}
 @PostMapping("/challenge") public ResponseEntity<Challenge> challenge(@Valid @RequestBody Start body,@AuthenticationPrincipal SessionIdentity principal,HttpServletRequest request){
  enabled();limits.check("GOOGLE_START:ip",clientIp.resolve(request),30);
  if(body.link()){
   if(principal==null)throw new ApiFailure(HttpStatus.UNAUTHORIZED,"AUTHENTICATION_REQUIRED","Entre na sua conta Atlas para vincular o Google.");
   if(principal.reauthenticatedAt()==null||!clock.instant().isBefore(principal.reauthenticatedAt().plusSeconds(300)))throw new ApiFailure(HttpStatus.FORBIDDEN,"REAUTHENTICATION_REQUIRED","Confirme sua identidade antes de vincular o Google.");
  }else if(principal!=null)throw new ApiFailure(HttpStatus.CONFLICT,"ALREADY_AUTHENTICATED","Saia da conta atual antes de entrar com outra conta.");
  var nonce=tokens.random();challenges.create(tokens.hash(nonce),clock.instant().plusSeconds(300));request.getSession(true).setAttribute(FLOW,new Flow(nonce,clock.instant(),body.link()?principal.id():null,body.link()?principal.authVersion():0));return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(new Challenge(nonce));
 }
 @PostMapping("/complete") public ResponseEntity<?> complete(@Valid @RequestBody Credential body,@AuthenticationPrincipal SessionIdentity principal,HttpServletRequest request,HttpServletResponse response){
  enabled();limits.check("GOOGLE_COMPLETE:ip",clientIp.resolve(request),30);var session=request.getSession(false);Object value=session==null?null:session.getAttribute(FLOW);if(session!=null)session.removeAttribute(FLOW);
  if(!(value instanceof Flow flow)||!clock.instant().isBefore(flow.at().plusSeconds(300))||!challenges.consume(tokens.hash(flow.nonce()),clock.instant()))throw new ApiFailure(HttpStatus.UNAUTHORIZED,"GOOGLE_CHALLENGE_EXPIRED","O acesso expirou. Clique novamente no botão do Google.");
  try{
   if(flow.user()!=null&&(principal==null||!flow.user().equals(principal.id())||principal.authVersion()!=flow.authVersion()||auth.current(principal.id()).authVersion()!=flow.authVersion()||principal.reauthenticatedAt()==null||!clock.instant().isBefore(principal.reauthenticatedAt().plusSeconds(300))))throw new ApiFailure(HttpStatus.UNAUTHORIZED,"GOOGLE_CHALLENGE_EXPIRED","Confirme novamente sua identidade para vincular o Google.");
   if(flow.user()==null&&principal!=null)throw new ApiFailure(HttpStatus.CONFLICT,"ALREADY_AUTHENTICATED","Sua sessão mudou. Tente novamente.");
   var identity=verifier.verify(body.credential(),flow.nonce());
   if(flow.user()!=null){google.link(flow.user(),flow.authVersion(),identity);events.event(flow.user(),"GOOGLE_LINK","SUCCESS",requestId(request));return ResponseEntity.noContent().build();}
   var account=google.login(identity);limits.check("GOOGLE:account",account.id().toString(),10);Object result=sessions.begin(account,request,response);events.event(account.id(),"GOOGLE_LOGIN",result instanceof LoginSessions.MfaRequired?"PENDING":"SUCCESS",requestId(request));return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(result);
  }catch(ApiFailure failure){events.event(flow.user(),"GOOGLE_AUTH","FAILURE",requestId(request));throw failure;}
 }
}
