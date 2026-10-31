package io.atlas.api.shared.web;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestIdFilter extends OncePerRequestFilter {
    public static final String ATTRIBUTE = "atlas.requestId";
    private static final Logger LOGGER = LoggerFactory.getLogger(RequestIdFilter.class);

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        // Generate locally; never echo untrusted headers, query strings, body or credentials in logs.
        String requestId = UUID.randomUUID().toString();
        request.setAttribute(ATTRIBUTE, requestId);
        response.setHeader("X-Request-ID", requestId);
        MDC.put("requestId", requestId);
        long startedAt = System.nanoTime();
        try {
            chain.doFilter(request, response);
        } finally {
            LOGGER.atInfo().addKeyValue("event", "http_request")
                .addKeyValue("method", request.getMethod())
                .addKeyValue("status", response.getStatus())
                .addKeyValue("durationMs", (System.nanoTime() - startedAt) / 1_000_000).log("HTTP request completed");
            MDC.remove("requestId");
        }
    }
}
