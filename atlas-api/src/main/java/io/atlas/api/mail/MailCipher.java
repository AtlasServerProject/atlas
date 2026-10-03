package io.atlas.api.mail;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HexFormat;
import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.stereotype.Component;
@Component
public class MailCipher {
    private final byte[] key;
    private final SecureRandom random=new SecureRandom();
    public MailCipher(MailProperties properties) {
        try { key=Base64.getDecoder().decode(properties.encryptionKey());if(key.length!=32) throw new IllegalArgumentException(); }
        catch(Exception exception) { throw new IllegalArgumentException("Configure a 32-byte Base64 mail encryption key outside source control"); }
    }
    public String encrypt(String value) {
        try {
            byte[] iv=new byte[12];random.nextBytes(iv);Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE,new SecretKeySpec(key,"AES"),new GCMParameterSpec(128,iv));
            byte[] encrypted=cipher.doFinal(value.getBytes(StandardCharsets.UTF_8));
            byte[] result=new byte[iv.length+encrypted.length];System.arraycopy(iv,0,result,0,iv.length);System.arraycopy(encrypted,0,result,iv.length,encrypted.length);
            return Base64.getEncoder().encodeToString(result);
        } catch(Exception exception) { throw new IllegalStateException("Mail encryption unavailable"); }
    }
    public String decrypt(String value) {
        try {
            byte[] data=Base64.getDecoder().decode(value);Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE,new SecretKeySpec(key,"AES"),new GCMParameterSpec(128,data,0,12));
            return new String(cipher.doFinal(data,12,data.length-12),StandardCharsets.UTF_8);
        } catch(Exception exception) { throw new IllegalStateException("Mail decryption failed"); }
    }
    public String digest(String identity) {
        try { Mac mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec(key,"HmacSHA256"));return HexFormat.of().formatHex(mac.doFinal(identity.getBytes(StandardCharsets.UTF_8))); }
        catch(Exception exception) {throw new IllegalStateException("Rate digest unavailable");}
    }
}
