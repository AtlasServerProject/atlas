package io.atlas.api.auth.service;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
@ConfigurationProperties("atlas.auth")
public record AuthProperties(Duration verificationDuration, Duration resetDuration, Duration absoluteSessionDuration,
                             Duration rateWindow, int ipAttempts, int accountAttempts) {
    public AuthProperties {
        positive(verificationDuration); positive(resetDuration); positive(absoluteSessionDuration); positive(rateWindow);
        if (ipAttempts < 1 || accountAttempts < 1) throw new IllegalArgumentException("Positive auth attempt limits required");
    }
    private static void positive(Duration value) {
        if (value == null || value.isNegative() || value.isZero()) throw new IllegalArgumentException("Positive auth durations required");
    }
}
