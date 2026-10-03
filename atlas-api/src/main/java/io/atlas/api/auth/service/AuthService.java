package io.atlas.api.auth.service;
import io.atlas.api.auth.model.Account;
import io.atlas.api.auth.model.AuthRequests;
import io.atlas.api.auth.repository.AccountRepository;
import io.atlas.api.auth.repository.TokenRepository;
import io.atlas.api.mail.MailOutbox;
import io.atlas.api.mail.MailProperties;
import io.atlas.api.shared.error.ApiFailure;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.util.Locale;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
@Service
public class AuthService {
    private final AccountRepository accounts;private final TokenRepository tokens;private final TokenCodec codec;
    private final PasswordEncoder encoder;private final MailOutbox outbox;private final MailProperties mail;
    private final AuthProperties properties;private final Clock clock;private final String dummyHash;
    public AuthService(AccountRepository accounts,TokenRepository tokens,TokenCodec codec,PasswordEncoder encoder,MailOutbox outbox,MailProperties mail,AuthProperties properties,Clock clock) {
        this.accounts=accounts;this.tokens=tokens;this.codec=codec;this.encoder=encoder;this.outbox=outbox;this.mail=mail;this.properties=properties;this.clock=clock;dummyHash=encoder.encode(codec.random());
    }
    public String normalize(String email) {return email.strip().toLowerCase(Locale.ROOT);}
    private void passwordValid(String password) {if(password.getBytes(StandardCharsets.UTF_8).length>72) throw new ApiFailure(HttpStatus.UNPROCESSABLE_CONTENT,"PASSWORD_TOO_LONG","A senha pode ter no máximo 72 bytes UTF-8.");}
    @Transactional
    public void register(AuthRequests.Register input) {
        passwordValid(input.password());String username=input.username().strip();
        if(username.isEmpty()) throw new ApiFailure(HttpStatus.UNPROCESSABLE_CONTENT,"VALIDATION_ERROR","Informe um nickname.");
        var account=accounts.create(username,normalize(input.email()),encoder.encode(input.password()),clock.instant());
        account.ifPresent(a->issue(a,"VERIFY_EMAIL"));
    }
    public Account login(AuthRequests.Login input) {
        passwordValid(input.password());var account=accounts.email(normalize(input.email()));
        boolean matches=encoder.matches(input.password(),account.map(Account::passwordHash).orElse(dummyHash));
        if(!matches || account.isEmpty()) throw new ApiFailure(HttpStatus.UNAUTHORIZED,"INVALID_CREDENTIALS","Email ou senha incorretos.");
        return account.get();
    }
    @Transactional public void resend(String email) { accounts.email(normalize(email)).ifPresent(a->{accounts.lock(a.id());accounts.id(a.id()).filter(current->!current.emailVerified()).ifPresent(current->issue(current,"VERIFY_EMAIL"));}); }
    @Transactional public void forgot(String email) { accounts.email(normalize(email)).ifPresent(a->{accounts.lock(a.id());issue(a,"RESET_PASSWORD");}); }
    private void issue(Account account,String purpose) {
        String secret=codec.random();String hash=codec.hash(secret);var now=clock.instant();
        tokens.invalidate(account.id(),purpose,now);tokens.create(account.id(),hash,purpose,now.plus(purpose.equals("VERIFY_EMAIL")?properties.verificationDuration():properties.resetDuration()));
        String route=purpose.equals("VERIFY_EMAIL")?"/verificar-email":"/redefinir-senha";
        String link=mail.webUrl().replaceAll("/$","")+route+"#token="+secret;
        outbox.enqueue(new MailOutbox.Message(account.email(),purpose.equals("VERIFY_EMAIL")?"Confirme sua conta Atlas":"Redefina sua senha Atlas", "Olá, "+account.username()+".\n\nAbra este link para continuar:\n"+link+"\n\nSe você não solicitou esta ação, ignore esta mensagem."));
    }
    private UUID consume(String secret,String purpose) {
        String hash=codec.hash(secret);var owner=tokens.owner(hash,purpose).orElseThrow(this::invalidToken);accounts.lock(owner);
        if(!tokens.consume(hash,purpose,clock.instant())) throw invalidToken();return owner;
    }
    @Transactional public void verify(String secret) {accounts.verify(consume(secret,"VERIFY_EMAIL"));}
    @Transactional public void reset(String secret,String password) {
        passwordValid(password);String hash=encoder.encode(password);UUID owner=consume(secret,"RESET_PASSWORD");
        accounts.password(owner,hash);tokens.invalidate(owner,"RESET_PASSWORD",clock.instant());accounts.removeSessions(owner);
    }
    private ApiFailure invalidToken() {return new ApiFailure(HttpStatus.BAD_REQUEST,"INVALID_TOKEN","Link inválido ou expirado. Solicite um novo.");}
    public Account current(UUID id) {return accounts.id(id).orElseThrow(()->new ApiFailure(HttpStatus.UNAUTHORIZED,"AUTHENTICATION_REQUIRED","Entre novamente na sua conta."));}
}
