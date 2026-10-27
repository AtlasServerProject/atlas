package io.atlas.api.auth.service;
import io.atlas.api.auth.repository.SecurityEventRepository;
import java.util.UUID;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
@Service public class SecurityEvents {
 private final SecurityEventRepository repo;
 public SecurityEvents(SecurityEventRepository repo){this.repo=repo;}
 public void event(UUID user,String action,String result,String request){repo.event(user,action,result,request);}
 @Scheduled(initialDelay=3600000,fixedDelay=3600000) public void prune(){
  try{repo.prune();}catch(Exception e){LoggerFactory.getLogger(getClass()).error("Security ephemeral cleanup unavailable");}
 }
}
