package io.atlas.api;

import io.atlas.api.mail.MailOutbox;
import io.atlas.api.auth.service.TokenCodec;
import java.net.*;
import java.net.http.*;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.crypto.password.PasswordEncoder;
import tools.jackson.databind.ObjectMapper;
import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class AuthIntegrationTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry registry) { TestDatabase.properties(registry); }
    @LocalServerPort int port;
    @Autowired JdbcClient jdbc;
    @Autowired ObjectMapper mapper;
    @Autowired MailOutbox mail;
    @Autowired PasswordEncoder encoder;
    @Autowired TokenCodec codec;
    @Autowired @SuppressWarnings("rawtypes") org.springframework.session.SessionRepository sessions;
    private String password;
    @BeforeEach void clearLimits() { jdbc.sql("DELETE FROM atlas_web.auth_rate_limits").update(); password=UUID.randomUUID().toString(); }
    private class Browser {
        final CookieManager cookies=new CookieManager(null,CookiePolicy.ACCEPT_ALL);
        final HttpClient client=HttpClient.newBuilder().cookieHandler(cookies).build();
        String token,header;
        HttpResponse<String> get(String path) throws Exception {return client.send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+port+"/api/v1/"+path)).GET().build(),HttpResponse.BodyHandlers.ofString());}
        HttpResponse<String> post(String path,Map<String,?> body) throws Exception {
            var csrf=mapper.readTree(get("auth/csrf").body()); token=csrf.get("token").asString();header=csrf.get("headerName").asString();
            return client.send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+port+"/api/v1/auth/"+path)).header("Content-Type","application/json").header(header,token)
                .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body))).build(),HttpResponse.BodyHandlers.ofString());
        }
        String session() {return cookies.getCookieStore().getCookies().stream().filter(c->c.getName().equals("ATLAS_SESSION")).findFirst().orElseThrow().getValue();}
    }
    private String email() {return UUID.randomUUID()+"@example.invalid";}
    private String register(Browser browser,String email) throws Exception {
        assertThat(browser.post("register",Map.of("username","Atlas test","email",email,"password",password)).statusCode()).isEqualTo(202);
        return jdbc.sql("SELECT id::text FROM atlas_web.users WHERE email=:email").param("email",email.toLowerCase(Locale.ROOT)).query(String.class).single();
    }
    private String linkToken(String email,String route) {
        var texts=jdbc.sql("SELECT encrypted_payload FROM atlas_web.mail_outbox WHERE status='PENDING' ORDER BY created_at DESC").query(String.class).list();
        return texts.stream().map(mail::read).filter(m->m.to().equals(email)&&m.text().contains(route)).map(m->m.text().split("#token=")[1].split("\\s")[0]).findFirst().orElseThrow();
    }
    @Test void persistentAccountRotationLogoutAndNoRoleInjection() throws Exception {
        var browser=new Browser();String email=email();String id=register(browser,email);
        String preLogin=browser.session();
        var login=browser.post("login",Map.of("email",email.toUpperCase(Locale.ROOT),"password",password));
        assertThat(login.statusCode()).isEqualTo(200);
        assertThat(login.body()).contains(id,"\"role\":\"USER\"").doesNotContain("passwordHash","authVersion",password);
        assertThat(browser.session()).isNotEqualTo(preLogin);
        assertThat(login.headers().allValues("set-cookie").toString()).contains("HttpOnly","SameSite=Lax");
        String hash=jdbc.sql("SELECT password_hash FROM atlas_web.users WHERE id=:id::uuid").param("id",id).query(String.class).single();
        assertThat(hash).startsWith("$2");assertThat(encoder.matches(password,hash)).isTrue();
        assertThat(browser.get("users/me").statusCode()).isEqualTo(200);
        assertThat(jdbc.sql("SELECT count(*) FROM atlas_web.web_sessions WHERE principal_name=:id").param("id",id).query(Integer.class).single()).isPositive();
        assertThat(browser.post("register",Map.of("username","Injected","email",email(),"password",password,"role","ADMIN")).statusCode()).isEqualTo(400);
        assertThat(browser.post("logout",Map.of()).statusCode()).isEqualTo(204);
        assertThat(browser.get("users/me").statusCode()).isEqualTo(401);
        assertThat(jdbc.sql("SELECT count(*) FROM atlas_web.web_sessions WHERE principal_name=:id").param("id",id).query(Integer.class).single()).isZero();
    }
    @Test void verificationResendExpiryAndSingleUse() throws Exception {
        var browser=new Browser();String email=email();String id=register(browser,email);String original=linkToken(email,"verificar-email");
        assertThat(browser.post("resend-verification",Map.of("email",email)).statusCode()).isEqualTo(202);
        String renewed=linkToken(email,"verificar-email");assertThat(renewed).isNotEqualTo(original);
        assertThat(browser.post("verify-email",Map.of("token",original)).statusCode()).isEqualTo(400);
        assertThat(browser.post("reset-password",Map.of("token",renewed,"password",password)).statusCode()).isEqualTo(400);
        assertThat(browser.post("verify-email",Map.of("token",renewed)).statusCode()).isEqualTo(204);
        assertThat(browser.post("verify-email",Map.of("token",renewed)).statusCode()).isEqualTo(400);
        assertThat(jdbc.sql("SELECT email_verified FROM atlas_web.users WHERE id=:id::uuid").param("id",id).query(Boolean.class).single()).isTrue();
        String other=email();register(browser,other);String expired=linkToken(other,"verificar-email");
        jdbc.sql("UPDATE atlas_web.auth_tokens SET expires_at=now()-interval '1 second' WHERE token_hash=:hash").param("hash",codec.hash(expired)).update();
        assertThat(browser.post("verify-email",Map.of("token",expired)).statusCode()).isEqualTo(400);
    }
    @Test void resetRevokesAllSessionsAndDoesNotRevealMissingAccounts() throws Exception {
        var first=new Browser();var second=new Browser();String email=email();String id=register(first,email);
        for(var browser:List.of(first,second)) assertThat(browser.post("login",Map.of("email",email,"password",password)).statusCode()).isEqualTo(200);
        assertThat(first.post("forgot-password",Map.of("email",email())).statusCode()).isEqualTo(202);
        assertThat(first.post("forgot-password",Map.of("email",email)).statusCode()).isEqualTo(202);
        String token=linkToken(email,"redefinir-senha");String newPassword=UUID.randomUUID().toString();
        assertThat(new Browser().post("reset-password",Map.of("token",token,"password",newPassword)).statusCode()).isEqualTo(204);
        assertThat(first.get("users/me").statusCode()).isEqualTo(401);assertThat(second.get("users/me").statusCode()).isEqualTo(401);
        assertThat(first.post("login",Map.of("email",email,"password",password)).statusCode()).isEqualTo(401);
        assertThat(first.post("login",Map.of("email",email,"password",newPassword)).statusCode()).isEqualTo(200);
        assertThat(first.post("reset-password",Map.of("token",token,"password",password)).statusCode()).isEqualTo(400);
        assertThat(jdbc.sql("SELECT auth_version FROM atlas_web.users WHERE id=:id::uuid").param("id",id).query(Long.class).single()).isEqualTo(2);
    }
    @Test void existingSessionUsesCurrentRoleAndAuthVersion() throws Exception {
        var browser=new Browser();String email=email();String id=register(browser,email);
        browser.post("login",Map.of("email",email,"password",password));
        assertThat(browser.get("admin/not-implemented").statusCode()).isEqualTo(403);
        try(var c=TestDatabase.admin();var stmt=c.prepareStatement("UPDATE atlas_web.users SET role='ADMIN' WHERE id=?::uuid")) {stmt.setString(1,id);stmt.executeUpdate();}
        assertThat(browser.get("users/me").body()).contains("\"role\":\"ADMIN\"");
        assertThat(browser.get("admin/not-implemented").statusCode()).isEqualTo(404);
        try(var c=TestDatabase.admin();var stmt=c.prepareStatement("UPDATE atlas_web.users SET role='USER' WHERE id=?::uuid")) {stmt.setString(1,id);stmt.executeUpdate();}
        assertThat(browser.get("admin/not-implemented").statusCode()).isEqualTo(403);
        jdbc.sql("UPDATE atlas_web.users SET auth_version=auth_version+1 WHERE id=:id::uuid").param("id",id).update();
        assertThat(browser.get("users/me").statusCode()).isEqualTo(401);
    }
    @Test void duplicateRegistrationEncryptedQueueAndPersistentRateLimit() throws Exception {
        var browser=new Browser();String email=email();register(browser,email);
        assertThat(browser.post("register",Map.of("username","Other","email",email.toUpperCase(Locale.ROOT),"password",password)).statusCode()).isEqualTo(202);
        assertThat(jdbc.sql("SELECT count(*) FROM atlas_web.users WHERE email=:email").param("email",email).query(Integer.class).single()).isEqualTo(1);
        var ciphertexts=jdbc.sql("SELECT encrypted_payload FROM atlas_web.mail_outbox WHERE status='PENDING'").query(String.class).list();
        assertThat(ciphertexts).allSatisfy(s->assertThat(s).doesNotContain(email,"#token=",password));
        for(int i=0;i<5;i++) assertThat(browser.post("login",Map.of("email",email,"password","incorrect-password")).statusCode()).isEqualTo(401);
        assertThat(new Browser().post("login",Map.of("email",email.toUpperCase(Locale.ROOT),"password",password)).statusCode()).isEqualTo(429);
        assertThat(browser.post("register",Map.of("username","Long","email",email(),"password","é".repeat(37))).statusCode()).isEqualTo(422);
    }
    @Test void inactivityAndAbsoluteExpiryInvalidateAuthentication() throws Exception {
        var browser=new Browser();String email=email();register(browser,email);
        browser.post("login",Map.of("email",email,"password",password));
        String sessionId=new String(Base64.getDecoder().decode(browser.session()),java.nio.charset.StandardCharsets.UTF_8);
        org.springframework.session.Session session=sessions.findById(sessionId);
        org.springframework.security.core.context.SecurityContext context=session.getAttribute("SPRING_SECURITY_CONTEXT");
        var principal=(io.atlas.api.auth.model.SessionIdentity)context.getAuthentication().getPrincipal();
        var old=new io.atlas.api.auth.model.SessionIdentity(principal.id(),principal.authVersion(),java.time.Instant.now().minusSeconds(86401));
        context.setAuthentication(org.springframework.security.authentication.UsernamePasswordAuthenticationToken.authenticated(old,null,context.getAuthentication().getAuthorities()));
        session.setAttribute("SPRING_SECURITY_CONTEXT",context);sessions.save(session);
        assertThat(browser.get("users/me").statusCode()).isEqualTo(401);
        browser.post("login",Map.of("email",email,"password",password));
        jdbc.sql("UPDATE atlas_web.web_sessions SET last_access_time=1,expiry_time=1 WHERE principal_name=:id").param("id",principal.id().toString()).update();
        assertThat(browser.get("users/me").statusCode()).isEqualTo(401);
    }
    @Test void queueRetryLeasingAndPayloadErasure() {
        // The isolated fixture can discard pending test messages before this worker test.
        jdbc.sql("DELETE FROM atlas_web.mail_outbox").update();
        mail.enqueue(new MailOutbox.Message(email(),"Test","Private disposable token"));
        var first=mail.claim();assertThat(first).hasSize(1);assertThat(mail.claim()).isEmpty();
        mail.failed(first.getFirst());assertThat(mail.claim()).isEmpty();
        for(int attempt=2;attempt<=5;attempt++) {
            jdbc.sql("UPDATE atlas_web.mail_outbox SET next_attempt_at=now()-interval '1 second'").update();
            var pending=mail.claim();assertThat(pending.getFirst().attempts()).isEqualTo(attempt);mail.failed(pending.getFirst());
        }
        assertThat(jdbc.sql("SELECT status FROM atlas_web.mail_outbox").query(String.class).single()).isEqualTo("REVIEW");
        assertThat(mail.claim()).isEmpty();
        mail.sent(first.getFirst());
        assertThat(jdbc.sql("SELECT status FROM atlas_web.mail_outbox").query(String.class).single()).isEqualTo("REVIEW");
        jdbc.sql("DELETE FROM atlas_web.mail_outbox").update();
        mail.enqueue(new MailOutbox.Message(email(),"Test","Disposable payload"));
        var claimed=mail.claim().getFirst();mail.sent(claimed);mail.failed(claimed);
        assertThat(jdbc.sql("SELECT status FROM atlas_web.mail_outbox").query(String.class).single()).isEqualTo("SENT");
        assertThat(jdbc.sql("SELECT encrypted_payload FROM atlas_web.mail_outbox").query(String.class).single()).isEmpty();
    }
    @Test void concurrentConsumptionHasExactlyOneWinner() throws Exception {
        var browser=new Browser();String email=email();register(browser,email);String token=linkToken(email,"verificar-email");
        try(var pool=Executors.newFixedThreadPool(2)) {
            var tasks=List.<Callable<Integer>>of(()->new Browser().post("verify-email",Map.of("token",token)).statusCode(),()->new Browser().post("verify-email",Map.of("token",token)).statusCode());
            var results=pool.invokeAll(tasks);assertThat(List.of(results.get(0).get(),results.get(1).get())).containsExactlyInAnyOrder(204,400);
        }
    }
}
