package io.atlas.api.mail;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
@Service
public class MailDispatcher {
    private static final Logger LOGGER=LoggerFactory.getLogger(MailDispatcher.class);
    private final MailOutbox outbox;private final MailDelivery delivery;
    public MailDispatcher(MailOutbox outbox,MailDelivery delivery) {this.outbox=outbox;this.delivery=delivery;}
    @Scheduled(fixedDelayString="${atlas.mail.retry-delay-ms:5000}")
    public void dispatch() {
        try {
            for(var message:outbox.claim()) {
                try {delivery.deliver(message.id(),outbox.read(message.ciphertext()));outbox.sent(message);}
                catch(Exception exception) {outbox.failed(message);LOGGER.warn("Mail attempt failed; payload and exception suppressed");}
            }
        } catch(Exception exception) {LOGGER.warn("Mail queue temporarily unavailable");}
    }
}
