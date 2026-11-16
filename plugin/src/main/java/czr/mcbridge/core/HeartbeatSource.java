package czr.mcbridge.core;

import com.google.gson.JsonObject;

/** Supplies the `data` for each heartbeat (TPS, players, memory...). Called off the main thread. */
@FunctionalInterface
public interface HeartbeatSource {
    JsonObject snapshot();
}
