package io.atlas.client;

import java.util.Locale;
import java.text.Normalizer;
import org.slf4j.LoggerFactory;

/** Emits only a fixed code from the actual disconnect screen, never remote text or account data. */
public final class AtlasConnectionDiagnostic {
 private AtlasConnectionDiagnostic() {}
 public static void report(String reason) {
  String text=Normalizer.normalize(reason,Normalizer.Form.NFD).replaceAll("\\p{M}","").toLowerCase(Locale.ROOT);
  String code=text.contains("invalid session")||text.contains("sessao invalida")?"AUTH_INVALID_SESSION"
   :text.contains("flying is not enabled")||text.contains("nao e permitido voar")?"SERVER_FLIGHT_DISABLED"
   :text.contains("unknown registr")||text.contains("registro")&&text.contains("desconhecid")?"MOD_REGISTRY_MISMATCH"
   :text.contains("connection reset")?"NETWORK_RESET"
   :text.contains("connection refused")||text.contains("timed out")||text.contains("unknown host")?"NETWORK_UNREACHABLE"
   :"DISCONNECT_UNKNOWN";
  LoggerFactory.getLogger("AtlasDiagnostic").warn("[AtlasDiagnostic] code={}",code);
 }
}
