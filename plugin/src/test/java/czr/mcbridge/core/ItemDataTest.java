package czr.mcbridge.core;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.util.Map;
import java.util.zip.GZIPOutputStream;

import static org.junit.jupiter.api.Assertions.assertTrue;

class ItemDataTest {
    static DataOutputStream d;
    static void tag(int t, String name) throws IOException { d.writeByte(t); d.writeUTF(name); }
    static void str(String n, String v) throws IOException { tag(8, n); d.writeUTF(v); }
    static void i(String n, int v) throws IOException { tag(3, n); d.writeInt(v); }
    static void b(String n, int v) throws IOException { tag(1, n); d.writeByte(v); }
    static void f(String n, float v) throws IOException { tag(5, n); d.writeFloat(v); }
    static void end() throws IOException { d.writeByte(0); }
    static void item(String id, int count, Integer slot, boolean sharp, Integer damage, String name) throws IOException {
        if (slot != null) b("Slot", slot);
        str("id", id); i("count", count);
        if (sharp || damage != null || name != null) {
            tag(10, "components");
            if (sharp) { tag(10, "minecraft:enchantments"); i("minecraft:sharpness", 5); end(); }
            if (damage != null) i("minecraft:damage", damage);
            if (name != null) str("minecraft:custom_name", name);
            end();
        }
    }
    static void check(boolean ok, String what) { assertTrue(ok, what); }

        @Test
    void readsOfflinePlayerFiles() throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        d = new DataOutputStream(new GZIPOutputStream(bytes));
        tag(10, "");
        f("Health", 13.3f); i("foodLevel", 15); i("XpLevel", 30); f("XpP", 0.5f); i("playerGameType", 0);
        str("Dimension", "minecraft:the_nether"); i("SelectedItemSlot", 2);
        tag(9, "Inventory"); d.writeByte(10); d.writeInt(4);
        item("minecraft:diamond_sword", 1, 0, true, 100, "{\"text\":\"Excal\",\"extra\":[{\"text\":\"ibur\"}]}"); end();
        item("minecraft:cobblestone", 64, 9, false, null, null); end();
        b("Slot", 10); str("id", "minecraft:red_shulker_box"); i("count", 1);
        tag(10, "components"); tag(9, "minecraft:container"); d.writeByte(10); d.writeInt(1);
        i("slot", 3); tag(10, "item"); str("id", "minecraft:diamond"); i("count", 9); end(); end();
        end(); end();
        item("minecraft:iron_helmet", 1, 103, false, null, null); end();
        tag(10, "equipment"); tag(10, "offhand"); str("id", "minecraft:shield"); i("count", 1); end(); end();
        tag(9, "EnderItems"); d.writeByte(10); d.writeInt(1); item("minecraft:ender_pearl", 16, 26, false, null, null); end();
        end();
        d.close();

        Map<String, Object> root = Nbt.readGzip(new ByteArrayInputStream(bytes.toByteArray()));
        ItemData.Materials m = new ItemData.Materials() {
            public boolean isBlock(String id) { return id.contains("cobble") || id.contains("shulker"); }
            public int maxDurability(String id) { return id.contains("sword") ? 1561 : 0; }
        };
        var inv = ItemData.inventory(root, m);
        var sword = inv.getAsJsonArray("hotbar").get(0).getAsJsonObject();
        check(sword.get("name").getAsString().equals("Excalibur"), "custom name json");
        check(sword.get("durability").getAsInt() == 1461, "durability");
        check(sword.getAsJsonArray("enchantments").get(0).getAsJsonObject().get("id").getAsString().equals("sharpness"), "enchant");
        check(inv.getAsJsonArray("main").get(0).getAsJsonObject().get("block").getAsBoolean(), "block");
        var shulker = inv.getAsJsonArray("main").get(1).getAsJsonObject();
        check(shulker.getAsJsonArray("contents").size() == 27 && shulker.getAsJsonArray("contents").get(3).getAsJsonObject().get("amount").getAsInt() == 9, "shulker contents");
        check(inv.getAsJsonArray("armor").get(0).getAsJsonObject().get("type").getAsString().equals("iron_helmet"), "old armor slot");
        check(inv.get("offhand").getAsJsonObject().get("type").getAsString().equals("shield"), "equipment offhand");
        check(inv.getAsJsonArray("ender_chest").get(26).getAsJsonObject().get("amount").getAsInt() == 16, "ender chest");
        check(inv.get("selected_slot").getAsInt() == 2, "selected");
        var v = ItemData.vitals(root);
        check(v.get("health").getAsDouble() == 13.5 && v.get("environment").getAsString().equals("nether") && v.get("world").getAsString().equals("world_nether"), "vitals");
        check("Plain".equals(ItemData.plainText("Plain")) && "Hi".equals(ItemData.plainText(Map.of("text", "Hi"))), "plain text");

    }
}
