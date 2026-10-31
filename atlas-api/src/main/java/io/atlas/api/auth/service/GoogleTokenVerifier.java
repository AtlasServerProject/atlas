package io.atlas.api.auth.service;
import io.atlas.api.shared.error.ApiFailure;
import java.nio.charset.StandardCharsets;import java.security.MessageDigest;import java.time.*;import java.util.*;
import org.springframework.http.HttpStatus;import org.springframework.security.oauth2.jwt.JwtDecoder;import org.springframework.security.oauth2.jwt.JwtException;
/** Tokens verified by Nimbus/Google rotating public keys, never by a client-supplied profile. */
public class GoogleTokenVerifier {
 public record Identity(String subject,String email,String name){@Override public String toString(){return "GoogleIdentity[redacted]";}}
 private final GoogleProperties properties;private final JwtDecoder decoder;private final Clock clock;
 public GoogleTokenVerifier(GoogleProperties properties,JwtDecoder decoder,Clock clock){this.properties=properties;this.decoder=decoder;this.clock=clock;}
 public Identity verify(String credential,String nonce){
  try{
   var jwt=decoder.decode(credential);String issuer=jwt.getClaimAsString("iss"),sub=jwt.getSubject(),email=jwt.getClaimAsString("email"),actualNonce=jwt.getClaimAsString("nonce"),hd=jwt.getClaimAsString("hd"),azp=jwt.getClaimAsString("azp");
   if(issuer==null||!Set.of("https://accounts.google.com","accounts.google.com").contains(issuer)||!List.of(properties.clientId()).equals(jwt.getAudience())||(azp!=null&&!properties.clientId().equals(azp))||sub==null||sub.isBlank()||sub.length()>255||jwt.getExpiresAt()==null||!clock.instant().isBefore(jwt.getExpiresAt())||jwt.getIssuedAt()==null||jwt.getIssuedAt().isAfter(clock.instant().plusSeconds(60))||jwt.getIssuedAt().isBefore(clock.instant().minusSeconds(600))||actualNonce==null||nonce==null||!MessageDigest.isEqual(nonce.getBytes(StandardCharsets.UTF_8),actualNonce.getBytes(StandardCharsets.UTF_8))||!Boolean.TRUE.equals(jwt.getClaimAsBoolean("email_verified"))||email==null||email.length()>254||!email.matches("[^\\s@]+@[^\\s@]+\\.[^\\s@]+"))throw invalid();
   email=email.toLowerCase(Locale.ROOT);String domain=email.substring(email.lastIndexOf('@')+1);
   // Google documents that email_verified alone is insufficient for third-party email accounts.
   if(!domain.equals("gmail.com")&&(hd==null||!domain.equals(hd.toLowerCase(Locale.ROOT))))throw new ApiFailure(HttpStatus.UNPROCESSABLE_CONTENT,"GOOGLE_EMAIL_NOT_HOSTED","Para este endereço, use o acesso por email e senha do Atlas.");
   String name=jwt.getClaimAsString("name");if(name==null||name.strip().length()<3)name="Treinador Atlas";String display=name.strip().codePoints().limit(32).collect(StringBuilder::new,StringBuilder::appendCodePoint,StringBuilder::append).toString();return new Identity(sub,email,display);
  }catch(ApiFailure e){throw e;}catch(JwtException|IllegalArgumentException e){throw invalid();}
 }
 private ApiFailure invalid(){return new ApiFailure(HttpStatus.UNAUTHORIZED,"INVALID_GOOGLE_CREDENTIAL","Não foi possível confirmar sua conta Google. Tente novamente.");}
}
