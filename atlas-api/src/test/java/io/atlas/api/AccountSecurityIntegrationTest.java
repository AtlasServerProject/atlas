package io.atlas.api;
import io.atlas.api.auth.service.Totp;
import java.net.*;import java.net.http.*;import java.util.*;import java.time.*;
import org.junit.jupiter.api.*;import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.*;import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;import tools.jackson.databind.ObjectMapper;
import static org.assertj.core.api.Assertions.*;
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT,properties="atlas.auth.require-staff-mfa=true")
@ActiveProfiles("test")
class AccountSecurityIntegrationTest {
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){TestDatabase.properties(r);}
 @LocalServerPort int port;@Autowired JdbcTemplate db;@Autowired PasswordEncoder encoder;@Autowired ObjectMapper json;
 UUID id;String email,password;
 @BeforeEach void fixture(){id=UUID.randomUUID();email=id+"@example.invalid";password=UUID.randomUUID().toString();db.update("DELETE FROM atlas_web.auth_rate_limits");TestDatabase.adminSql("INSERT INTO atlas_web.users(id,username,email,password_hash,role,email_verified) VALUES(?,'Security fixture',?,?,'ADMIN',TRUE)",id,email,encoder.encode(password));}
 class Browser{
  final CookieManager cookies=new CookieManager(null,CookiePolicy.ACCEPT_ALL);final HttpClient client=HttpClient.newBuilder().cookieHandler(cookies).build();
  HttpResponse<String> get(String path)throws Exception{return client.send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+port+"/api/v1/"+path)).GET().build(),HttpResponse.BodyHandlers.ofString());}
  HttpResponse<String> post(String path,Map<String,?> data)throws Exception{var csrf=json.readTree(get("auth/csrf").body());return client.send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+port+"/api/v1/auth/"+path)).header("Content-Type","application/json").header(csrf.get("headerName").asString(),csrf.get("token").asString()).POST(HttpRequest.BodyPublishers.ofString(json.writeValueAsString(data))).build(),HttpResponse.BodyHandlers.ofString());}
  HttpResponse<String> login()throws Exception{return post("login",Map.of("email",email,"password",password));}
 }
 @Test void staffCannotAuthenticateBeforeEnrollmentAndRecoveryIsSingleUse()throws Exception{
  var b=new Browser();assertThat(b.login().body()).contains("\"setupRequired\":true");assertThat(b.get("users/me").statusCode()).isEqualTo(401);assertThat(b.get("admin/catalog").statusCode()).isEqualTo(401);
  var setup=b.post("mfa/setup",Map.of());assertThat(setup.statusCode()).isEqualTo(200);String secret=json.readTree(setup.body()).get("secret").asString();
  String ciphertext=db.queryForObject("SELECT pending_ciphertext FROM atlas_web.account_mfa WHERE user_id=?",String.class,id);assertThat(ciphertext).doesNotContain(secret);
  assertThat(b.post("mfa/verify",Map.of("code","abcdef")).statusCode()).isEqualTo(401);
  String code=Totp.code(secret,Instant.now().getEpochSecond()/30);var enabled=b.post("mfa/verify",Map.of("code",code));assertThat(enabled.statusCode()).withFailMessage(enabled.body()).isEqualTo(200);
  var codes=json.readTree(enabled.body()).get("recoveryCodes");assertThat(codes.size()).isEqualTo(10);String recovery=codes.get(0).asString();assertThat(b.get("users/me").body()).contains("\"mfaEnabled\":true");assertThat(b.get("admin/catalog").statusCode()).isEqualTo(200);
  assertThat(db.queryForObject("SELECT count(*) FROM atlas_web.mfa_recovery_codes WHERE user_id=?",Integer.class,id)).isEqualTo(10);
  b.post("logout",Map.of());assertThat(b.login().body()).contains("\"setupRequired\":false");assertThat(b.get("users/me").statusCode()).isEqualTo(401);
  assertThat(b.post("mfa/verify",Map.of("code",code)).statusCode()).isEqualTo(401);
  assertThat(b.post("mfa/verify",Map.of("code",recovery)).statusCode()).isEqualTo(200);
  b.post("logout",Map.of());b.login();assertThat(b.post("mfa/verify",Map.of("code",recovery)).statusCode()).isEqualTo(401);
  assertThat(db.queryForObject("SELECT count(*) FROM atlas_web.security_events WHERE user_id=? AND action='MFA_VERIFY' AND result='FAILURE'",Integer.class,id)).isGreaterThanOrEqualTo(3);
 }
 @Test void rolePromotionInvalidatesSessionWithoutSecondFactor()throws Exception{
  TestDatabase.adminSql("UPDATE atlas_web.users SET role='USER' WHERE id=?",id);var b=new Browser();assertThat(b.login().body()).contains("\"role\":\"USER\"");assertThat(b.get("users/me").statusCode()).isEqualTo(200);TestDatabase.adminSql("UPDATE atlas_web.users SET role='ADMIN' WHERE id=?",id);assertThat(b.get("users/me").statusCode()).isEqualTo(401);assertThat(b.get("admin/catalog").statusCode()).isEqualTo(401);
 }
 @Test void challengeNeedsPasswordAndExpires()throws Exception{
  var anonymous=new Browser();assertThat(anonymous.post("mfa/setup",Map.of()).statusCode()).isEqualTo(401);assertThat(anonymous.post("mfa/verify",Map.of("code","000000")).statusCode()).isEqualTo(401);
  var b=new Browser();b.login();String secret=json.readTree(b.post("mfa/setup",Map.of()).body()).get("secret").asString();db.update("UPDATE atlas_web.account_mfa SET pending_expires_at=NOW()-INTERVAL '1 second' WHERE user_id=?",id);assertThat(b.post("mfa/verify",Map.of("code",Totp.code(secret,Instant.now().getEpochSecond()/30))).statusCode()).isEqualTo(401);
 }
 @Test void runtimeCannotEscalateRolesOrRewriteSecurityAudit()throws Exception{
  try(var connection=TestDatabase.runtime();var statement=connection.createStatement()){
   assertThatThrownBy(()->statement.executeUpdate("UPDATE atlas_web.users SET role='ADMIN' WHERE id='"+id+"'")).isInstanceOf(java.sql.SQLException.class);
   assertThatThrownBy(()->statement.executeUpdate("INSERT INTO atlas_web.users(id,username,email,password_hash,role) VALUES(gen_random_uuid(),'forged','forged@example.invalid','unused','ADMIN')")).isInstanceOf(java.sql.SQLException.class);
   assertThatThrownBy(()->statement.executeUpdate("DELETE FROM atlas_web.security_events")).isInstanceOf(java.sql.SQLException.class);
  }
 }
}
