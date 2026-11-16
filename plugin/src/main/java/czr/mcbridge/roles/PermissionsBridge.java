package czr.mcbridge.roles;

import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.plugin.Plugin;

import java.util.List;
import java.util.UUID;
import java.util.function.Consumer;

/** The permissions plugin MCBridge syncs groups with: LuckPerms if installed, otherwise Vault. */
public interface PermissionsBridge {
    String name();

    List<String> groups(Player player);

    void addGroup(UUID player, String group);

    void removeGroup(UUID player, String group);

    default void onGroupsChanged(Plugin plugin, Consumer<Player> listener) {}

    static PermissionsBridge detect(Plugin plugin) {
        if (Bukkit.getPluginManager().isPluginEnabled("LuckPerms")) {
            try {
                return new LuckPermsBridge();
            } catch (RuntimeException | LinkageError e) {
                plugin.getLogger().warning("LuckPerms found but couldn't be used for role sync: " + e);
            }
        }
        if (Bukkit.getPluginManager().isPluginEnabled("Vault")) {
            try {
                PermissionsBridge vault = VaultBridge.create();
                if (vault != null) return vault;
            } catch (RuntimeException | LinkageError e) {
                plugin.getLogger().warning("Vault found but couldn't be used for role sync: " + e);
            }
        }
        return null;
    }
}
