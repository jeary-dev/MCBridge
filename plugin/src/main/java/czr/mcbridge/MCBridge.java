package czr.mcbridge;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import czr.mcbridge.core.BridgeClient;
import czr.mcbridge.core.Envelope;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.serializer.plain.PlainTextComponentSerializer;
import org.bukkit.Bukkit;
import org.bukkit.command.PluginCommand;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;

import java.io.IOException;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Base64;

/** Plugin entry point: wires the Minecraft server to a {@link BridgeClient}. */
public final class MCBridge extends JavaPlugin {
    private static final long MAX_ICON_BYTES = 18 * 1024;

    private BridgeClient client;
    private Messages messages;
    private UpdateNotifier updates;
    private HeartbeatSampler sampler;
    private boolean startAnnounced;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        messages = new Messages(this);
        sampler = new HeartbeatSampler(this);
        sampler.start();
        getServer().getPluginManager().registerEvents(new EventsListener(this), this);

        updates = new UpdateNotifier(this);
        getServer().getPluginManager().registerEvents(updates, this);
        updates.start();

        PluginCommand cmd = getCommand("mcbridge");
        if (cmd != null) {
            MCBridgeCommand handler = new MCBridgeCommand(this);
            cmd.setExecutor(handler);
            cmd.setTabCompleter(handler);
        }
        PluginCommand discord = getCommand("discord");
        if (discord != null) {
            DiscordCommand handler = new DiscordCommand(this);
            discord.setExecutor(handler);
            discord.setTabCompleter(handler);
        }
        connect();
    }

    @Override
    public void onDisable() {
        disconnect(true);
    }

    void connect() {
        String url = getConfig().getString("bot-url", "");
        String token = getConfig().getString("token", "");
        if (token == null || token.isBlank()) {
            getLogger().warning("Not linked to Discord yet. Run /setup in your Discord server, "
                    + "then /mcbridge link <code> here.");
            return;
        }

        URI uri;
        try {
            uri = URI.create(url);
        } catch (IllegalArgumentException e) {
            getLogger().severe("bot-url in config.yml is not a valid address: " + url);
            return;
        }

        JsonArray capabilities = new JsonArray();
        for (String cap : new String[]{"chat", "whitelist", "console"}) {
            if (allowed(cap)) capabilities.add(cap);
        }
        capabilities.add("diagnostics");
        capabilities.add("link");
        JsonObject hello = new JsonObject();
        hello.addProperty("plugin_version", getPluginMeta().getVersion());
        hello.addProperty("platform", "paper");
        hello.addProperty("mc_version", Bukkit.getMinecraftVersion());
        hello.add("capabilities", capabilities);
        hello.addProperty("motd", plain(Bukkit.motd()));
        String icon = serverIcon();
        if (icon != null) hello.addProperty("icon", icon);

        client = new BridgeClient(uri, token, hello, sampler, new PaperCommandHandler(this), getLogger());
        client.onWelcome(c -> {
            if (!startAnnounced) {
                startAnnounced = true;
                JsonObject data = new JsonObject();
                data.addProperty("motd", plain(Bukkit.motd()));
                data.addProperty("max_players", Bukkit.getMaxPlayers());
                c.sendEvent("event.server_start", data);
            }
        });
        client.start();
    }

    void disconnect(boolean serverStopping) {
        if (client == null) return;
        Envelope last = null;
        if (serverStopping) {
            JsonObject data = new JsonObject();
            data.addProperty("reason", "shutdown");
            last = Envelope.of("event.server_stop", data);
        }
        client.stop(last, Duration.ofSeconds(2));
        client = null;
    }

    void reconnect() {
        disconnect(false);
        reloadConfig();
        connect();
    }

    private String serverIcon() {
        Path file = Path.of("server-icon.png");
        try {
            if (!Files.isRegularFile(file) || Files.size(file) > MAX_ICON_BYTES) return null;
            return Base64.getEncoder().encodeToString(Files.readAllBytes(file));
        } catch (IOException e) {
            return null;
        }
    }

    UpdateNotifier updates() {
        return updates;
    }

    Messages messages() {
        return messages;
    }

    BridgeClient client() {
        return client;
    }

    boolean allowed(String capability) {
        return getConfig().getBoolean("allow." + capability, false);
    }

    void sendEvent(String type, JsonObject data) {
        BridgeClient c = client;
        if (c != null) c.sendEvent(type, data);
    }

    boolean featureEnabled(String feature) {
        BridgeClient c = client;
        return c != null && c.featureEnabled(feature);
    }

    static JsonObject player(Player p) {
        JsonObject o = new JsonObject();
        o.addProperty("uuid", p.getUniqueId().toString());
        o.addProperty("name", p.getName());
        return o;
    }

    static String plain(Component component) {
        return component == null ? "" : PlainTextComponentSerializer.plainText().serialize(component);
    }
}
