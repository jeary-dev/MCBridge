package czr.mcbridge;

import com.destroystokyo.paper.profile.PlayerProfile;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import czr.mcbridge.core.CommandHandler;
import czr.mcbridge.core.Envelope;
import czr.mcbridge.core.Replies;
import czr.mcbridge.core.Replies.ErrorCode;
import net.kyori.adventure.text.Component;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.function.Supplier;
import java.util.regex.Pattern;

/**
 * Runs commands from Discord. The plugin checks its OWN config before every command,
 * so even a compromised bot can't do something the server owner didn't allow.
 */
final class PaperCommandHandler implements CommandHandler {
    private static final Pattern PLAYER_NAME = Pattern.compile("^[A-Za-z0-9_]{3,16}$");
    private static final int MAX_CHAT = 256;
    private static final int MAX_CONSOLE = 1000;
    private static final int MAX_OUTPUT = 1500;

    private final MCBridge plugin;

    PaperCommandHandler(MCBridge plugin) {
        this.plugin = plugin;
    }

    @Override
    public CompletableFuture<JsonObject> handle(Envelope cmd) {
        return switch (cmd.type()) {
            case "cmd.chat_send" -> chatSend(cmd.data());
            case "cmd.whitelist" -> whitelist(cmd.data());
            case "cmd.console" -> console(cmd.data());
            case "cmd.diagnostics" -> onMainThread(Diagnostics::collect);
            case "cmd.link_result" -> linkResult(cmd.data());
            case "cmd.moderate" -> moderate(cmd.data());
            case "cmd.tab_complete" -> tabComplete(cmd.data());
            case "cmd.player_stats" -> playerLookup(cmd.data(), true);
            case "cmd.inventory" -> playerLookup(cmd.data(), false);
            case "cmd.message" -> message(cmd.data());
            case "cmd.set_features" -> setFeatures(cmd.data());
            case "cmd.set_groups" -> setGroups(cmd.data());
            default -> done(Replies.error(ErrorCode.UNKNOWN_COMMAND, "Unknown command " + cmd.type()));
        };
    }

    private CompletableFuture<JsonObject> chatSend(JsonObject data) {
        if (!plugin.allowed("chat")) return forbidden("chat");
        String author = actorName(data);
        String message = Envelope.str(data, "message");
        if (author == null || message == null || message.isBlank() || message.length() > MAX_CHAT) {
            return done(Replies.error(ErrorCode.INVALID, "missing or bad actor/message"));
        }
        return onMainThread(() -> {
            Component line = plugin.messages().render("discord-chat",
                    Messages.text("author", author), Messages.text("message", message));
            Bukkit.broadcast(line);
            return Replies.ok("sent");
        });
    }

    private CompletableFuture<JsonObject> whitelist(JsonObject data) {
        if (!plugin.allowed("whitelist")) return forbidden("whitelist");
        String action = Envelope.str(data, "action");
        String name = Envelope.str(data, "player_name");
        if (!"add".equals(action) && !"remove".equals(action)) {
            return done(Replies.error(ErrorCode.INVALID, "action must be add or remove"));
        }
        if (name == null || !PLAYER_NAME.matcher(name).matches()) {
            return done(Replies.error(ErrorCode.INVALID, "not a valid Minecraft username"));
        }
        boolean add = action.equals("add");

        return CompletableFuture.supplyAsync(() -> {
            PlayerProfile profile = Bukkit.createProfile(name);
            return profile.complete(false) && profile.getId() != null ? profile : null;
        }).thenCompose(profile -> {
            if (profile == null) {
                return done(Replies.error(ErrorCode.PLAYER_NOT_FOUND, "No Minecraft account called " + name));
            }
            return onMainThread(() -> {
                OfflinePlayer player = Bukkit.getOfflinePlayer(profile.getId());
                player.setWhitelisted(add);
                plugin.getLogger().info((add ? "Whitelisted " : "Un-whitelisted ") + profile.getName()
                        + " (requested by " + actorName(data) + " via Discord)");
                return Replies.ok((add ? "Added " : "Removed ") + profile.getName()
                        + (add ? " to" : " from") + " the whitelist");
            });
        });
    }

