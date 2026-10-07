package io.atlas.api.auth.model;
import java.time.Instant;
import java.util.UUID;
public record Account(UUID id, String username, String email, String passwordHash,
                      String role, boolean emailVerified, long authVersion, Instant createdAt) {
    @Override public String toString() { return "Account[id="+id+"]"; }
    public UserView view() { return new UserView(id, username, email, role, emailVerified, createdAt); }
    public record UserView(UUID id, String username, String email, String role, boolean emailVerified, Instant createdAt) { }
}
