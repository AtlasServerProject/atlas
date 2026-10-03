package io.atlas.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import io.atlas.api.config.CorsProperties;
import java.util.List;
import org.junit.jupiter.api.Test;

class CorsPropertiesTest {
    @Test void rejectsWildcardAndNonOrigins() {
        for (String origin : List.of("*", "https://*.example.com", "https://example.com/path", "https://name@example.com", "ftp://example.com")) {
            assertThatThrownBy(() -> new CorsProperties(List.of(origin))).isInstanceOf(IllegalArgumentException.class);
        }
    }
    @Test void emptyConfigurationAllowsNoOrigins() { assertThat(new CorsProperties(null).allowedOrigins()).isEmpty(); }
}
