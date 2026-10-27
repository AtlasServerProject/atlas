package io.atlas.api.auth.service;
import io.atlas.api.auth.model.Account;import io.atlas.api.auth.repository.*;import io.atlas.api.shared.error.ApiFailure;
import java.time.Clock;import java.util.*;import org.springframework.http.HttpStatus;import org.springframework.security.crypto.password.PasswordEncoder;import org.springframework.stereotype.Service;import org.springframework.transaction.annotation.Transactional;
@Service public class GoogleIdentityService {
 private final AccountRepository accounts;private final GoogleIdentityRepository identities;private final PasswordEncoder passwords;private final TokenCodec tokens;private final Clock clock;
 public GoogleIdentityService(AccountRepository accounts,GoogleIdentityRepository identities,PasswordEncoder passwords,TokenCodec tokens,Clock clock){this.accounts=accounts;this.identities=identities;this.passwords=passwords;this.tokens=tokens;this.clock=clock;}
 public boolean linked(UUID id){return identities.linked(id);}
 @Transactional public Account login(GoogleTokenVerifier.Identity identity){
  var owner=identities.owner(identity.subject());
  if(owner.isPresent()){var account=accounts.id(owner.get()).orElseThrow(this::conflict);if(!account.email().equals(identity.email()))throw new ApiFailure(HttpStatus.CONFLICT,"GOOGLE_EMAIL_CHANGED","O email da sua conta mudou. Entre pelo acesso do Atlas e procure o suporte.");return account;}
  if(accounts.email(identity.email()).isPresent())throw new ApiFailure(HttpStatus.CONFLICT,"GOOGLE_ACCOUNT_EXISTS","Este email já possui uma conta Atlas. Entre com sua senha e vincule o Google em Minha conta.");
  var account=accounts.create(identity.name(),identity.email(),passwords.encode(tokens.random()),clock.instant()).orElseThrow(this::conflict);
  accounts.verify(account.id());if(!identities.link(account.id(),identity.subject()))throw conflict();return accounts.id(account.id()).orElseThrow(this::conflict);
 }
 @Transactional public void link(UUID user,long expectedAuthVersion,GoogleTokenVerifier.Identity identity){
  accounts.lock(user);var account=accounts.id(user).orElseThrow(this::conflict);if(account.authVersion()!=expectedAuthVersion)throw new ApiFailure(HttpStatus.UNAUTHORIZED,"GOOGLE_CHALLENGE_EXPIRED","Confirme novamente sua identidade para vincular o Google.");if(!account.email().equals(identity.email()))throw new ApiFailure(HttpStatus.CONFLICT,"GOOGLE_EMAIL_MISMATCH","Escolha a conta Google com o mesmo email da sua conta Atlas.");
  if(!identities.link(user,identity.subject()))throw conflict();accounts.verify(user);
 }
 private ApiFailure conflict(){return new ApiFailure(HttpStatus.CONFLICT,"GOOGLE_LINK_CONFLICT","Não foi possível vincular esta conta Google. Ela pode já estar vinculada.");}
}
