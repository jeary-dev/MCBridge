package czr.mcbridge;

import czr.mcbridge.core.BridgeClient;
import czr.mcbridge.core.LinkClient;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import org.bukkit.Bukkit;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;

import java.net.URI;
import java.util.List;
import java.util.concurrent.CompletionException;

/** In-game /mcbridge status | reload | link <code>. */
final class MCBridgeCommand implements CommandExecutor, TabCompleter {
    private final MCBridge plugin;

    MCBridgeCommand(MCBridge plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        String sub = args.length == 0 ? "status" : args[0].toLowerCase();
        switch (sub) {
            case "status" -> status(sender);
            case "reload" -> {
                plugin.reconnect();
                sender.sendMessage(Component.text("MCBridge: config reloaded, reconnecting...", NamedTextColor.GREEN));
            }
            case "link" -> {
                if (args.length < 2) {
                    sender.sendMessage(Component.text("Usage: /mcbridge link <code>  (get a code with /setup in Discord)",
                            NamedTextColor.GRAY));
                } else {
                    link(sender, args[1]);
                }
            }
            default -> sender.sendMessage(Component.text("Usage: /mcbridge <status|reload|link <code>>", NamedTextColor.GRAY));
        }
        return true;
    }

    private void status(CommandSender sender) {
        BridgeClient c = plugin.client();
        if (c == null) {
            sender.sendMessage(Component.text("MCBridge: not linked yet. Run /setup in Discord, then /mcbridge link <code>",
                    NamedTextColor.RED));
        } else if (c.isConnected()) {
            sender.sendMessage(Component.text("MCBridge: connected as " + c.serverId(), NamedTextColor.GREEN));
        } else {
            sender.sendMessage(Component.text("MCBridge: " + c.state().name().toLowerCase()
                    + " (check the server console for details)", NamedTextColor.YELLOW));
        }
    }

    private void link(CommandSender sender, String code) {
        URI botUrl;
        try {
            botUrl = URI.create(plugin.getConfig().getString("bot-url", ""));
        } catch (IllegalArgumentException e) {
            sender.sendMessage(Component.text("MCBridge: bot-url in config.yml is invalid", NamedTextColor.RED));
            return;
        }
        sender.sendMessage(Component.text("MCBridge: linking...", NamedTextColor.GRAY));

        LinkClient.link(botUrl, code).whenComplete((linked, error) -> Bukkit.getScheduler().runTask(plugin, () -> {
            if (error != null) {
                Throwable cause = error instanceof CompletionException && error.getCause() != null ? error.getCause() : error;
                sender.sendMessage(Component.text("MCBridge: linking failed - " + cause.getMessage(), NamedTextColor.RED));
                return;
            }
            plugin.getConfig().set("token", linked.token());
            plugin.saveConfig();
            plugin.reconnect();
            sender.sendMessage(Component.text("MCBridge: linked as \"" + linked.name() + "\" - connecting to Discord!",
                    NamedTextColor.GREEN));
        }));
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        return args.length == 1 ? List.of("status", "reload", "link") : List.of();
    }
}
