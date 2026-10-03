package io.atlas.api.commerce.service;
import io.atlas.api.commerce.model.CommerceModels.*;
import io.atlas.api.commerce.repository.CommerceRepository;
import io.atlas.api.auth.service.*;
import io.atlas.api.catalog.repository.CatalogRepository;
import io.atlas.api.shared.error.ApiFailure;
import java.time.*;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;
@Service
public class OrderService {
 private final CommerceRepository repo;private final CatalogRepository catalog;private final AuthService auth;private final Clock clock;private final TokenCodec tokens;private final ObjectMapper json;private final boolean enabled;
 public OrderService(CommerceRepository repo,CatalogRepository catalog,AuthService auth,Clock clock,TokenCodec tokens,ObjectMapper json,@Value("${atlas.commerce.sales-enabled:false}") boolean enabled){this.repo=repo;this.catalog=catalog;this.auth=auth;this.clock=clock;this.tokens=tokens;this.json=json;this.enabled=enabled;}
 private ApiFailure fail(HttpStatus status,String code,String message){return new ApiFailure(status,code,message);}
 private OrderView effective(OrderView o){return new OrderView(o.id(),o.snapshot(),o.totalCents(),o.currency(),o.quantity(),o.createdAt(),o.expiresAt(),o.paymentStatus().equals("PENDING")&&!clock.instant().isBefore(o.expiresAt())?"EXPIRED":o.paymentStatus(),o.deliveryStatus());}
 @Transactional public OrderView checkout(UUID user,String key,Checkout input,String request){
 if(key==null||!key.matches("[A-Za-z0-9_-]{16,100}"))throw fail(HttpStatus.BAD_REQUEST,"INVALID_IDEMPOTENCY_KEY","Informe uma chave de idempotência válida.");
 repo.lockUser(user);var hash=tokens.hash(json.writeValueAsString(input));var old=repo.existing(user,key);if(old!=null){if(!old.hash().equals(hash))throw fail(HttpStatus.CONFLICT,"IDEMPOTENCY_CONFLICT","Esta chave já foi usada com outro pedido.");return effective(old.order());}
 if(!auth.current(user).emailVerified())throw fail(HttpStatus.FORBIDDEN,"EMAIL_NOT_VERIFIED","Confirme seu email antes de criar um pedido.");var link=repo.current(user);if(link==null)throw fail(HttpStatus.CONFLICT,"MINECRAFT_NOT_LINKED","Vincule sua conta Minecraft antes de criar um pedido.");
 var product=catalog.product(input.productId(),true);if(!enabled||!product.purchasable())throw fail(HttpStatus.CONFLICT,"SALES_CLOSED","As vendas ainda estão fechadas.");
 if(!product.active()||!repo.serverActive(input.server())||!product.server().equals(input.server())||!link.server().equals(input.server())||!product.category().equals("VIPs")||product.durationDays()==null||input.quantity()!=1)throw fail(HttpStatus.CONFLICT,"INVALID_DESTINATION","Produto ou destino indisponível.");
 var now=clock.instant();var promotion=catalog.promotions(now,false).stream().filter(p->p.productId()==product.id()&&p.server().equals(input.server())&&p.status().equals("ACTIVE")).findFirst().orElse(null);int price=promotion==null?product.priceCents():promotion.finalCents();long revision=catalog.revision();
 if(input.productRevision()!=product.revision()||input.catalogRevision()!=revision||input.expectedCents()!=price)throw fail(HttpStatus.CONFLICT,"QUOTE_CHANGED","O preço ou catálogo mudou. Atualize e confirme o valor novamente.");
 var snap=new Snapshot(product.id(),product.name(),product.slug(),product.server(),product.durationDays(),price,promotion==null?null:promotion.id(),product.revision(),revision,link.subject(),link.corePlayerId(),link.minecraftUuid(),link.nickname());var order=new OrderView(UUID.randomUUID(),snap,price,"BRL",1,now,now.plusSeconds(1800),"PENDING","WAITING");repo.order(user,link.id(),key,hash,order,request);return order;
 }
 @Transactional(readOnly=true) public OrdersPage list(UUID user,int page){if(page<0||page>100000)throw fail(HttpStatus.BAD_REQUEST,"INVALID_PAGE","Página inválida.");var items=repo.orders(user,page);return new OrdersPage(items.stream().limit(20).map(this::effective).toList(),page,20,items.size()>20);}
 @Transactional(readOnly=true) public OrderView detail(UUID user,UUID id){var order=repo.detail(user,id);if(order==null)throw fail(HttpStatus.NOT_FOUND,"ORDER_NOT_FOUND","Pedido não encontrado.");return effective(order);}
}
