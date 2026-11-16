package czr.mcbridge.roles;

import net.luckperms.api.LuckPerms;
import net.luckperms.api.LuckPermsProvider;
import net.luckperms.api.event.user.UserDataRecalculateEvent;
import net.luckperms.api.model.user.User;
import net.luckperms.api.node.NodeType;
import net.luckperms.api.node.types.InheritanceNode;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.plugin.Plugin;

import java.util.List;
import java.util.UUID;
import java.util.function.Consumer;

/** Role sync through LuckPerms. Also notices when a player's groups change while they're online. */
final class LuckPermsBridge implements PermissionsBridge {
    private final LuckPerms api = LuckPermsProvider.get();

    @Override
    public String name() {
        return "LuckPerms";
    }

    @Override
    public List<String> groups(Player player) {
        User user = api.getUserManager().getUser(player.getUniqueId());
        if (user == null) return List.of();
        return user.getNodes(NodeType.INHERITANCE).stream().map(InheritanceNode::getGroupName).distinct().toList();
    }

    @Override
    public void addGroup(UUID player, String group) {
        if (api.getGroupManager().getGroup(group) == null) return;
        api.getUserManager().modifyUser(player, u -> u.data().add(InheritanceNode.builder(group).build()));
    }

    @Override
    public void removeGroup(UUID player, String group) {
        api.getUserManager().modifyUser(player, u -> u.data().remove(InheritanceNode.builder(group).build()));
    }

    @Override
    public void onGroupsChanged(Plugin plugin, Consumer<Player> listener) {
        api.getEventBus().subscribe(plugin, UserDataRecalculateEvent.class, event -> {
            UUID id = event.getUser().getUniqueId();
            Bukkit.getScheduler().runTask(plugin, () -> {
                Player player = Bukkit.getPlayer(id);
                if (player != null) listener.accept(player);
            });
        });
    }
}
