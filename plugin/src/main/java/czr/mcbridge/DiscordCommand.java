package czr.mcbridge;

import com.google.gson.JsonObject;
import czr.mcbridge.core.BridgeClient;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
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
        if (!(sender instanceof Player player)) {
            sender.sendMessage(Component.text("Only players can link a Discord account.", NamedTextColor.RED));
            return true;
        }
        if (args.length < 2 || !args[0].equalsIgnoreCase("link")) {
            player.sendMessage(Component.text("Run /account link in Discord to get a code, then type ",
                    NamedTextColor.GRAY).append(Component.text("/discord link <code>", NamedTextColor.WHITE)));
            return true;
        }
        if (!CODE.matcher(args[1]).matches()) {
            player.sendMessage(Component.text("That doesn't look like a link code.", NamedTextColor.RED));
            return true;
        }
        BridgeClient client = plugin.client();
        if (client == null || !client.isConnected()) {
            player.sendMessage(Component.text("This server isn't connected to Discord right now. Try again later.",
                    NamedTextColor.RED));
            return true;
        }
        JsonObject data = new JsonObject();
        data.add("player", MCBridge.player(player));
        data.addProperty("code", args[1]);
        plugin.sendEvent("event.link_request", data);
        player.sendMessage(Component.text("Linking...", NamedTextColor.GRAY));
        return true;
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        return args.length == 1 ? List.of("link") : List.of();
    }
}
