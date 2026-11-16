package czr.mcbridge;

import com.google.gson.JsonArray;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import czr.mcbridge.core.Replies;
import czr.mcbridge.core.Replies.ErrorCode;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.OfflinePlayer;
import org.bukkit.Statistic;
import org.bukkit.advancement.Advancement;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.PlayerInventory;
import org.bukkit.inventory.meta.Damageable;
import org.bukkit.inventory.meta.ItemMeta;

import java.util.Iterator;
import java.util.Map;

/** Reads a player's Minecraft statistics and inventory for /stats and /inventory. Runs on the main thread. */
final class PlayerInfo {
    private static final Statistic[] DISTANCE = {
            Statistic.WALK_ONE_CM, Statistic.SPRINT_ONE_CM, Statistic.CROUCH_ONE_CM, Statistic.SWIM_ONE_CM,
            Statistic.FLY_ONE_CM, Statistic.AVIATE_ONE_CM, Statistic.BOAT_ONE_CM, Statistic.HORSE_ONE_CM,
            Statistic.MINECART_ONE_CM, Statistic.PIG_ONE_CM, Statistic.STRIDER_ONE_CM, Statistic.CLIMB_ONE_CM,
            Statistic.FALL_ONE_CM, Statistic.WALK_ON_WATER_ONE_CM, Statistic.WALK_UNDER_WATER_ONE_CM};

    private PlayerInfo() {}

    static OfflinePlayer find(String name) {
        Player online = Bukkit.getPlayerExact(name);
        if (online != null) return online;
        OfflinePlayer cached = Bukkit.getOfflinePlayerIfCached(name);
        return cached != null && cached.hasPlayedBefore() ? cached : null;
    }

    static JsonObject stats(String name) {
        OfflinePlayer p = find(name);
        if (p == null) return Replies.error(ErrorCode.PLAYER_NOT_FOUND, name + " hasn't played on this server");
        JsonObject stats = new JsonObject();
        put(stats, "play_time_ticks", p, Statistic.PLAY_ONE_MINUTE);
        put(stats, "deaths", p, Statistic.DEATHS);
        put(stats, "mob_kills", p, Statistic.MOB_KILLS);
        put(stats, "player_kills", p, Statistic.PLAYER_KILLS);
        put(stats, "jumps", p, Statistic.JUMP);
        put(stats, "damage_dealt", p, Statistic.DAMAGE_DEALT);
        put(stats, "damage_taken", p, Statistic.DAMAGE_TAKEN);
        put(stats, "fish_caught", p, Statistic.FISH_CAUGHT);
        put(stats, "animals_bred", p, Statistic.ANIMALS_BRED);
        put(stats, "villager_trades", p, Statistic.TRADED_WITH_VILLAGER);
        put(stats, "items_enchanted", p, Statistic.ITEM_ENCHANTED);
        long distance = 0;
        for (Statistic s : DISTANCE) distance += read(p, s);
        stats.addProperty("distance_cm", distance);

        JsonObject data = new JsonObject();
        data.addProperty("name", p.getName());
        data.addProperty("uuid", p.getUniqueId().toString());
        data.addProperty("online", p instanceof Player);
        if (p instanceof Player online) {
            long mined = 0;
            for (Material m : Material.values()) {
                if (m.isBlock() && !m.isLegacy()) {
                    try {
                        mined += online.getStatistic(Statistic.MINE_BLOCK, m);
                    } catch (IllegalArgumentException ignored) {
                    }
                }
            }
            stats.addProperty("blocks_mined", mined);
            data.add("advancements", advancements(online));
        }
        data.add("stats", stats);
        return Replies.ok("", data);
    }

    private static void put(JsonObject out, String key, OfflinePlayer p, Statistic s) {
        out.addProperty(key, read(p, s));
    }

    private static long read(OfflinePlayer p, Statistic s) {
        try {
            return p.getStatistic(s);
        } catch (IllegalArgumentException | UnsupportedOperationException e) {
            return 0;
        }
    }

    private static JsonObject advancements(Player p) {
        int done = 0;
        int total = 0;
        Iterator<Advancement> it = Bukkit.advancementIterator();
        while (it.hasNext()) {
            Advancement a = it.next();
            if (a.getDisplay() == null) continue;
            total++;
            if (p.getAdvancementProgress(a).isDone()) done++;
        }
        JsonObject o = new JsonObject();
        o.addProperty("done", done);
        o.addProperty("total", total);
        return o;
    }

    static JsonObject inventory(String name) {
        Player p = Bukkit.getPlayerExact(name);
        if (p == null) {
            return Replies.error(ErrorCode.PLAYER_NOT_FOUND, name + " isn't online. /inventory works for online players");
        }
        PlayerInventory inv = p.getInventory();
        JsonArray armor = new JsonArray();
        armor.add(item(inv.getHelmet()));
        armor.add(item(inv.getChestplate()));
        armor.add(item(inv.getLeggings()));
        armor.add(item(inv.getBoots()));
        ItemStack[] storage = inv.getStorageContents();
        JsonArray hotbar = new JsonArray();
        JsonArray main = new JsonArray();
        for (int i = 0; i < storage.length; i++) {
            (i < 9 ? hotbar : main).add(item(storage[i]));
        }
        JsonObject data = new JsonObject();
        data.addProperty("name", p.getName());
        data.addProperty("uuid", p.getUniqueId().toString());
        data.add("armor", armor);
        data.add("offhand", item(inv.getItemInOffHand()));
        data.add("hotbar", hotbar);
        data.add("main", main);
        return Replies.ok("", data);
    }

    private static com.google.gson.JsonElement item(ItemStack stack) {
        if (stack == null || stack.getType().isAir() || stack.getAmount() <= 0) return JsonNull.INSTANCE;
        JsonObject o = new JsonObject();
        o.addProperty("type", stack.getType().getKey().getKey());
        o.addProperty("amount", stack.getAmount());
        ItemMeta meta = stack.hasItemMeta() ? stack.getItemMeta() : null;
        if (meta != null && meta.hasDisplayName()) {
            o.addProperty("name", MCBridge.plain(meta.displayName()));
        }
        JsonArray enchants = new JsonArray();
        for (Map.Entry<Enchantment, Integer> e : stack.getEnchantments().entrySet()) {
            JsonObject en = new JsonObject();
            en.addProperty("id", e.getKey().getKey().getKey());
            en.addProperty("level", e.getValue());
            enchants.add(en);
        }
        if (!enchants.isEmpty()) o.add("enchantments", enchants);
        short max = stack.getType().getMaxDurability();
        if (max > 0 && meta instanceof Damageable damageable) {
            o.addProperty("durability", max - damageable.getDamage());
            o.addProperty("max_durability", max);
        }
        return o;
    }
}
