package io.atlas.api.catalog.controller;
import io.atlas.api.catalog.model.CatalogModels.*;
import io.atlas.api.catalog.service.CatalogService;
import io.atlas.api.auth.model.SessionIdentity;
import jakarta.validation.Valid;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.http.*;
@RestController @RequestMapping("/api/v1")
public class CatalogController {
 private final CatalogService service;
 public CatalogController(CatalogService service){this.service=service;}
 private String request(HttpServletRequest r){return String.valueOf(r.getAttribute(io.atlas.api.shared.web.RequestIdFilter.ATTRIBUTE));}
 @GetMapping("/catalog") ResponseEntity<Catalog> catalog(){return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(service.catalog(false));}
 @GetMapping("/admin/catalog") Catalog admin(){return service.catalog(true);}
 @PostMapping("/admin/products") Product create(@Valid @RequestBody ProductInput p,@AuthenticationPrincipal SessionIdentity user,HttpServletRequest r){return service.create(p,user.id(),request(r));}
 @PatchMapping("/admin/products/{id}") Product update(@PathVariable long id,@Valid @RequestBody ProductInput p,@AuthenticationPrincipal SessionIdentity user,HttpServletRequest r){return service.update(id,p,user.id(),request(r));}
 @PatchMapping("/admin/products/{id}/price") Product price(@PathVariable long id,@Valid @RequestBody Price p,@AuthenticationPrincipal SessionIdentity user,HttpServletRequest r){return service.price(id,p,user.id(),request(r));}
 @PatchMapping("/admin/products/{id}/offer") Product offer(@PathVariable long id,@Valid @RequestBody Offer p,@AuthenticationPrincipal SessionIdentity user,HttpServletRequest r){return service.offer(id,p,user.id(),request(r));}
 @PostMapping("/admin/promotions") Promotion createPromotion(@Valid @RequestBody PromotionInput p,@AuthenticationPrincipal SessionIdentity user,HttpServletRequest r){return service.save(null,p,user.id(),request(r));}
 @PatchMapping("/admin/promotions/{id}") Promotion updatePromotion(@PathVariable long id,@Valid @RequestBody PromotionInput p,@AuthenticationPrincipal SessionIdentity user,HttpServletRequest r){return service.save(id,p,user.id(),request(r));}
 @PatchMapping("/admin/promotions/{id}/status") Promotion status(@PathVariable long id,@Valid @RequestBody Transition p,@AuthenticationPrincipal SessionIdentity user,HttpServletRequest r){return service.transition(id,p,user.id(),request(r));}
}
