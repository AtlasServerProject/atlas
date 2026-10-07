package io.atlas.api.payment;
import io.atlas.api.commerce.model.CommerceModels.OrderView;
import java.time.Instant;
import java.util.List;
public interface PaymentProvider {
 record Preference(String id,String url) {}
 record Payment(String id,String reference,String collector,int cents,String currency,String status,boolean live,Instant changedAt,Instant approvedAt,int refundedCents,boolean verifiedTestCollector) {
  public Payment(String id,String reference,String collector,int cents,String currency,String status,boolean live,Instant changedAt,Instant approvedAt,int refundedCents){this(id,reference,collector,cents,currency,status,live,changedAt,approvedAt,refundedCents,false);}
  public boolean matchesMode(boolean production){return production?live&&!verifiedTestCollector:!live||verifiedTestCollector;}
 }
 Preference create(OrderView order,String attemptId);
 Payment payment(String id);
 List<Payment> search(String reference);
}
