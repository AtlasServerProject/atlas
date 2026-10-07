package io.atlas.api;
import io.atlas.api.payment.*;
import io.atlas.api.commerce.model.CommerceModels.*;
import io.atlas.api.shared.error.ApiFailure;
import java.util.*;
import java.time.*;
import java.sql.Timestamp;
import java.nio.charset.StandardCharsets;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.*;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.ObjectMapper;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT,properties={"atlas.payment.enabled=true","atlas.payment.mode=test","atlas.payment.access-token=isolated-test-token","atlas.payment.webhook-secret=isolated-webhook-secret","atlas.payment.collector-id=123456","atlas.payment.notification-url=https://example.invalid/api/v1/webhooks/mercadopago","atlas.mail.web-url=https://example.invalid","atlas.payment.dispatch-delay-ms=3600000","atlas.payment.reconcile-delay-ms=3600000"})
@ActiveProfiles("test")
class PaymentIntegrationTest {
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){TestDatabase.properties(r);}
 @Autowired PaymentService service;@Autowired PaymentRepository repo;@Autowired JdbcTemplate db;@Autowired ObjectMapper json;@Autowired PlatformTransactionManager manager;
 @MockitoBean PaymentProvider provider;
 @org.springframework.boot.test.web.server.LocalServerPort int port;
 UUID order,user;Instant created;String paymentId;
 @BeforeEach void seed(){
 user=UUID.randomUUID();order=UUID.randomUUID();created=Instant.now().minusSeconds(5).truncatedTo(java.time.temporal.ChronoUnit.MICROS);paymentId=Long.toUnsignedString(ThreadLocalRandom.current().nextLong(1,Long.MAX_VALUE));
 db.update("INSERT INTO atlas_web.users(id,username,email,password_hash,email_verified) VALUES(?,'Payment test',?,'unused',TRUE)",user,user+"@example.invalid");UUID link=UUID.randomUUID(),subject=UUID.randomUUID();db.update("INSERT INTO atlas_web.minecraft_links(id,user_id,subject,core_player_id,minecraft_uuid,nickname,server,linked_at) VALUES(?,?,?,123,?,'PaymentTest','emerald',?)",link,user,subject,UUID.randomUUID(),Timestamp.from(created));
 long product=db.queryForObject("SELECT id FROM atlas_web.products ORDER BY id LIMIT 1",Long.class);
 var snapshot=new Snapshot(product,"VIP test","vip-test","emerald",30,2500,null,1,1,subject,123,UUID.randomUUID(),"PaymentTest");
 db.update("INSERT INTO atlas_web.orders(id,user_id,link_id,product_id,idempotency_key,request_hash,snapshot,total_cents,currency,quantity,created_at,expires_at,payment_status,delivery_status) VALUES(?,?,?,?,?,? ,?::jsonb,2500,'BRL',1,?,?,'PENDING','WAITING')",order,user,link,product,UUID.randomUUID().toString(),"a".repeat(64),json.writeValueAsString(snapshot),Timestamp.from(created),Timestamp.from(created.plusSeconds(1800)));
 when(provider.create(any(),any())).thenReturn(new PaymentProvider.Preference("test-"+order,"https://sandbox.mercadopago.com.br/checkout/test"));when(provider.search(any())).thenReturn(List.of());
 }
 PaymentProvider.Payment payment(String status,int cents,String collector,boolean live,Instant changed,Instant approved){return new PaymentProvider.Payment(paymentId,order.toString(),collector,cents,"BRL",status,live,changed,approved,status.equals("refunded")?cents:0);}
 PaymentProvider.Payment valid(String status){return payment(status,2500,"123456",false,Instant.now(),created.plusSeconds(1));}
 void deliver(PaymentProvider.Payment p){doReturn(p).when(provider).payment(paymentId);repo.enqueue(paymentId);service.dispatch();}
 String status(){return repo.order(order,user,false).paymentStatus();}
 int outbox(){return db.queryForObject("SELECT count(*) FROM atlas_web.delivery_outbox WHERE order_id=?",Integer.class,order);}
 @Test void checkoutIsPersistedAndIdempotentAndOwnerOnly(){var first=service.checkout(user,order);assertThat(first.state()).isEqualTo("READY");assertThat(service.checkout(user,order)).isEqualTo(first);verify(provider,times(1)).create(any(),any());assertThatThrownBy(()->service.checkout(UUID.randomUUID(),order)).isInstanceOf(ApiFailure.class);}
 @Test void timeoutDoesNotAutomaticallyCreateAnotherPreference(){when(provider.create(any(),any())).thenThrow(new IllegalStateException());assertThatThrownBy(()->service.checkout(user,order)).isInstanceOf(ApiFailure.class);assertThat(service.checkout(user,order).state()).isEqualTo("UNKNOWN");verify(provider,times(1)).create(any(),any());assertThat(outbox()).isZero();}
 @Test void approvedAndDuplicateEventsCreateExactlyOneObligation(){service.checkout(user,order);deliver(valid("approved"));deliver(valid("approved"));assertThat(status()).isEqualTo("PAID");assertThat(outbox()).isEqualTo(1);assertThat(repo.order(order,user,false).deliveryStatus()).isEqualTo("PROCESSING");}
 @Test void wrongAmountReceiverAndEnvironmentNeverDeliver(){service.checkout(user,order);for(var p:List.of(payment("approved",2400,"123456",false,Instant.now(),created),payment("approved",2500,"999",false,Instant.now(),created),payment("approved",2500,"123456",true,Instant.now(),created))){deliver(p);assertThat(status()).isEqualTo("PENDING");assertThat(outbox()).isZero();}}
 @Test void unknownReferenceAndPaymentWithoutAttemptNeverDeliver(){deliver(valid("approved"));assertThat(outbox()).isZero();service.checkout(user,order);var p=valid("approved");deliver(new PaymentProvider.Payment(p.id(),UUID.randomUUID().toString(),p.collector(),p.cents(),p.currency(),p.status(),p.live(),p.changedAt(),p.approvedAt(),0));assertThat(outbox()).isZero();}
 @Test void reorderedPendingAndOldApprovalNeverRegressPaidOrRefund(){service.checkout(user,order);deliver(valid("approved"));deliver(payment("pending",2500,"123456",false,created.minusSeconds(1),null));assertThat(status()).isEqualTo("PAID");deliver(valid("refunded"));assertThat(status()).isEqualTo("REFUNDED");deliver(valid("approved"));assertThat(status()).isEqualTo("REFUNDED");assertThat(outbox()).isEqualTo(1);assertThat(db.queryForObject("SELECT state FROM atlas_web.delivery_outbox WHERE order_id=?",String.class,order)).isEqualTo("REVIEW");}
 @Test void latePaymentIsPaidButHeldForReview(){service.checkout(user,order);deliver(payment("approved",2500,"123456",false,Instant.now(),created.plusSeconds(1801)));assertThat(status()).isEqualTo("PAID");assertThat(repo.order(order,user,false).deliveryStatus()).isEqualTo("REVIEW");assertThat(outbox()).isZero();}
 @Test void expiredOrderWithTimelyApprovalStillDelivers()throws Exception{service.checkout(user,order);try(var c=TestDatabase.admin();var st=c.prepareStatement("UPDATE atlas_web.orders SET created_at=?,expires_at=? WHERE id=?")){st.setTimestamp(1,Timestamp.from(created.minusSeconds(2000)));st.setTimestamp(2,Timestamp.from(created.minusSeconds(1)));st.setObject(3,order);st.executeUpdate();}deliver(payment("approved",2500,"123456",false,Instant.now(),created.minusSeconds(2)));assertThat(status()).isEqualTo("PAID");assertThat(outbox()).isEqualTo(1);}
 @Test void paymentFetchFailureRetriesDurably(){service.checkout(user,order);when(provider.payment(paymentId)).thenThrow(new IllegalStateException());repo.enqueue(paymentId);service.dispatch();assertThat(status()).isEqualTo("PENDING");assertThat(db.queryForObject("SELECT failures FROM atlas_web.payment_jobs WHERE payment_id=?",Integer.class,paymentId)).isEqualTo(1);db.update("UPDATE atlas_web.payment_jobs SET next_attempt=now() WHERE payment_id=?",paymentId);deliver(valid("approved"));assertThat(outbox()).isEqualTo(1);}
 @Test void webhookSignatureAndDeduplicationAreVerifiedBeforeQueueing()throws Exception{service.checkout(user,order);String request=UUID.randomUUID().toString(),timestamp="1780000000";var mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec("isolated-webhook-secret".getBytes(StandardCharsets.UTF_8),"HmacSHA256"));String signature="ts="+timestamp+",v1="+HexFormat.of().formatHex(mac.doFinal(("id:"+paymentId+";request-id:"+request+";ts:"+timestamp+";").getBytes(StandardCharsets.UTF_8)));assertThatThrownBy(()->service.webhook(signature,request,"999","payment")).isInstanceOf(ApiFailure.class);service.webhook(signature,request,paymentId,"payment");service.webhook(signature,request,paymentId,"payment");assertThat(db.queryForObject("SELECT generation FROM atlas_web.payment_jobs WHERE payment_id=?",Integer.class,paymentId)).isEqualTo(1);assertThat(outbox()).isZero();}
 @Test void lostWebhookIsRecoveredByReconciliation(){service.checkout(user,order);when(provider.search(order.toString())).thenReturn(List.of(valid("approved")));when(provider.payment(paymentId)).thenReturn(valid("approved"));service.reconcile();service.dispatch();assertThat(outbox()).isEqualTo(1);}
 @Test void unknownCreationIsReconciledWithoutRetryingCreation(){when(provider.create(any(),any())).thenThrow(new IllegalStateException());assertThatThrownBy(()->service.checkout(user,order)).isInstanceOf(ApiFailure.class);when(provider.search(order.toString())).thenReturn(List.of(valid("approved")));when(provider.payment(paymentId)).thenReturn(valid("approved"));service.reconcile();service.dispatch();assertThat(outbox()).isEqualTo(1);verify(provider,times(1)).create(any(),any());}
 @Test void twoPaymentsAreReviewedAndOnlyOneDelivers(){service.checkout(user,order);deliver(valid("approved"));paymentId=Long.toUnsignedString(ThreadLocalRandom.current().nextLong(1,Long.MAX_VALUE));deliver(valid("approved"));assertThat(outbox()).isEqualTo(1);deliver(valid("refunded"));assertThat(status()).isEqualTo("PAID");}
 @Test void sameProviderPaymentCannotBeMovedToAnotherOrder(){service.checkout(user,order);deliver(valid("approved"));UUID original=order;String originalPayment=paymentId;seed();paymentId=originalPayment;service.checkout(user,order);deliver(valid("approved"));assertThat(outbox()).isZero();assertThat(status()).isEqualTo("PENDING");assertThat(db.queryForObject("SELECT count(*) FROM atlas_web.delivery_outbox WHERE order_id=?",Integer.class,original)).isEqualTo(1);}
 @Test void concurrentCheckoutMakesOnlyOneProviderCall()throws Exception{var pool=Executors.newFixedThreadPool(2);try{var first=pool.submit(()->service.checkout(user,order));var second=pool.submit(()->service.checkout(user,order));first.get(10,TimeUnit.SECONDS);second.get(10,TimeUnit.SECONDS);verify(provider,times(1)).create(any(),any());}finally{pool.shutdownNow();}}
 @Test void outboxFailureRollsBackPaymentAndRetryIsSafe()throws Exception{service.checkout(user,order);try(var connection=TestDatabase.admin();var statement=connection.createStatement()){statement.execute("CREATE OR REPLACE FUNCTION atlas_web.fail_m5_outbox() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'isolated fault'; END $$");statement.execute("CREATE TRIGGER fail_m5_outbox BEFORE INSERT ON atlas_web.delivery_outbox FOR EACH ROW EXECUTE FUNCTION atlas_web.fail_m5_outbox()");try{deliver(valid("approved"));assertThat(status()).isEqualTo("PENDING");assertThat(outbox()).isZero();}finally{statement.execute("DROP TRIGGER fail_m5_outbox ON atlas_web.delivery_outbox");statement.execute("DROP FUNCTION atlas_web.fail_m5_outbox()");}}deliver(valid("approved"));assertThat(outbox()).isEqualTo(1);}
 @Test void eventArrivingDuringLeaseRemainsPendingAfterCompletion(){repo.enqueue(paymentId);var job=repo.claim().stream().filter(j->j.id().equals(paymentId)).findFirst().orElseThrow();repo.enqueue(paymentId);repo.finish(job);assertThat(repo.claim().stream().anyMatch(j->j.id().equals(paymentId))).isTrue();}
 @Test void publicWebhookRequiresSignatureAndDoesNotRequireSessionOrCsrf()throws Exception{
 var client=java.net.http.HttpClient.newHttpClient();String path="http://127.0.0.1:"+port+"/api/v1/webhooks/mercadopago?data.id="+paymentId+"&type=payment";
 var unsigned=java.net.http.HttpRequest.newBuilder(java.net.URI.create(path)).POST(java.net.http.HttpRequest.BodyPublishers.ofString("{}")).build();
 assertThat(client.send(unsigned,java.net.http.HttpResponse.BodyHandlers.discarding()).statusCode()).isEqualTo(401);
 String request=UUID.randomUUID().toString(),ts="1780000000";var mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec("isolated-webhook-secret".getBytes(StandardCharsets.UTF_8),"HmacSHA256"));
 String signature="ts="+ts+",v1="+HexFormat.of().formatHex(mac.doFinal(("id:"+paymentId+";request-id:"+request+";ts:"+ts+";").getBytes(StandardCharsets.UTF_8)));
 var signed=java.net.http.HttpRequest.newBuilder(java.net.URI.create(path)).header("x-signature",signature).header("x-request-id",request).POST(java.net.http.HttpRequest.BodyPublishers.ofString("{}")).build();
 assertThat(client.send(signed,java.net.http.HttpResponse.BodyHandlers.discarding()).statusCode()).isEqualTo(200);
 var ownerOnly=java.net.http.HttpRequest.newBuilder(java.net.URI.create("http://127.0.0.1:"+port+"/api/v1/orders/"+order+"/payment")).POST(java.net.http.HttpRequest.BodyPublishers.ofString("{}")).build();assertThat(client.send(ownerOnly,java.net.http.HttpResponse.BodyHandlers.discarding()).statusCode()).isIn(401,403);
 }
 @Test void providerRedirectIsRestricted(){assertThat(MercadoPagoProvider.safeUrl("https://sandbox.mercadopago.com.br/checkout/test")).isTrue();for(String url:List.of("javascript:alert(1)","https://mercadopago.com.br.evil.invalid/a","https://www.mercadopago.com.br@evil.invalid/a","http://www.mercadopago.com.br/a"))assertThat(MercadoPagoProvider.safeUrl(url)).isFalse();}
}
