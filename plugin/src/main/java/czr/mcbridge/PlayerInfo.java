package czr.mcbridge;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import czr.mcbridge.core.ItemData;
import czr.mcbridge.core.Nbt;
import czr.mcbridge.core.Replies;
import czr.mcbridge.core.Replies.ErrorCode;
import io.papermc.paper.advancement.AdvancementDisplay;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.OfflinePlayer;
import org.bukkit.Statistic;
import org.bukkit.World;
import org.bukkit.advancement.Advancement;
import org.bukkit.advancement.AdvancementProgress;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.block.ShulkerBox;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.PlayerInventory;
import org.bukkit.inventory.meta.BlockStateMeta;
import org.bukkit.inventory.meta.Damageable;
import org.bukkit.inventory.meta.EnchantmentStorageMeta;
import org.bukkit.inventory.meta.ItemMeta;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Reads a player's statistics, vitals, advancements and inventory for /stats, /player, /advancements
 * and /inventory. Online players are read live (main thread); offline players from their save files.
 */
final class PlayerInfo {
    private static final Statistic[] DISTANCE = {
            Statistic.WALK_ONE_CM, Statistic.SPRINT_ONE_CM, Statistic.CROUCH_ONE_CM, Statistic.SWIM_ONE_CM,
            Statistic.FLY_ONE_CM, Statistic.AVIATE_ONE_CM, Statistic.BOAT_ONE_CM, Statistic.HORSE_ONE_CM,
            Statistic.MINECART_ONE_CM, Statistic.PIG_ONE_CM, Statistic.STRIDER_ONE_CM, Statistic.CLIMB_ONE_CM,
            Statistic.FALL_ONE_CM, Statistic.WALK_ON_WATER_ONE_CM, Statistic.WALK_UNDER_WATER_ONE_CM};
    private static final List<String> TAB_ORDER = List.of("story", "nether", "end", "adventure", "husbandry");
    private static final DateTimeFormatter AWARDED = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss Z");
    private static final int MAX_RECENT = 7;
    private static final int MAX_REPLY_CHARS = 200_000;

    static final ItemData.Materials MATERIALS = new ItemData.Materials() {
        @Override
        public boolean isBlock(String id) {
            Material m = Material.matchMaterial(id);
            return m != null && m.isBlock();
        }

        @Override
        public int maxDurability(String id) {
            Material m = Material.matchMaterial(id);
            return m == null ? 0 : m.getMaxDurability();
        }
    };

    private PlayerInfo() {}

    static OfflinePlayer find(String name) {
        Player online = Bukkit.getPlayerExact(name);
        if (online != null) return online;
        OfflinePlayer cached = Bukkit.getOfflinePlayerIfCached(name);
        return cached != null && cached.hasPlayedBefore() ? cached : null;
    }

    static JsonObject notFound(String name) {
        return Replies.error(ErrorCode.PLAYER_NOT_FOUND, name + " hasn't played on this server");
    }

    static Path mainWorld() {
        return Bukkit.getWorlds().get(0).getWorldFolder().toPath();
    }

    static Path playerDataFile(OfflinePlayer p) {
        return mainWorld().resolve("playerdata").resolve(p.getUniqueId() + ".dat");
    }

    static Path advancementsFile(OfflinePlayer p) {
        return mainWorld().resolve("advancements").resolve(p.getUniqueId() + ".json");
    }

    static Map<String, Object> readPlayerData(Path file) {
        if (!Files.isRegularFile(file)) return null;
        try (InputStream in = Files.newInputStream(file)) {
            return Nbt.readGzip(in);
        } catch (IOException e) {
            return null;
        }
    }

    static JsonObject readJson(Path file) {
        if (!Files.isRegularFile(file)) return null;
        try {
            JsonElement e = JsonParser.parseString(Files.readString(file));
            return e.isJsonObject() ? e.getAsJsonObject() : null;
        } catch (IOException | RuntimeException e) {
            return null;
        }
    }

    private static JsonObject base(OfflinePlayer p) {
        JsonObject data = new JsonObject();
        data.addProperty("name", p.getName());
        data.addProperty("uuid", p.getUniqueId().toString());
        data.addProperty("online", p instanceof Player);
        return data;
    }

