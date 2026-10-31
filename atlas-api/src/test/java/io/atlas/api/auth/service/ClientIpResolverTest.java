package io.atlas.api.auth.service;
import java.time.*;import java.nio.charset.StandardCharsets;import java.util.HexFormat;
import javax.crypto.Mac;import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.Test;import org.springframework.mock.web.MockHttpServletRequest;
import static org.assertj.core.api.Assertions.*;
class ClientIpResolverTest {
 final String key="synthetic-test-key-for-gateway-identity-0123456789";
 final Clock clock=Clock.fixed(Instant.parse("2026-10-25T12:00:00Z"),ZoneOffset.UTC);
 MockHttpServletRequest signed(String ip,long seconds)throws Exception{
  var r=new MockHttpServletRequest("POST","/api/v1/auth/login");r.setRemoteAddr("127.0.0.1");String time=""+(clock.instant().getEpochSecond()+seconds);
  var mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8),"HmacSHA256"));
  r.addHeader("X-Atlas-Verified-IP",ip);r.addHeader("X-Atlas-IP-Time",time);r.addHeader("X-Atlas-IP-Signature",HexFormat.of().formatHex(mac.doFinal(("POST\n/api/v1/auth/login\n"+time+"\n"+ip).getBytes(StandardCharsets.UTF_8))));return r;
 }
 @Test void separateClientsKeepSeparateBuckets()throws Exception{var resolver=new ClientIpResolver(key,true,clock);assertThat(resolver.resolve(signed("203.0.113.1",0))).isEqualTo("203.0.113.1");assertThat(resolver.resolve(signed("203.0.113.2",0))).isEqualTo("203.0.113.2");}
 @Test void rejectsForgedExpiredAndNonGatewayRequests()throws Exception{
  var resolver=new ClientIpResolver(key,true,clock);var forged=signed("203.0.113.1",0);forged.removeHeader("X-Atlas-IP-Signature");forged.addHeader("X-Atlas-IP-Signature","0".repeat(64));assertThatThrownBy(()->resolver.resolve(forged)).hasMessageContaining("temporariamente");
  var expired=signed("203.0.113.1",-61);assertThatThrownBy(()->resolver.resolve(expired)).isInstanceOf(RuntimeException.class);
  var direct=signed("203.0.113.1",0);direct.setRemoteAddr("198.51.100.2");assertThatThrownBy(()->resolver.resolve(direct)).isInstanceOf(RuntimeException.class);
  var changed=signed("203.0.113.1",0);changed.setRequestURI("/api/v1/auth/register");assertThatThrownBy(()->resolver.resolve(changed)).isInstanceOf(RuntimeException.class);
 }
 @Test void neverTrustsOrdinaryForwardingHeaders(){var r=new MockHttpServletRequest();r.setRemoteAddr("198.51.100.3");r.addHeader("X-Forwarded-For","127.0.0.1");r.addHeader("CF-Connecting-IP","127.0.0.1");assertThat(new ClientIpResolver("",false,clock).resolve(r)).isEqualTo("198.51.100.3");assertThatThrownBy(()->new ClientIpResolver(key,true,clock).resolve(r)).isInstanceOf(RuntimeException.class);}
}
