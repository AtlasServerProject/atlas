package io.atlas.api.payment;
import java.util.*;
import java.time.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.http.HttpStatus;
import io.atlas.api.shared.error.ApiFailure;
import io.atlas.api.commerce.model.CommerceModels.OrderView;
@Service
public class PaymentService {
 private final PaymentRepository repo;private final PaymentProvider provider;private final PaymentSettings settings;private final TransactionTemplate tx;private final Clock clock;
 public record Checkout(UUID orderId,String state,String checkoutUrl,String mode){}
 private record Preparation(PaymentRepository.Attempt attempt,OrderView order,boolean create){}
 public PaymentService(PaymentRepository repo,PaymentProvider provider,PaymentSettings settings,PlatformTransactionManager transactions,Clock clock){this.repo=repo;this.provider=provider;this.settings=settings;this.tx=new TransactionTemplate(transactions);this.clock=clock;}
 private ApiFailure fail(HttpStatus status,String code,String message){return new ApiFailure(status,code,message);}
 public Checkout checkout(UUID user,UUID orderId){
 if(!settings.enabled)throw fail(HttpStatus.CONFLICT,"PAYMENTS_CLOSED","Pagamentos ainda indisponíveis.");
 var prepared=tx.execute(s->{var order=repo.order(orderId,user,true);if(order==null)throw fail(HttpStatus.NOT_FOUND,"ORDER_NOT_FOUND","Pedido não encontrado.");if(!order.paymentStatus().equals("PENDING")||!clock.instant().isBefore(order.expiresAt()))throw fail(HttpStatus.CONFLICT,"ORDER_NOT_PAYABLE","Este pedido não está disponível para pagamento.");var old=repo.attempt(orderId);if(old!=null){if(!old.mode().equals(settings.mode))throw fail(HttpStatus.CONFLICT,"PAYMENT_MODE_CHANGED","Pedido indisponível neste ambiente.");return new Preparation(old,order,false);}return new Preparation(repo.create(orderId,settings.mode,clock.instant()),order,true);});
 var attempt=prepared.attempt();
 if(prepared.create()){
 try{var preference=provider.create(prepared.order(),attempt.id().toString());tx.executeWithoutResult(s->repo.ready(attempt,preference,clock.instant()));}
 catch(Exception e){tx.executeWithoutResult(s->repo.unknown(attempt,clock.instant()));throw fail(HttpStatus.SERVICE_UNAVAILABLE,"PAYMENT_CREATION_UNCERTAIN","Não foi possível confirmar o início do pagamento. Consulte este pedido antes de tentar novamente.");}
 }
 var current=repo.attempt(orderId);return new Checkout(orderId,current.state(),current.url(),current.mode());
 }
 public void webhook(String signature,String request,String id,String type){
 if(!settings.enabled)throw fail(HttpStatus.SERVICE_UNAVAILABLE,"PAYMENTS_CLOSED","Pagamentos indisponíveis.");
 if(!WebhookSignature.valid(signature,request,id,settings.secret))throw fail(HttpStatus.UNAUTHORIZED,"INVALID_WEBHOOK","Notificação inválida.");
 if(!"payment".equals(type))throw fail(HttpStatus.BAD_REQUEST,"INVALID_WEBHOOK","Notificação inválida.");
 String hash;try{hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest((id+":"+request+":"+signature).getBytes(StandardCharsets.UTF_8)));}catch(Exception e){throw new IllegalStateException();}
 tx.executeWithoutResult(s->{if(repo.event(hash,id))repo.enqueue(id);});
 }
 public void reconcile(){
 if(!settings.enabled)return;
 for(UUID order:repo.dueOrders())try{for(var payment:provider.search(order.toString())){if(!payment.id().matches("[0-9]{1,30}"))throw new IllegalStateException();tx.executeWithoutResult(s->repo.enqueue(payment.id()));}tx.executeWithoutResult(s->repo.scanned(order));}catch(Exception ignored){/* Persisted attempts remain eligible; no remote body/secret logging. */}
 }
 public void dispatch(){
 if(!settings.enabled)return;
 for(var job:repo.claim())try{var payment=provider.payment(job.id());tx.executeWithoutResult(s->{if(repo.owns(job)){apply(payment,job.id());repo.finish(job);}});}catch(Exception e){repo.retry(job);}
 }
 // The provider fetch occurs before this short transaction. Serialize all transitions on the order.
 private void apply(PaymentProvider.Payment payment,String requestedId){
 var now=clock.instant();UUID orderId;try{orderId=UUID.fromString(payment.reference());}catch(Exception e){repo.review(requestedId,"UNKNOWN_REFERENCE",now);return;}
 var order=repo.order(orderId,null,true);var attempt=repo.attempt(orderId);
 if(order==null||attempt==null||!payment.id().equals(requestedId)||!payment.collector().equals(settings.collector)||payment.live()!=settings.live()||!attempt.mode().equals(settings.mode)||payment.cents()!=order.totalCents()||!payment.currency().equals(order.currency())){repo.review(requestedId,"PAYMENT_MISMATCH",now);return;}
 var bound=repo.observedOrder(payment.id());if(bound!=null&&!bound.equals(orderId)){repo.review(payment.id(),"PAYMENT_ALREADY_BOUND",now);return;}
 var observed=repo.observedAt(payment.id());if(observed!=null&&payment.changedAt().isBefore(observed))return;
 String prior=repo.previousStatus(payment.id());
 if(Set.of("refunded","charged_back").contains(prior==null?"":prior)&&!Set.of("refunded","charged_back").contains(payment.status()))return;
 boolean duplicate=repo.anotherPaid(orderId,payment.id());
 if("approved".equals(prior)&&Set.of("pending","in_process","authorized","rejected","cancelled").contains(payment.status()))return;
 repo.observe(payment,orderId,now);
 if(duplicate&&payment.status().equals("approved")){repo.review(payment.id(),"DUPLICATE_PAYMENT",now);return;}
 if(payment.refundedCents()>0||payment.status().equals("refunded")||payment.status().equals("charged_back")){
 if(duplicate){repo.review(payment.id(),"SECOND_PAYMENT_REFUND",now);return;}
 String state=payment.status().equals("charged_back")?"CHARGEBACK":payment.status().equals("refunded")||payment.refundedCents()>=order.totalCents()?"REFUNDED":order.paymentStatus();
 repo.status(orderId,state,"REVIEW","PAYMENT_COMPENSATION_REVIEW",now);repo.hold(orderId);repo.review(payment.id(),"COMPENSATION_REQUIRED",now);return;
 }
 if(payment.status().equals("approved")){
 if(Set.of("REFUNDED","CHARGEBACK").contains(order.paymentStatus())){repo.review(payment.id(),"TERMINAL_ORDER",now);return;}
 if(payment.approvedAt()==null||payment.approvedAt().isBefore(order.createdAt())||!payment.approvedAt().isBefore(order.expiresAt())||payment.approvedAt().isAfter(now.plusSeconds(60))){repo.review(payment.id(),"LATE_OR_INVALID_APPROVAL",now);if(!order.paymentStatus().equals("PAID"))repo.status(orderId,"PAID","REVIEW","LATE_PAYMENT_REVIEW",now);return;}
 if(!order.paymentStatus().equals("PAID")){repo.status(orderId,"PAID","PROCESSING","PAYMENT_CONFIRMED",now);repo.outbox(orderId,now);}return;
 }
 // A failed attempt does not cancel a preference: another PIX/card attempt can still succeed.
 if(!Set.of("pending","in_process","authorized","rejected","cancelled").contains(payment.status()))repo.review(payment.id(),"UNKNOWN_PROVIDER_STATUS",now);
 }
}
