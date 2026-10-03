package io.atlas.api.payment;
import io.atlas.api.commerce.model.CommerceModels.OrderView;
import java.net.URI;
import java.net.http.*;
import java.time.*;
import java.math.BigDecimal;
import java.util.*;
import org.springframework.stereotype.Component;
import tools.jackson.databind.*;
@Component
public class MercadoPagoProvider implements PaymentProvider {
 private final PaymentSettings settings;private final ObjectMapper json;
 private final HttpClient client;
 @org.springframework.beans.factory.annotation.Autowired
 public MercadoPagoProvider(PaymentSettings settings,ObjectMapper json){this(settings,json,HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).followRedirects(HttpClient.Redirect.NEVER).build());}
 MercadoPagoProvider(PaymentSettings settings,ObjectMapper json,HttpClient client){this.settings=settings;this.json=json;this.client=client;}
 private JsonNode call(String path,Object body,String key){
 try{
 var request=HttpRequest.newBuilder(URI.create("https://api.mercadopago.com"+path)).timeout(Duration.ofSeconds(10)).header("Authorization","Bearer "+settings.token).header("Accept","application/json");
 if(body!=null)request.header("Content-Type","application/json").header("X-Idempotency-Key",key).POST(HttpRequest.BodyPublishers.ofString(json.writeValueAsString(body)));
 var response=client.send(request.build(),HttpResponse.BodyHandlers.ofInputStream());
 try(var stream=response.body()){
 if(response.statusCode()<200||response.statusCode()>=300)throw new IllegalStateException("Provider unavailable");
 byte[] bytes=stream.readNBytes(1048577);if(bytes.length>1048576)throw new IllegalStateException("Provider response too large");
 return json.readTree(bytes);
 }
 }catch(InterruptedException e){Thread.currentThread().interrupt();throw new IllegalStateException("Provider interrupted");}catch(Exception e){throw new IllegalStateException("Provider unavailable");}
 }
 public Preference create(OrderView order,String attemptId){
 String back=settings.webUrl.replaceAll("/$","")+"/minhas-compras";
 var payload=new LinkedHashMap<String,Object>();
 payload.put("items",List.of(Map.of("id",order.snapshot().slug(),"title",order.snapshot().productName(),"quantity",1,"currency_id","BRL","unit_price",BigDecimal.valueOf(order.totalCents(),2))));
 payload.put("external_reference",order.id().toString());payload.put("metadata",Map.of("atlas_attempt_id",attemptId));payload.put("back_urls",Map.of("success",back,"failure",back,"pending",back));payload.put("auto_return","approved");payload.put("notification_url",settings.notificationUrl);payload.put("expires",true);payload.put("expiration_date_from",order.createdAt().toString());payload.put("expiration_date_to",order.expiresAt().toString());
 payload.put("payment_methods",Map.of("excluded_payment_types",List.of(Map.of("id","ticket")),"installments",1));
 var result=call("/checkout/preferences",payload,attemptId);String id=result.path("id").asText();String url=result.path(settings.live()?"init_point":"sandbox_init_point").asText();
 if(id.isBlank()||!safeUrl(url))throw new IllegalStateException("Invalid preference");return new Preference(id,url);
 }
 public static boolean safeUrl(String url){try{var uri=URI.create(url);return "https".equals(uri.getScheme())&&uri.getUserInfo()==null&&uri.getPort()==-1&&Set.of("www.mercadopago.com.br","sandbox.mercadopago.com.br").contains(uri.getHost());}catch(Exception e){return false;}}
 public Payment payment(String id){if(!id.matches("[0-9]{1,30}"))throw new IllegalArgumentException("Invalid payment id");return parse(call("/v1/payments/"+id,null,null));}
 public List<Payment> search(String reference){UUID.fromString(reference);var result=call("/v1/payments/search?external_reference="+reference+"&sort=date_created&criteria=desc&limit=100",null,null);if(result.path("paging").path("total").asInt()>100)throw new IllegalStateException("Payment search requires review");List<Payment> found=new ArrayList<>();for(var entry:result.path("results"))found.add(parse(entry));return found;}
 private int cents(JsonNode node){return new BigDecimal(node.asText()).movePointRight(2).intValueExact();}
 private Instant instant(JsonNode node){return OffsetDateTime.parse(node.asText()).toInstant();}
 private Payment parse(JsonNode p){return new Payment(p.path("id").asText(),p.path("external_reference").asText(),p.path("collector_id").asText(),cents(p.path("transaction_amount")),p.path("currency_id").asText(),p.path("status").asText(),p.path("live_mode").asBoolean(),instant(p.path("date_last_updated")),p.path("date_approved").isNull()||p.path("date_approved").isMissingNode()?null:instant(p.path("date_approved")),p.path("transaction_amount_refunded").isMissingNode()?0:cents(p.path("transaction_amount_refunded")));}
}
