package czr.mcbridge.core;

import com.google.gson.JsonObject;

import java.util.concurrent.CompletableFuture;

/**
 * Runs a cmd.* from the bot. Must complete with reply data built by {@link Replies}
 * (never throw: the bot is waiting for exactly one reply).
 */
@FunctionalInterface
public interface CommandHandler {
    CompletableFuture<JsonObject> handle(Envelope command);
}
