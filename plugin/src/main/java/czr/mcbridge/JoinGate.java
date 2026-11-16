package czr.mcbridge;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import czr.mcbridge.core.BridgeClient;
import czr.mcbridge.core.Envelope;
import net.kyori.adventure.text.Component;
import org.bukkit.Bukkit;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.AsyncPlayerPreLoginEvent;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.logging.Level;

/**
 * Join requirements: before a player logs in, asks the bot whether they've linked their Discord
 * (and have the right role). Unlinked players are kicked with a code they redeem in Discord.
 * Operators always get in. If the bot can't be reached, players who got in recently still can.
 */
final class JoinGate implements Listener {
    private static final long WAIT_MS = 3000;
    private static final long REMEMBER_MS = 30L * 24 * 3600 * 1000;
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    private final MCBridge plugin;
    private final Path stateFile;
    private final Map<String, CompletableFuture<JsonObject>> pending = new ConcurrentHashMap<>();
    private final Map<String, Long> recentlyAllowed = new ConcurrentHashMap<>();
    private volatile String mode = "off";

    JoinGate(MCBridge plugin) {
        this.plugin = plugin;
        this.stateFile = plugin.getDataFolder().toPath().resolve("state.json");
        load();
    }

    String mode() {
        return mode;
    }

    void setMode(String newMode) {
        if (!newMode.equals("off") && !newMode.equals("linked") && !newMode.equals("role")) return;
        if (newMode.equals(mode)) return;
        mode = newMode;
        plugin.getLogger().info("Join requirement: " + switch (newMode) {
            case "linked" -> "players must link their Discord account";
            case "role" -> "players must link their Discord account and have a role";
            default -> "off";
        });
        save();
    }

    boolean complete(String requestId, JsonObject result) {
        CompletableFuture<JsonObject> f = pending.remove(requestId);
        if (f == null) return false;
        f.complete(result);
        return true;
    }

    @EventHandler(priority = EventPriority.LOW)
    public void onPreLogin(AsyncPlayerPreLoginEvent event) {
        if (event.getLoginResult() != AsyncPlayerPreLoginEvent.Result.ALLOWED || mode.equals("off")) return;
        UUID id = event.getUniqueId();
        if (Bukkit.getOfflinePlayer(id).isOp()) return;

        BridgeClient client = plugin.client();
        if (client == null || !client.isConnected()) {
            fallback(event);
            return;
        }
        String requestId = UUID.randomUUID().toString();
        CompletableFuture<JsonObject> future = new CompletableFuture<>();
        pending.put(requestId, future);
        JsonObject player = new JsonObject();
        player.addProperty("uuid", id.toString());
        player.addProperty("name", event.getName());
        JsonObject data = new JsonObject();
        data.add("player", player);
        data.addProperty("request_id", requestId);
        client.sendEvent("event.access_request", data);
        try {
            apply(event, future.get(WAIT_MS, TimeUnit.MILLISECONDS));
        } catch (TimeoutException e) {
            fallback(event);
        } catch (Exception e) {
            plugin.getLogger().log(Level.WARNING, "Join check failed for " + event.getName(), e);
            fallback(event);
        } finally {
            pending.remove(requestId);
        }
    }

    private void apply(AsyncPlayerPreLoginEvent event, JsonObject result) {
        boolean allowed = result.has("allowed") && result.get("allowed").getAsBoolean();
        if (allowed) {
            remember(event.getUniqueId());
            return;
        }
        String reason = Envelope.str(result, "reason");
        String code = Envelope.str(result, "code");
        String role = Envelope.str(result, "role");
        String discord = Envelope.str(result, "discord");
        String key = switch (reason == null ? "" : reason) {
            case "not_linked" -> "join-not-linked";
            case "missing_role" -> "join-missing-role";
            case "not_in_discord" -> "join-not-in-discord";
            default -> null;
        };
        if (key == null) {
            fallback(event);
            return;
        }
        recentlyAllowed.remove(event.getUniqueId().toString());
        Component message = plugin.messages().render(key,
                Messages.text("code", code == null ? "" : code),
                Messages.text("role", role == null ? "" : role),
                Messages.text("discord", discord == null ? "our Discord" : discord));
        event.disallow(AsyncPlayerPreLoginEvent.Result.KICK_WHITELIST, message);
    }

    private void fallback(AsyncPlayerPreLoginEvent event) {
        String policy = plugin.getConfig().getString("join-requirement.when-bot-offline", "recent");
        if (policy.equalsIgnoreCase("allow")) return;
        if (policy.equalsIgnoreCase("recent")) {
            Long last = recentlyAllowed.get(event.getUniqueId().toString());
            if (last != null && System.currentTimeMillis() - last < REMEMBER_MS) return;
        }
        event.disallow(AsyncPlayerPreLoginEvent.Result.KICK_OTHER, plugin.messages().render("join-unavailable"));
    }

    private void remember(UUID id) {
        Long previous = recentlyAllowed.put(id.toString(), System.currentTimeMillis());
        if (previous == null || System.currentTimeMillis() - previous > 3600_000) save();
    }

    private void load() {
        if (!Files.isRegularFile(stateFile)) return;
        try {
            JsonElement root = JsonParser.parseString(Files.readString(stateFile));
            if (!root.isJsonObject()) return;
            JsonObject o = root.getAsJsonObject();
            String saved = Envelope.str(o, "join_requirement");
            if (saved != null) mode = saved;
            if (o.has("recently_allowed") && o.get("recently_allowed").isJsonObject()) {
                long now = System.currentTimeMillis();
                for (Map.Entry<String, JsonElement> e : o.getAsJsonObject("recently_allowed").entrySet()) {
                    long ts = e.getValue().getAsLong();
                    if (now - ts < REMEMBER_MS) recentlyAllowed.put(e.getKey(), ts);
                }
            }
        } catch (IOException | RuntimeException e) {
            plugin.getLogger().warning("Couldn't read state.json: " + e.getMessage());
        }
    }

    private synchronized void save() {
        JsonObject o = new JsonObject();
        o.addProperty("join_requirement", mode);
        JsonObject allowed = new JsonObject();
        long now = System.currentTimeMillis();
        recentlyAllowed.forEach((id, ts) -> {
            if (now - ts < REMEMBER_MS) allowed.addProperty(id, ts);
        });
        o.add("recently_allowed", allowed);
        String text = GSON.toJson(o);
        try {
            Files.createDirectories(stateFile.getParent());
            Path tmp = stateFile.resolveSibling("state.json.tmp");
            Files.writeString(tmp, text);
            Files.move(tmp, stateFile, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            plugin.getLogger().warning("Couldn't save state.json: " + e.getMessage());
        }
    }
}
