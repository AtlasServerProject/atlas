package io.atlas.api.auth.repository;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
@Repository public class SecurityEventRepository {
 private final JdbcClient jdbc;
 public SecurityEventRepository(JdbcClient jdbc){this.jdbc=jdbc;}
 public void event(UUID user,String action,String result,String request){
  jdbc.sql("INSERT INTO atlas_web.security_events(user_id,action,result,request_id) VALUES(:user,:action,:result,:request)")
   .param("user",user).param("action",action).param("result",result).param("request",request==null?"unknown":request).update();
 }
 public void prune(){jdbc.sql("SELECT atlas_web.prune_security_ephemera()").query(Object.class).optional();}
}
