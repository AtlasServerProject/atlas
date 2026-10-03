package io.atlas.api.config;

import io.atlas.api.shared.error.ApiErrorWriter;
import io.atlas.api.auth.service.CurrentAccountFilter;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.security.web.context.SecurityContextHolderFilter;
import org.springframework.security.web.csrf.CsrfTokenRepository;
import org.springframework.security.web.csrf.HttpSessionCsrfTokenRepository;
import java.util.List;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

@Configuration
@EnableMethodSecurity
@EnableConfigurationProperties(CorsProperties.class)
public class SecurityConfiguration {
    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http, ApiErrorWriter errors, CurrentAccountFilter accountFilter, SecurityContextRepository contexts, CsrfTokenRepository tokens) throws Exception {
        // Unimplemented commerce routes stay closed; ADMIN checks are enforced by the backend.
        return http
            .cors(cors -> {})
            .securityContext(context -> context.securityContextRepository(contexts))
            .csrf(csrf -> csrf.csrfTokenRepository(tokens).ignoringRequestMatchers("/internal/v1/minecraft/proofs", "/api/v1/webhooks/mercadopago"))
            .addFilterAfter(accountFilter, SecurityContextHolderFilter.class)
            .logout(logout -> logout.disable())
            .requestCache(cache -> cache.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health", "/actuator/health/liveness", "/actuator/health/readiness",
                    "/api/v1/system", "/api/v1/auth/csrf", "/api/v1/auth/register", "/api/v1/auth/login",
                    "/api/v1/auth/logout", "/api/v1/auth/verify-email", "/api/v1/auth/resend-verification",
                    "/api/v1/auth/forgot-password", "/api/v1/auth/reset-password").permitAll()
                .requestMatchers(org.springframework.http.HttpMethod.GET, "/api/v1/catalog").permitAll()
                .requestMatchers("/internal/v1/minecraft/proofs", "/api/v1/webhooks/mercadopago").permitAll()
                .requestMatchers("/api/v1/users/me", "/api/v1/users/me/**", "/api/v1/orders", "/api/v1/orders/**").authenticated()
                .requestMatchers("/api/v1/admin/**").hasRole("ADMIN")
                .requestMatchers("/actuator/**").hasRole("OPERATIONS")
                .anyRequest().denyAll())
            .exceptionHandling(handler -> handler
                .authenticationEntryPoint((req, res, ex) -> errors.write(req, res, 401, "AUTHENTICATION_REQUIRED", "Autenticação necessária."))
                .accessDeniedHandler((req, res, ex) -> errors.write(req, res, 403, "ACCESS_DENIED", "Acesso não autorizado.")))
            .build();
    }
    @Bean SecurityContextRepository securityContextRepository() { return new HttpSessionSecurityContextRepository(); }
    @Bean CsrfTokenRepository csrfTokenRepository() { return new HttpSessionCsrfTokenRepository(); }
    @Bean FilterRegistrationBean<CurrentAccountFilter> accountFilterRegistration(CurrentAccountFilter filter) {
        var registration = new FilterRegistrationBean<>(filter); registration.setEnabled(false); return registration;
    }
    @Bean
    UserDetailsService noDevelopmentAccounts() {
        // Prevent Boot from generating a default user/password and printing it to logs.
        return username -> { throw new UsernameNotFoundException("JSON authentication is handled by AuthService"); };
    }
    @Bean
    CorsConfigurationSource corsConfigurationSource(CorsProperties properties) {
        CorsConfiguration cors = new CorsConfiguration();
        cors.setAllowedOrigins(properties.allowedOrigins());
        cors.setAllowedMethods(List.of("GET", "POST", "PATCH", "DELETE", "OPTIONS"));
        cors.setAllowedHeaders(List.of("Content-Type", "X-CSRF-TOKEN", "Idempotency-Key"));
        cors.setExposedHeaders(List.of("X-Request-ID"));
        cors.setAllowCredentials(true);
        cors.setMaxAge(600L);
        var source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", cors);
        return source;
    }
}
