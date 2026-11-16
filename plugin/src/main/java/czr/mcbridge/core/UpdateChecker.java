package czr.mcbridge.core;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;

/** Asks GitHub for the latest MCBridge release and compares it with the running version. */
public final class UpdateChecker {
    public static final String LATEST_RELEASE = "https://api.github.com/repos/jeary-dev/MCBridge/releases/latest";
    private static final String DOWNLOAD_PREFIX = "https://github.com/jeary-dev/MCBridge/";

    public record Release(String version, String url) {}

    private UpdateChecker() {}

    public static CompletableFuture<Optional<Release>> check(String currentVersion) {
        HttpRequest request = HttpRequest.newBuilder(URI.create(LATEST_RELEASE))
                .timeout(Duration.ofSeconds(10))
                .header("Accept", "application/vnd.github+json")
                .header("User-Agent", "MCBridge/" + currentVersion)
                .GET()
                .build();
        return HttpClient.newHttpClient()
                .sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(response -> {
                    if (response.statusCode() != 200) return Optional.<Release>empty();
                    return parse(response.body()).filter(r -> isNewer(r.version(), currentVersion));
                })
                .exceptionally(e -> Optional.empty());
    }

    static Optional<Release> parse(String body) {
        try {
            JsonObject json = JsonParser.parseString(body).getAsJsonObject();
            String tag = Envelope.str(json, "tag_name");
            String url = Envelope.str(json, "html_url");
            if (tag == null || json.has("draft") && json.get("draft").getAsBoolean()
                    || json.has("prerelease") && json.get("prerelease").getAsBoolean()) {
                return Optional.empty();
            }
            if (url == null || !url.startsWith(DOWNLOAD_PREFIX)) url = DOWNLOAD_PREFIX + "releases/latest";
            return Optional.of(new Release(clean(tag), url));
        } catch (RuntimeException e) {
            return Optional.empty();
        }
    }

    public static boolean isNewer(String candidate, String current) {
        int[] a = numbers(candidate);
        int[] b = numbers(current);
        for (int i = 0; i < Math.max(a.length, b.length); i++) {
            int x = i < a.length ? a[i] : 0;
            int y = i < b.length ? b[i] : 0;
            if (x != y) return x > y;
        }
        return false;
    }

    static String clean(String version) {
        String v = version.trim();
        if (v.startsWith("v") || v.startsWith("V")) v = v.substring(1);
        return v;
    }

    private static int[] numbers(String version) {
        String v = clean(version);
        int dash = v.indexOf('-');
        if (dash >= 0) v = v.substring(0, dash);
        String[] parts = v.split("\\.");
        int[] out = new int[parts.length];
        for (int i = 0; i < parts.length; i++) {
            try {
                out[i] = Integer.parseInt(parts[i].replaceAll("[^0-9]", ""));
            } catch (NumberFormatException e) {
                out[i] = 0;
            }
        }
        return out;
    }
}
