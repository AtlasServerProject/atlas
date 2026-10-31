package io.atlas.api.auth.service;
import java.security.*;import java.security.interfaces.*;import java.time.*;import java.util.*;
import com.nimbusds.jose.*;import com.nimbusds.jose.crypto.RSASSASigner;import com.nimbusds.jwt.*;
import org.junit.jupiter.api.*;import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import static org.assertj.core.api.Assertions.*;
class GoogleTokenVerifierTest {
 static KeyPair pair;final String client="synthetic-google.apps.googleusercontent.com",nonce="synthetic-nonce-random-bound-to-session";final Instant now=Instant.now();GoogleTokenVerifier verifier;
 @BeforeAll static void keys()throws Exception{var generator=KeyPairGenerator.getInstance("RSA");generator.initialize(2048);pair=generator.generateKeyPair();}
 @BeforeEach void setup(){verifier=new GoogleTokenVerifier(new GoogleProperties(true,client),NimbusJwtDecoder.withPublicKey((RSAPublicKey)pair.getPublic()).build(),Clock.fixed(now,ZoneOffset.UTC));}
 JWTClaimsSet.Builder claims(){return new JWTClaimsSet.Builder().issuer("https://accounts.google.com").audience(client).subject("google-stable-subject").issueTime(Date.from(now)).expirationTime(Date.from(now.plusSeconds(300))).claim("nonce",nonce).claim("email","fixture@gmail.com").claim("email_verified",true).claim("name","Atlas Trainer");}
 String signed(JWTClaimsSet.Builder claims,KeyPair key)throws Exception{var jwt=new SignedJWT(new JWSHeader(JWSAlgorithm.RS256),claims.build());jwt.sign(new RSASSASigner((RSAPrivateKey)key.getPrivate()));return jwt.serialize();}
 @Test void acceptsSignedIdentityAndWorkspace()throws Exception{assertThat(verifier.verify(signed(claims(),pair),nonce).subject()).isEqualTo("google-stable-subject");assertThat(verifier.verify(signed(claims().claim("email","staff@atlas.example").claim("hd","atlas.example"),pair),nonce).email()).isEqualTo("staff@atlas.example");}
 @Test void rejectsWrongAudienceIssuerNonceAndUnverifiedEmail()throws Exception{
  for(var claims:List.of(claims().audience("another.apps.googleusercontent.com"),claims().issuer("https://evil.invalid"),claims().claim("nonce","other"),claims().claim("email_verified",false),claims().expirationTime(Date.from(now.minusSeconds(120))),claims().issueTime(Date.from(now.plusSeconds(180))))){String token=signed(claims,pair);assertThatThrownBy(()->verifier.verify(token,nonce)).isInstanceOf(RuntimeException.class);}
 }
 @Test void rejectsUnsignedAndForgedTokens()throws Exception{var generator=KeyPairGenerator.getInstance("RSA");generator.initialize(2048);String token=signed(claims(),generator.generateKeyPair());assertThatThrownBy(()->verifier.verify(token,nonce)).isInstanceOf(RuntimeException.class);assertThatThrownBy(()->verifier.verify(new PlainJWT(claims().build()).serialize(),nonce)).isInstanceOf(RuntimeException.class);}
 @Test void thirdPartyEmailDoesNotBecomeAuthoritativeJustBecauseGoogleVerifiedIt()throws Exception{String token=signed(claims().claim("email","person@external.example"),pair);assertThatThrownBy(()->verifier.verify(token,nonce)).hasMessageContaining("email e senha");}
}
