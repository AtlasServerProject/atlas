package io.atlas.api.auth.service;

import io.atlas.api.shared.error.ApiFailure;
import jakarta.servlet.http.HttpServletRequest;
import java.net.InetAddress;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.util.HexFormat;
import java.util.Set;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

/** Only a loopback gateway holding the private key can assert the originating IP. */
@Component
public final class ClientIpResolver {
    private static final Set<String> LOOPBACK = Set.of("127.0.0.1", "::1", "0:0:0:0:0:0:0:1");
    private final byte[] key;
    private final boolean required;
    private final Clock clock;
    public ClientIpResolver(@Value("${atlas.proxy.hmac-key:}") String key,
                            @Value("${atlas.proxy.required:false}") boolean required, Clock clock) {
        this.key = key.getBytes(StandardCharsets.UTF_8); this.required = required; this.clock = clock;
        if (required && this.key.length < 43) throw new IllegalStateException("Private gateway identity key required");
    }
    public String resolve(HttpServletRequest request) {
        String ip = request.getHeader("X-Atlas-Verified-IP"), timestamp = request.getHeader("X-Atlas-IP-Time"), signature = request.getHeader("X-Atlas-IP-Signature");
        if (LOOPBACK.contains(request.getRemoteAddr()) && key.length >= 43 && ip != null && ip.length() <= 45
                && ip.matches("[0-9a-fA-F:.]+") && timestamp != null && timestamp.matches("[0-9]{10,12}")
                && signature != null && signature.matches("[0-9a-f]{64}")) {
            try {
                long time = Long.parseLong(timestamp);
                if (time >= clock.instant().getEpochSecond() - 60 && time <= clock.instant().getEpochSecond() + 10) {
                    Mac mac = Mac.getInstance("HmacSHA256"); mac.init(new SecretKeySpec(key,"HmacSHA256"));
                    String payload = request.getMethod() + "\n" + request.getRequestURI() + "\n" + timestamp + "\n" + ip;
                    if (MessageDigest.isEqual(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)), HexFormat.of().parseHex(signature))) {
                        return InetAddress.getByName(ip).getHostAddress();
                    }
                }
            } catch (Exception ignored) { /* Untrusted/malformed headers are never used as a bucket. */ }
        }
        if (required) throw new ApiFailure(HttpStatus.SERVICE_UNAVAILABLE, "GATEWAY_IDENTITY_UNAVAILABLE", "Acesso temporariamente indisponível. Tente novamente.");
        return request.getRemoteAddr(); // Direct isolated/local servers only; enabled gateway deployments fail closed.
    }
}
