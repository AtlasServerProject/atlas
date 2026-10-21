package io.atlas.api.support;
import java.util.*;
import java.time.Instant;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
@Repository
public class SupportRepository {
 public record Ticket(UUID id,UUID orderId,UUID userId,String title,String status,Instant createdAt,Instant updatedAt){}
 public record Member(UUID id,String username,String role){}
 public List<Member> team(int page){return db.query("SELECT id,username,role FROM atlas_web.users WHERE role IN ('SUPPORT','MODERATOR','ADMIN') ORDER BY role,username,id LIMIT 21 OFFSET ?",(r,n)->new Member(r.getObject(1,UUID.class),r.getString(2),r.getString(3)),page*20);}
 public record Message(long id,String kind,String body,Instant createdAt){}
 private final JdbcTemplate db;
 public SupportRepository(JdbcTemplate db){this.db=db;}
 private Ticket row(java.sql.ResultSet r,int n)throws java.sql.SQLException{return new Ticket(r.getObject("id",UUID.class),r.getObject("order_id",UUID.class),r.getObject("user_id",UUID.class),r.getString("title"),r.getString("status"),r.getTimestamp("created_at").toInstant(),r.getTimestamp("updated_at").toInstant());}
 public Ticket find(UUID id,boolean lock){return db.query("SELECT * FROM atlas_web.support_tickets WHERE id=?"+(lock?" FOR UPDATE":""),this::row,id).stream().findFirst().orElse(null);}
 public Ticket forOrder(UUID order){return db.query("SELECT * FROM atlas_web.support_tickets WHERE order_id=?",this::row,order).stream().findFirst().orElse(null);}
 public List<Ticket> list(UUID user,int page){return db.query("SELECT * FROM atlas_web.support_tickets"+(user==null?"":" WHERE user_id=?")+" ORDER BY updated_at DESC,id LIMIT 21 OFFSET ?",this::row,user==null?new Object[]{page*20}:new Object[]{user,page*20});}
 public void create(UUID id,UUID order,UUID user,String title){db.update("INSERT INTO atlas_web.support_tickets(id,order_id,user_id,title) VALUES(?,?,?,?)",id,order,user,title);}
 public void lockOrder(UUID order){db.queryForObject("SELECT id FROM atlas_web.orders WHERE id=? FOR UPDATE",UUID.class,order);}
 public List<Message> messages(UUID ticket,int after){return db.query("SELECT id,kind,body,created_at FROM atlas_web.support_messages WHERE ticket_id=? AND id>? ORDER BY id LIMIT 101",(r,n)->new Message(r.getLong(1),r.getString(2),r.getString(3),r.getTimestamp(4).toInstant()),ticket,after);}
 public void message(UUID ticket,UUID author,String kind,String body){db.update("INSERT INTO atlas_web.support_messages(ticket_id,author,kind,body) VALUES(?,?,?,?)",ticket,author,kind,body);}
 public void status(UUID ticket,String status){db.update("UPDATE atlas_web.support_tickets SET status=?,updated_at=now() WHERE id=?",status,ticket);}
}
