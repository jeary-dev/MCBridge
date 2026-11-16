package czr.mcbridge;

import czr.mcbridge.core.UpdateChecker;
import czr.mcbridge.core.UpdateChecker.Release;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.event.ClickEvent;
import net.kyori.adventure.text.event.HoverEvent;
import org.bukkit.Bukkit;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;

import static czr.mcbridge.Messages.text;

/** Checks GitHub for a newer MCBridge every 6 hours and tells the console and admins about it. */
final class UpdateNotifier implements Listener {
    private static final long FIRST_CHECK_TICKS = 20L * 10;
    private static final long EVERY_TICKS = 20L * 60 * 60 * 6;
    private static final String PERMISSION = "mcbridge.admin";

    private final MCBridge plugin;
    private final String current;
    private volatile Release latest;
    private String announced;

    UpdateNotifier(MCBridge plugin) {
        this.plugin = plugin;
        this.current = plugin.getPluginMeta().getVersion();
    }

    void start() {
        Bukkit.getScheduler().runTaskTimerAsynchronously(plugin, this::check, FIRST_CHECK_TICKS, EVERY_TICKS);
    }

    Release latest() {
        return latest;
    }

    private void check() {
        if (!plugin.getConfig().getBoolean("update-check", true)) return;
        UpdateChecker.check(current).thenAccept(found -> found.ifPresent(release ->
                Bukkit.getScheduler().runTask(plugin, () -> onFound(release))));
    }

    private void onFound(Release release) {
        latest = release;
        if (release.version().equals(announced)) return;
        announced = release.version();
        plugin.getLogger().warning("A new version of MCBridge is out: " + current + " -> " + release.version()
                + ". Download it from " + release.url());
        for (Player p : Bukkit.getOnlinePlayers()) {
            if (p.hasPermission(PERMISSION)) tell(p);
        }
    }

    void tell(CommandSender to) {
        Release r = latest;
        if (r == null) return;
        Component message = plugin.messages().prefixed("update-available",
                text("current", current), text("latest", r.version()))
                .clickEvent(ClickEvent.openUrl(r.url()))
                .hoverEvent(HoverEvent.showText(Component.text("Open " + r.url())));
        to.sendMessage(message);
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onJoin(PlayerJoinEvent event) {
        Player player = event.getPlayer();
        if (latest != null && player.hasPermission(PERMISSION)) {
            Bukkit.getScheduler().runTaskLater(plugin, () -> {
                if (player.isOnline()) tell(player);
            }, 40L);
        }
    }
}
