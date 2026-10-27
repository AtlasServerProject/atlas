package io.atlas.api.auth.service;
import io.atlas.api.auth.model.SessionIdentity;import io.atlas.api.shared.error.ApiErrorWriter;
import java.time.*;import java.util.*;import java.util.concurrent.atomic.AtomicBoolean;
import org.junit.jupiter.api.*;import org.springframework.mock.web.*;import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;import org.springframework.security.core.context.SecurityContextHolder;
import static org.assertj.core.api.Assertions.*;import static org.mockito.Mockito.*;
class SensitiveOperationFilterTest {
 final Clock clock=Clock.fixed(Instant.parse("2026-10-25T12:00:00Z"),ZoneOffset.UTC);
 @AfterEach void clear(){SecurityContextHolder.clearContext();}
 @Test void staleProofBlocksMutationBeforeControllerAndFreshProofAllowsIt()throws Exception{
  var errors=mock(ApiErrorWriter.class);var filter=new SensitiveOperationFilter(clock,errors);var request=new MockHttpServletRequest("PATCH","/api/v1/admin/products/1/price");var response=new MockHttpServletResponse();var called=new AtomicBoolean();
  var stale=new SessionIdentity(UUID.randomUUID(),1,clock.instant().minusSeconds(600),clock.instant(),clock.instant().minusSeconds(301));SecurityContextHolder.getContext().setAuthentication(UsernamePasswordAuthenticationToken.authenticated(stale,null,List.of()));
  filter.doFilter(request,response,(r,s)->called.set(true));assertThat(called).isFalse();verify(errors).write(eq(request),eq(response),eq(403),eq("REAUTHENTICATION_REQUIRED"),anyString());
  var fresh=new SessionIdentity(stale.id(),1,stale.authenticatedAt(),clock.instant(),clock.instant());SecurityContextHolder.getContext().setAuthentication(UsernamePasswordAuthenticationToken.authenticated(fresh,null,List.of()));filter.doFilter(new MockHttpServletRequest("PATCH",request.getRequestURI()),new MockHttpServletResponse(),(r,s)->called.set(true));assertThat(called).isTrue();
 }
}
