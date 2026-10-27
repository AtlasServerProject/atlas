package br.com.atlascobblemon.launcher;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import static org.assertj.core.api.Assertions.assertThat;
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class LauncherApiTest {
 @LocalServerPort int port;
 private HttpResponse<String> request(String path,String method) throws Exception {
  return HttpClient.newHttpClient().send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+port+path))
   .method(method,HttpRequest.BodyPublishers.noBody()).build(),HttpResponse.BodyHandlers.ofString());
 }
 @Test void healthIsPublicAndDoesNotExposeDetails() throws Exception {
  var result=request("/actuator/health","GET");assertThat(result.statusCode()).isEqualTo(200);
  assertThat(result.body()).isEqualTo("{\"status\":\"UP\"}");
 }
 @Test void statusReportsMissingIntegrations() throws Exception {
  var result=request("/api/launcher/status","GET");assertThat(result.statusCode()).isEqualTo(200);
  assertThat(result.body()).contains("\"releasesAvailable\":false","\"authenticationAvailable\":false","\"eventsAvailable\":false");
  assertThat(result.headers().firstValue("X-Content-Type-Options")).contains("nosniff");
 }
 @Test void anonymousCannotPublishOrRollback() throws Exception {
  for(var path:new String[]{"/api/admin/modpacks/releases","/api/admin/modpacks/1/publish","/api/admin/modpacks/1/rollback"})
   assertThat(request(path,"POST").statusCode()).isEqualTo(403);
 }
 @Test void privateRoutesAndUnsupportedMethodsAreDenied() throws Exception {
  assertThat(request("/actuator/env","GET").statusCode()).isEqualTo(403);
  assertThat(request("/api/launcher/status","POST").statusCode()).isEqualTo(403);
 }
}
