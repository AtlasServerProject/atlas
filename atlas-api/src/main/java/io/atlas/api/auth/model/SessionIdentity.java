package io.atlas.api.auth.model;
import java.io.Serializable;
import java.security.Principal;
import java.time.Instant;
import java.util.UUID;
public record SessionIdentity(UUID id, long authVersion, Instant authenticatedAt) implements Principal, Serializable {
    @Override public String getName() { return id.toString(); }
}
