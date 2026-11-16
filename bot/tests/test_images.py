"""The image cards render for full, empty and odd data, and items get sensible colours and shapes."""
import io

from PIL import Image

from mcbridge_bot import images


def size(png: bytes) -> tuple[int, int]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    return Image.open(io.BytesIO(png)).size


def it(t, n=1, **k):
    return dict(type=t, amount=n, **k)


def test_player_card_with_and_without_live_data():
    tracked = {"playtime_s": 5000, "joins": 3, "deaths": 1, "first_seen": 1_700_000_000, "last_seen": 1_700_100_000,
               "online": False}
    live = {"online": True, "health": 7.5, "max_health": 20, "food": 9, "level": 3, "exp": 0.4, "world": "world",
            "environment": "normal", "gamemode": "creative", "ping": 900, "op": True, "banned": False}
    w, h = size(images.player_card("czrbyn", server="SMP", tracked=tracked, live=live, discord_name="c"))
    assert w == 640 * images.OUT
    w2, h2 = size(images.player_card("czrbyn", server="SMP", tracked=tracked))
    assert h2 < h
    size(images.player_card("x" * 40, server="S" * 80, live={"online": False}, skin=b"not a png"))


def test_advancements_card():
    data = {"name": "czrbyn", "done": 3, "total": 10, "online": False,
            "tabs": [{"id": "minecraft:story/root", "title": "Minecraft", "done": 3, "total": 5},
                     {"id": "custom:quests/root", "title": "Quests", "done": 0, "total": 5}],
            "recent": [{"title": "Stone Age", "tab": "minecraft:story/root", "tab_title": "Minecraft",
                        "ts": 1_700_000_000_000, "frame": "challenge"}]}
    size(images.advancements_card(data, server="SMP"))
    size(images.advancements_card({"name": "x", "done": 0, "total": 0}, server="SMP"))


def test_inventory_and_container_cards():
    data = {"name": "czrbyn", "online": False, "selected_slot": 1,
            "armor": [it("diamond_helmet"), None, it("iron_leggings", durability=1, max_durability=225), None],
            "offhand": it("shield"),
            "hotbar": [it("netherite_sword", enchantments=[{"id": "sharpness", "level": 5}]),
                       it("red_shulker_box", block=True, contents=[it("dirt", 64, block=True)] + [None] * 26)],
            "main": [it("weird_modded_thing", 3)] + [None] * 26,
            "ender_chest": [it("diamond", 64)] + [None] * 26}
    size(images.inventory_card(data, server="SMP"))
    size(images.inventory_card({"name": "empty"}, server="SMP"))
    assert [s for s, _, _ in images.shulker_slots(data)] == ["hotbar"]
    size(images.container_card("Red Shulker Box", data["hotbar"][1]["contents"], subtitle="x",
                               color=images.shulker_color("red_shulker_box")))


def test_item_colours_and_kinds():
    assert images.material_color("diamond_sword") == images.material_color("diamond")
    assert images.material_color("light_blue_wool") == images.DYES["light_blue"]
    assert images.material_color("blue_shulker_box") == images.DYES["blue"]
    assert images.material_color("totally_unknown").startswith("#")
    assert images.item_kind({"type": "netherite_pickaxe"}) == "pickaxe"
    assert images.item_kind({"type": "golden_boots"}) == "boots"
    assert images.item_kind({"type": "oak_planks", "block": True}) == "block"
    assert images.item_kind({"type": "lime_shulker_box", "block": True}) == "shulker"
    assert images.item_kind({"type": "iron_ingot"}) == "ingot"
    assert images.item_kind({"type": "cooked_beef"}) == "food"
    assert images.item_kind({"type": "name_tag"}) == "chip"
    assert images.abbreviation("name_tag") == "NT"
    assert images.roman(4) == "IV" and images.roman(50) == "50"
