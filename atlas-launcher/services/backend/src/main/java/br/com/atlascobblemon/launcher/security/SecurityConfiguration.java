package br.com.atlascobblemon.launcher.security;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
@Configuration
public class SecurityConfiguration {
 @Bean SecurityFilterChain launcherSecurity(HttpSecurity http) throws Exception {
  return http.authorizeHttpRequests(auth -> auth
   .requestMatchers(HttpMethod.GET,"/actuator/health","/api/launcher/status").permitAll()
   .anyRequest().denyAll())
   .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
   .exceptionHandling(errors -> errors.authenticationEntryPoint(new HttpStatusEntryPoint(HttpStatus.FORBIDDEN)))
   .build();
 }
 // No default administrative account or generated password. Authentication comes in phase 4.
 @Bean UserDetailsService noLocalAccounts() { return name -> { throw new UsernameNotFoundException("Unavailable"); }; }
}
