package io.atlas.api.auth.service;
import io.atlas.api.auth.model.SessionIdentity;
import io.atlas.api.shared.error.ApiErrorWriter;
import jakarta.servlet.*;import jakarta.servlet.http.*;
import java.io.IOException;import java.time.Clock;import java.util.Set;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
@Component public final class SensitiveOperationFilter extends OncePerRequestFilter {
 private final Clock clock;private final ApiErrorWriter errors;
 public SensitiveOperationFilter(Clock clock,ApiErrorWriter errors){this.clock=clock;this.errors=errors;}
 @Override protected void doFilterInternal(HttpServletRequest request,HttpServletResponse response,FilterChain chain)throws ServletException,IOException{
  String path=request.getRequestURI();boolean sensitive=Set.of("POST","PATCH","DELETE").contains(request.getMethod())&&(path.startsWith("/api/v1/admin/products")||path.startsWith("/api/v1/admin/promotions")||path.startsWith("/api/v1/admin/deliveries"));
  var auth=SecurityContextHolder.getContext().getAuthentication();
  if(sensitive&&auth!=null&&auth.getPrincipal() instanceof SessionIdentity p&&(p.reauthenticatedAt()==null||!clock.instant().isBefore(p.reauthenticatedAt().plusSeconds(300)))){errors.write(request,response,403,"REAUTHENTICATION_REQUIRED","Confirme novamente sua identidade para concluir esta ação.");return;}
  chain.doFilter(request,response);
 }
}
