package czr.mcbridge;

import com.google.gson.JsonObject;
import czr.mcbridge.core.BridgeClient;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;

import java.util.List;
import java.util.regex.Pattern;

/** /discord link <code>: links the player's Minecraft account to their Discord account. */
final class DiscordCommand implements CommandExecutor, TabCompleter {
    private static final Pattern CODE = Pattern.compile("^[A-Za-z0-9-]{4,12}$");

    private final MCBridge plugin;

    DiscordCommand(MCBridge plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        Messages msg = plugin.messages();
        if (!(sender instanceof Player player)) {
            msg.send(sender, "account-players-only");
            return true;
        }
        if (args.length < 2 || !args[0].equalsIgnoreCase("link")) {
            msg.send(player, "account-usage");
            return true;
        }
        if (!CODE.matcher(args[1]).matches()) {
            msg.send(player, "account-bad-code");
            return true;
        }
        BridgeClient client = plugin.client();
        if (client == null || !client.isConnected()) {
            msg.send(player, "account-offline");
            return true;
        }
        JsonObject data = new JsonObject();
        data.add("player", MCBridge.player(player));
        data.addProperty("code", args[1]);
        plugin.sendEvent("event.link_request", data);
        msg.send(player, "account-linking");
        return true;
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        return args.length == 1 ? List.of("link") : List.of();
    }
}