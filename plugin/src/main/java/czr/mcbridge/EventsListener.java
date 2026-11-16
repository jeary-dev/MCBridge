package czr.mcbridge;

import com.google.gson.JsonObject;
import io.papermc.paper.advancement.AdvancementDisplay;
import io.papermc.paper.event.player.AsyncChatEvent;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.player.PlayerAdvancementDoneEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/** Turns Minecraft events into protocol events (event.player_*). */
final class EventsListener implements Listener {
    private static final int MAX_CHAT = 256;

    private final MCBridge plugin;
    private final Map<UUID, Long> joinedAt = new ConcurrentHashMap<>();

    EventsListener(MCBridge plugin) {
        this.plugin = plugin;
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onJoin(PlayerJoinEvent event) {
        Player p = event.getPlayer();
        joinedAt.put(p.getUniqueId(), System.currentTimeMillis());

        JsonObject data = new JsonObject();
        data.add("player", MCBridge.player(p));
        data.addProperty("first_join", !p.hasPlayedBefore());
        plugin.sendEvent("event.player_join", data);
        plugin.sendGroups(p, "join");
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onQuit(PlayerQuitEvent event) {
        Player p = event.getPlayer();
        Long since = joinedAt.remove(p.getUniqueId());
        plugin.forgetGroups(p);

        String reason = "quit";
        if (event.getReason() == PlayerQuitEvent.QuitReason.KICKED) {
            reason = p.isBanned() ? "ban" : "kick";
        }

        JsonObject data = new JsonObject();
        data.add("player", MCBridge.player(p));
        data.addProperty("reason", reason);
        data.addProperty("session_s", since == null ? 0 : (System.currentTimeMillis() - since) / 1000);
        plugin.sendEvent("event.player_leave", data);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onChat(AsyncChatEvent event) {
        if (!plugin.featureEnabled("chat_bridge")) return;
        String message = MCBridge.plain(event.message()).strip();
        if (message.isEmpty()) return;
        if (message.length() > MAX_CHAT) message = message.substring(0, MAX_CHAT);

        JsonObject data = new JsonObject();
        data.add("player", MCBridge.player(event.getPlayer()));
        data.addProperty("message", message);
        plugin.sendEvent("event.player_chat", data);
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onDeath(PlayerDeathEvent event) {
        if (event.deathMessage() == null) return;
        JsonObject data = new JsonObject();
        data.add("player", MCBridge.player(event.getPlayer()));
        data.addProperty("message", MCBridge.plain(event.deathMessage()));
        plugin.sendEvent("event.player_death", data);
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onAdvancement(PlayerAdvancementDoneEvent event) {
        AdvancementDisplay display = event.getAdvancement().getDisplay();
        if (display == null || !display.doesAnnounceToChat()) return;

        JsonObject data = new JsonObject();
        data.add("player", MCBridge.player(event.getPlayer()));
        data.addProperty("key", event.getAdvancement().getKey().getKey());
        data.addProperty("title", MCBridge.plain(display.title()));
        plugin.sendEvent("event.player_advancement", data);
    }
}
