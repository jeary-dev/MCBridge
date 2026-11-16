package czr.mcbridge.core;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;

import java.nio.charset.StandardCharsets;
import java.util.UUID;

/**
 * One protocol message (see docs/PROTOCOL.md). Immutable.
 * Every frame on the WebSocket is exactly one envelope.
 */
public final class Envelope {
    public static final int VERSION = 1;
    public static final int MAX_FRAME_BYTES = 256 * 1024;
    private static final Gson GSON = new Gson();

    private final String type;
    private final String id;
    private final long ts;
    private final String replyTo;
    private final JsonObject data;

    private Envelope(String type, String id, long ts, String replyTo, JsonObject data) {
        this.type = type;
        this.id = id;
        this.ts = ts;
        this.replyTo = replyTo;
        this.data = data;
    }

    public static Envelope of(String type, JsonObject data) {
        return new Envelope(type, UUID.randomUUID().toString(), System.currentTimeMillis(), null,
                data == null ? new JsonObject() : data);
    }

    public static Envelope reply(String replyTo, JsonObject data) {
        return new Envelope("reply", UUID.randomUUID().toString(), System.currentTimeMillis(), replyTo, data);
    }

    public String type() { return type; }
    public String id() { return id; }
    public long ts() { return ts; }
    public String replyTo() { return replyTo; }
    public JsonObject data() { return data; }

    public String toJson() {
        JsonObject root = new JsonObject();
        root.addProperty("v", VERSION);
        root.addProperty("type", type);
        root.addProperty("id", id);
        root.addProperty("ts", ts);
        root.add("reply_to", replyTo == null ? JsonNull.INSTANCE : new JsonPrimitive(replyTo));
        root.add("data", data);
        return GSON.toJson(root);
    }

    public static Envelope parse(String text) throws ProtocolException {
        if (text.getBytes(StandardCharsets.UTF_8).length > MAX_FRAME_BYTES) {
            throw new ProtocolException("message is larger than 256 KiB");
        }
        JsonElement el;
        try {
            el = JsonParser.parseString(text);
        } catch (JsonParseException e) {
            throw new ProtocolException("not valid JSON");
        }
        if (!el.isJsonObject()) throw new ProtocolException("envelope must be a JSON object");
        JsonObject o = el.getAsJsonObject();

        if (!isNumber(o, "v") || o.get("v").getAsInt() != VERSION) {
            throw new ProtocolException("unsupported or missing protocol version");
        }
        if (!isString(o, "type") || !isString(o, "id")) throw new ProtocolException("missing type or id");
        if (!isNumber(o, "ts")) throw new ProtocolException("missing ts");
        if (!o.has("data") || !o.get("data").isJsonObject()) throw new ProtocolException("data must be an object");

        String replyTo = null;
        if (o.has("reply_to") && !o.get("reply_to").isJsonNull()) {
            if (!isString(o, "reply_to")) throw new ProtocolException("reply_to must be a string or null");
            replyTo = o.get("reply_to").getAsString();
        }
        return new Envelope(o.get("type").getAsString(), o.get("id").getAsString(),
                o.get("ts").getAsLong(), replyTo, o.getAsJsonObject("data"));
    }

    public static String str(JsonObject obj, String key) {
        return isString(obj, key) ? obj.get(key).getAsString() : null;
    }

    private static boolean isString(JsonObject o, String key) {
        return o.has(key) && o.get(key).isJsonPrimitive() && o.getAsJsonPrimitive(key).isString();
    }

    private static boolean isNumber(JsonObject o, String key) {
        return o.has(key) && o.get(key).isJsonPrimitive() && o.getAsJsonPrimitive(key).isNumber();
    }
}
