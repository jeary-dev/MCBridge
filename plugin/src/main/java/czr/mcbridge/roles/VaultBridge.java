package czr.mcbridge.roles;

import net.milkbowl.vault.permission.Permission;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.entity.Player;
import org.bukkit.plugin.RegisteredServiceProvider;

import java.util.List;
import java.util.UUID;

/** Role sync through Vault and whatever permissions plugin is behind it. Groups sync when players join. */
final class VaultBridge implements PermissionsBridge {
    private final Permission perms;

    private VaultBridge(Permission perms) {
        this.perms = perms;
    }

    static VaultBridge create() {
        RegisteredServiceProvider<Permission> rsp = Bukkit.getServicesManager().getRegistration(Permission.class);
        if (rsp == null || !rsp.getProvider().hasGroupSupport()) return null;
        return new VaultBridge(rsp.getProvider());
    }

    @Override
    public String name() {
        return "Vault (" + perms.getName() + ")";
    }

    @Override
    public List<String> groups(Player player) {
        String[] groups = perms.getPlayerGroups(null, player);
        return groups == null ? List.of() : List.of(groups);
    }

    @Override
    public void addGroup(UUID player, String group) {
        OfflinePlayer p = Bukkit.getOfflinePlayer(player);
        perms.playerAddGroup(null, p, group);
    }

    @Override
    public void removeGroup(UUID player, String group) {
        OfflinePlayer p = Bukkit.getOfflinePlayer(player);
        perms.playerRemoveGroup(null, p, group);
    }
}
