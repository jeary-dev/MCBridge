package czr.mcbridge.core;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

/**
 * Swaps a short link code (from /setup in Discord) for this server's secret token.
 * POST {bot}/v1/link  {"code": "K7P-2QX"}  ->  {"server_id", "name", "token"}
 */
public final class LinkClient {
    public record Linked(String serverId, String name, String token) {}

    private LinkClient() {}

    public static URI linkUri(URI botUrl) {
        String scheme = switch (botUrl.getScheme() == null ? "" : botUrl.getScheme().toLowerCase()) {
            case "wss", "https" -> "https";
            default -> "http";
        };
        String port = botUrl.getPort() == -1 ? "" : ":" + botUrl.getPort();
        return URI.create(scheme + "://" + botUrl.getHost() + port + "/v1/link");
    }

    public static CompletableFuture<Linked> link(URI botUrl, String code) {
        JsonObject body = new JsonObject();
        body.addProperty("code", code);
        HttpRequest request = HttpRequest.newBuilder(linkUri(botUrl))
                .timeout(Duration.ofSeconds(10))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body.toString()))
                .build();

        return HttpClient.newHttpClient()
                .sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(response -> {
                    JsonObject json;
                    try {
                        json = JsonParser.parseString(response.body()).getAsJsonObject();
                    } catch (Exception e) {
                        throw new IllegalStateException("The bot sent an unexpected reply (HTTP " + response.statusCode() + ")");
                    }
                    if (response.statusCode() != 200) {
                        String error = Envelope.str(json, "error");
                        throw new IllegalStateException(error != null ? error : "HTTP " + response.statusCode());
                    }
                    String serverId = Envelope.str(json, "server_id");
                    String name = Envelope.str(json, "name");
                    String token = Envelope.str(json, "token");
                    if (serverId == null || token == null) {
                        throw new IllegalStateException("The bot's reply was missing the token");
                    }
                    return new Linked(serverId, name, token);
                });
    }
}
