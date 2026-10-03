package io.atlas.api.catalog.service;
import io.atlas.api.catalog.model.CatalogModels.*;
import io.atlas.api.catalog.repository.CatalogRepository;
import io.atlas.api.shared.error.ApiFailure;
import java.time.Clock;
import java.util.UUID;
import java.math.BigDecimal;
import java.math.RoundingMode;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.security.access.prepost.PreAuthorize;
import tools.jackson.databind.ObjectMapper;
@Service
public class CatalogService {
 private final CatalogRepository repo;private final Clock clock;private final ObjectMapper json;
 public CatalogService(CatalogRepository repo,Clock clock,ObjectMapper json){this.repo=repo;this.clock=clock;this.json=json;}
 @Transactional(readOnly=true,isolation=org.springframework.transaction.annotation.Isolation.REPEATABLE_READ)
 public Catalog catalog(boolean admin){var now=clock.instant();var products=repo.products(admin);var promotions=repo.promotions(now,admin).stream().filter(p->products.stream().anyMatch(x->x.id()==p.productId())).toList();var priced=products.stream().map(p->{var offer=promotions.stream().filter(x->x.productId()==p.id()&&x.status().equals("ACTIVE")).findFirst().orElse(null);return new Product(p.id(),p.slug(),p.name(),p.description(),p.category(),p.active(),p.server(),p.priceCents(),p.purchasable(),p.revision(),p.durationDays(),offer==null?p.priceCents():offer.finalCents(),offer==null?null:offer.id());}).toList();return new Catalog(now,repo.revision(),priced,promotions);}
 private ApiFailure bad(String text){return new ApiFailure(HttpStatus.BAD_REQUEST,"INVALID_OFFER",text);}
 private void revision(long supplied,long actual){if(supplied!=actual)throw new ApiFailure(HttpStatus.CONFLICT,"REVISION_CONFLICT","Outra edição alterou os dados. Atualize o catálogo e revise o formulário antes de salvar.");}
 private String encode(Object value){return value==null?null:json.writeValueAsString(value);}
 private void changed(UUID actor,String action,String resource,Object before,Object after,String request){repo.audit(actor,action,resource,encode(before),encode(after),request);repo.bump();}
 private void version(Product p){repo.version(p.id(),p.revision(),encode(p));}
 @PreAuthorize("hasRole('ADMIN')") @Transactional
 public Product create(ProductInput input,UUID actor,String request){if(input.revision()!=0)throw bad("Produto novo deve ter revisão zero.");long id=repo.create(input);var p=repo.product(id,false);version(p);changed(actor,"CREATE_PRODUCT","product:"+id,null,p,request);return p;}
 @PreAuthorize("hasRole('ADMIN')") @Transactional
 public Product update(long id,ProductInput input,UUID actor,String request){var old=repo.product(id,true);revision(input.revision(),old.revision());validatePrice(id,input.priceCents());repo.update(id,input);var p=repo.product(id,false);version(p);changed(actor,"UPDATE_PRODUCT","product:"+id,old,p,request);return p;}
 private void validatePrice(long id,int cents){if(repo.invalidPrice(id,cents,clock.instant()))throw bad("Encerre ou ajuste as promoções antes de reduzir o preço base abaixo do preço promocional.");}
 @PreAuthorize("hasRole('ADMIN')") @Transactional
 public Product price(long id,Price input,UUID actor,String request){var old=repo.product(id,true);revision(input.revision(),old.revision());validatePrice(id,input.priceCents());repo.price(id,input.priceCents());repo.increment(id);var p=repo.product(id,false);version(p);changed(actor,"UPDATE_PRICE","product:"+id,old,p,request);return p;}
 @PreAuthorize("hasRole('ADMIN')") @Transactional
 public Product offer(long id,Offer input,UUID actor,String request){var old=repo.product(id,true);revision(input.revision(),old.revision());repo.offer(id,input.active());var p=repo.product(id,false);version(p);changed(actor,"UPDATE_OFFER","product:"+id,old,p,request);return p;}
 private Promotion find(long id){return repo.promotions(clock.instant(),true).stream().filter(p->p.id()==id).findFirst().orElseThrow(()->new ApiFailure(HttpStatus.NOT_FOUND,"PROMOTION_NOT_FOUND","Promoção não encontrada."));}
 @PreAuthorize("hasRole('ADMIN')") @Transactional
 public Promotion save(Long id,PromotionInput input,UUID actor,String request){var product=repo.product(input.productId(),true);revision(input.productRevision(),product.revision());var old=id==null?null:find(id);if(old!=null){revision(input.revision(),old.revision());if(old.productId()!=input.productId()||!old.server().equals(input.server()))throw bad("Não é possível trocar o produto da promoção.");if(old.status().equals("CANCELLED")||old.status().equals("FINISHED"))throw bad("Promoção encerrada não pode ser editada.");}else if(input.revision()!=0)throw bad("Promoção nova deve ter revisão zero.");
 if(!input.endsAt().isAfter(input.startsAt())||!input.endsAt().isAfter(clock.instant()))throw bad("O término deve ser futuro e posterior ao início.");
 if((input.finalCents()==null)==(input.discountBasisPoints()==null))throw bad("Escolha preço final ou porcentagem.");
 int cents=input.finalCents()!=null?input.finalCents():BigDecimal.valueOf(product.priceCents()).multiply(BigDecimal.valueOf(10000-input.discountBasisPoints())).divide(BigDecimal.valueOf(10000),0,RoundingMode.HALF_UP).intValueExact();
 if(cents<1||cents>=product.priceCents())throw bad("O preço promocional deve ser positivo e menor que o preço base.");
 long target=id==null?repo.createPromotion(input,product.priceCents(),cents):id;if(id!=null)repo.updatePromotion(id,input,product.priceCents(),cents);var p=find(target);changed(actor,id==null?"CREATE_PROMOTION":"UPDATE_PROMOTION","promotion:"+target,old,p,request);return p;}
 @PreAuthorize("hasRole('ADMIN')") @Transactional
 public Promotion transition(long id,Transition input,UUID actor,String request){var initial=find(id);repo.product(initial.productId(),true);var old=find(id);revision(input.revision(),old.revision());if(old.status().equals("FINISHED")||old.status().equals("CANCELLED"))throw bad("Promoção já encerrada.");repo.terminal(id,input.status());var p=find(id);changed(actor,"END_PROMOTION","promotion:"+id,old,p,request);return p;}
}
