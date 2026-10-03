package io.atlas.api.payment;
import io.atlas.api.commerce.model.CommerceModels.OrderView;
import java.time.Instant;
import java.util.List;
public interface PaymentProvider {
 record Preference(String id,String url) {}
 record Payment(String id,String reference,String collector,int cents,String currency,String status,boolean live,Instant changedAt,Instant approvedAt,int refundedCents) {}
 Preference create(OrderView order,String attemptId);
 Payment payment(String id);
 List<Payment> search(String reference);
}
