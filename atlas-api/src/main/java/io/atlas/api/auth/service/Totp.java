package io.atlas.api.auth.service;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
/** RFC 6238 SHA-1, 30-second step, six digits; no third-party QR service receives secrets. */
public final class Totp {
 private static final String ALPHABET="ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
 private Totp(){}
 public static String base32(byte[] bytes){StringBuilder out=new StringBuilder();int value=0,bits=0;for(byte b:bytes){value=(value<<8)|(b&255);bits+=8;while(bits>=5){bits-=5;out.append(ALPHABET.charAt((value>>bits)&31));}}if(bits>0)out.append(ALPHABET.charAt((value<<(5-bits))&31));return out.toString();}
 private static byte[] decode(String input){var out=new java.io.ByteArrayOutputStream();int value=0,bits=0;for(char c:input.toCharArray()){int n=ALPHABET.indexOf(c);if(n<0)throw new IllegalArgumentException();value=(value<<5)|n;bits+=5;if(bits>=8){bits-=8;out.write((value>>bits)&255);}}return out.toByteArray();}
 public static String code(String secret,long step){try{Mac mac=Mac.getInstance("HmacSHA1");mac.init(new SecretKeySpec(decode(secret),"HmacSHA1"));byte[] bytes=mac.doFinal(ByteBuffer.allocate(8).putLong(step).array());int offset=bytes[bytes.length-1]&15;int binary=ByteBuffer.wrap(bytes,offset,4).getInt()&0x7fffffff;return String.format(java.util.Locale.ROOT,"%06d",binary%1_000_000);}catch(Exception e){throw new IllegalArgumentException("Invalid authenticator secret");}}
 public static long match(String secret,String input,long step,long last){if(input==null||!input.matches("[0-9]{6}"))return -1;long accepted=-1;for(long candidate=step-1;candidate<=step+1;candidate++){boolean equal=MessageDigest.isEqual(code(secret,candidate).getBytes(StandardCharsets.US_ASCII),input.getBytes(StandardCharsets.US_ASCII));if(equal&&candidate>last)accepted=candidate;}return accepted;}
}