    static JsonObject stats(String name) {
        OfflinePlayer p = find(name);
        if (p == null) return notFound(name);
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

        JsonObject data = base(p);
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
            int done = 0;
            int total = 0;
            Iterator<Advancement> it = Bukkit.advancementIterator();
            while (it.hasNext()) {
                Advancement a = it.next();
                if (a.getDisplay() == null) continue;
                total++;
                if (online.getAdvancementProgress(a).isDone()) done++;
            }
            JsonObject adv = new JsonObject();
            adv.addProperty("done", done);
            adv.addProperty("total", total);
            data.add("advancements", adv);
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

    static JsonObject playerInfo(OfflinePlayer p, Map<String, Object> saved) {
        JsonObject data = base(p);
        data.addProperty("op", p.isOp());
        data.addProperty("whitelisted", p.isWhitelisted());
        data.addProperty("banned", p.isBanned());
        data.addProperty("first_played", p.getFirstPlayed());
        data.addProperty("last_played", p.getLastPlayed());
        if (p instanceof Player online) {
            data.addProperty("health", Math.round(online.getHealth() * 2) / 2.0);
            AttributeInstance max = online.getAttribute(Attribute.MAX_HEALTH);
            data.addProperty("max_health", max == null ? 20.0 : max.getValue());
            data.addProperty("food", online.getFoodLevel());
            data.addProperty("saturation", online.getSaturation());
            data.addProperty("level", online.getLevel());
            data.addProperty("exp", Math.max(0, Math.min(1, online.getExp())));
            World world = online.getWorld();
            data.addProperty("world", world.getName());
            data.addProperty("environment", world.getEnvironment().name().toLowerCase());
            data.addProperty("gamemode", online.getGameMode().name().toLowerCase());
            data.addProperty("ping", online.getPing());
        } else if (saved != null) {
            ItemData.vitals(saved).entrySet().forEach(e -> data.add(e.getKey(), e.getValue()));
        }
        return Replies.ok("", data);
    }

    private record Award(boolean done, long ts) {}

    private interface ProgressSource {
        Award of(Advancement advancement);
    }

    static JsonObject advancementsOnline(Player p) {
        return advancements(p, a -> {
            AdvancementProgress progress = p.getAdvancementProgress(a);
            long latest = 0;
            for (String criterion : progress.getAwardedCriteria()) {
                Date date = progress.getDateAwarded(criterion);
                if (date != null) latest = Math.max(latest, date.getTime());
            }
            return new Award(progress.isDone(), latest);
        });
    }

    static JsonObject advancementsOffline(OfflinePlayer p, JsonObject saved) {
        JsonObject file = saved == null ? new JsonObject() : saved;
        return advancements(p, a -> {
            JsonElement entry = file.get(a.getKey().toString());
            if (entry == null || !entry.isJsonObject()) return new Award(false, 0);
            JsonObject o = entry.getAsJsonObject();
            boolean done = o.has("done") && o.get("done").isJsonPrimitive() && o.get("done").getAsBoolean();
            long latest = 0;
            if (o.has("criteria") && o.get("criteria").isJsonObject()) {
                for (Map.Entry<String, JsonElement> c : o.getAsJsonObject("criteria").entrySet()) {
                    try {
                        latest = Math.max(latest, OffsetDateTime.parse(c.getValue().getAsString(), AWARDED)
                                .toInstant().toEpochMilli());
                    } catch (RuntimeException ignored) {
                    }
                }
            }
            return new Award(done, latest);
        });
    }

    private static String tabOf(NamespacedKey key) {
        String path = key.getKey();
        int slash = path.indexOf('/');
        return key.getNamespace() + ":" + (slash < 0 ? path : path.substring(0, slash));
    }

    private static String pretty(String tab) {
        String s = tab.substring(tab.indexOf(':') + 1).replace('_', ' ');
        return s.isEmpty() ? tab : Character.toUpperCase(s.charAt(0)) + s.substring(1);
    }

    private static JsonObject advancements(OfflinePlayer p, ProgressSource source) {
        Map<String, int[]> tabs = new LinkedHashMap<>();
        Map<String, String> tabTitles = new HashMap<>();
        List<JsonObject> completed = new ArrayList<>();
        int done = 0;
        int total = 0;
        Iterator<Advancement> it = Bukkit.advancementIterator();
        while (it.hasNext()) {
            Advancement a = it.next();
            AdvancementDisplay display = a.getDisplay();
            if (display == null || a.getKey().getKey().startsWith("recipes/")) continue;
            String tab = tabOf(a.getKey());
            int[] counts = tabs.computeIfAbsent(tab, t -> new int[2]);
            counts[1]++;
            total++;
            if (a.getKey().getKey().endsWith("/root")) tabTitles.put(tab, MCBridge.plain(display.title()));
            Award award = source.of(a);
            if (!award.done()) continue;
            counts[0]++;
            done++;
            JsonObject r = new JsonObject();
            r.addProperty("key", a.getKey().toString());
            r.addProperty("title", MCBridge.plain(display.title()));
            r.addProperty("tab", tab + "/root");
            r.addProperty("frame", display.frame().name().toLowerCase());
            r.addProperty("ts", award.ts());
            completed.add(r);
        }
        List<String> order = new ArrayList<>(tabs.keySet());
        order.sort((x, y) -> {
            int ix = x.startsWith("minecraft:") ? TAB_ORDER.indexOf(x.substring(10)) : -1;
            int iy = y.startsWith("minecraft:") ? TAB_ORDER.indexOf(y.substring(10)) : -1;
            if (ix < 0) ix = 100;
            if (iy < 0) iy = 100;
            return ix != iy ? Integer.compare(ix, iy) : x.compareTo(y);
        });
        JsonArray tabList = new JsonArray();
        for (String tab : order) {
            JsonObject t = new JsonObject();
            t.addProperty("id", tab + "/root");
            t.addProperty("title", tabTitles.getOrDefault(tab, pretty(tab)));
            t.addProperty("done", tabs.get(tab)[0]);
            t.addProperty("total", tabs.get(tab)[1]);
            tabList.add(t);
        }
        completed.sort((x, y) -> Long.compare(y.get("ts").getAsLong(), x.get("ts").getAsLong()));
        JsonArray recent = new JsonArray();
        for (JsonObject r : completed.subList(0, Math.min(MAX_RECENT, completed.size()))) {
            String tab = r.get("tab").getAsString();
            String key = tab.substring(0, tab.length() - 5);
            r.addProperty("tab_title", tabTitles.getOrDefault(key, pretty(key)));
            recent.add(r);
        }
        JsonObject data = base(p);
        data.addProperty("done", done);
        data.addProperty("total", total);
        data.add("tabs", tabList);
        data.add("recent", recent);
        return Replies.ok("", data);
    }

    static JsonObject inventoryOnline(Player p) {
        PlayerInventory inv = p.getInventory();
        JsonArray armor = new JsonArray();
        armor.add(item(inv.getHelmet(), true));
        armor.add(item(inv.getChestplate(), true));
        armor.add(item(inv.getLeggings(), true));
        armor.add(item(inv.getBoots(), true));
        ItemStack[] storage = inv.getStorageContents();
        JsonArray hotbar = new JsonArray();
        JsonArray main = new JsonArray();
        for (int i = 0; i < storage.length && i < 36; i++) {
            (i < 9 ? hotbar : main).add(item(storage[i], true));
        }
        JsonArray ender = new JsonArray();
        for (ItemStack stack : p.getEnderChest().getContents()) ender.add(item(stack, false));
        JsonObject data = base(p);
        data.add("armor", armor);
        data.add("offhand", item(inv.getItemInOffHand(), true));
        data.add("hotbar", hotbar);
        data.add("main", main);
        data.add("ender_chest", ender);
        data.addProperty("selected_slot", inv.getHeldItemSlot());
        return Replies.ok("", trim(data));
    }

    static JsonObject inventoryOffline(OfflinePlayer p, Map<String, Object> saved) {
        if (saved == null) {
            return Replies.error(ErrorCode.PLAYER_NOT_FOUND, "No saved inventory for " + p.getName());
        }
        JsonObject data = base(p);
        ItemData.inventory(saved, MATERIALS).entrySet().forEach(e -> data.add(e.getKey(), e.getValue()));
        return Replies.ok("", trim(data));
    }

    private static JsonObject trim(JsonObject data) {
        if (data.toString().length() <= MAX_REPLY_CHARS) return data;
        for (String section : new String[]{"hotbar", "main"}) {
            for (JsonElement e : data.getAsJsonArray(section)) {
                if (e.isJsonObject()) e.getAsJsonObject().remove("contents");
            }
        }
        return data;
    }

    private static JsonElement item(ItemStack stack, boolean withContents) {
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
        if (meta instanceof EnchantmentStorageMeta) o.addProperty("glint", true);
        short max = stack.getType().getMaxDurability();
        if (max > 0 && meta instanceof Damageable damageable) {
            o.addProperty("durability", max - damageable.getDamage());
            o.addProperty("max_durability", max);
        }
        if (stack.getType().isBlock()) o.addProperty("block", true);
        if (withContents && meta instanceof BlockStateMeta bsm && bsm.hasBlockState()
                && bsm.getBlockState() instanceof ShulkerBox box) {
            JsonArray contents = new JsonArray();
            for (ItemStack inside : box.getInventory().getContents()) contents.add(item(inside, false));
            o.add("contents", contents);
        }
        return o;
    }
}
