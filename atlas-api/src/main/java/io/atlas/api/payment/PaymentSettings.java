package io.atlas.api.payment;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
@Component
public class PaymentSettings {
 public final String token,secret,collector,mode,webUrl,notificationUrl;
 public final boolean enabled;
 public PaymentSettings(@Value("${atlas.payment.enabled:false}") boolean enabled,@Value("${atlas.payment.mode:test}") String mode,@Value("${atlas.payment.access-token:}") String token,@Value("${atlas.payment.webhook-secret:}") String secret,@Value("${atlas.payment.collector-id:}") String collector,@Value("${atlas.mail.web-url:}") String webUrl,@Value("${atlas.payment.notification-url:}") String notificationUrl){
 this.enabled=enabled;this.mode=mode;this.token=token;this.secret=secret;this.collector=collector;this.webUrl=webUrl;this.notificationUrl=notificationUrl;
 if(enabled && (!(mode.equals("test")||mode.equals("production"))||token.isBlank()||secret.isBlank()||!collector.matches("[0-9]+")||!webUrl.startsWith("https://")||!notificationUrl.startsWith("https://")))throw new IllegalStateException("Payment configuration is incomplete");
 }
 public boolean live(){return mode.equals("production");}
}
