package io.atlas.api.payment;
import org.springframework.stereotype.Component;
import org.springframework.scheduling.annotation.Scheduled;
import org.slf4j.LoggerFactory;
@Component
public class PaymentDispatcher {
 private final PaymentService service;
 public PaymentDispatcher(PaymentService service){this.service=service;}
 @Scheduled(fixedDelayString="${atlas.payment.dispatch-delay-ms:10000}") public void dispatch(){try{service.dispatch();}catch(Exception e){LoggerFactory.getLogger(getClass()).warn("Payment queue temporarily unavailable");}}
 @Scheduled(fixedDelayString="${atlas.payment.reconcile-delay-ms:60000}") public void reconcile(){try{service.reconcile();}catch(Exception e){LoggerFactory.getLogger(getClass()).warn("Payment reconciliation temporarily unavailable");}}
}
