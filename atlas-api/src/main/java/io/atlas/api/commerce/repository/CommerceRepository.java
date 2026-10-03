package io.atlas.api.commerce.repository;
import io.atlas.api.commerce.model.CommerceModels.*;
import java.util.*;
import java.time.Instant;
import java.sql.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import tools.jackson.databind.ObjectMapper;
@Repository
public class CommerceRepository {
 private final JdbcTemplate db;private final ObjectMapper json;
 public CommerceRepository(JdbcTemplate db,ObjectMapper json){this.db=db;this.json=json;}
 private Timestamp ts(Instant value){return Timestamp.from(value);}
 public void lockUser(UUID id){db.queryForObject("SELECT id FROM atlas_web.users WHERE id=? FOR UPDATE",UUID.class,id);}
 public void lockSubject(UUID id){db.queryForObject("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",Object.class,id.toString());}
 private LinkView link(ResultSet r,int n)throws SQLException{return new LinkView(r.getObject("id",UUID.class),r.getObject("subject",UUID.class),r.getLong("core_player_id"),r.getObject("minecraft_uuid",UUID.class),r.getString("nickname"),r.getString("server"),r.getTimestamp("linked_at").toInstant());}
 public LinkView current(UUID user){return db.query("SELECT * FROM atlas_web.minecraft_links WHERE user_id=? AND revoked_at IS NULL",this::link,user).stream().findFirst().orElse(null);}
 public boolean occupied(UUID subject){return Boolean.TRUE.equals(db.queryForObject("SELECT EXISTS(SELECT 1 FROM atlas_web.minecraft_links WHERE subject=? AND revoked_at IS NULL)",Boolean.class,subject));}
 public ChallengeView pending(UUID user,Instant now){return db.query("SELECT * FROM atlas_web.minecraft_challenges WHERE user_id=? AND state IN ('WAITING','PROVED') AND expires_at>? ORDER BY created_at DESC LIMIT 1",this::challenge,user,ts(now)).stream().findFirst().orElse(null);}
 private ChallengeView challenge(ResultSet r,int n)throws SQLException{return new ChallengeView(r.getObject("id",UUID.class),r.getString("state"),r.getTimestamp("expires_at").toInstant(),r.getObject("subject",UUID.class),r.getString("nickname"),r.getString("server"));}
 public void cancel(UUID user){db.update("UPDATE atlas_web.minecraft_challenges SET state='CANCELLED' WHERE user_id=? AND state IN ('WAITING','PROVED')",user);}
 public void create(UUID id,UUID user,String hash,Instant now,Instant expires){db.update("INSERT INTO atlas_web.minecraft_challenges(id,user_id,code_hash,created_at,expires_at,state) VALUES(?,?,?,?,?,'WAITING')",id,user,hash,ts(now),ts(expires));}
 public UUID owner(String hash){return db.query("SELECT user_id FROM atlas_web.minecraft_challenges WHERE code_hash=?",(r,n)->r.getObject(1,UUID.class),hash).stream().findFirst().orElse(null);}
 public Map<String,Object> lockedChallenge(String hash){return db.queryForMap("SELECT * FROM atlas_web.minecraft_challenges WHERE code_hash=? FOR UPDATE",hash);}
 public void prove(UUID challenge,Proof proof){db.update("UPDATE atlas_web.minecraft_challenges SET state='PROVED',subject=?,core_player_id=?,minecraft_uuid=?,nickname=?,server=? WHERE id=?",proof.subject(),proof.corePlayerId(),proof.minecraftUuid(),proof.nickname(),proof.server(),challenge);}
 public LinkView confirm(UUID user,UUID challenge,Instant now){var id=UUID.randomUUID();db.update("INSERT INTO atlas_web.minecraft_links(id,user_id,subject,core_player_id,minecraft_uuid,nickname,server,linked_at) SELECT ?,user_id,subject,core_player_id,minecraft_uuid,nickname,server,? FROM atlas_web.minecraft_challenges WHERE id=? AND user_id=?",id,ts(now),challenge,user);db.update("UPDATE atlas_web.minecraft_challenges SET state='CONFIRMED' WHERE id=?",challenge);return current(user);}
 public void revoke(UUID user,Instant now){db.update("UPDATE atlas_web.minecraft_links SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",ts(now),user);}
 public void audit(UUID user,String action,UUID subject,String request,Instant now){db.update("INSERT INTO atlas_web.identity_audit(user_id,action,subject,request_id,created_at) VALUES(?,?,?,?,?)",user,action,subject,request,ts(now));}
 public boolean serverActive(String server){return db.query("SELECT active FROM atlas_web.servers WHERE slug=? FOR SHARE",(r,n)->r.getBoolean(1),server).stream().findFirst().orElse(false);}
 public record Stored(OrderView order,String hash) {}
 private OrderView order(ResultSet r,int n)throws SQLException{return new OrderView(r.getObject("id",UUID.class),json.readValue(r.getString("snapshot"),Snapshot.class),r.getInt("total_cents"),r.getString("currency"),r.getInt("quantity"),r.getTimestamp("created_at").toInstant(),r.getTimestamp("expires_at").toInstant(),r.getString("payment_status"),r.getString("delivery_status"));}
 public Stored existing(UUID user,String key){return db.query("SELECT * FROM atlas_web.orders WHERE user_id=? AND idempotency_key=?",(r,n)->new Stored(order(r,n),r.getString("request_hash")),user,key).stream().findFirst().orElse(null);}
 public void order(UUID user,UUID link,String key,String hash,OrderView order,String request){db.update("INSERT INTO atlas_web.orders(id,user_id,link_id,product_id,idempotency_key,request_hash,snapshot,total_cents,currency,quantity,created_at,expires_at,payment_status,delivery_status) VALUES(?,?,?,?,?,?,?::jsonb,?,'BRL',1,?,?,'PENDING','WAITING')",order.id(),user,link,order.snapshot().productId(),key,hash,json.writeValueAsString(order.snapshot()),order.totalCents(),ts(order.createdAt()),ts(order.expiresAt()));db.update("INSERT INTO atlas_web.order_events(order_id,event,request_id,created_at) VALUES(?,'CREATED',?,?)",order.id(),request,ts(order.createdAt()));}
 public OrderView detail(UUID user,UUID id){return db.query("SELECT * FROM atlas_web.orders WHERE user_id=? AND id=?",this::order,user,id).stream().findFirst().orElse(null);}
 public List<OrderView> orders(UUID user,int page){return db.query("SELECT * FROM atlas_web.orders WHERE user_id=? ORDER BY created_at DESC,id LIMIT 21 OFFSET ?",this::order,user,page*20);}
}
