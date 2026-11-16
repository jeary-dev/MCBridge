package czr.mcbridge.core;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class UpdateCheckerTest {
    @Test
    void comparesVersionsNumerically() {
        assertTrue(UpdateChecker.isNewer("v0.2.2", "0.2.1"));
        assertTrue(UpdateChecker.isNewer("0.2.10", "0.2.9"));
        assertTrue(UpdateChecker.isNewer("1.0", "0.9.9"));
        assertFalse(UpdateChecker.isNewer("0.2.1", "0.2.1"));
        assertFalse(UpdateChecker.isNewer("0.2.0", "0.2.1"));
        assertFalse(UpdateChecker.isNewer("0.2.1-beta", "0.2.1"));
    }

    @Test
    void readsGithubReleases() {
        var r = UpdateChecker.parse("{\"tag_name\":\"v0.3.0\",\"html_url\":\"https://github.com/jeary-dev/MCBridge/releases/tag/v0.3.0\"}");
        assertEquals("0.3.0", r.orElseThrow().version());
        assertTrue(UpdateChecker.parse("{\"tag_name\":\"v9\",\"prerelease\":true}").isEmpty());
        assertTrue(UpdateChecker.parse("not json").isEmpty());
        var evil = UpdateChecker.parse("{\"tag_name\":\"v1\",\"html_url\":\"https://evil.example\"}");
        assertEquals("https://github.com/jeary-dev/MCBridge/releases/latest", evil.orElseThrow().url());
    }
}
