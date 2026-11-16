package czr.mcbridge;

import czr.mcbridge.core.BridgeClient;
import czr.mcbridge.core.LinkClient;
import org.bukkit.Bukkit;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;

import java.net.URI;
import java.util.List;
import java.util.concurrent.CompletionException;

import static czr.mcbridge.Messages.text;

/** In-game /mcbridge status | reload | link <code> | help. */
final class MCBridgeCommand implements CommandExecutor, TabCompleter {
    private final MCBridge plugin;

    MCBridgeCommand(MCBridge plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        Messages msg = plugin.messages();
        String sub = args.length == 0 ? "status" : args[0].toLowerCase();
        switch (sub) {
            case "status" -> status(sender);
            case "reload" -> {
                plugin.reconnect();
                msg.send(sender, "reloaded");
            }
            case "link" -> {
                if (args.length < 2) msg.send(sender, "link-usage");
                else link(sender, args[1]);
            }
            default -> msg.send(sender, "help");
        }
        return true;
    }

    private void status(CommandSender sender) {
        Messages msg = plugin.messages();
        BridgeClient c = plugin.client();
        if (c == null) {
            msg.send(sender, "status-not-linked");
        } else if (c.isConnected()) {
            msg.send(sender, "status-connected", text("server", c.serverId()));
        } else {
            msg.send(sender, "status-other", text("state", c.state().name().toLowerCase()));
        }
    }

    private void link(CommandSender sender, String code) {
        Messages msg = plugin.messages();
        URI botUrl;
        try {
            botUrl = URI.create(plugin.getConfig().getString("bot-url", ""));
        } catch (IllegalArgumentException e) {
            msg.send(sender, "bot-url-invalid");
            return;
        }
        msg.send(sender, "linking");

        LinkClient.link(botUrl, code).whenComplete((linked, error) -> Bukkit.getScheduler().runTask(plugin, () -> {
            if (error != null) {
                Throwable cause = error instanceof CompletionException && error.getCause() != null ? error.getCause() : error;
                msg.send(sender, "link-failed", text("reason", String.valueOf(cause.getMessage())));
                return;
            }
            plugin.getConfig().set("token", linked.token());
            plugin.saveConfig();
            plugin.reconnect();
            msg.send(sender, "link-success", text("name", linked.name()));
        }));
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        return args.length == 1 ? List.of("status", "reload", "link", "help") : List.of();
    }
}