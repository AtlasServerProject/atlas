package io.atlas.api.catalog.model;
import jakarta.validation.constraints.*;
import java.time.Instant;
import java.util.List;
public final class CatalogModels {
 public record Product(long id,String slug,String name,String description,String category,boolean active,String server,int priceCents,boolean purchasable,long revision,Integer durationDays,int finalCents,Long promotionId) {}
 public record Promotion(long id,long productId,String server,String name,int originalCents,int finalCents,Integer discountBasisPoints,Instant startsAt,Instant endsAt,String status,long revision) {}
 public record Catalog(Instant serverTime,long revision,List<Product> products,List<Promotion> promotions) {}
 public record ProductInput(@NotBlank @Pattern(regexp="[a-z0-9]+(?:-[a-z0-9]+)*") @Size(max=80) String slug,@NotBlank @Size(max=100) String name,@NotNull @Size(max=2000) String description,@NotBlank @Pattern(regexp="VIPs|Chaves|Pacotes|Cosméticos") String category,@NotNull Boolean active,@NotBlank @Pattern(regexp="emerald") String server,@Min(1) @Max(100000000) int priceCents,@Min(0) long revision) {}
 public record Price(@Min(1) @Max(100000000) int priceCents,@Min(1) long revision) {}
 public record Offer(@NotNull Boolean active,@Min(1) long revision) {}
 public record PromotionInput(@Min(1) long productId,@NotBlank @Pattern(regexp="emerald") String server,@NotBlank @Size(max=100) String name,Integer finalCents,@Min(1) @Max(9999) Integer discountBasisPoints,@NotNull Instant startsAt,@NotNull Instant endsAt,@Min(0) long revision,@Min(1) long productRevision) {}
 public record Transition(@Pattern(regexp="CANCELLED|FINISHED") @NotNull String status,@Min(1) long revision) {}
}
