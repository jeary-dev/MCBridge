package czr.mcbridge.core;

import java.io.BufferedInputStream;
import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.GZIPInputStream;

/**
 * A small read-only reader for Minecraft's NBT format, enough to read player data files.
 * Compounds become maps, lists become lists, numbers stay numbers and arrays become Java arrays.
 */
public final class Nbt {
    private static final int MAX_DEPTH = 64;
    private static final int MAX_LENGTH = 1 << 20;

    private Nbt() {}

    public static Map<String, Object> readGzip(InputStream in) throws IOException {
        DataInputStream d = new DataInputStream(new BufferedInputStream(new GZIPInputStream(in)));
        int type = d.readByte();
        if (type != 10) throw new IOException("not an NBT compound");
        d.readUTF();
        return compound(d, 0);
    }

    private static Map<String, Object> compound(DataInputStream d, int depth) throws IOException {
        if (depth > MAX_DEPTH) throw new IOException("NBT nested too deep");
        Map<String, Object> out = new LinkedHashMap<>();
        while (true) {
            int type = d.readByte();
            if (type == 0) return out;
            String name = d.readUTF();
            out.put(name, read(d, type, depth + 1));
        }
    }

    private static int length(DataInputStream d) throws IOException {
        int n = d.readInt();
        if (n < 0 || n > MAX_LENGTH) throw new IOException("bad NBT length " + n);
        return n;
    }

    private static Object read(DataInputStream d, int type, int depth) throws IOException {
        switch (type) {
            case 1: return d.readByte();
            case 2: return d.readShort();
            case 3: return d.readInt();
            case 4: return d.readLong();
            case 5: return d.readFloat();
            case 6: return d.readDouble();
            case 7: {
                byte[] a = new byte[length(d)];
                d.readFully(a);
                return a;
            }
            case 8: return d.readUTF();
            case 9: {
                int inner = d.readByte();
                int n = length(d);
                List<Object> list = new ArrayList<>(Math.min(n, 1024));
                for (int i = 0; i < n; i++) list.add(read(d, inner, depth + 1));
                return list;
            }
            case 10: return compound(d, depth);
            case 11: {
                int[] a = new int[length(d)];
                for (int i = 0; i < a.length; i++) a[i] = d.readInt();
                return a;
            }
            case 12: {
                long[] a = new long[length(d)];
                for (int i = 0; i < a.length; i++) a[i] = d.readLong();
                return a;
            }
            default: throw new IOException("unknown NBT tag " + type);
        }
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> map(Object o) {
        return o instanceof Map<?, ?> m ? (Map<String, Object>) m : Map.of();
    }

    @SuppressWarnings("unchecked")
    public static List<Object> list(Object o) {
        return o instanceof List<?> l ? (List<Object>) l : List.of();
    }

    public static String str(Object o) {
        return o instanceof String s ? s : null;
    }

    public static Number num(Object o) {
        return o instanceof Number n ? n : null;
    }

    public static int integer(Object o, int fallback) {
        return o instanceof Number n ? n.intValue() : fallback;
    }
}
