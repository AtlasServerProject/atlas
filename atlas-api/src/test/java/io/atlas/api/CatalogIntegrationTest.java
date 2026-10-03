package io.atlas.api;
import io.atlas.api.catalog.model.CatalogModels.*;
import io.atlas.api.catalog.repository.CatalogRepository;
import io.atlas.api.catalog.service.CatalogService;
import java.time.*;
import java.net.*;
import java.net.http.*;
import java.sql.DriverManager;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.test.context.support.WithMockUser;
import tools.jackson.databind.ObjectMapper;
import static org.assertj.core.api.Assertions.*;
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test") @WithMockUser(roles="ADMIN")
class CatalogIntegrationTest {
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){TestDatabase.properties(r);}
 @Autowired CatalogService service;@Autowired CatalogRepository repo;@Autowired JdbcTemplate db;@Autowired ObjectMapper json;@Autowired PasswordEncoder passwords;
 @LocalServerPort int port;UUID actor;Product product;
 @BeforeEach void seed(){actor=UUID.randomUUID();db.update("INSERT INTO atlas_web.users(id,username,email,password_hash,role,email_verified) VALUES(?,?,?,?,'ADMIN',TRUE)",actor,"Catalog test",actor+"@example.invalid",passwords.encode(actor.toString()));product=service.create(new ProductInput("test-"+actor,"Test VIP","Test","VIPs",true,"emerald",2500,0),actor,"test-request");}
 @AfterEach void releaseFixture(){db.update("UPDATE atlas_web.users SET role='USER' WHERE id=?",actor);if(product!=null){db.update("UPDATE atlas_web.promotions SET terminal_status='CANCELLED' WHERE product_id=?",product.id());db.update("UPDATE atlas_web.products SET active=FALSE WHERE id=?",product.id());}}
 private PromotionInput offer(Instant start,Instant end,Integer cents,Integer basis){return new PromotionInput(product.id(),"emerald","Test offer",cents,basis,start,end,0,product.revision());}
 @Test void versionsAuditOptimisticConflictAndDeactivation(){var updated=service.price(product.id(),new Price(3500,product.revision()),actor,"audit-request");assertThat(updated.priceCents()).isEqualTo(3500);assertThat(updated.revision()).isEqualTo(2);assertThatThrownBy(()->service.price(product.id(),new Price(4500,1),actor,"test")).hasMessageContaining("Outra edição");assertThat(db.queryForObject("SELECT count(*) FROM atlas_web.product_versions WHERE product_id=?",Integer.class,product.id())).isEqualTo(2);assertThat(db.queryForObject("SELECT count(*) FROM atlas_web.catalog_audit WHERE actor=?",Integer.class,actor)).isEqualTo(2);service.offer(product.id(),new Offer(false,2),actor,"test");assertThat(service.catalog(false).products()).noneMatch(p->p.id()==product.id());assertThat(service.catalog(true).products()).anyMatch(p->p.id()==product.id()&&!p.active());}
 @Test void exactBoundariesRoundingAndTerminalState(){var start=Instant.now().plusSeconds(60);var end=start.plusSeconds(60);var p=service.save(null,offer(start,end,null,3333),actor,"test");assertThat(p.finalCents()).isEqualTo(1667);var atStart=new CatalogService(repo,Clock.fixed(p.startsAt(),ZoneOffset.UTC),json);var atEnd=new CatalogService(repo,Clock.fixed(p.endsAt(),ZoneOffset.UTC),json);assertThat(atStart.catalog(false).promotions()).anyMatch(x->x.id()==p.id()&&x.status().equals("ACTIVE"));assertThat(atEnd.catalog(true).promotions()).anyMatch(x->x.id()==p.id()&&x.status().equals("FINISHED"));service.transition(p.id(),new Transition("CANCELLED",p.revision()),actor,"test");assertThat(atStart.catalog(true).promotions()).anyMatch(x->x.id()==p.id()&&x.status().equals("CANCELLED"));assertThat(atStart.catalog(false).promotions()).noneMatch(x->x.id()==p.id());}
 @Test void overlapAndPriceValidationRollback(){var start=Instant.now();var p=service.save(null,offer(start,start.plusSeconds(600),2000,null),actor,"test");assertThatThrownBy(()->service.save(null,offer(start.plusSeconds(1),start.plusSeconds(900),1900,null),actor,"test")).isInstanceOf(org.springframework.dao.DataIntegrityViolationException.class);assertThatThrownBy(()->service.price(product.id(),new Price(1900,1),actor,"test")).hasMessageContaining("promoções");assertThat(repo.product(product.id(),false).priceCents()).isEqualTo(2500);assertThat(db.queryForObject("SELECT count(*) FROM atlas_web.catalog_audit WHERE actor=?",Integer.class,actor)).isEqualTo(2);service.save(null,offer(p.endsAt(),p.endsAt().plusSeconds(60),1900,null),actor,"test");}
 @Test void directConcurrentInsertsCannotOverlap()throws Exception{var pool=Executors.newFixedThreadPool(2);var go=new CountDownLatch(1);Callable<String> task=()->{go.await();try(var c=DriverManager.getConnection(TestDatabase.URL,"atlas_api_runtime",TestDatabase.RUNTIME_PASSWORD);var s=c.prepareStatement("INSERT INTO atlas_web.promotions(product_id,server,name,original_cents,final_cents,starts_at,ends_at) VALUES(?,'emerald','Concurrent',2500,2000,now(),now()+interval '1 hour')")){s.setLong(1,product.id());s.executeUpdate();return "OK";}catch(java.sql.SQLException e){return e.getSQLState();}};try{var a=pool.submit(task);var b=pool.submit(task);go.countDown();assertThat(List.of(a.get(10,TimeUnit.SECONDS),b.get(10,TimeUnit.SECONDS))).containsExactlyInAnyOrder("OK","23P01");}finally{pool.shutdownNow();}assertThat(db.queryForObject("SELECT count(*) FROM atlas_web.promotions WHERE product_id=?",Integer.class,product.id())).isEqualTo(1);}
 private class Browser {
  final HttpClient client=HttpClient.newBuilder().cookieHandler(new CookieManager(null,CookiePolicy.ACCEPT_ALL)).build();
  HttpResponse<String> get(String path)throws Exception{return client.send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+port+"/api/v1/"+path)).GET().build(),HttpResponse.BodyHandlers.ofString());}
  HttpResponse<String> write(String path,String method,Object body,boolean csrf)throws Exception{var r=HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+port+"/api/v1/"+path)).header("Content-Type","application/json");if(csrf){var token=json.readTree(get("auth/csrf").body());r.header(token.get("headerName").asString(),token.get("token").asString());}return client.send(r.method(method,HttpRequest.BodyPublishers.ofString(json.writeValueAsString(body))).build(),HttpResponse.BodyHandlers.ofString());}
  void login()throws Exception{assertThat(write("auth/login","POST",Map.of("email",actor+"@example.invalid","password",actor.toString()),true).statusCode()).isEqualTo(200);}
 }
 @Test void realHttpAuthorizationValidationAndConflict()throws Exception{var browser=new Browser();assertThat(browser.get("catalog").statusCode()).isEqualTo(200);assertThat(browser.get("admin/catalog").statusCode()).isEqualTo(401);browser.login();assertThat(browser.write("admin/products/"+product.id()+"/price","PATCH",new Price(3000,1),false).statusCode()).isEqualTo(403);assertThat(browser.write("admin/products/"+product.id()+"/price","PATCH",Map.of("priceCents",-1,"revision",1),true).statusCode()).isEqualTo(422);assertThat(browser.write("admin/products/"+product.id()+"/price","PATCH",new Price(3000,1),true).statusCode()).isEqualTo(200);assertThat(browser.write("admin/products/"+product.id()+"/price","PATCH",new Price(4000,1),true).statusCode()).isEqualTo(409);db.update("UPDATE atlas_web.users SET role='USER' WHERE id=?",actor);assertThat(browser.get("admin/catalog").statusCode()).isEqualTo(403);assertThat(browser.write("admin/products/"+product.id()+"/price","PATCH",new Price(4000,2),true).statusCode()).isEqualTo(403);}
}
