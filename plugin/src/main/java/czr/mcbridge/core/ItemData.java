package czr.mcbridge.core;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.util.List;
import java.util.Map;

/**
 * Turns items and player data read from NBT (offline players) into the same JSON the bot gets
 * for online players. Knows both the old (before 1.21.5) and new layouts of player files.
 */
public final class ItemData {
    public interface Materials {
        boolean isBlock(String id);

        int maxDurability(String id);
    }

    public static final int CONTAINER_SLOTS = 27;
    private static final String[] ARMOR_KEYS = {"head", "chest", "legs", "feet"};
    private static final int[] ARMOR_SLOTS = {103, 102, 101, 100};
    private static final String[] GAMEMODES = {"survival", "creative", "adventure", "spectator"};

    private ItemData() {}

    public static JsonElement item(Object tag, Materials materials, boolean withContents) {
        Map<String, Object> item = Nbt.map(tag);
        String id = Nbt.str(item.get("id"));
        if (id == null || id.isEmpty() || id.equals("minecraft:air")) return JsonNull.INSTANCE;
        int count = Nbt.integer(item.containsKey("count") ? item.get("count") : item.get("Count"), 1);
        if (count <= 0) return JsonNull.INSTANCE;
        String type = id.startsWith("minecraft:") ? id.substring(10) : id.replace(':', '_');
        Map<String, Object> components = Nbt.map(item.get("components"));

        JsonObject o = new JsonObject();
        o.addProperty("type", type);
        o.addProperty("amount", count);
        String name = plainText(components.get("minecraft:custom_name"));
        if (name != null && !name.isBlank()) o.addProperty("name", name.length() > 64 ? name.substring(0, 64) : name);
        JsonArray enchants = enchantments(components.get("minecraft:enchantments"));
        if (!enchants.isEmpty()) o.add("enchantments", enchants);
        if (components.containsKey("minecraft:stored_enchantments")
                || Boolean.TRUE.equals(asBool(components.get("minecraft:enchantment_glint_override")))) {
            o.addProperty("glint", true);
        }
        int max = materials.maxDurability(id);
        if (max > 0) {
            int damage = Nbt.integer(components.get("minecraft:damage"), 0);
            o.addProperty("durability", Math.max(0, max - damage));
            o.addProperty("max_durability", max);
        }
        if (materials.isBlock(id)) o.addProperty("block", true);
        if (withContents && type.endsWith("shulker_box")) {
            JsonArray contents = emptySlots(CONTAINER_SLOTS);
            for (Object entry : Nbt.list(components.get("minecraft:container"))) {
                Map<String, Object> e = Nbt.map(entry);
                int slot = Nbt.integer(e.get("slot"), -1);
                if (slot >= 0 && slot < CONTAINER_SLOTS) contents.set(slot, item(e.get("item"), materials, false));
            }
            o.add("contents", contents);
        }
        return o;
    }

    public static JsonObject inventory(Map<String, Object> root, Materials materials) {
        JsonArray hotbar = emptySlots(9);
        JsonArray main = emptySlots(27);
        JsonArray armor = emptySlots(4);
        JsonElement offhand = JsonNull.INSTANCE;
        for (Object entry : Nbt.list(root.get("Inventory"))) {
            Map<String, Object> e = Nbt.map(entry);
            int slot = Nbt.integer(e.get("Slot"), -999);
            JsonElement item = item(e, materials, true);
            if (slot >= 0 && slot < 9) hotbar.set(slot, item);
            else if (slot >= 9 && slot < 36) main.set(slot - 9, item);
            else if (slot == -106) offhand = item;
            else {
                for (int i = 0; i < 4; i++) if (ARMOR_SLOTS[i] == slot) armor.set(i, item);
            }
        }
        Map<String, Object> equipment = Nbt.map(root.get("equipment"));
        for (int i = 0; i < 4; i++) {
            if (equipment.containsKey(ARMOR_KEYS[i])) armor.set(i, item(equipment.get(ARMOR_KEYS[i]), materials, true));
        }
        if (equipment.containsKey("offhand")) offhand = item(equipment.get("offhand"), materials, true);

        JsonArray ender = emptySlots(CONTAINER_SLOTS);
        for (Object entry : Nbt.list(root.get("EnderItems"))) {
            Map<String, Object> e = Nbt.map(entry);
            int slot = Nbt.integer(e.get("Slot"), -1);
            if (slot >= 0 && slot < CONTAINER_SLOTS) ender.set(slot, item(e, materials, false));
        }

        JsonObject data = new JsonObject();
        data.add("armor", armor);
        data.add("offhand", offhand);
        data.add("hotbar", hotbar);
        data.add("main", main);
        data.add("ender_chest", ender);
        data.addProperty("selected_slot", Nbt.integer(root.get("SelectedItemSlot"), 0));
        return data;
    }

