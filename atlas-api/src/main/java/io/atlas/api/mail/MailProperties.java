package io.atlas.api.mail;
import java.net.URI;
import java.nio.file.Path;
import org.springframework.boot.context.properties.ConfigurationProperties;
@ConfigurationProperties("atlas.mail")
public record MailProperties(String mode,String encryptionKey,String from,String webUrl,Path localDirectory) {
    @Override public String toString() { return "MailProperties[mode="+mode+"]"; }
    public MailProperties {
        if(!"local".equals(mode) && !"smtp".equals(mode)) throw new IllegalArgumentException("Mail mode must be local or smtp");
        URI url=URI.create(webUrl);
        if(url.getHost()==null || (!"http".equals(url.getScheme()) && !"https".equals(url.getScheme())) || url.getUserInfo()!=null || url.getQuery()!=null || url.getFragment()!=null) throw new IllegalArgumentException("A valid public frontend URL is required");
        if("smtp".equals(mode) && !"https".equals(url.getScheme())) throw new IllegalArgumentException("SMTP links require a public HTTPS frontend URL");
        if("smtp".equals(mode) && (from==null || !from.matches("[^\\s@]+@[^\\s@]+\\.[^\\s@]+"))) throw new IllegalArgumentException("A mail sender is required for SMTP");
    }
}
