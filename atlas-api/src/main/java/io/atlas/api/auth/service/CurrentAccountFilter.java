package io.atlas.api.auth.service;
import io.atlas.api.auth.model.SessionIdentity;
import io.atlas.api.auth.repository.AccountRepository;
import io.atlas.api.shared.error.ApiErrorWriter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Clock;
import java.util.List;
import org.springframework.dao.DataAccessException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
@Component
public class CurrentAccountFilter extends OncePerRequestFilter {
    private final AccountRepository accounts;private final AuthProperties properties;private final Clock clock;private final ApiErrorWriter errors;
    public CurrentAccountFilter(AccountRepository accounts,AuthProperties properties,Clock clock,ApiErrorWriter errors) {this.accounts=accounts;this.properties=properties;this.clock=clock;this.errors=errors;}
    @Override protected void doFilterInternal(HttpServletRequest request,HttpServletResponse response,FilterChain chain) throws ServletException,IOException {
        var authentication=SecurityContextHolder.getContext().getAuthentication();
        if(authentication!=null && authentication.getPrincipal() instanceof SessionIdentity identity) {
            try {
                var account=accounts.id(identity.id());
                if(account.isEmpty() || account.get().authVersion()!=identity.authVersion() || !clock.instant().isBefore(identity.authenticatedAt().plus(properties.absoluteSessionDuration()))) {
                    SecurityContextHolder.clearContext();var session=request.getSession(false);if(session!=null) session.invalidate();
                } else {
                    // Query current role on every request: revocation is effective in existing sessions.
                    SecurityContextHolder.getContext().setAuthentication(UsernamePasswordAuthenticationToken.authenticated(identity,null,List.of(new SimpleGrantedAuthority("ROLE_"+account.get().role()))));
                }
            } catch(DataAccessException exception) {errors.write(request,response,503,"DEPENDENCY_UNAVAILABLE","Serviço temporariamente indisponível.");return;}
        }
        chain.doFilter(request,response);
    }
}
