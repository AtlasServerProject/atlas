package io.atlas.api.auth.service;
import io.atlas.api.auth.model.*;import io.atlas.api.shared.error.ApiFailure;
import jakarta.servlet.http.*;import java.io.Serializable;import java.time.*;import java.util.*;
import org.springframework.http.HttpStatus;import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;import org.springframework.security.core.authority.SimpleGrantedAuthority;import org.springframework.security.core.context.SecurityContextHolder;import org.springframework.security.web.context.SecurityContextRepository;import org.springframework.security.web.csrf.CsrfTokenRepository;import org.springframework.stereotype.Service;
/** Shared local/federated session boundary. An external identity never bypasses Atlas MFA. */
@Service public class LoginSessions {
 private static final String CHALLENGE="atlas.mfa.challenge";
 public record Challenge(UUID id,long version,Instant at,boolean setup) implements Serializable {}
 public record MfaRequired(boolean mfaRequired,boolean setupRequired){}
 private final AuthService auth;private final MfaService mfa;private final Clock clock;private final SecurityContextRepository contexts;private final CsrfTokenRepository csrf;
 public LoginSessions(AuthService auth,MfaService mfa,Clock clock,SecurityContextRepository contexts,CsrfTokenRepository csrf){this.auth=auth;this.mfa=mfa;this.clock=clock;this.contexts=contexts;this.csrf=csrf;}
 public void clear(HttpServletRequest request,HttpServletResponse response){SecurityContextHolder.clearContext();var old=request.getSession(false);if(old!=null)old.invalidate();csrf.saveToken(null,request,response);}
 public void enrollment(Account a,HttpServletRequest request){request.getSession(true).setAttribute(CHALLENGE,new Challenge(a.id(),a.authVersion(),clock.instant(),true));}
 public Object begin(Account a,HttpServletRequest request,HttpServletResponse response){
  if(mfa.required(a)){clear(request,response);request.getSession(true).setAttribute(CHALLENGE,new Challenge(a.id(),a.authVersion(),clock.instant(),!a.mfaEnabled()));return new MfaRequired(true,!a.mfaEnabled());}
  return establish(a,request,response,clock.instant(),null);
 }
 public Account.UserView establish(Account account,HttpServletRequest request,HttpServletResponse response,Instant at,Instant mfaAt){clear(request,response);request.getSession(true);var identity=new SessionIdentity(account.id(),account.authVersion(),at,mfaAt,clock.instant());var context=SecurityContextHolder.createEmptyContext();context.setAuthentication(UsernamePasswordAuthenticationToken.authenticated(identity,null,List.of(new SimpleGrantedAuthority("ROLE_"+account.role()))));SecurityContextHolder.setContext(context);contexts.saveContext(context,request,response);return account.view();}
 public Challenge challenge(HttpServletRequest request){var session=request.getSession(false);Object value=session==null?null:session.getAttribute(CHALLENGE);if(value instanceof Challenge c&&clock.instant().isBefore(c.at().plusSeconds(300))&&auth.current(c.id()).authVersion()==c.version())return c;throw new ApiFailure(HttpStatus.UNAUTHORIZED,"MFA_CHALLENGE_EXPIRED","Entre novamente para confirmar a autenticação.");}
}
