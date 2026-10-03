package io.atlas.api;
import io.atlas.api.delivery.*;
import io.atlas.api.delivery.DeliveryModels.*;
import io.atlas.api.commerce.model.CommerceModels.Snapshot;
import io.atlas.api.shared.error.ApiFailure;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.*;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.ObjectMapper;
import java.time.*;
import java.sql.Timestamp;
import java.util.*;
import java.util.concurrent.*;
import static org.assertj.core.api.Assertions.*;
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT,properties={"atlas.delivery.enabled=true","atlas.delivery.mode=test","atlas.core.key=isolated-core-key-at-least-43-characters-for-tests"})
@ActiveProfiles("test")
class DeliveryIntegrationTest {
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){TestDatabase.properties(r);}
 @Autowired DeliveryService service;@Autowired DeliveryRepository repo;@Autowired JdbcTemplate db;@Autowired ObjectMapper json;
 @org.springframework.boot.test.web.server.LocalServerPort int port;
 UUID user,order,subject,id;Instant created;
 @BeforeEach void seed(){user=UUID.randomUUID();order=UUID.randomUUID();subject=UUID.randomUUID();id=UUID.randomUUID();created=Instant.now().minusSeconds(5);UUID link=UUID.randomUUID();
 db.update("INSERT INTO atlas_web.users(id,username,email,password_hash,email_verified) VALUES(?,'Delivery test',?,'unused',TRUE)",user,user+"@example.invalid");
 db.update("INSERT INTO atlas_web.minecraft_links(id,user_id,subject,core_player_id,minecraft_uuid,nickname,server,linked_at) VALUES(?,?,?,123,?,'DeliveryTest','emerald',?)",link,user,subject,UUID.randomUUID(),Timestamp.from(created));
 long product=db.queryForObject("SELECT id FROM atlas_web.products ORDER BY id LIMIT 1",Long.class);var snap=new Snapshot(product,"VIP 1","vip-1","emerald",30,2500,null,1,1,subject,123,UUID.randomUUID(),"DeliveryTest");
 db.update("INSERT INTO atlas_web.orders(id,user_id,link_id,product_id,idempotency_key,request_hash,snapshot,total_cents,currency,quantity,created_at,expires_at,payment_status,delivery_status) VALUES(?,?,?,?,?,? ,?::jsonb,2500,'BRL',1,?,?,'PAID','PROCESSING')",order,user,link,product,UUID.randomUUID().toString(),"a".repeat(64),json.writeValueAsString(snap),Timestamp.from(created),Timestamp.from(created.plusSeconds(1800)));
 db.update("INSERT INTO atlas_web.payment_attempts(id,order_id,mode,state,created_at,updated_at) VALUES(?,?,'test','CREATING',?,?)",UUID.randomUUID(),order,Timestamp.from(created),Timestamp.from(created));db.update("INSERT INTO atlas_web.delivery_outbox(id,order_id,created_at) VALUES(?,?,?)",id,order,Timestamp.from(created));}
 Delivery claim(){return service.claim().stream().filter(d->d.id().equals(id)).findFirst().orElseThrow();}
 Ack ack(Delivery d){var now=Instant.now().truncatedTo(java.time.temporal.ChronoUnit.MILLIS);return new Ack(d.leaseToken(),new Receipt(id,UUID.randomUUID(),subject,123,"emerald","test","vip-1",30,now),new Balance(subject,123,"emerald",30*86400000L,0,0,now));}
 @Test void leaseAndAckAreIdempotentAndPublicMirrorIsOwned(){var d=claim();assertThat(service.claim()).noneMatch(x->x.id().equals(id));var ack=ack(d);service.ack(id,ack);service.ack(id,ack);assertThat(db.queryForObject("SELECT count(*) FROM atlas_web.order_events WHERE order_id=? AND event='DELIVERY_CONFIRMED'",Integer.class,order)).isEqualTo(1);assertThat(service.vip(user).activeLevel()).isEqualTo(1);assertThat(service.vip(UUID.randomUUID()).linked()).isFalse();assertThat(db.queryForObject("SELECT delivery_status FROM atlas_web.orders WHERE id=?",String.class,order)).isEqualTo("DELIVERED");}
 @Test void expiredClaimAndStaleAckCannotOverwriteNewLease(){var first=claim();db.update("UPDATE atlas_web.delivery_outbox SET lease_until=now()-interval '1 second',next_attempt=now() WHERE id=?",id);var second=claim();assertThat(second.leaseToken()).isNotEqualTo(first.leaseToken());assertThatThrownBy(()->service.ack(id,ack(first))).isInstanceOf(ApiFailure.class);service.ack(id,ack(second));}
 @Test void mismatchedReceiptAndRefundNeverMarkDelivered(){var d=claim();var a=ack(d);var wrong=new Ack(d.leaseToken(),new Receipt(id,a.receipt().receiptId(),UUID.randomUUID(),123,"emerald","test","vip-1",30,a.receipt().activatedAt()),a.balance());assertThatThrownBy(()->service.ack(id,wrong)).isInstanceOf(ApiFailure.class);db.update("UPDATE atlas_web.orders SET payment_status='REFUNDED' WHERE id=?",order);assertThatThrownBy(()->service.ack(id,a)).isInstanceOf(ApiFailure.class);}
 @Test void paymentsFromAnotherModeAreNeverClaimed(){db.update("UPDATE atlas_web.payment_attempts SET mode='production' WHERE order_id=?",order);assertThat(service.claim()).noneMatch(x->x.id().equals(id));}
 @Test void retriesUseSameIdRequirePaidOrderAndRecordReason(){var d=claim();service.failed(id,new Failed(d.leaseToken(),"IDENTITY_MISMATCH"));service.retry(id,user,"Recipient checked in isolated fixture");assertThat(claim().id()).isEqualTo(id);assertThat(db.queryForObject("SELECT count(*) FROM atlas_web.delivery_audit WHERE delivery_id=? AND action='REPROCESS'",Integer.class,id)).isEqualTo(1);}
 @Test void retryLimitMovesToReviewAndNeverDeletesOrder(){db.update("UPDATE atlas_web.delivery_outbox SET attempts=8 WHERE id=?",id);assertThat(service.claim()).noneMatch(x->x.id().equals(id));assertThat(db.queryForObject("SELECT delivery_status FROM atlas_web.orders WHERE id=?",String.class,order)).isEqualTo("REVIEW");}
 @Test void twoWorkersCannotClaimSameDelivery()throws Exception{var pool=Executors.newFixedThreadPool(2);try{var go=new CountDownLatch(1);Callable<List<Delivery>> task=()->{go.await();return service.claim();};var a=pool.submit(task);var b=pool.submit(task);go.countDown();var all=new ArrayList<>(a.get(10,TimeUnit.SECONDS));all.addAll(b.get(10,TimeUnit.SECONDS));assertThat(all.stream().filter(x->x.id().equals(id)).count()).isEqualTo(1);}finally{pool.shutdownNow();}}
 @Test void pauseResumeCrossesOfflineExpiriesAndMirrorCannotRegress(){var t=Instant.parse("2026-01-01T00:00:00Z");var b=new Balance(subject,123,"emerald",10*86400000L,20*86400000L,30*86400000L,t);var now=t.plusSeconds(35*86400L);assertThat(DeliveryModels.view(true,b,now).activeLevel()).isEqualTo(2);assertThat(DeliveryModels.view(true,b,now).paused().getFirst().remainingSeconds()).isEqualTo(10*86400L);assertThat(DeliveryModels.view(true,b,t.plusSeconds(65*86400L)).activeLevel()).isZero();service.sync(List.of(b));service.sync(List.of(new Balance(subject,123,"emerald",0,0,0,t.minusSeconds(1))));assertThat(repo.vip(user,t).activeLevel()).isEqualTo(3);}
 @Test void internalRouteRequiresKeyAndNeverUsesBrowserSession()throws Exception{var client=java.net.http.HttpClient.newHttpClient();var url=java.net.URI.create("http://127.0.0.1:"+port+"/internal/v1/deliveries/claim");var noKey=java.net.http.HttpRequest.newBuilder(url).header("Content-Type","application/json").POST(java.net.http.HttpRequest.BodyPublishers.ofString("{\"server\":\"emerald\"}")).build();assertThat(client.send(noKey,java.net.http.HttpResponse.BodyHandlers.discarding()).statusCode()).isEqualTo(403);var valid=java.net.http.HttpRequest.newBuilder(url).header("X-Atlas-Key","isolated-core-key-at-least-43-characters-for-tests").header("Content-Type","application/json").POST(java.net.http.HttpRequest.BodyPublishers.ofString("{\"server\":\"emerald\"}")).build();assertThat(client.send(valid,java.net.http.HttpResponse.BodyHandlers.discarding()).statusCode()).isEqualTo(200);}

 @Test void ackStorageFailureRollsBackStatusAndReplayCompletesOnce()throws Exception{
  var d=claim();var a=ack(d);
  try(var c=TestDatabase.admin();var s=c.createStatement()){
   s.execute("CREATE FUNCTION atlas_web.fail_vip_mirror() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'isolated mirror failure'; END $$");s.execute("CREATE TRIGGER fail_vip_mirror BEFORE INSERT ON atlas_web.vip_mirrors FOR EACH ROW EXECUTE FUNCTION atlas_web.fail_vip_mirror()");
   try{assertThatThrownBy(()->service.ack(id,a)).isInstanceOf(RuntimeException.class);assertThat(db.queryForObject("SELECT state FROM atlas_web.delivery_outbox WHERE id=?",String.class,id)).isEqualTo("WAITING");}
   finally{s.execute("DROP TRIGGER fail_vip_mirror ON atlas_web.vip_mirrors");s.execute("DROP FUNCTION atlas_web.fail_vip_mirror()");}
  }
  service.ack(id,a);service.ack(id,a);assertThat(db.queryForObject("SELECT count(*) FROM atlas_web.order_events WHERE order_id=? AND event='DELIVERY_CONFIRMED'",Integer.class,order)).isEqualTo(1);
 }
}
