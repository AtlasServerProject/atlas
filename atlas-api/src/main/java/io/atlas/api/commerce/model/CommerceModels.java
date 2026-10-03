package io.atlas.api.commerce.model;
import jakarta.validation.constraints.*;
import java.time.Instant;
import java.util.*;
public final class CommerceModels {
 public record LinkView(UUID id,UUID subject,long corePlayerId,UUID minecraftUuid,String nickname,String server,Instant linkedAt) {}
 public record ChallengeView(UUID id,String state,Instant expiresAt,UUID subject,String nickname,String server) {}
 public record LinkStatus(LinkView current,ChallengeView pending) {}
 public record ChallengeCreated(UUID id,String code,Instant expiresAt) { @Override public String toString(){return "ChallengeCreated[id="+id+"]";} }
 public record Confirmation(@NotNull UUID challengeId,@NotNull UUID subject) {}
 public record Unlink(@NotBlank @Size(max=128) String password) { @Override public String toString(){return "Unlink[redacted]";} }
 public record Proof(@NotBlank @Pattern(regexp="[A-Za-z0-9_-]{43}") String code,@NotNull UUID subject,@Min(1) long corePlayerId,@NotNull UUID minecraftUuid,@NotBlank @Pattern(regexp="[A-Za-z0-9_]{1,16}") String nickname,@Pattern(regexp="emerald") @NotNull String server) { @Override public String toString(){return "Proof[redacted]";} }
 public record Checkout(@Min(1) long productId,@Pattern(regexp="emerald") @NotNull String server,@Min(1) @Max(1) int quantity,@Min(1) long productRevision,@Min(1) long catalogRevision,@Min(1) int expectedCents) {}
 public record Snapshot(long productId,String productName,String slug,String server,int durationDays,int unitCents,Long promotionId,long productRevision,long catalogRevision,UUID subject,long corePlayerId,UUID minecraftUuid,String nickname) {}
 public record OrderView(UUID id,Snapshot snapshot,int totalCents,String currency,int quantity,Instant createdAt,Instant expiresAt,String paymentStatus,String deliveryStatus) {}
 public record OrdersPage(List<OrderView> items,int page,int size,boolean hasNext) {}
}
