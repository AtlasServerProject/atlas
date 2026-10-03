package io.atlas.api.mail;
import java.nio.file.Files;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.UUID;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.core.env.Environment;
import org.springframework.core.env.Profiles;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Component;
@Component
public class MailDelivery {
    private final MailProperties properties;private final ObjectProvider<JavaMailSender> smtp;
    public MailDelivery(MailProperties properties,ObjectProvider<JavaMailSender> smtp,Environment environment) {
        this.properties=properties;this.smtp=smtp;
        if("local".equals(properties.mode()) && (!environment.acceptsProfiles(Profiles.of("local","test")) || environment.acceptsProfiles(Profiles.of("staging","prod")))) throw new IllegalArgumentException("Local mail delivery is permitted only in local/test profiles");
        if("smtp".equals(properties.mode()) && smtp.getIfAvailable()==null) throw new IllegalArgumentException("SMTP must be configured before starting staging/production");
    }
    public void deliver(UUID id,MailOutbox.Message message) throws Exception {
        if("local".equals(properties.mode())) {
            var directory=properties.localDirectory();Files.createDirectories(directory);Files.setPosixFilePermissions(directory,PosixFilePermissions.fromString("rwx------"));
            var target=directory.resolve(id+".eml");
            if(!Files.exists(target)) Files.createFile(target,PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rw-------")));
            Files.writeString(target,"To: "+message.to()+"\nSubject: "+message.subject()+"\n\n"+message.text());
        } else {
            var sender=smtp.getObject();var mail=sender.createMimeMessage();
            var helper=new MimeMessageHelper(mail,true,"UTF-8");
            helper.setFrom(properties.from(),"Atlas Cobblemon");helper.setTo(message.to());helper.setSubject(message.subject());
            helper.setText(message.text(),MailTemplate.html(message));sender.send(mail);
        }
    }
}