    private CompletableFuture<JsonObject> console(JsonObject data) {
        if (!plugin.allowed("console")) return forbidden("console");
        String command = Envelope.str(data, "command");
        if (command == null || command.isBlank() || command.length() > MAX_CONSOLE || command.startsWith("/")) {
            return done(Replies.error(ErrorCode.INVALID, "bad command"));
        }
        String actor = actorName(data);
        return onMainThread(() -> {
            plugin.getLogger().warning("[Discord console] " + actor + " ran: " + command);
            StringBuilder output = new StringBuilder();
            CommandSender sender = Bukkit.createCommandSender(
                    feedback -> output.append(MCBridge.plain(feedback)).append('\n'));
            boolean known = Bukkit.dispatchCommand(sender, command);
            if (!known) {
                return Replies.error(ErrorCode.INVALID, "Unknown command: " + command.split(" ")[0]);
            }
            String result = output.toString().strip();
            if (result.length() > MAX_OUTPUT) result = result.substring(0, MAX_OUTPUT) + "\n...(truncated)";
            return Replies.ok(result.isEmpty() ? "(no output)" : result);
        });
    }

    private CompletableFuture<JsonObject> linkResult(JsonObject data) {
        String uuid = Envelope.str(data, "player_uuid");
        String message = Envelope.str(data, "message");
        boolean ok = data.has("ok") && data.get("ok").isJsonPrimitive() && data.get("ok").getAsBoolean();
        UUID id;
        try {
            id = uuid == null ? null : UUID.fromString(uuid);
        } catch (IllegalArgumentException e) {
            id = null;
        }
        if (id == null || message == null || message.isBlank()) {
            return done(Replies.error(ErrorCode.INVALID, "missing or bad player_uuid/message"));
        }
        UUID target = id;
        return onMainThread(() -> {
            Player player = Bukkit.getPlayer(target);
            if (player == null) return Replies.ok("player is offline");
            plugin.messages().send(player, ok ? "account-linked" : "account-link-failed",
                    Messages.text("message", message));
            return Replies.ok("sent");
        });
    }

    private static final Set<String> GAMEMODES = Set.of("survival", "creative", "adventure", "spectator");

    private CompletableFuture<JsonObject> moderate(JsonObject data) {
        if (!plugin.allowed("moderation")) return forbidden("moderation");
        String action = Envelope.str(data, "action");
        String name = Envelope.str(data, "player_name");
        if (name == null || !PLAYER_NAME.matcher(name).matches()) {
            return done(Replies.error(ErrorCode.INVALID, "not a valid Minecraft username"));
        }
        String actor = actorName(data);
        String reason = Envelope.str(data, "reason");
        reason = reason == null || reason.isBlank() ? null : reason.replaceAll("[\\p{Cntrl}]", " ").strip();
        if (reason != null && reason.length() > 200) reason = reason.substring(0, 200);
        String why = reason != null ? reason : "By " + actor + " via Discord";
        String gamemode = Envelope.str(data, "gamemode");
        String command;
        switch (action == null ? "" : action) {
            case "kick" -> command = "kick " + name + " " + why;
            case "ban" -> command = "ban " + name + " " + why;
            case "unban" -> command = "pardon " + name;
            case "op" -> command = "op " + name;
            case "deop" -> command = "deop " + name;
            case "gamemode" -> {
                if (gamemode == null || !GAMEMODES.contains(gamemode)) {
                    return done(Replies.error(ErrorCode.INVALID, "unknown game mode"));
                }
                command = "gamemode " + gamemode + " " + name;
            }
            default -> {
                return done(Replies.error(ErrorCode.INVALID, "unknown moderation action"));
            }
        }
        String finalCommand = command;
        return onMainThread(() -> {
            if ((action.equals("kick") || action.equals("gamemode")) && Bukkit.getPlayerExact(name) == null) {
                return Replies.error(ErrorCode.PLAYER_NOT_FOUND, name + " isn't online");
            }
            plugin.getLogger().info("[Discord moderation] " + actor + ": " + finalCommand);
            StringBuilder output = new StringBuilder();
            CommandSender sender = Bukkit.createCommandSender(
                    feedback -> output.append(MCBridge.plain(feedback)).append('\n'));
            Bukkit.dispatchCommand(sender, finalCommand);
            String result = output.toString().strip();
            return Replies.ok(result.isEmpty() ? "Done" : result);
        });
    }

