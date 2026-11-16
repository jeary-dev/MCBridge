package czr.mcbridge.core;

import com.google.gson.JsonObject;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class EnvelopeTest {
    @Test
    void roundTrip() throws Exception {
        JsonObject data = new JsonObject();
        data.addProperty("reason", "shutdown");
        Envelope out = Envelope.of("event.server_stop", data);

        Envelope back = Envelope.parse(out.toJson());
        assertEquals("event.server_stop", back.type());
        assertEquals(out.id(), back.id());
        assertNull(back.replyTo());
        assertEquals("shutdown", Envelope.str(back.data(), "reason"));
    }

    @Test
    void replyKeepsReplyTo() throws Exception {
        Envelope reply = Envelope.reply("abc-123", Replies.ok("done"));
        Envelope back = Envelope.parse(reply.toJson());
        assertEquals("reply", back.type());
        assertEquals("abc-123", back.replyTo());
        assertTrue(back.data().get("ok").getAsBoolean());
    }

    @Test
    void errorReplyShape() {
        JsonObject err = Replies.error(Replies.ErrorCode.FORBIDDEN, "nope");
        assertFalse(err.get("ok").getAsBoolean());
        assertEquals("FORBIDDEN", err.getAsJsonObject("error").get("code").getAsString());
    }

    @Test
    void parsesMessagesFromTheBot() throws Exception {
        String json = "{\"v\":1,\"type\":\"cmd.whitelist\",\"id\":\"x\",\"ts\":1,\"reply_to\":null,"
                + "\"data\":{\"actor\":{\"discord_id\":\"1\",\"name\":\"corbyn\"},\"action\":\"add\",\"player_name\":\"Steve\"}}";
        Envelope env = Envelope.parse(json);
        assertEquals("cmd.whitelist", env.type());
        assertEquals("Steve", Envelope.str(env.data(), "player_name"));
    }

    @Test
    void unknownFieldsAreIgnored() throws Exception {
        String json = "{\"v\":1,\"type\":\"welcome\",\"id\":\"x\",\"ts\":1,\"data\":{},\"something_new\":true}";
        assertEquals("welcome", Envelope.parse(json).type());
    }

    @Test
    void rejectsGarbage() {
        assertThrows(ProtocolException.class, () -> Envelope.parse("not json"));
        assertThrows(ProtocolException.class, () -> Envelope.parse("[1,2]"));
        assertThrows(ProtocolException.class, () -> Envelope.parse("{\"v\":1}"));
    }

    @Test
    void rejectsOtherProtocolVersions() {
        String v2 = "{\"v\":2,\"type\":\"welcome\",\"id\":\"x\",\"ts\":1,\"data\":{}}";
        assertThrows(ProtocolException.class, () -> Envelope.parse(v2));
    }

    @Test
    void rejectsHugeMessages() {
        String big = "{\"v\":1,\"type\":\"x\",\"id\":\"x\",\"ts\":1,\"data\":{\"m\":\"" + "a".repeat(70_000) + "\"}}";
        assertThrows(ProtocolException.class, () -> Envelope.parse(big));
    }

    @Test
    void strReturnsNullForMissingOrWrongType() {
        JsonObject o = new JsonObject();
        o.addProperty("n", 5);
        assertNull(Envelope.str(o, "missing"));
        assertNull(Envelope.str(o, "n"));
    }

    @Test
    void okReplyCanCarryData() {
        JsonObject data = new JsonObject();
        data.addProperty("chunks", 12);
        JsonObject reply = Replies.ok("", data);
        assertTrue(reply.get("ok").getAsBoolean());
        assertEquals(12, reply.getAsJsonObject("data").get("chunks").getAsInt());
    }
}
