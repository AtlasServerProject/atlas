package io.atlas.api.delivery;
import io.atlas.api.delivery.DeliveryModels.*;
import io.atlas.api.shared.error.ApiFailure;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import java.time.*;
import java.util.*;
@Service
public class DeliveryService {
 private final DeliveryRepository repo;private final Clock clock;private final boolean enabled;private final String mode;
 public DeliveryService(DeliveryRepository repo,Clock clock,@Value("${atlas.delivery.enabled:false}") boolean enabled,@Value("${atlas.delivery.mode:production}") String mode){this.repo=repo;this.clock=clock;this.enabled=enabled;this.mode=mode;if(!Set.of("production","test").contains(mode))throw new IllegalArgumentException("Invalid delivery mode");}
 private ApiFailure fail(String code,String message){return new ApiFailure(HttpStatus.CONFLICT,code,message);}
 @Transactional public List<Delivery> claim(){
  if(!enabled)return List.of();var now=clock.instant();List<Delivery> out=new ArrayList<>();
  for(var r:repo.claim(mode,now)){var s=r.snapshot();if(!Set.of("vip-1","vip-2","vip-3").contains(s.slug())||s.durationDays()!=30||s.corePlayerId()<1||s.subject()==null){repo.review(r,"UNSUPPORTED_PLAN",now);continue;}out.add(new Delivery(r.id(),r.token(),s.server(),r.mode(),s.subject(),s.corePlayerId(),s.slug(),s.durationDays()));}return out;
 }
 private DeliveryRepository.Row owned(UUID id,UUID token){var r=repo.lock(id);if(r==null)throw fail("DELIVERY_NOT_FOUND","Entrega não encontrada.");if(!"WAITING".equals(r.state())||!"PAID".equals(r.paymentStatus())||!Objects.equals(r.token(),token)||r.leaseUntil()==null||!clock.instant().isBefore(r.leaseUntil()))throw fail("DELIVERY_LEASE_LOST","A tentativa não está mais disponível.");return r;}
 @Transactional public void ack(UUID id,Ack ack){
  var r=repo.lock(id);if(r==null)throw fail("DELIVERY_NOT_FOUND","Entrega não encontrada.");var receipt=ack.receipt();var s=r.snapshot();var b=ack.balance();var now=clock.instant();
  if(!receipt.deliveryId().equals(id)||!receipt.subject().equals(s.subject())||receipt.corePlayerId()!=s.corePlayerId()||!receipt.plan().equals(s.slug())||receipt.days()!=s.durationDays()||!receipt.server().equals(s.server())||!receipt.mode().equals(r.mode())||!b.subject().equals(s.subject())||b.corePlayerId()!=s.corePlayerId()||!b.server().equals(s.server())||receipt.activatedAt().isAfter(now.plusSeconds(60))||b.checkpoint().isBefore(receipt.activatedAt())||b.checkpoint().isAfter(now.plusSeconds(60)))throw fail("DELIVERY_RECEIPT_MISMATCH","Recibo de entrega divergente.");
  if("DELIVERED".equals(r.state())){if(!receipt.equals(r.receipt())||!Objects.equals(r.token(),ack.leaseToken()))throw fail("DELIVERY_RECEIPT_MISMATCH","Recibo de entrega divergente.");repo.mirror(b,now);return;}
  owned(id,ack.leaseToken());repo.delivered(r,ack,now);repo.mirror(b,now);
 }
 @Transactional public void failed(UUID id,Failed input){var r=owned(id,input.leaseToken());if(input.code().equals("CORE_UNAVAILABLE"))repo.fail(r,input.code(),clock.instant());else repo.review(r,input.code(),clock.instant());}
 @Transactional public void sync(List<Balance> balances){if(balances.size()>100)throw fail("INVALID_BATCH","Lote inválido.");var now=clock.instant();for(var b:balances){if(!repo.known(b)||b.checkpoint().isAfter(now.plusSeconds(60)))throw fail("INVALID_VIP_STATUS","Estado VIP divergente.");repo.mirror(b,now);}}
 @Transactional(readOnly=true) public VipView vip(UUID user){return repo.vip(user,clock.instant());}
 @Transactional(readOnly=true) public List<Attempt> attempts(int page){if(page<0||page>100000)throw fail("INVALID_PAGE","Página inválida.");return repo.attempts(page);}
 @Transactional public void retry(UUID id,UUID actor,String reason){var r=repo.lock(id);var now=clock.instant();if(r==null)throw fail("DELIVERY_NOT_FOUND","Entrega não encontrada.");if(!r.paymentStatus().equals("PAID")||r.state().equals("DELIVERED")||(r.leaseUntil()!=null&&r.leaseUntil().isAfter(now)))throw fail("DELIVERY_RETRY_BLOCKED","Entrega indisponível para reprocessamento.");repo.retry(r,actor,reason,now);}
}
