package czr.mcbridge.core;

import com.google.gson.JsonObject;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.net.http.WebSocketHandshakeException;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Keeps one WebSocket connection to the mcbridge bot alive.
 *
 * <ul>
 *   <li>connects with the server token, sends {@code hello}, waits for {@code welcome}</li>
 *   <li>sends heartbeats every interval the bot asks for</li>
 *   <li>runs incoming {@code cmd.*} through a {@link CommandHandler} and sends exactly one reply</li>
 *   <li>reconnects with exponential backoff (1s, 2s, 4s... max 60s, + jitter) if the connection drops</li>
 * </ul>
 *
 * Contains no Minecraft code, so it can be tested on its own and reused for other platforms.
 */
public final class BridgeClient {
    public enum State { DISCONNECTED, CONNECTING, CONNECTED, STOPPED }

    private static final int MAX_BACKOFF_S = 60;

    private final URI uri;
    private final String token;
    private final JsonObject hello;
    private final HeartbeatSource heartbeats;
    private final CommandHandler commands;
    private final Logger log;
    private final HttpClient http;
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "mcbridge-client");
        t.setDaemon(true);
        return t;
    });

    private volatile State state = State.DISCONNECTED;
    private volatile WebSocket socket;
    private volatile String serverId;
    private volatile JsonObject features = new JsonObject();
    private volatile Consumer<BridgeClient> onWelcome = c -> {};
    private ScheduledFuture<?> heartbeatTask;
    private CompletableFuture<?> sendChain = CompletableFuture.completedFuture(null);
    private int attempt;

    public BridgeClient(URI uri, String token, JsonObject hello, HeartbeatSource heartbeats,
                        CommandHandler commands, Logger log) {
        this.uri = uri;
        this.token = token;
        this.hello = hello;
        this.heartbeats = heartbeats;
        this.commands = commands;
        this.log = log;
        this.http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();
    }

    public void onWelcome(Consumer<BridgeClient> callback) {
        this.onWelcome = callback;
    }

    public void start() {
        scheduler.execute(this::connect);
    }

    public State state() { return state; }
    public boolean isConnected() { return state == State.CONNECTED; }
    public String serverId() { return serverId; }

    public boolean featureEnabled(String name) {
        JsonObject f = features;
        return f.has(name) && f.get(name).isJsonPrimitive() && f.get(name).getAsBoolean();
    }

    public void sendEvent(String type, JsonObject data) {
        if (state == State.CONNECTED) {
            send(Envelope.of(type, data));
        }
    }

    public void stop(Envelope finalMessage, Duration timeout) {
        boolean wasConnected = state == State.CONNECTED;
        state = State.STOPPED;
        WebSocket ws = socket;
        try {
            if (ws != null && wasConnected && finalMessage != null) {
                send(finalMessage).get(timeout.toMillis(), TimeUnit.MILLISECONDS);
            }
            if (ws != null) {
                ws.sendClose(WebSocket.NORMAL_CLOSURE, "server stopping")
                        .get(timeout.toMillis(), TimeUnit.MILLISECONDS);
            }
        } catch (Exception e) {
            log.log(Level.FINE, "error while closing", e);
        } finally {
            scheduler.shutdownNow();
        }
    }

    private void connect() {
        if (state == State.STOPPED) return;
        state = State.CONNECTING;
        http.newWebSocketBuilder()
                .header("Authorization", "Bearer " + token)
                .connectTimeout(Duration.ofSeconds(10))
                .buildAsync(uri, new Listener())
                .whenComplete((ws, err) -> {
                    if (err != null) {
                        Throwable cause = err.getCause() != null ? err.getCause() : err;
                        if (cause instanceof WebSocketHandshakeException hs && hs.getResponse().statusCode() == 401) {
                            log.severe("The bot rejected our token. Check 'token' in plugins/MCBridge/config.yml.");
                            attempt = Math.max(attempt, 6);
                        } else {
                            log.warning("Can't reach the mcbridge bot at " + uri + ": " + cause.getMessage());
                        }
                        scheduleReconnect();
                        return;
                    }
                    socket = ws;
                    send(Envelope.of("hello", hello));
                });
    }

    private void scheduleReconnect() {
        if (state == State.STOPPED || scheduler.isShutdown()) return;
        state = State.DISCONNECTED;
        long delayMs = Math.min(MAX_BACKOFF_S, 1L << Math.min(attempt, 6)) * 1000L
                + ThreadLocalRandom.current().nextLong(1000);
        attempt++;
        log.info("Reconnecting to the bot in " + (delayMs / 1000) + "s...");
        scheduler.schedule(this::connect, delayMs, TimeUnit.MILLISECONDS);
    }

    private synchronized void onDisconnected(WebSocket ws, String why) {
        if (ws != socket) return;
        socket = null;
        if (heartbeatTask != null) heartbeatTask.cancel(false);
        if (state == State.STOPPED) return;
        log.warning("Disconnected from the bot (" + why + ")");
        scheduleReconnect();
    }

    private synchronized CompletableFuture<?> send(Envelope env) {
        WebSocket ws = socket;
        if (ws == null) return CompletableFuture.completedFuture(null);
        String text = env.toJson();
        sendChain = sendChain
                .handle((ok, err) -> null)
                .thenCompose(v -> ws.sendText(text, true))
                .exceptionally(err -> {
                    log.log(Level.FINE, "send failed", err);
                    return null;
                });
        return sendChain;
    }

    private void handle(String text) {
        Envelope env;
        try {
            env = Envelope.parse(text);
        } catch (ProtocolException e) {
            log.warning("Bot sent a bad message: " + e.getMessage());
            return;
        }

        if (env.type().equals("welcome")) {
            onWelcomeMessage(env.data());
        } else if (env.type().startsWith("cmd.")) {
            CompletableFuture<JsonObject> result;
            try {
                result = commands.handle(env);
            } catch (Exception e) {
                result = CompletableFuture.completedFuture(
                        Replies.error(Replies.ErrorCode.INTERNAL, String.valueOf(e.getMessage())));
            }
            result.exceptionally(e -> Replies.error(Replies.ErrorCode.INTERNAL, String.valueOf(e.getMessage())))
                  .thenAccept(data -> send(Envelope.reply(env.id(), data)));
        }
    }

    private synchronized void onWelcomeMessage(JsonObject data) {
        serverId = Envelope.str(data, "server_id");
        features = data.has("features") && data.get("features").isJsonObject()
                ? data.getAsJsonObject("features") : new JsonObject();
        int interval = data.has("heartbeat_interval_s") ? Math.max(1, data.get("heartbeat_interval_s").getAsInt()) : 10;

        state = State.CONNECTED;
        attempt = 0;
        log.info("Connected to the mcbridge bot as " + serverId);

        if (heartbeatTask != null) heartbeatTask.cancel(false);
        heartbeatTask = scheduler.scheduleAtFixedRate(() -> {
            try {
                send(Envelope.of("heartbeat", heartbeats.snapshot()));
            } catch (Exception e) {
                log.log(Level.WARNING, "heartbeat failed", e);
            }
        }, 0, interval, TimeUnit.SECONDS);

        try {
            onWelcome.accept(this);
        } catch (Exception e) {
            log.log(Level.WARNING, "onWelcome callback failed", e);
        }
    }

    private final class Listener implements WebSocket.Listener {
        private final StringBuilder buffer = new StringBuilder();

        @Override
        public void onOpen(WebSocket ws) {
            ws.request(1);
        }

        @Override
        public CompletionStage<?> onText(WebSocket ws, CharSequence data, boolean last) {
            buffer.append(data);
            if (last) {
                String text = buffer.toString();
                buffer.setLength(0);
                handle(text);
            }
            ws.request(1);
            return null;
        }

        @Override
        public CompletionStage<?> onClose(WebSocket ws, int statusCode, String reason) {
            onDisconnected(ws, "closed " + statusCode + (reason.isEmpty() ? "" : ": " + reason));
            return null;
        }

        @Override
        public void onError(WebSocket ws, Throwable error) {
            onDisconnected(ws, String.valueOf(error.getMessage()));
        }
    }
}
