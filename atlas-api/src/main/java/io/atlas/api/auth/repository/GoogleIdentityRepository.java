package io.atlas.api.auth.repository;
import java.util.*;import org.springframework.jdbc.core.simple.JdbcClient;import org.springframework.stereotype.Repository;
@Repository public class GoogleIdentityRepository {
 private final JdbcClient db;public GoogleIdentityRepository(JdbcClient db){this.db=db;}
 public Optional<UUID> owner(String sub){return db.sql("SELECT user_id FROM atlas_web.external_identities WHERE provider='GOOGLE' AND subject=:subject").param("subject",sub).query(UUID.class).optional();}
 public boolean linked(UUID user){return db.sql("SELECT count(*) FROM atlas_web.external_identities WHERE provider='GOOGLE' AND user_id=:id").param("id",user).query(Integer.class).single()>0;}
 public boolean link(UUID user,String subject){return db.sql("INSERT INTO atlas_web.external_identities(provider,subject,user_id) VALUES('GOOGLE',:subject,:id) ON CONFLICT DO NOTHING").param("subject",subject).param("id",user).update()==1;}
}
