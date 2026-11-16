package czr.mcbridge;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import czr.mcbridge.core.BridgeClient;
import czr.mcbridge.core.Envelope;
import czr.mcbridge.roles.PermissionsBridge;
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
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/** Plugin entry point: wires the Minecraft server to a {@link BridgeClient}. */
public final class MCBridge extends JavaPlugin {
    private static final long MAX_ICON_BYTES = 18 * 1024;

    private BridgeClient client;
    private Messages messages;
    private UpdateNotifier updates;
    private HeartbeatSampler sampler;
    private ConsoleStream consoleStream;
    private PermissionsBridge permissions;
    private JoinGate joinGate;
    private final Map<UUID, List<String>> lastGroups = new ConcurrentHashMap<>();
    private boolean startAnnounced;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        messages = new Messages(this);
        sampler = new HeartbeatSampler(this);
        sampler.start();
        getServer().getPluginManager().registerEvents(new EventsListener(this), this);
        joinGate = new JoinGate(this);
        getServer().getPluginManager().registerEvents(joinGate, this);
        updates = new UpdateNotifier(this);
        getServer().getPluginManager().registerEvents(updates, this);
        updates.start();
        consoleStream = new ConsoleStream(this);
        permissions = PermissionsBridge.detect(this);
        if (permissions != null) {
            getLogger().info("Role sync will use " + permissions.name());
            permissions.onGroupsChanged(this, p -> sendGroups(p, "change"));
        }

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
        if (consoleStream != null) consoleStream.disable();
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
        capabilities.add("stats");
        capabilities.add("inventory");
        capabilities.add("player_info");
        capabilities.add("advancements");
        capabilities.add("join_gate");
        if (allowed("chat")) capabilities.add("message");
        if (allowed("moderation")) capabilities.add("moderation");
        if (allowed("console")) capabilities.add("console_stream");
        if (permissions != null && allowed("roles", true)) capabilities.add("roles");
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
        if (consoleStream != null) consoleStream.disable();
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
        return allowed(capability, false);
    }

    boolean allowed(String capability, boolean byDefault) {
        return getConfig().getBoolean("allow." + capability, byDefault);
    }

    JoinGate joinGate() {
        return joinGate;
    }

    PermissionsBridge permissions() {
        return permissions;
    }

    void setConsoleStream(boolean enabled) {
        if (enabled) consoleStream.enable();
        else consoleStream.disable();
    }

    void sendGroups(Player player, String reason) {
        if (permissions == null || !allowed("roles", true)) return;
        List<String> groups = permissions.groups(player);
        List<String> previous = lastGroups.put(player.getUniqueId(), groups);
        if (reason.equals("change") && groups.equals(previous)) return;
        JsonArray list = new JsonArray();
        groups.forEach(list::add);
        JsonObject data = new JsonObject();
        data.add("player", player(player));
        data.add("groups", list);
        data.addProperty("reason", reason);
        sendEvent("event.player_groups", data);
    }

    void forgetGroups(Player player) {
        lastGroups.remove(player.getUniqueId());
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
