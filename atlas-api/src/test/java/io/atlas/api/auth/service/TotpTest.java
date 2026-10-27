package io.atlas.api.auth.service;
import org.junit.jupiter.api.Test;import static org.assertj.core.api.Assertions.*;
class TotpTest {
 @Test void rfc6238VectorsAndReplayProtection(){String secret=Totp.base32("12345678901234567890".getBytes(java.nio.charset.StandardCharsets.US_ASCII));long[] times={59,1111111109,1111111111,1234567890,2000000000,20000000000L};String[] codes={"287082","081804","050471","005924","279037","353130"};for(int i=0;i<times.length;i++){long step=times[i]/30;assertThat(Totp.code(secret,step)).isEqualTo(codes[i]);assertThat(Totp.match(secret,codes[i],step,step-1)).isEqualTo(step);assertThat(Totp.match(secret,codes[i],step,step)).isEqualTo(-1);}assertThat(Totp.match(secret,"abcdef",1,-1)).isEqualTo(-1);}
}
