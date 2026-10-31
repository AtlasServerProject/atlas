package io.atlas.api.payment;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
public final class WebhookSignature {
 private WebhookSignature(){}
 public static boolean valid(String signature,String requestId,String dataId,String secret){
 if(signature==null||signature.length()>300||requestId==null||!requestId.matches("[A-Za-z0-9-]{1,100}")||dataId==null||!dataId.matches("[0-9]{1,30}")||secret.isBlank())return false;
 try{
 Map<String,String> fields=new HashMap<>();for(String part:signature.split(",")){String[] pair=part.trim().split("=",2);if(pair.length!=2||fields.put(pair[0],pair[1])!=null)return false;}
 String ts=fields.get("ts"),hash=fields.get("v1");if(ts==null||!ts.matches("[0-9]{1,20}")||hash==null||!hash.matches("[a-fA-F0-9]{64}"))return false;
 var mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8),"HmacSHA256"));
 return MessageDigest.isEqual(mac.doFinal(("id:"+dataId+";request-id:"+requestId+";ts:"+ts+";").getBytes(StandardCharsets.UTF_8)),HexFormat.of().parseHex(hash));
 }catch(Exception e){return false;}
 }
}
