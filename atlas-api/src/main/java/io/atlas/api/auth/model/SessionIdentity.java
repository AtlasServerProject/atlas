package io.atlas.api.auth.model;
import java.io.Serializable;
import java.security.Principal;
import java.time.Instant;
import java.util.UUID;
public record SessionIdentity(UUID id, long authVersion, Instant authenticatedAt, Instant mfaVerifiedAt, Instant reauthenticatedAt) implements Principal, Serializable {
    public SessionIdentity(UUID id,long version,Instant at){this(id,version,at,null,at);}
    @Override public String getName() { return id.toString(); }
}
