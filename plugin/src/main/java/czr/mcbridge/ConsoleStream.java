package czr.mcbridge;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.core.LogEvent;
import org.apache.logging.log4j.core.Logger;
import org.apache.logging.log4j.core.appender.AbstractAppender;
import org.apache.logging.log4j.core.config.Property;
import org.bukkit.Bukkit;
import org.bukkit.scheduler.BukkitTask;

import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicInteger;

/** Copies the server console to Discord's console channel, in batches. Only runs when allow.console is on. */
final class ConsoleStream extends AbstractAppender {
    private static final int MAX_QUEUED = 5000;
    private static final int MAX_PER_BATCH = 200;
    private static final int MAX_LINE = 2000;
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("HH:mm:ss").withZone(ZoneId.systemDefault());

    private final MCBridge plugin;
    private final ConcurrentLinkedQueue<String> queue = new ConcurrentLinkedQueue<>();
    private final AtomicInteger size = new AtomicInteger();
    private BukkitTask flusher;

    ConsoleStream(MCBridge plugin) {
        super("MCBridgeConsole", null, null, true, Property.EMPTY_ARRAY);
        this.plugin = plugin;
    }

    synchronized void enable() {
        if (flusher != null) return;
        start();
        ((Logger) LogManager.getRootLogger()).addAppender(this);
        flusher = Bukkit.getScheduler().runTaskTimerAsynchronously(plugin, this::flush, 20L, 20L);
    }

    synchronized void disable() {
        if (flusher == null) return;
        ((Logger) LogManager.getRootLogger()).removeAppender(this);
        flusher.cancel();
        flusher = null;
        stop();
        queue.clear();
        size.set(0);
    }

    @Override
    public void append(LogEvent event) {
        if (size.get() >= MAX_QUEUED) return;
        String message = event.getMessage() == null ? "" : event.getMessage().getFormattedMessage();
        StringBuilder line = new StringBuilder()
                .append('[').append(TIME.format(Instant.ofEpochMilli(event.getTimeMillis()))).append(' ')
                .append(event.getLevel().name()).append("]: ").append(message);
        if (event.getThrown() != null) line.append("\n").append(event.getThrown());
        String text = line.length() > MAX_LINE ? line.substring(0, MAX_LINE) : line.toString();
        queue.add(text);
        size.incrementAndGet();
    }

    private void flush() {
        if (queue.isEmpty()) return;
        JsonArray lines = new JsonArray();
        String line;
        while (lines.size() < MAX_PER_BATCH && (line = queue.poll()) != null) {
            size.decrementAndGet();
            lines.add(line);
        }
        JsonObject data = new JsonObject();
        data.add("lines", lines);
        plugin.sendEvent("event.console", data);
    }
}
