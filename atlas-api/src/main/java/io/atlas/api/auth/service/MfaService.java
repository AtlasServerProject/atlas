package io.atlas.api.auth.service;
import io.atlas.api.auth.repository.MfaRepository;
import io.atlas.api.auth.model.Account;
import io.atlas.api.mail.MailCipher;
import io.atlas.api.shared.error.ApiFailure;
import java.time.*;
import java.util.*;
import java.security.SecureRandom;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
@Service public class MfaService {
 public record Setup(String secret,String issuer,String account){@Override public String toString(){return "MfaSetup[redacted]";}}
 private final MfaRepository repo;private final MailCipher cipher;private final Clock clock;private final boolean staffRequired;private final SecureRandom random=new SecureRandom();
 public MfaService(MfaRepository repo,MailCipher cipher,Clock clock,@Value("${atlas.auth.require-staff-mfa:true}") boolean required){this.repo=repo;this.cipher=cipher;this.clock=clock;staffRequired=required;}
 public boolean required(Account a){return a.mfaEnabled()||(staffRequired&&Set.of("ADMIN","SUPPORT","MODERATOR").contains(a.role()));}
 private ApiFailure invalid(){return new ApiFailure(HttpStatus.UNAUTHORIZED,"INVALID_MFA_CODE","Código inválido ou expirado.");}
 private String secret(UUID id,String ciphertext){String raw=cipher.decrypt(ciphertext),prefix="mfa:"+id+":";if(!raw.startsWith(prefix))throw new IllegalStateException("Authenticator identity mismatch");return raw.substring(prefix.length());}
 @Transactional public Setup setup(Account account){var state=repo.lock(account.id());if(account.mfaEnabled()||(state!=null&&state.enabled()!=null))throw new ApiFailure(HttpStatus.CONFLICT,"MFA_ALREADY_ENABLED","A proteção já está ativa.");byte[] bytes=new byte[20];random.nextBytes(bytes);String secret=Totp.base32(bytes);repo.pending(account.id(),cipher.encrypt("mfa:"+account.id()+":"+secret),clock.instant().plusSeconds(300));return new Setup(secret,"Atlas Cobblemon",account.email());}
 @Transactional public List<String> verify(Account account,String code,boolean allowSetup){
  var state=repo.lock(account.id());if(state==null)throw invalid();
  if(state.enabled()==null){
   if(!allowSetup||state.expires()==null||!clock.instant().isBefore(state.expires()))throw invalid();
   long step=Totp.match(secret(account.id(),state.pending()),code,clock.instant().getEpochSecond()/30,-1);if(step<0)throw invalid();
   repo.enable(account.id(),step,clock.instant());var codes=new ArrayList<String>();for(int i=0;i<10;i++){byte[] bytes=new byte[10];random.nextBytes(bytes);String raw=Totp.base32(bytes);repo.recovery(account.id(),cipher.digest("mfa-recovery:"+account.id()+":"+raw));codes.add(raw.substring(0,4)+"-"+raw.substring(4,8)+"-"+raw.substring(8,12)+"-"+raw.substring(12));}return List.copyOf(codes);
  }
  long step=Totp.match(secret(account.id(),state.secret()),code,clock.instant().getEpochSecond()/30,state.last());
  if(step>=0){repo.step(account.id(),step);return List.of();}
  String recovery=code==null?"":code.replace("-","").toUpperCase(Locale.ROOT);
  if(recovery.matches("[A-Z2-7]{16}")&&repo.consume(account.id(),cipher.digest("mfa-recovery:"+account.id()+":"+recovery)))return List.of();
  throw invalid();
 }
}