    public static JsonObject vitals(Map<String, Object> root) {
        JsonObject o = new JsonObject();
        Number health = Nbt.num(root.get("Health"));
        if (health != null) o.addProperty("health", Math.round(health.doubleValue() * 2) / 2.0);
        o.addProperty("max_health", 20.0);
        o.addProperty("food", Nbt.integer(root.get("foodLevel"), 20));
        Number saturation = Nbt.num(root.get("foodSaturationLevel"));
        if (saturation != null) o.addProperty("saturation", saturation.doubleValue());
        o.addProperty("level", Nbt.integer(root.get("XpLevel"), 0));
        Number progress = Nbt.num(root.get("XpP"));
        o.addProperty("exp", progress == null ? 0 : Math.max(0, Math.min(1, progress.doubleValue())));
        int mode = Nbt.integer(root.get("playerGameType"), -1);
        if (mode >= 0 && mode < GAMEMODES.length) o.addProperty("gamemode", GAMEMODES[mode]);
        String dimension = Nbt.str(root.get("Dimension"));
        if (dimension != null) {
            String env = switch (dimension) {
                case "minecraft:overworld" -> "normal";
                case "minecraft:the_nether" -> "nether";
                case "minecraft:the_end" -> "the_end";
                default -> "custom";
            };
            o.addProperty("environment", env);
            o.addProperty("world", switch (env) {
                case "normal" -> "world";
                case "nether" -> "world_nether";
                case "the_end" -> "world_the_end";
                default -> dimension.contains(":") ? dimension.substring(dimension.indexOf(':') + 1) : dimension;
            });
        }
        return o;
    }

    static JsonArray enchantments(Object tag) {
        Map<String, Object> map = Nbt.map(tag);
        if (map.containsKey("levels")) map = Nbt.map(map.get("levels"));
        JsonArray out = new JsonArray();
        for (Map.Entry<String, Object> e : map.entrySet()) {
            Number level = Nbt.num(e.getValue());
            if (level == null) continue;
            JsonObject en = new JsonObject();
            String key = e.getKey();
            en.addProperty("id", key.startsWith("minecraft:") ? key.substring(10) : key);
            en.addProperty("level", level.intValue());
            out.add(en);
        }
        return out;
    }

    public static String plainText(Object tag) {
        if (tag == null) return null;
        if (tag instanceof String s) {
            String t = s.strip();
            if (t.startsWith("{") || t.startsWith("[") || t.startsWith("\"")) {
                try {
                    return flatten(JsonParser.parseString(t));
                } catch (RuntimeException e) {
                    return s;
                }
            }
            return s;
        }
        StringBuilder out = new StringBuilder();
        if (tag instanceof List<?> list) {
            for (Object o : list) {
                String part = plainText(o);
                if (part != null) out.append(part);
            }
            return out.toString();
        }
        Map<String, Object> map = Nbt.map(tag);
        Object text = map.containsKey("text") ? map.get("text") : map.get("");
        if (text != null) out.append(text);
        else if (map.get("translate") instanceof String key) out.append(map.getOrDefault("fallback", key));
        for (Object extra : Nbt.list(map.get("extra"))) {
            String part = plainText(extra);
            if (part != null) out.append(part);
        }
        return out.toString();
    }

    private static String flatten(JsonElement e) {
        if (e == null || e.isJsonNull()) return "";
        if (e.isJsonPrimitive()) return e.getAsString();
        StringBuilder out = new StringBuilder();
        if (e.isJsonArray()) {
            e.getAsJsonArray().forEach(x -> out.append(flatten(x)));
            return out.toString();
        }
        JsonObject o = e.getAsJsonObject();
        if (o.has("text")) out.append(o.get("text").getAsString());
        else if (o.has("translate")) out.append(o.has("fallback") ? o.get("fallback").getAsString()
                : o.get("translate").getAsString());
        if (o.has("extra")) out.append(flatten(o.get("extra")));
        return out.toString();
    }

    private static Boolean asBool(Object o) {
        if (o instanceof Boolean b) return b;
        if (o instanceof Number n) return n.intValue() != 0;
        return null;
    }

    public static JsonArray emptySlots(int n) {
        JsonArray a = new JsonArray();
        for (int i = 0; i < n; i++) a.add(JsonNull.INSTANCE);
        return a;
    }
}
