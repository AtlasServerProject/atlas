package io.atlas.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.sql.SQLException;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Import(FoundationIntegrationTest.ValidationFixture.class)
class FoundationIntegrationTest {
    @Autowired MockMvc mvc;
    @Autowired Flyway flyway;
    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) { TestDatabase.properties(registry); }

    @Test void servesMetadataThroughRuntimeRoleAndReturnsRequestId() throws Exception {
        var result = mvc.perform(get("/api/v1/system")).andExpect(status().isOk())
            .andExpect(jsonPath("$.stage").value("M6_VIP_DELIVERY"))
            .andExpect(jsonPath("$.schemaGeneration").value(8))
            .andExpect(jsonPath("$.serverTime").isNotEmpty())
            .andExpect(header().exists("X-Request-ID")).andReturn();
        assertThat(result.getResponse().getHeader("X-Request-ID")).matches("[a-f0-9-]{36}");
    }
    @Test void hidesHealthDetailsAndIncludesDatabaseInReadiness() throws Exception {
        mvc.perform(get("/actuator/health/readiness")).andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("UP")).andExpect(jsonPath("$.components").doesNotExist());
        mvc.perform(get("/actuator/health/liveness")).andExpect(status().isOk());
    }
    @Test void protectsMetricsAndFutureAdminRoutes() throws Exception {
        var result = mvc.perform(get("/actuator/metrics")).andExpect(status().isUnauthorized())
            .andExpect(jsonPath("$.code").value("AUTHENTICATION_REQUIRED"))
            .andExpect(jsonPath("$.requestId").isNotEmpty()).andReturn();
        assertThat(result.getResponse().getContentAsString()).contains(result.getResponse().getHeader("X-Request-ID"));
        mvc.perform(get("/api/v1/admin/products").with(user("player").roles("USER")))
            .andExpect(status().isForbidden()).andExpect(jsonPath("$.code").value("ACCESS_DENIED"));
        mvc.perform(get("/actuator/metrics").with(user("operator").roles("OPERATIONS"))).andExpect(status().isOk());
    }
    @Test void rejectsUntrustedCorsAndAllowsExactFrontendOrigin() throws Exception {
        mvc.perform(options("/api/v1/system").header("Origin", "http://localhost:4200")
            .header("Access-Control-Request-Method", "GET"))
            .andExpect(status().isOk()).andExpect(header().string("Access-Control-Allow-Origin", "http://localhost:4200"));
        mvc.perform(options("/api/v1/system").header("Origin", "https://untrusted.invalid")
            .header("Access-Control-Request-Method", "GET"))
            .andExpect(status().isForbidden()).andExpect(header().doesNotExist("Access-Control-Allow-Origin"));
    }
    @Test void csrfIsRequiredAndTokenEndpointIsNotCached() throws Exception {
        mvc.perform(post("/api/v1/system").contentType("application/json").content("{\"name\":\"ok\"}"))
            .andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/auth/csrf")).andExpect(status().isOk())
            .andExpect(jsonPath("$.token").isNotEmpty()).andExpect(jsonPath("$.headerName").value("X-CSRF-TOKEN"))
            .andExpect(header().string("Cache-Control", "no-store"));
        mvc.perform(post("/api/v1/system").with(csrf()).contentType("application/json").content("{\"name\":\"ok\"}"))
            .andExpect(status().isOk());
    }
    @Test void validationAndMalformedJsonUseStableErrorsWithoutInputEcho() throws Exception {
        mvc.perform(post("/api/v1/system").with(csrf()).contentType("application/json").content("{\"name\":\"\"}"))
            .andExpect(status().is(422)).andExpect(jsonPath("$.code").value("VALIDATION_ERROR"))
            .andExpect(jsonPath("$.fieldErrors[0].field").value("name"));
        mvc.perform(post("/api/v1/system").with(csrf()).contentType("application/json").content("not-json-private-input"))
            .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("MALFORMED_REQUEST"))
            .andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("private-input"))));
    }
    @Test void runtimeCannotChangeMetadataMigrationLedgerOrCoreTables() throws Exception {
        try (var connection = TestDatabase.runtime(); var statement = connection.createStatement()) {
            assertThatThrownBy(() -> statement.execute("CREATE TABLE atlas_web.forbidden (id integer)"))
                .isInstanceOf(SQLException.class);
            assertThatThrownBy(() -> statement.execute("UPDATE atlas_web.system_metadata SET schema_generation = 2"))
                .isInstanceOf(SQLException.class);
            assertThatThrownBy(() -> statement.execute("SELECT * FROM atlas_web.flyway_schema_history"))
                .isInstanceOf(SQLException.class);
            assertThatThrownBy(() -> statement.execute("SELECT * FROM public.core_sentinel"))
                .isInstanceOf(SQLException.class);
        }
        try (var connection = TestDatabase.admin(); var statement = connection.createStatement();
             var rows = statement.executeQuery("SELECT count(*) FROM public.core_sentinel")) {
            rows.next(); assertThat(rows.getInt(1)).isEqualTo(1);
        }
    }
    @Test void migrationReentryIsIdempotentAndChecksumsValidate() {
        flyway.validate();
        assertThat(flyway.migrate().migrationsExecuted).isZero();
        assertThat(flyway.info().current().getVersion().getVersion()).isEqualTo("8");
    }
    // Test-only controller exercises actual Bean Validation/advice without inventing business routes.
    @RestController
    static class ValidationFixture {
        @PostMapping("/api/v1/system") Input echo(@Valid @RequestBody Input input) { return input; }
        record Input(@NotBlank String name) { }
    }
}
