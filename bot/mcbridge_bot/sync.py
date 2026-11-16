"""Small pure helpers for role sync, the console channel and stat channels. No Discord code, easy to test."""
from __future__ import annotations

import re

DIRECTIONS = {"both", "minecraft-to-discord", "discord-to-minecraft"}
TO_DISCORD = {"both", "minecraft-to-discord"}
TO_MINECRAFT = {"both", "discord-to-minecraft"}

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
SECTION_CODES = re.compile(r"§[0-9a-fk-orx]", re.IGNORECASE)
IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?(?![\d.])")
IPV6 = re.compile(r"\[?(?<![\w:])(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}(?![\w:])\]?(?::\d{1,5})?")
CODE_BLOCK_LIMIT = 1900


def roles_for_discord(links: list[dict], groups: list[str], member_role_ids: set[str]) -> tuple[set[str], set[str]]:
    have = {g.lower() for g in groups}
    add, remove = set(), set()
    for link in links:
        if link["direction"] not in TO_DISCORD:
            continue
        role = link["role_id"]
        if link["group_name"] in have and role not in member_role_ids:
            add.add(role)
        elif link["group_name"] not in have and role in member_role_ids:
            remove.add(role)
    return add, remove


def groups_for_minecraft(links: list[dict], member_role_ids: set[str], groups: list[str]) -> tuple[list[str], list[str]]:
    have = {g.lower() for g in groups}
    add, remove = [], []
    for link in links:
        if link["direction"] not in TO_MINECRAFT:
            continue
        group = link["group_name"]
        if link["role_id"] in member_role_ids and group not in have:
            add.append(group)
        elif link["role_id"] not in member_role_ids and group in have:
            remove.append(group)
    return sorted(add), sorted(remove)


def clean_console_line(line: str) -> str:
    line = ANSI.sub("", line)
    line = SECTION_CODES.sub("", line)
    line = IPV4.sub("[IP hidden]", line)
    line = IPV6.sub(lambda m: "[IP hidden]" if "::" in m.group(0) or m.group(0).count(":") >= 5 else m.group(0), line)
    return line.replace("```", "'''").rstrip()


def console_blocks(lines: list[str], max_blocks: int = 2) -> list[str]:
    blocks, current = [], ""
    skipped = 0
    for raw in lines:
        line = clean_console_line(raw)[:CODE_BLOCK_LIMIT - 20]
        if not line:
            continue
        if len(current) + len(line) + 1 > CODE_BLOCK_LIMIT:
            if len(blocks) + 1 >= max_blocks:
                skipped += 1
                continue
            blocks.append(current)
            current = ""
        current += line + "\n"
    if current:
        blocks.append(current)
    out = [f"```ansi\n{b.rstrip()}\n```" for b in blocks]
    if skipped and out:
        out[-1] = out[-1][:-3] + f"… {skipped} more line{'s' if skipped != 1 else ''} skipped\n```"
    return out


def stat_channel_name(online: bool, players: int | None, max_players: int | None) -> str:
    if not online:
        return "🔴 Server offline"
    if players is None:
        return "🟢 Server online"
    return f"🟢 {players}/{max_players} online"