    private CompletableFuture<JsonObject> tabComplete(JsonObject data) {
        if (!plugin.allowed("console")) return forbidden("console");
        String text = Envelope.str(data, "command");
        if (text == null || text.length() > MAX_CONSOLE) return done(Replies.error(ErrorCode.INVALID, "bad command"));
        String line = text.startsWith("/") ? text.substring(1) : text;
        return onMainThread(() -> {
            List<String> found;
            if (!line.contains(" ")) {
                found = new ArrayList<>();
                for (String known : Bukkit.getCommandMap().getKnownCommands().keySet()) {
                    if (!known.contains(":") && known.startsWith(line.toLowerCase())) found.add(known);
                }
                found.sort(String::compareTo);
            } else {
                List<String> raw = Bukkit.getCommandMap().tabComplete(Bukkit.getConsoleSender(), line);
                found = raw == null ? List.of() : raw;
            }
            JsonArray suggestions = new JsonArray();
            found.stream().limit(25).forEach(suggestions::add);
            JsonObject out = new JsonObject();
            out.add("suggestions", suggestions);
            return Replies.ok("", out);
        });
    }

    private CompletableFuture<JsonObject> playerLookup(JsonObject data, boolean stats) {
        String name = Envelope.str(data, "player_name");
        if (name == null || !PLAYER_NAME.matcher(name).matches()) {
            return done(Replies.error(ErrorCode.INVALID, "not a valid Minecraft username"));
        }
        return onMainThread(() -> stats ? PlayerInfo.stats(name) : PlayerInfo.inventory(name));
    }

    private CompletableFuture<JsonObject> message(JsonObject data) {
        if (!plugin.allowed("chat")) return forbidden("chat");
        String name = Envelope.str(data, "player_name");
        String message = Envelope.str(data, "message");
        String author = actorName(data);
        if (name == null || message == null || message.isBlank() || message.length() > MAX_CHAT || author == null) {
            return done(Replies.error(ErrorCode.INVALID, "missing or bad player/message"));
        }
        return onMainThread(() -> {
            Player player = Bukkit.getPlayerExact(name);
            if (player == null) return Replies.error(ErrorCode.PLAYER_NOT_FOUND, name + " isn't online");
            player.sendMessage(plugin.messages().render("private-message",
                    Messages.text("author", author), Messages.text("message", message)));
            return Replies.ok("Sent to " + player.getName());
        });
    }

    private CompletableFuture<JsonObject> setFeatures(JsonObject data) {
        boolean stream = data.has("console_stream") && data.get("console_stream").isJsonPrimitive()
                && data.get("console_stream").getAsBoolean();
        return onMainThread(() -> {
            plugin.setConsoleStream(stream && plugin.allowed("console"));
            return Replies.ok("ok");
        });
    }

    private CompletableFuture<JsonObject> setGroups(JsonObject data) {
        if (!plugin.allowed("roles", true) || plugin.permissions() == null) return forbidden("roles");
        String uuid = Envelope.str(data, "player_uuid");
        UUID id;
        try {
            id = UUID.fromString(uuid == null ? "" : uuid);
        } catch (IllegalArgumentException e) {
            return done(Replies.error(ErrorCode.INVALID, "bad player_uuid"));
        }
        List<String> add = strings(data, "add");
        List<String> remove = strings(data, "remove");
        return onMainThread(() -> {
            for (String g : remove) plugin.permissions().removeGroup(id, g);
            for (String g : add) plugin.permissions().addGroup(id, g);
            return Replies.ok("ok");
        });
    }

    private static List<String> strings(JsonObject data, String key) {
        List<String> out = new ArrayList<>();
        if (data.has(key) && data.get(key).isJsonArray()) {
            data.getAsJsonArray(key).forEach(e -> {
                if (e.isJsonPrimitive() && e.getAsString().matches("[A-Za-z0-9_.-]{1,64}")) out.add(e.getAsString());
            });
        }
        return out;
    }

    private CompletableFuture<JsonObject> onMainThread(Supplier<JsonObject> work) {
        CompletableFuture<JsonObject> future = new CompletableFuture<>();
        try {
            Bukkit.getScheduler().runTask(plugin, () -> {
                try {
                    future.complete(work.get());
                } catch (Exception e) {
                    future.complete(Replies.error(ErrorCode.INTERNAL, String.valueOf(e.getMessage())));
                }
            });
        } catch (Exception e) {
            future.complete(Replies.error(ErrorCode.INTERNAL, "server is shutting down"));
        }
        return future;
    }

    private CompletableFuture<JsonObject> forbidden(String capability) {
        return done(Replies.error(ErrorCode.FORBIDDEN,
                capability + " is disabled in plugins/MCBridge/config.yml (allow." + capability + ")"));
    }

    private static CompletableFuture<JsonObject> done(JsonObject reply) {
        return CompletableFuture.completedFuture(reply);
    }

    private static String actorName(JsonObject data) {
        return data.has("actor") && data.get("actor").isJsonObject()
                ? Envelope.str(data.getAsJsonObject("actor"), "name") : null;
    }
}
