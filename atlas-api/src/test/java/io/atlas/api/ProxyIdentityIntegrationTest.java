package io.atlas.api;
import java.net.*;import java.net.http.*;import java.util.*;import javax.crypto.Mac;import javax.crypto.spec.SecretKeySpec;import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.*;import org.springframework.beans.factory.annotation.Autowired;import org.springframework.boot.test.context.SpringBootTest;import org.springframework.boot.test.web.server.LocalServerPort;import org.springframework.test.context.*;import org.springframework.jdbc.core.JdbcTemplate;import tools.jackson.databind.ObjectMapper;import static org.assertj.core.api.Assertions.*;
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT,properties={"atlas.proxy.required=true","atlas.proxy.hmac-key=synthetic-integration-proxy-key-01234567890123456789","atlas.auth.ip-attempts=2"})
@ActiveProfiles("test")
class ProxyIdentityIntegrationTest {
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){TestDatabase.properties(r);}
 @LocalServerPort int port;@Autowired ObjectMapper json;@Autowired JdbcTemplate db;
 final String key="synthetic-integration-proxy-key-01234567890123456789";
 @BeforeEach void clear(){db.update("DELETE FROM atlas_web.auth_rate_limits");}
 HttpResponse<String> attempt(String ip,boolean signed)throws Exception{
  var client=HttpClient.newBuilder().cookieHandler(new CookieManager(null,CookiePolicy.ACCEPT_ALL)).build();String base="http://127.0.0.1:"+port+"/api/v1/auth/";var csrf=json.readTree(client.send(HttpRequest.newBuilder(URI.create(base+"csrf")).GET().build(),HttpResponse.BodyHandlers.ofString()).body());
  var builder=HttpRequest.newBuilder(URI.create(base+"login")).header("Content-Type","application/json").header(csrf.get("headerName").asString(),csrf.get("token").asString()).header("CF-Connecting-IP",ip).header("X-Forwarded-For",ip);
  if(signed){String now=""+java.time.Instant.now().getEpochSecond();var mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8),"HmacSHA256"));String payload="POST\n/api/v1/auth/login\n"+now+"\n"+ip;builder.header("X-Atlas-Verified-IP",ip).header("X-Atlas-IP-Time",now).header("X-Atlas-IP-Signature",HexFormat.of().formatHex(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8))));}
  return client.send(builder.POST(HttpRequest.BodyPublishers.ofString(json.writeValueAsString(Map.of("email",UUID.randomUUID()+"@example.invalid","password","synthetic-invalid-password")))).build(),HttpResponse.BodyHandlers.ofString());
 }
 @Test void oneVisitorCannotExhaustAnotherVisitorsLoginLimit()throws Exception{assertThat(attempt("203.0.113.1",true).statusCode()).isEqualTo(401);assertThat(attempt("203.0.113.1",true).statusCode()).isEqualTo(401);assertThat(attempt("203.0.113.1",true).statusCode()).isEqualTo(429);assertThat(attempt("203.0.113.2",true).statusCode()).isEqualTo(401);}
 @Test void unsignedClientHeadersFailClosedRatherThanCreateGlobalBucket()throws Exception{var response=attempt("203.0.113.3",false);assertThat(response.statusCode()).isEqualTo(503);assertThat(response.body()).contains("GATEWAY_IDENTITY_UNAVAILABLE");assertThat(db.queryForObject("SELECT count(*) FROM atlas_web.auth_rate_limits",Integer.class)).isZero();}
}
