package io.atlas.api;
import io.atlas.api.mail.*;
import jakarta.mail.*;
import jakarta.mail.internet.*;
import java.nio.file.Path;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.support.StaticListableBeanFactory;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.mail.javamail.JavaMailSenderImpl;
import static org.assertj.core.api.Assertions.*;
class MailMimeTest {
 @Test void smtpContainsBothPlainAndHtmlWithoutSending()throws Exception{
  class Capture extends JavaMailSenderImpl { MimeMessage captured; @Override public void send(MimeMessage message){captured=message;} }
  var sender=new Capture();var beans=new StaticListableBeanFactory(Map.of("smtp",sender));
  var props=new MailProperties("smtp",Base64.getEncoder().encodeToString(new byte[32]),"atlas@example.invalid","https://example.invalid",Path.of(".runtime/mail"));
  var delivery=new MailDelivery(props,beans.getBeanProvider(org.springframework.mail.javamail.JavaMailSender.class),new StandardEnvironment());
  String link="https://example.invalid/verificar-email#token=test-token";
  delivery.deliver(UUID.randomUUID(),new MailOutbox.Message("test@example.invalid","Confirme seu email — Atlas Cobblemon","Olá.\n"+link));
  sender.captured.saveChanges();assertThat(((InternetAddress)sender.captured.getFrom()[0]).getPersonal()).isEqualTo("Atlas Cobblemon");
  var types=new ArrayList<String>();var contents=new ArrayList<String>();collect(sender.captured,types,contents);
  assertThat(types).anyMatch(t->t.startsWith("text/plain")).anyMatch(t->t.startsWith("text/html"));assertThat(contents).allMatch(c->c.contains(link));
 }
 private void collect(Part part,List<String> types,List<String> contents)throws Exception{if(part.getContent() instanceof Multipart parts){for(int i=0;i<parts.getCount();i++)collect(parts.getBodyPart(i),types,contents);}else{types.add(part.getContentType());contents.add(part.getContent().toString());}}
}
