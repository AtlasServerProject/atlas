package io.atlas.api.commerce.service;
import io.atlas.api.commerce.model.CommerceModels.*;
import io.atlas.api.commerce.repository.CommerceRepository;
import io.atlas.api.auth.service.*;
import io.atlas.api.shared.error.ApiFailure;
import java.time.*;
import java.util.*;
import java.sql.Timestamp;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.HttpStatus;
@Service
public class IdentityService {
 private final CommerceRepository repo;private final AuthService auth;private final TokenCodec tokens;private final RateLimiter limits;private final Clock clock;
 public IdentityService(CommerceRepository repo,AuthService auth,TokenCodec tokens,RateLimiter limits,Clock clock){this.repo=repo;this.auth=auth;this.tokens=tokens;this.limits=limits;this.clock=clock;}
 private ApiFailure conflict(String code,String text){return new ApiFailure(HttpStatus.CONFLICT,code,text);}
 private void verified(UUID user){if(!auth.current(user).emailVerified())throw new ApiFailure(HttpStatus.FORBIDDEN,"EMAIL_NOT_VERIFIED","Confirme seu email antes de vincular o Minecraft.");}
 @Transactional(readOnly=true) public LinkStatus status(UUID user){return new LinkStatus(repo.current(user),repo.pending(user,clock.instant()));}
 @Transactional public ChallengeCreated create(UUID user,String request){repo.lockUser(user);verified(user);if(repo.current(user)!=null)throw conflict("ALREADY_LINKED","Sua conta já está vinculada.");repo.cancel(user);var now=clock.instant();var code=tokens.random();var id=UUID.randomUUID();var expires=now.plusSeconds(600);repo.create(id,user,tokens.hash(code),now,expires);repo.audit(user,"CHALLENGE_CREATED",null,request,now);return new ChallengeCreated(id,code,expires);}
 @Transactional public void prove(Proof proof,String request){var hash=tokens.hash(proof.code());var owner=repo.owner(hash);if(owner==null)throw conflict("INVALID_CHALLENGE","Código inválido, utilizado ou expirado.");repo.lockUser(owner);var row=repo.lockedChallenge(hash);var now=clock.instant();if(!row.get("state").equals("WAITING")||!now.isBefore(((Timestamp)row.get("expires_at")).toInstant()))throw conflict("INVALID_CHALLENGE","Código inválido, utilizado ou expirado.");verified(owner);if(!repo.serverActive(proof.server()))throw conflict("INVALID_DESTINATION","Servidor indisponível.");repo.lockSubject(proof.subject());if(repo.occupied(proof.subject()))throw conflict("PLAYER_LINKED","Este jogador já está vinculado. Resolva o vínculo anterior no site.");repo.prove((UUID)row.get("id"),proof);repo.audit(owner,"GAME_PROOF",proof.subject(),request,now);}
 @Transactional public LinkView confirm(UUID user,Confirmation input,String request){repo.lockUser(user);verified(user);var now=clock.instant();var pending=repo.pending(user,now);if(pending==null||!pending.state().equals("PROVED")||!pending.id().equals(input.challengeId())||!input.subject().equals(pending.subject()))throw conflict("INVALID_CHALLENGE","Confirmação inválida ou expirada. Gere um novo código.");repo.lockSubject(input.subject());if(repo.current(user)!=null||repo.occupied(input.subject()))throw conflict("PLAYER_LINKED","Conta ou jogador já vinculados.");var link=repo.confirm(user,input.challengeId(),now);repo.audit(user,"LINK_CONFIRMED",link.subject(),request,now);return link;}
 @Transactional public void unlink(UUID user,Unlink input,String request){repo.lockUser(user);var account=auth.current(user);if(!auth.login(new io.atlas.api.auth.model.AuthRequests.Login(account.email(),input.password())).id().equals(user))throw new ApiFailure(HttpStatus.FORBIDDEN,"ACCESS_DENIED","Senha incorreta.");var link=repo.current(user);if(link==null)throw conflict("NOT_LINKED","Nenhum jogador vinculado.");repo.revoke(user,clock.instant());repo.cancel(user);repo.audit(user,"LINK_REVOKED",link.subject(),request,clock.instant());}
}
