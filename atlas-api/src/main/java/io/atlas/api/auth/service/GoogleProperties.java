package io.atlas.api.auth.service;
import org.springframework.boot.context.properties.ConfigurationProperties;
@ConfigurationProperties("atlas.google")
public record GoogleProperties(boolean enabled,String clientId){
 public GoogleProperties {clientId=clientId==null?"":clientId.trim();if(enabled&&!clientId.matches("[A-Za-z0-9-]+\\.apps\\.googleusercontent\\.com"))throw new IllegalArgumentException("Configure a valid Google web client ID");}
}
