from mcbridge_bot import sync

LINKS = [
    {"group_name": "vip", "role_id": "1", "direction": "both"},
    {"group_name": "staff", "role_id": "2", "direction": "minecraft-to-discord"},
    {"group_name": "booster", "role_id": "3", "direction": "discord-to-minecraft"},
]


def test_roles_for_discord():
    add, remove = sync.roles_for_discord(LINKS, ["VIP", "default"], {"2", "3"})
    assert add == {"1"} and remove == {"2"}


def test_groups_for_minecraft():
    add, remove = sync.groups_for_minecraft(LINKS, {"3"}, ["vip", "staff"])
    assert add == ["booster"] and remove == ["vip"]


def test_console_cleaning_hides_ips_and_colours():
    line = "\x1b[32m[12:00:01 INFO]: czrbyn[/192.168.1.20:51234] logged in §awith entity id 5"
    out = sync.clean_console_line(line)
    assert "192.168" not in out and "[IP hidden]" in out and "\x1b" not in out and "§a" not in out
    assert "2001:db8" not in sync.clean_console_line("from [2001:db8:85a3::8a2e:370:7334]:25565")
    assert sync.clean_console_line("TPS 19.9, version 1.21.11") == "TPS 19.9, version 1.21.11"
    assert out.startswith("[12:00:01 INFO]")
    assert "fe80" not in sync.clean_console_line("at fe80:0:0:0:200:f8ff:fe21:67cf done")


def test_console_blocks_limit_and_skip():
    lines = [f"line {i} " + "x" * 80 for i in range(200)]
    blocks = sync.console_blocks(lines, max_blocks=2)
    assert len(blocks) == 2 and all(len(b) <= 2000 for b in blocks)
    assert "more lines skipped" in blocks[-1]
    assert sync.console_blocks([]) == []


def test_stat_channel_name():
    assert sync.stat_channel_name(True, 3, 20) == "🟢 3/20 online"
    assert sync.stat_channel_name(False, None, None) == "🔴 Server offline"
