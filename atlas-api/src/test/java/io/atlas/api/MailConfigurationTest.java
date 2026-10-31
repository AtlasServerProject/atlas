package io.atlas.api;
import io.atlas.api.mail.MailCipher;
import io.atlas.api.mail.MailProperties;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.util.Base64;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;
class MailConfigurationTest {
    private MailProperties properties(String mode,String url,String key) { return new MailProperties(mode,key,"atlas@example.invalid",url,Path.of(".runtime/mail")); }
    private String key() {byte[] key=new byte[32];new SecureRandom().nextBytes(key);return Base64.getEncoder().encodeToString(key);}
    @Test void smtpRequiresHttpsAndLocalAllowsHttp() {
        assertThatThrownBy(()->properties("smtp","http://example.invalid",key())).isInstanceOf(IllegalArgumentException.class);
        assertThat(properties("local","http://localhost:4200",key()).webUrl()).isEqualTo("http://localhost:4200");
        assertThatThrownBy(()->properties("local","https://example.invalid?token=secret",key())).isInstanceOf(IllegalArgumentException.class);
    }
    @Test void authenticatedEncryptionRejectsTamperingAndWrongKey() {
        var cipher=new MailCipher(properties("local","http://localhost:4200",key()));
        var encrypted=cipher.encrypt("Disposable confidential payload");assertThat(cipher.decrypt(encrypted)).isEqualTo("Disposable confidential payload");
        assertThatThrownBy(()->new MailCipher(properties("local","http://localhost:4200",key())).decrypt(encrypted)).isInstanceOf(IllegalStateException.class);
        byte[] bytes=Base64.getDecoder().decode(encrypted);bytes[bytes.length-1]^=1;
        assertThatThrownBy(()->cipher.decrypt(Base64.getEncoder().encodeToString(bytes))).isInstanceOf(IllegalStateException.class);
    }
    @Test void malformedKeyAndUnsupportedModeFailClosed() {
        assertThatThrownBy(()->new MailCipher(properties("local","http://localhost:4200","invalid"))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(()->properties("disabled","http://localhost:4200",key())).isInstanceOf(IllegalArgumentException.class);
    }
}
