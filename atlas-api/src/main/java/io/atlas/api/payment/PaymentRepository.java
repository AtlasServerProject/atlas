package io.atlas.api.payment;
import java.util.*;
import java.time.*;
import java.sql.Timestamp;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import tools.jackson.databind.ObjectMapper;
import io.atlas.api.commerce.model.CommerceModels.*;
@Repository
public class PaymentRepository {
 private final JdbcTemplate db;private final ObjectMapper json;
 public PaymentRepository(JdbcTemplate db,ObjectMapper json){this.db=db;this.json=json;}
 public record Attempt(UUID id,UUID orderId,String mode,String state,String url){}
 public record Job(String id,long generation,UUID lease){}
 public OrderView order(UUID id,UUID user,boolean lock){String sql="SELECT * FROM atlas_web.orders WHERE id=?"+(user==null?"":" AND user_id=?")+(lock?" FOR UPDATE":"");return db.query(sql,(r,n)->new OrderView(r.getObject("id",UUID.class),json.readValue(r.getString("snapshot"),Snapshot.class),r.getInt("total_cents"),r.getString("currency"),r.getInt("quantity"),r.getTimestamp("created_at").toInstant(),r.getTimestamp("expires_at").toInstant(),r.getString("payment_status"),r.getString("delivery_status")),user==null?new Object[]{id}:new Object[]{id,user}).stream().findFirst().orElse(null);}
 public Attempt attempt(UUID order){return db.query("SELECT * FROM atlas_web.payment_attempts WHERE order_id=?",(r,n)->new Attempt(r.getObject("id",UUID.class),order,r.getString("mode"),r.getString("state"),r.getString("checkout_url")),order).stream().findFirst().orElse(null);}
 public Attempt create(UUID order,String mode,Instant now){UUID id=UUID.randomUUID();db.update("INSERT INTO atlas_web.payment_attempts(id,order_id,mode,state,created_at,updated_at) VALUES(?,?,?,'CREATING',?,?)",id,order,mode,Timestamp.from(now),Timestamp.from(now));return new Attempt(id,order,mode,"CREATING",null);}
 public void ready(Attempt a,PaymentProvider.Preference p,Instant now){db.update("UPDATE atlas_web.payment_attempts SET state='READY',preference_id=?,checkout_url=?,updated_at=? WHERE id=? AND state='CREATING'",p.id(),p.url(),Timestamp.from(now),a.id());}
 public void unknown(Attempt a,Instant now){db.update("UPDATE atlas_web.payment_attempts SET state='UNKNOWN',updated_at=? WHERE id=? AND state='CREATING'",Timestamp.from(now),a.id());}
 public boolean event(String hash,String payment){return db.update("INSERT INTO atlas_web.payment_webhooks(event_hash,payment_id) VALUES(?,?) ON CONFLICT DO NOTHING",hash,payment)>0;}
 public void enqueue(String id){db.update("INSERT INTO atlas_web.payment_jobs(payment_id) VALUES(?) ON CONFLICT(payment_id) DO UPDATE SET generation=payment_jobs.generation+1,next_attempt=now()",id);}
 public List<Job> claim(){return db.query("WITH due AS (SELECT payment_id FROM atlas_web.payment_jobs WHERE generation>completed_generation AND next_attempt<=now() AND (lease_until IS NULL OR lease_until<now()) ORDER BY next_attempt LIMIT 10 FOR UPDATE SKIP LOCKED) UPDATE atlas_web.payment_jobs j SET lease_until=now()+interval '60 seconds',lease_token=gen_random_uuid() FROM due WHERE j.payment_id=due.payment_id RETURNING j.payment_id,j.generation,j.lease_token",(r,n)->new Job(r.getString(1),r.getLong(2),r.getObject(3,UUID.class)));}
 public void finish(Job job){db.update("UPDATE atlas_web.payment_jobs SET completed_generation=greatest(completed_generation,?),lease_until=NULL,lease_token=NULL,failures=0 WHERE payment_id=? AND lease_token=?",job.generation(),job.id(),job.lease());}
 public void retry(Job job){db.update("UPDATE atlas_web.payment_jobs SET lease_until=NULL,lease_token=NULL,failures=failures+1,next_attempt=now()+interval '60 seconds' WHERE payment_id=? AND lease_token=?",job.id(),job.lease());}
 public boolean owns(Job job){return Boolean.TRUE.equals(db.queryForObject("SELECT EXISTS(SELECT 1 FROM atlas_web.payment_jobs WHERE payment_id=? AND lease_token=?)",Boolean.class,job.id(),job.lease()));}
 public List<UUID> dueOrders(){return db.query("SELECT order_id FROM atlas_web.payment_attempts WHERE state IN ('READY','UNKNOWN','REVIEW') OR (state='CREATING' AND updated_at<now()-interval '60 seconds') ORDER BY updated_at LIMIT 20",(r,n)->r.getObject(1,UUID.class));}
 public void scanned(UUID order){db.update("UPDATE atlas_web.payment_attempts SET updated_at=now(),state=CASE WHEN state='CREATING' THEN 'UNKNOWN' ELSE state END WHERE order_id=?",order);}
 public UUID observedOrder(String id){return db.query("SELECT order_id FROM atlas_web.payment_observations WHERE payment_id=?",(r,n)->r.getObject(1,UUID.class),id).stream().findFirst().orElse(null);}
 public Instant observedAt(String id){return db.query("SELECT changed_at FROM atlas_web.payment_observations WHERE payment_id=?",(r,n)->r.getTimestamp(1).toInstant(),id).stream().findFirst().orElse(null);}
 public String previousStatus(String id){return db.query("SELECT provider_status FROM atlas_web.payment_observations WHERE payment_id=?",(r,n)->r.getString(1),id).stream().findFirst().orElse(null);}
 public boolean anotherPaid(UUID order,String id){return Boolean.TRUE.equals(db.queryForObject("SELECT EXISTS(SELECT 1 FROM atlas_web.payment_observations WHERE order_id=? AND payment_id<>? AND provider_status IN ('approved','refunded','charged_back'))",Boolean.class,order,id));}
 public void observe(PaymentProvider.Payment p,UUID order,Instant now){db.update("INSERT INTO atlas_web.payment_observations(payment_id,order_id,provider_status,changed_at,checked_at) VALUES(?,?,?,?,?) ON CONFLICT(payment_id) DO UPDATE SET provider_status=excluded.provider_status,changed_at=excluded.changed_at,checked_at=excluded.checked_at",p.id(),order,p.status(),Timestamp.from(p.changedAt()),Timestamp.from(now));}
 public void status(UUID order,String payment,String delivery,String event,Instant now){db.update("UPDATE atlas_web.orders SET payment_status=?,delivery_status=? WHERE id=?",payment,delivery,order);db.update("INSERT INTO atlas_web.order_events(order_id,event,request_id,created_at) VALUES(?,?,?,?)",order,event,"payment-reconciliation",Timestamp.from(now));}
 public void outbox(UUID order,Instant now){db.update("INSERT INTO atlas_web.delivery_outbox(id,order_id,created_at) VALUES(?,?,?) ON CONFLICT(order_id) DO NOTHING",UUID.randomUUID(),order,Timestamp.from(now));}
 public void review(String payment,String reason,Instant now){db.update("INSERT INTO atlas_web.payment_reviews(payment_id,reason,created_at) VALUES(?,?,?) ON CONFLICT DO NOTHING",payment,reason,Timestamp.from(now));}
 public void hold(UUID order){db.update("UPDATE atlas_web.delivery_outbox SET state='REVIEW' WHERE order_id=? AND state='WAITING'",order);}
}
