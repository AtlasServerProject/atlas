package io.atlas.api.auth.model;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
public final class AuthRequests {
    public record Register(@NotBlank @Size(max=32) String username,
                           @NotBlank @Email @Size(max=254) String email,
                           @NotBlank @Size(min=8,max=128) String password) { @Override public String toString() { return "AuthRequest[redacted]"; } }
    public record Login(@NotBlank @Email @Size(max=254) String email, @NotBlank @Size(max=128) String password) { @Override public String toString() { return "AuthRequest[redacted]"; } }
    public record EmailRequest(@NotBlank @Email @Size(max=254) String email) { @Override public String toString() { return "EmailRequest[redacted]"; } }
    public record Token(@NotBlank @Size(max=128) String token) { @Override public String toString() { return "Token[redacted]"; } }
    public record Reset(@NotBlank @Size(max=128) String token, @NotBlank @Size(min=8,max=128) String password) { @Override public String toString() { return "AuthRequest[redacted]"; } }
    private AuthRequests() { }
}
