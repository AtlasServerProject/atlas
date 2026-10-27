package io.atlas.api.config;
import io.atlas.api.auth.service.*;import java.time.*;
import org.springframework.boot.context.properties.EnableConfigurationProperties;import org.springframework.context.annotation.*;import org.springframework.http.client.SimpleClientHttpRequestFactory;import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;import org.springframework.web.client.RestTemplate;
@Configuration @EnableConfigurationProperties(GoogleProperties.class)
public class GoogleConfiguration {
 @Bean GoogleTokenVerifier googleTokenVerifier(GoogleProperties p,Clock clock){
  if(!p.enabled())return new GoogleTokenVerifier(p,token->{throw new org.springframework.security.oauth2.jwt.JwtException("Google disabled");},clock);
  var factory=new SimpleClientHttpRequestFactory();factory.setConnectTimeout(Duration.ofSeconds(3));factory.setReadTimeout(Duration.ofSeconds(5));
  var decoder=NimbusJwtDecoder.withJwkSetUri("https://www.googleapis.com/oauth2/v3/certs").restOperations(new RestTemplate(factory)).build();
  return new GoogleTokenVerifier(p,decoder,clock);
 }
}
