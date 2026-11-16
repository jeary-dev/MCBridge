package czr.mcbridge;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import czr.mcbridge.core.HeartbeatSource;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.scheduler.BukkitTask;

/**
 * Takes a snapshot of server stats once a second ON THE MAIN THREAD (where Bukkit is safe to use).
 * The client thread then just reads the latest snapshot when it's time to send a heartbeat.
 */
final class HeartbeatSampler implements HeartbeatSource {
    private final MCBridge plugin;
    private final long startedAt = System.currentTimeMillis();
    private volatile JsonObject latest = new JsonObject();
    private BukkitTask task;

    HeartbeatSampler(MCBridge plugin) {
        this.plugin = plugin;
    }

    void start() {
        sample();
        task = Bukkit.getScheduler().runTaskTimer(plugin, this::sample, 20L, 20L);
    }

    @Override
    public JsonObject snapshot() {
        return latest.deepCopy();
    }

    private void sample() {
        JsonObject o = new JsonObject();

        JsonArray tps = new JsonArray();
        for (double t : Bukkit.getTPS()) {
            tps.add(Math.round(Math.min(t, 20.0) * 100.0) / 100.0);
        }
        o.add("tps", tps);
        o.addProperty("mspt", Math.round(Bukkit.getAverageTickTime() * 10.0) / 10.0);

        JsonArray players = new JsonArray();
        for (Player p : Bukkit.getOnlinePlayers()) {
            players.add(MCBridge.player(p));
        }
        o.add("players", players);
        o.addProperty("max_players", Bukkit.getMaxPlayers());

        Runtime rt = Runtime.getRuntime();
        JsonObject memory = new JsonObject();
        memory.addProperty("used_mb", (rt.totalMemory() - rt.freeMemory()) / (1024 * 1024));
        memory.addProperty("max_mb", rt.maxMemory() / (1024 * 1024));
        o.add("memory", memory);

        o.addProperty("uptime_s", (System.currentTimeMillis() - startedAt) / 1000);
        latest = o;
    }
}
