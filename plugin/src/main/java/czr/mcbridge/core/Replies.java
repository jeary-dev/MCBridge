package czr.mcbridge.core;

import com.google.gson.JsonObject;

/** Builds the `data` of a reply message. */
public final class Replies {
    public enum ErrorCode { UNKNOWN_COMMAND, FORBIDDEN, INVALID, PLAYER_NOT_FOUND, INTERNAL }

    private Replies() {}

    public static JsonObject ok(String result) {
        JsonObject o = new JsonObject();
        o.addProperty("ok", true);
        o.addProperty("result", result == null ? "" : result);
        return o;
    }

    public static JsonObject ok(String result, JsonObject data) {
        JsonObject o = ok(result);
        if (data != null) o.add("data", data);
        return o;
    }

    public static JsonObject error(ErrorCode code, String message) {
        JsonObject err = new JsonObject();
        err.addProperty("code", code.name());
        err.addProperty("message", message == null ? code.name() : message);
        JsonObject o = new JsonObject();
        o.addProperty("ok", false);
        o.add("error", err);
        return o;
    }
}
