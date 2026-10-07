package io.atlas.api.payment;
import java.net.http.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.time.*;
import org.junit.jupiter.api.*;
import tools.jackson.databind.ObjectMapper;
import org.mockito.ArgumentCaptor;
import static org.mockito.Mockito.*;
import static org.assertj.core.api.Assertions.*;
import io.atlas.api.commerce.model.CommerceModels.*;
class MercadoPagoProviderTest {
 HttpClient client;MercadoPagoProvider provider;ObjectMapper json=new ObjectMapper();
 @BeforeEach void setup(){client=mock(HttpClient.class);provider=new MercadoPagoProvider(new PaymentSettings(true,"test","private-test-token","private-test-secret","123456","https://example.invalid","https://example.invalid/webhook"),json,client);}
 @SuppressWarnings("unchecked") void reply(String text)throws Exception{HttpResponse<InputStream> response=mock(HttpResponse.class);when(response.statusCode()).thenReturn(200);when(response.body()).thenAnswer(a->new ByteArrayInputStream(text.getBytes(StandardCharsets.UTF_8)));when(client.send(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenReturn(response);}
 @Test void parseRealProviderFieldsPreservesCentsAndApprovalDate()throws Exception{reply("{\"id\":123,\"external_reference\":\"bce4c142-c68e-491c-a58c-e6ecac9a7d17\",\"collector_id\":123456,\"transaction_amount\":25.00,\"currency_id\":\"BRL\",\"status\":\"approved\",\"live_mode\":false,\"date_last_updated\":\"2026-10-03T08:00:01.000-03:00\",\"date_approved\":\"2026-10-03T08:00:00.000-03:00\",\"transaction_amount_refunded\":0}");var p=provider.payment("123");assertThat(p.cents()).isEqualTo(2500);assertThat(p.collector()).isEqualTo("123456");assertThat(p.approvedAt()).isEqualTo(Instant.parse("2026-10-03T11:00:00Z"));assertThat(p.live()).isFalse();var request=ArgumentCaptor.forClass(HttpRequest.class);verify(client).send(request.capture(),any(HttpResponse.BodyHandler.class));assertThat(request.getValue().uri().toString()).isEqualTo("https://api.mercadopago.com/v1/payments/123");assertThat(request.getValue().timeout()).contains(Duration.ofSeconds(10));}
 @Test void createsHostedSandboxPreferenceAndRejectsUnsafeRedirect()throws Exception{reply("{\"id\":\"pref-test\",\"sandbox_init_point\":\"https://sandbox.mercadopago.com.br/checkout/test\",\"init_point\":\"https://www.mercadopago.com.br/checkout/live\"}");var now=Instant.now();var s=new Snapshot(1,"VIP 1","vip-1","emerald",30,2500,null,1,1,UUID.randomUUID(),1,UUID.randomUUID(),"Player");var order=new OrderView(UUID.randomUUID(),s,2500,"BRL",1,now,now.plusSeconds(1800),"PENDING","WAITING");assertThat(provider.create(order,"attempt-test").url()).contains("sandbox.mercadopago.com.br");reply("{\"id\":\"pref-test\",\"sandbox_init_point\":\"https://evil.invalid/checkout\"}");assertThatThrownBy(()->provider.create(order,"attempt-test")).isInstanceOf(IllegalStateException.class);}
 @Test void networkFailureDoesNotLeakAuthorizationOrResponse()throws Exception{when(client.send(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenThrow(new IOException("private-test-token"));assertThatThrownBy(()->provider.payment("123")).hasMessage("Provider unavailable").hasNoCause();}
 @Test void rejectsNonNumericPaymentPath(){assertThatThrownBy(()->provider.payment("../users/me")).isInstanceOf(IllegalArgumentException.class);verifyNoInteractions(client);}

 @Test @SuppressWarnings("unchecked") void liveFlagNeedsAuthenticatedTestSellerEvidence()throws Exception{
  String payment="{\"id\":123,\"external_reference\":\"bce4c142-c68e-491c-a58c-e6ecac9a7d17\",\"collector_id\":123456,\"transaction_amount\":25,\"currency_id\":\"BRL\",\"status\":\"approved\",\"live_mode\":true,\"date_last_updated\":\"2026-10-03T11:00:01Z\",\"date_approved\":\"2026-10-03T11:00:00Z\",\"transaction_amount_refunded\":0}";
  for(String account:List.of("{\"id\":123456,\"tags\":[\"test_user\"]}","{\"id\":123456,\"tags\":[]}","{\"id\":999999,\"tags\":[\"test_user\"]}")){
   when(client.send(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenAnswer(a->{
    HttpRequest request=a.getArgument(0);String body=request.uri().getPath().equals("/users/me")?account:payment;
    HttpResponse<InputStream> response=mock(HttpResponse.class);when(response.statusCode()).thenReturn(200);when(response.body()).thenReturn(new ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8)));return response;
   });
   var result=provider.payment("123");boolean verified=account.contains("123456")&&account.contains("test_user");
   assertThat(result.live()).isTrue();assertThat(result.verifiedTestCollector()).isEqualTo(verified);
   assertThat(result.matchesMode(false)).isEqualTo(verified);assertThat(result.matchesMode(true)).isEqualTo(!verified);
  }
 }
}
