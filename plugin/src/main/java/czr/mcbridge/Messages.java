package czr.mcbridge;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.minimessage.MiniMessage;
import net.kyori.adventure.text.minimessage.tag.resolver.Placeholder;
import net.kyori.adventure.text.minimessage.tag.resolver.TagResolver;
import org.bukkit.command.CommandSender;
import czr.mcbridge.core.LegacyColors;

import java.util.Map;

/**
 * Every message the plugin shows to players, written in MiniMessage and overridable in config.yml
 * under "messages". Values filled in from outside (Discord names, chat text) are inserted as plain
 * text, so nobody can inject colours, links or click actions.
 */
final class Messages {
    private static final MiniMessage MM = MiniMessage.miniMessage();

    private static final String GREEN = "#3ddc84";
    private static final String RED = "#ff6b6b";
    private static final String AMBER = "#fab219";

    static final Map<String, String> DEFAULTS = Map.ofEntries(
            Map.entry("prefix", "<dark_gray>[</dark_gray><" + GREEN + ">MCBridge</" + GREEN + "><dark_gray>]</dark_gray> "),
            Map.entry("discord-chat", "<hover:show_text:'<gray>Sent from Discord'><dark_gray>[</dark_gray><#5865f2>Discord</#5865f2>"
                    + "<dark_gray>]</dark_gray> <#b5bac1><author></#b5bac1></hover><dark_gray> » </dark_gray><white><message>"),
            Map.entry("help", "<gray>Commands: <white>/mcbridge status</white> · <white>/mcbridge reload</white> · "
                    + "<white><click:suggest_command:'/mcbridge link '>/mcbridge link \\<code></click></white>"),
            Map.entry("status-connected", "<" + GREEN + ">●</" + GREEN + "> <gray>Connected to Discord as <white><server></white>"),
            Map.entry("status-not-linked", "<" + RED + ">●</" + RED + "> <gray>Not linked yet. Run <white>/setup</white> in Discord, "
                    + "then <white><click:suggest_command:'/mcbridge link '>/mcbridge link \\<code></click></white>"),
            Map.entry("status-other", "<" + AMBER + ">●</" + AMBER + "> <gray>Bot connection: <white><state></white>. "
                    + "Check the console for details."),
            Map.entry("reloaded", "<gray>Config reloaded. Reconnecting..."),
            Map.entry("link-usage", "<gray>Usage: <white><click:suggest_command:'/mcbridge link '>/mcbridge link \\<code></click></white>"
                    + " <dark_gray>·</dark_gray> get a code with <white>/setup</white> in Discord"),
            Map.entry("bot-url-invalid", "<" + RED + ">bot-url in config.yml isn't a valid address."),
            Map.entry("linking", "<gray>Linking..."),
            Map.entry("link-failed", "<" + RED + ">Linking failed:</" + RED + "> <gray><reason>"),
            Map.entry("link-success", "<" + GREEN + ">Linked as <white><name></white>!</" + GREEN + "> <gray>Connecting to Discord..."),
            Map.entry("account-usage", "<gray>Run <white>/account link</white> in Discord to get a code, then type "
                    + "<white><click:suggest_command:'/discord link '>/discord link \\<code></click></white>"),
            Map.entry("account-players-only", "<" + RED + ">Only players can link a Discord account."),
            Map.entry("account-bad-code", "<" + RED + ">That doesn't look like a link code."),
            Map.entry("account-offline", "<" + RED + ">This server isn't connected to Discord right now. Try again later."),
            Map.entry("account-linking", "<gray>Linking your account..."),
            Map.entry("account-linked", "<" + GREEN + "><message>"),
            Map.entry("account-link-failed", "<" + RED + "><message>")
    );

    private final MCBridge plugin;

    Messages(MCBridge plugin) {
        this.plugin = plugin;
    }

    Component render(String key, TagResolver... placeholders) {
        String raw = plugin.getConfig().getString("messages." + key, DEFAULTS.getOrDefault(key, key));
        return MM.deserialize(raw == null ? "" : LegacyColors.toMiniMessage(raw), placeholders);
    }

    Component prefixed(String key, TagResolver... placeholders) {
        return render("prefix").append(render(key, placeholders));
    }

    void send(CommandSender to, String key, TagResolver... placeholders) {
        to.sendMessage(prefixed(key, placeholders));
    }

    static TagResolver text(String name, String value) {
        return Placeholder.unparsed(name, value == null ? "" : value);
    }
}