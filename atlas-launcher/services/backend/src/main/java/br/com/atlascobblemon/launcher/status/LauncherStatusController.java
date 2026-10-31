package br.com.atlascobblemon.launcher.status;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
@RestController
public class LauncherStatusController {
 public record Status(int schemaVersion, String service, String version, String phase,
  boolean releasesAvailable, boolean authenticationAvailable, boolean eventsAvailable) {}
 @GetMapping("/api/launcher/status")
 public Status status() { return new Status(1,"atlas-launcher-api","0.1.0","foundation",false,false,false); }
}
