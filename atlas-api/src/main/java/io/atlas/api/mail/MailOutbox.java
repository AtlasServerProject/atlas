package io.atlas.api.mail;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import tools.jackson.databind.ObjectMapper;
@Repository
public class MailOutbox {
    public record Message(String to,String subject,String text) { @Override public String toString() {return "MailMessage[redacted]";} }
    public record Pending(UUID id,String ciphertext,int attempts) { }
    private final JdbcClient jdbc; private final MailCipher cipher; private final ObjectMapper mapper;private final Clock clock;
    public MailOutbox(JdbcClient jdbc,MailCipher cipher,ObjectMapper mapper,Clock clock) {this.jdbc=jdbc;this.cipher=cipher;this.mapper=mapper;this.clock=clock;}
    public void enqueue(Message message) {
        jdbc.sql("INSERT INTO atlas_web.mail_outbox(id,encrypted_payload) VALUES(:id,:payload)")
            .param("id",UUID.randomUUID()).param("payload",cipher.encrypt(mapper.writeValueAsString(message))).update();
    }
    public Message read(String ciphertext) {return mapper.readValue(cipher.decrypt(ciphertext),Message.class);}
    public List<Pending> claim() {
        Instant now=clock.instant();
        return jdbc.sql("""
            UPDATE atlas_web.mail_outbox SET lease_until=:lease,attempts=attempts+1
            WHERE id IN (SELECT id FROM atlas_web.mail_outbox WHERE status='PENDING' AND next_attempt_at<=:now
              AND (lease_until IS NULL OR lease_until<=:now) ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 10)
            RETURNING id,encrypted_payload,attempts
            """).param("now",java.sql.Timestamp.from(now)).param("lease",java.sql.Timestamp.from(now.plusSeconds(120)))
            .query((r,i)->new Pending(r.getObject("id",UUID.class),r.getString("encrypted_payload"),r.getInt("attempts"))).list();
    }
    public void sent(Pending message) { jdbc.sql("UPDATE atlas_web.mail_outbox SET status='SENT',encrypted_payload='',delivered_at=:now,lease_until=NULL WHERE id=:id AND attempts=:attempt AND status='PENDING'")
        .param("id",message.id()).param("attempt",message.attempts()).param("now",java.sql.Timestamp.from(clock.instant())).update(); }
    public void failed(Pending message) {
        jdbc.sql("UPDATE atlas_web.mail_outbox SET status=:status,next_attempt_at=:next,lease_until=NULL WHERE id=:id AND attempts=:attempt AND status='PENDING'")
            .param("id",message.id()).param("attempt",message.attempts()).param("status",message.attempts()>=5 ? "REVIEW":"PENDING")
            .param("next",java.sql.Timestamp.from(clock.instant().plusSeconds(Math.min(3600,30L<<message.attempts())))).update();
    }
}
