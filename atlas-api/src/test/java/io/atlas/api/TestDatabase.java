package io.atlas.api;

import java.sql.Connection;
import java.sql.DriverManager;
import java.util.UUID;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

final class TestDatabase {
    private static final PostgreSQLContainer CONTAINER;
    private static final String MAIL_KEY = System.getenv().getOrDefault("ATLAS_MAIL_ENCRYPTION_KEY", randomMailKey());
    static final String URL;
    static final String RUNTIME_PASSWORD;
    static final String MIGRATION_PASSWORD;
    static final String ADMIN_PASSWORD;
    static {
        String supplied = System.getenv("ATLAS_TEST_DB_URL");
        if (supplied != null && !supplied.isBlank()) {
            CONTAINER = null;
            URL = supplied;
            RUNTIME_PASSWORD = required("ATLAS_DB_PASSWORD");
            MIGRATION_PASSWORD = required("ATLAS_MIGRATION_PASSWORD");
            ADMIN_PASSWORD = required("ATLAS_TEST_ADMIN_PASSWORD");
        } else {
            // Only disposable database credentials; never application accounts or payment secrets.
            RUNTIME_PASSWORD = UUID.randomUUID().toString();
            MIGRATION_PASSWORD = UUID.randomUUID().toString();
            ADMIN_PASSWORD = UUID.randomUUID().toString();
            CONTAINER = new PostgreSQLContainer("postgres:18.6")
                .withDatabaseName("atlas_api_test").withUsername("atlas_api_bootstrap").withPassword(ADMIN_PASSWORD)
                .withEnv("ATLAS_DB_PASSWORD", RUNTIME_PASSWORD)
                .withEnv("ATLAS_MIGRATION_PASSWORD", MIGRATION_PASSWORD)
                .withCopyFileToContainer(MountableFile.forHostPath("infra/postgres/provision.sql"), "/atlas-provision.sql")
                .withCopyFileToContainer(MountableFile.forHostPath("infra/postgres/init.sh", 0755), "/docker-entrypoint-initdb.d/10-atlas.sh");
            CONTAINER.start();
            URL = CONTAINER.getJdbcUrl();
            try (Connection connection = admin(); var statement = connection.createStatement()) {
                statement.execute("CREATE TABLE public.core_sentinel (id INTEGER PRIMARY KEY)");
                statement.execute("INSERT INTO public.core_sentinel VALUES (1)");
            } catch (Exception exception) {
                throw new IllegalStateException("Unable to initialize isolated database fixture", exception);
            }
        }
    }
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("atlas.mail.encryption-key", () -> MAIL_KEY);
        registry.add("atlas.mail.retry-delay-ms", () -> "3600000");
        registry.add("spring.datasource.url", () -> URL);
        registry.add("spring.datasource.username", () -> "atlas_api_runtime");
        registry.add("spring.datasource.password", () -> RUNTIME_PASSWORD);
        registry.add("spring.flyway.url", () -> URL);
        registry.add("spring.flyway.user", () -> "atlas_api_migrator");
        registry.add("spring.flyway.password", () -> MIGRATION_PASSWORD);
    }
    static Connection admin() throws Exception { return DriverManager.getConnection(URL, "atlas_api_bootstrap", ADMIN_PASSWORD); }
    static Connection runtime() throws Exception { return DriverManager.getConnection(URL, "atlas_api_runtime", RUNTIME_PASSWORD); }
    private static String required(String name) {
        String value = System.getenv(name);
        if (value == null || value.isBlank()) throw new IllegalStateException("Missing isolated test configuration " + name);
        return value;
    }
    private static String randomMailKey() { byte[] key = new byte[32]; new java.security.SecureRandom().nextBytes(key); return java.util.Base64.getEncoder().encodeToString(key); }
    private TestDatabase() { }
}
