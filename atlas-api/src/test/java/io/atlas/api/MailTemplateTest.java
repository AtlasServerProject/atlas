package io.atlas.api;
import io.atlas.api.mail.MailTemplate;
import io.atlas.api.mail.MailOutbox;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;
class MailTemplateTest {
 @Test void confirmationEscapesNicknameAndPreservesFragment(){String link="https://example.invalid/verificar-email#token=test-token";String html=MailTemplate.html(new MailOutbox.Message("test@example.invalid","Confirmation","Olá, <script>alert('x')</script>.\n\n"+link));assertThat(html).contains("Confirmar meu email","&lt;script&gt;","href=\""+link+"\"").doesNotContain("<script>","src=","100%%");}
 @Test void nicknameCannotReplaceTheRealConfirmationLink(){var html=MailTemplate.html(new MailOutbox.Message("test@example.invalid","Confirmation","Olá, https://evil.invalid/verificar-email#token=bad.\n\nhttps://example.invalid/verificar-email#token=real"));assertThat(html).contains("href=\"https://example.invalid/verificar-email#token=real\"").doesNotContain("href=\"https://evil.invalid");}
 @Test void recoveryUsesItsOwnActionAndOtherMessagesHaveNoFabricatedLink(){assertThat(MailTemplate.html(new MailOutbox.Message("test@example.invalid","Reset","Olá.\nhttps://example.invalid/redefinir-senha#token=test-token"))).contains("Redefinir minha senha").doesNotContain("Confirmar meu email");assertThat(MailTemplate.html(new MailOutbox.Message("test@example.invalid","Other","<private>"))).contains("&lt;private&gt;").doesNotContain("href=");}
}
