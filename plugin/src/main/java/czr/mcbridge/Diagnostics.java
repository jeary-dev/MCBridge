package czr.mcbridge;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import czr.mcbridge.core.Replies;
import org.bukkit.Bukkit;
import org.bukkit.Chunk;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.entity.Entity;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Finds what is loading the server: chunks, entities and the busiest spots. Runs on the main thread. */
final class Diagnostics {
    private static final int TOP_CHUNKS = 5;
    private static final int TOP_TYPES = 8;

    private record Hotspot(String world, int x, int z, int entities, int tiles) {}

    private Diagnostics() {}

    static JsonObject collect() {
        JsonArray worlds = new JsonArray();
        Map<String, Integer> types = new HashMap<>();
        List<Hotspot> hotspots = new ArrayList<>();

        for (World world : Bukkit.getWorlds()) {
            Map<Long, int[]> perChunk = new HashMap<>();
            int entities = 0;
            for (Entity entity : world.getEntities()) {
                entities++;
                types.merge(String.valueOf(entity.getType()), 1, Integer::sum);
                Location at = entity.getLocation();
                perChunk.computeIfAbsent(key(at.getBlockX() >> 4, at.getBlockZ() >> 4), k -> new int[2])[0]++;
            }
            int tiles = 0;
            Chunk[] loaded = world.getLoadedChunks();
            for (Chunk chunk : loaded) {
                int count = chunk.getTileEntities(false).length;
                if (count > 0) {
                    tiles += count;
                    perChunk.computeIfAbsent(key(chunk.getX(), chunk.getZ()), k -> new int[2])[1] += count;
                }
            }
            for (Map.Entry<Long, int[]> e : perChunk.entrySet()) {
                long k = e.getKey();
                hotspots.add(new Hotspot(world.getName(), (int) (k >> 32), (int) k, e.getValue()[0], e.getValue()[1]));
            }

            JsonObject w = new JsonObject();
            w.addProperty("name", world.getName());
            w.addProperty("chunks", loaded.length);
            w.addProperty("entities", entities);
            w.addProperty("tile_entities", tiles);
            w.addProperty("players", world.getPlayers().size());
            worlds.add(w);
        }

        hotspots.sort((a, b) -> Integer.compare(b.entities() * 4 + b.tiles(), a.entities() * 4 + a.tiles()));
        JsonArray topChunks = new JsonArray();
        for (Hotspot h : hotspots.subList(0, Math.min(TOP_CHUNKS, hotspots.size()))) {
            JsonObject c = new JsonObject();
            c.addProperty("world", h.world());
            c.addProperty("x", h.x());
            c.addProperty("z", h.z());
            c.addProperty("entities", h.entities());
            c.addProperty("tile_entities", h.tiles());
            topChunks.add(c);
        }

        JsonArray topTypes = new JsonArray();
        types.entrySet().stream()
                .sorted((a, b) -> Integer.compare(b.getValue(), a.getValue()))
                .limit(TOP_TYPES)
                .forEach(e -> {
                    JsonObject t = new JsonObject();
                    t.addProperty("type", e.getKey());
                    t.addProperty("count", e.getValue());
                    topTypes.add(t);
                });

        JsonObject data = new JsonObject();
        data.add("worlds", worlds);
        data.add("top_chunks", topChunks);
        data.add("top_entities", topTypes);
        return Replies.ok("", data);
    }

    private static long key(int x, int z) {
        return ((long) x << 32) | (z & 0xffffffffL);
    }
}
