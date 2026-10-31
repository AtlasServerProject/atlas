package io.atlas.api.config;
import io.atlas.api.auth.service.AuthProperties;
import io.atlas.api.mail.MailProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
@Configuration
@EnableScheduling
@EnableConfigurationProperties({AuthProperties.class,MailProperties.class})
public class AuthConfiguration {
    @Bean PasswordEncoder passwordEncoder() {return new BCryptPasswordEncoder(12);}
}
