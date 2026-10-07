package io.atlas.api.delivery;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.time.Instant;
import java.util.*;
public final class DeliveryModels {
 public record Claim(@Pattern(regexp="emerald") @NotNull String server){}
 public record Delivery(UUID id,UUID leaseToken,String server,String mode,UUID subject,long corePlayerId,String plan,int days){}
 public record Balance(@NotNull UUID subject,@Min(1) long corePlayerId,@Pattern(regexp="emerald") @NotNull String server,@Min(0) @Max(3153600000000L) long vip1Ms,@Min(0) @Max(3153600000000L) long vip2Ms,@Min(0) @Max(3153600000000L) long vip3Ms,@NotNull Instant checkpoint){}
 public record Receipt(@NotNull UUID deliveryId,@NotNull UUID receiptId,@NotNull UUID subject,@Min(1) long corePlayerId,@Pattern(regexp="emerald") @NotNull String server,@Pattern(regexp="test|production") @NotNull String mode,@Pattern(regexp="vip-1|vip-2|vip-3") @NotNull String plan,@Min(30) @Max(30) int days,@NotNull Instant activatedAt){}
 public record Ack(@NotNull UUID leaseToken,@Valid @NotNull Receipt receipt,@Valid @NotNull Balance balance){}
 public record Failed(@NotNull UUID leaseToken,@Pattern(regexp="IDENTITY_MISMATCH|UNSUPPORTED_PLAN|CORE_UNAVAILABLE") @NotNull String code){}
 public record Retry(@NotBlank @Size(min=10,max=500) String reason){}
 public record VipView(boolean linked,boolean synchronizedWithCore,int activeLevel,Instant activeUntil,List<Paused> paused,Instant checkedAt){}
 public record Paused(int level,long remainingSeconds){}
 public record Attempt(UUID id,UUID orderId,String nickname,String state,int attempts,Instant leaseUntil,Instant nextAttempt,String lastError,Instant createdAt){}
 public static Balance advance(Balance b,Instant now){
  long elapsed=Math.max(0,java.time.Duration.between(b.checkpoint(),now).toMillis());long[] v={b.vip1Ms(),b.vip2Ms(),b.vip3Ms()};
  for(int i=2;i>=0;i--){long used=Math.min(v[i],elapsed);v[i]-=used;elapsed-=used;}
  return new Balance(b.subject(),b.corePlayerId(),b.server(),v[0],v[1],v[2],now.isBefore(b.checkpoint())?b.checkpoint():now);
 }
 public static VipView view(boolean linked,Balance saved,Instant now){
  if(saved==null)return new VipView(linked,false,0,null,List.of(),now);
  var b=advance(saved,now);long[] v={b.vip1Ms(),b.vip2Ms(),b.vip3Ms()};int level=0;for(int i=2;i>=0;i--)if(v[i]>0){level=i+1;break;}
  List<Paused> paused=new ArrayList<>();for(int i=level-2;i>=0;i--)if(v[i]>0)paused.add(new Paused(i+1,(v[i]+999)/1000));
  return new VipView(linked,true,level,level==0?null:b.checkpoint().plusMillis(v[level-1]),paused,now);
 }
}
