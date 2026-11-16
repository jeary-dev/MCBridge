package czr.mcbridge.core;

import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Turns classic colour codes (&8, &a, &l, &r, and hex like &#3ddc84) into MiniMessage tags, so
 * config messages can use either style, or both. Like in vanilla, a colour code ends any bold,
 * italic, etc. that came before it.
 */
public final class LegacyColors {
    private static final Pattern CODE = Pattern.compile("[&§](#[0-9A-Fa-f]{6}|[0-9A-Fa-fK-Ok-oRr])");

    private static final Map<Character, String> COLORS = Map.ofEntries(
            Map.entry('0', "black"), Map.entry('1', "dark_blue"), Map.entry('2', "dark_green"),
            Map.entry('3', "dark_aqua"), Map.entry('4', "dark_red"), Map.entry('5', "dark_purple"),
            Map.entry('6', "gold"), Map.entry('7', "gray"), Map.entry('8', "dark_gray"),
            Map.entry('9', "blue"), Map.entry('a', "green"), Map.entry('b', "aqua"),
            Map.entry('c', "red"), Map.entry('d', "light_purple"), Map.entry('e', "yellow"),
            Map.entry('f', "white"));

    private static final Map<Character, String> FORMATS = Map.of(
            'k', "obfuscated", 'l', "bold", 'm', "strikethrough", 'n', "underlined", 'o', "italic");

    private LegacyColors() {}

    public static String toMiniMessage(String input) {
        if (input == null || (input.indexOf('&') < 0 && input.indexOf('§') < 0)) return input;
        Matcher m = CODE.matcher(input);
        StringBuilder out = new StringBuilder();
        boolean formatted = false;
        while (m.find()) {
            String code = m.group(1).toLowerCase(Locale.ROOT);
            char c = code.charAt(0);
            String tag;
            if (c == '#') {
                tag = (formatted ? "<reset>" : "") + "<" + code + ">";
                formatted = false;
            } else if (c == 'r') {
                tag = "<reset>";
                formatted = false;
            } else if (FORMATS.containsKey(c)) {
                tag = "<" + FORMATS.get(c) + ">";
                formatted = true;
            } else {
                tag = (formatted ? "<reset>" : "") + "<" + COLORS.get(c) + ">";
                formatted = false;
            }
            m.appendReplacement(out, Matcher.quoteReplacement(tag));
        }
        m.appendTail(out);
        return out.toString();
    }
}
