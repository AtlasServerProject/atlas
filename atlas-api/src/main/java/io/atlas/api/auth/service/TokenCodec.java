package io.atlas.api.auth.service;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HexFormat;
import org.springframework.stereotype.Component;
@Component
public class TokenCodec {
    private final SecureRandom random=new SecureRandom();
    public String random() { byte[] bytes=new byte[32];random.nextBytes(bytes);return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes); }
    public String sixDigits() { return String.format(java.util.Locale.ROOT,"%06d",random.nextInt(1_000_000)); }
    public String hash(String token) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(token.getBytes(StandardCharsets.UTF_8))); }
        catch(Exception exception) { throw new IllegalStateException("Token digest unavailable"); }
    }
}
