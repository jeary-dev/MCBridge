package czr.mcbridge.core;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LegacyColorsTest {
    @Test
    void basicColours() {
        assertEquals("<dark_gray>[<green>MCBridge<dark_gray>] ", LegacyColors.toMiniMessage("&8[&aMCBridge&8] "));
    }

    @Test
    void hexAndSectionSign() {
        assertEquals("<#3ddc84>Hi <white>there", LegacyColors.toMiniMessage("&#3DDC84Hi §fthere"));
    }

    @Test
    void colourEndsFormattingLikeVanilla() {
        assertEquals("<red><bold>Big <reset><gray>small", LegacyColors.toMiniMessage("&c&lBig &7small"));
        assertEquals("<bold><reset><red>x", LegacyColors.toMiniMessage("&l&cx"));
        assertEquals("<italic>a<reset>b", LegacyColors.toMiniMessage("&oa&rb"));
    }

    @Test
    void leavesEverythingElseAlone() {
        assertEquals("Tom & Jerry <gray>ok</gray>", LegacyColors.toMiniMessage("Tom & Jerry <gray>ok</gray>"));
        assertEquals("<hover:show_text:'x'><gray>a</hover>", LegacyColors.toMiniMessage("<hover:show_text:'x'>&7a</hover>"));
    }
}
