package io.atlas.api.auth.service;

import io.atlas.api.auth.repository.RateLimitRepository;
import io.atlas.api.mail.MailCipher;
import io.atlas.api.shared.error.ApiFailure;
import java.time.Clock;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class RateLimiter {
    private final RateLimitRepository repository;
    private final Clock clock;
    private final MailCipher cipher;
    private final AuthProperties properties;

    public RateLimiter(RateLimitRepository repository, Clock clock, MailCipher cipher, AuthProperties properties) {
        this.repository = repository;
        this.clock = clock;
        this.cipher = cipher;
        this.properties = properties;
    }
    public void check(String scope, String identity, int limit) {
        var now = clock.instant();
        int attempts = repository.increment(cipher.digest(scope + ":" + identity), now, now.minus(properties.rateWindow()));
        if (attempts > limit) {
            throw new ApiFailure(HttpStatus.TOO_MANY_REQUESTS, "RATE_LIMITED", "Muitas tentativas. Aguarde antes de tentar novamente.");
        }
    }
}
