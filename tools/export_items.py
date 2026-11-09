#!/usr/bin/env python3
"""Выгрузка справочника вещей: картинки + data/items.js для сайта."""
import json, os, re, subprocess, sys
from PIL import Image

PROJ = "/home/fladver/Documents/My project"
SITE = os.path.expanduser("~/Documents/castle-defenders-site")
ITEMS = PROJ + "/Assets/Configs/Items"
OUT_IMG = SITE + "/img/items"
os.makedirs(OUT_IMG, exist_ok=True)


def field(t, k):
    m = re.search(r"^\s*" + k + r": ?(.*)$", t, re.M)
    if not m:
        return ""
    s = m.group(1).strip()
    if s.startswith('"'):
        s = s[1:-1].encode("latin1", "backslashreplace").decode("unicode_escape")
    return s


def num(t, k):
    v = field(t, k)
    return float(v) if v else 0.0


guid_cache = {}


def guid_path(g):
    if g not in guid_cache:
        r = subprocess.run(["grep", "-rl", "--include=*.meta", "^guid: " + g, PROJ + "/Assets"],
                           capture_output=True, text=True).stdout.splitlines()
        guid_cache[g] = r[0][:-5] if r else None
    return guid_cache[g]


def sprite_image(file_id, g):
    path = guid_path(g)
    im = Image.open(path).convert("RGBA")
    if file_id == "21300000":
        return im
    meta = open(path + ".meta").read()
    # Ищем блок спрайта с этим internalID и берём его rect
    for block in re.split(r"\n    - serializedVersion: 2\n", meta):
        if re.search(r"internalID: " + re.escape(file_id) + r"\b", block):
            x, y, w, h = (int(float(re.search(r"\b" + k + r": ([\d.]+)", block).group(1)))
                          for k in ("x", "y", "width", "height"))
            return im.crop((x, im.height - y - h, x + w, im.height - y))
    raise SystemExit("нет спрайта %s в %s" % (file_id, path))


def save_icon(im, name):
    im = im.crop(im.getbbox() or (0, 0, im.width, im.height))
    im.thumbnail((160, 160), Image.LANCZOS)
    im.save(OUT_IMG + "/" + name + ".png", optimize=True)


# Подложки качества (6 штук, ур. 6+ — последняя)
bg_path = PROJ + "/Assets/Resources/UI/ItemBackground.png"
bg = Image.open(bg_path).convert("RGBA")
for i, (x, y, w, h) in enumerate(re.findall(
        r"name: ItemBackground_\d\n\s+rect:\n\s+serializedVersion: 2\n\s+x: (\d+)\n\s+y: (\d+)\n\s+width: (\d+)\n\s+height: (\d+)",
        open(bg_path + ".meta").read())):
    x, y, w, h = map(int, (x, y, w, h))
    bg.crop((x, bg.height - y - h, x + w, bg.height - y)).resize((128, 128), Image.LANCZOS).save(
        OUT_IMG + "/q%d.png" % (i + 1), optimize=True)

SLOTS = ["weapon", "helmet", "armor", "boots", "gloves", "amulet", "ring", "ring"]
gear, potions, seen = [], [], set()
files = sorted(f for f in os.listdir(ITEMS) if f.endswith(".asset") and f != "ItemsDatabase.asset")
files += sorted("Swords/" + f for f in os.listdir(ITEMS + "/Swords") if f.endswith(".asset"))
for f in files:
    t = open(ITEMS + "/" + f).read()
    iid = field(t, "_id")
    if iid == "sword_01":
        continue  # базовый «Меч» в игре всегда превращается в один из обликов
    sp = re.search(r"_levelSprites:\n\s+- \{fileID: (-?\d+), guid: ([0-9a-f]+)", t)
    name = field(t, "_itemName")
    if field(t, "_isConsumable") == "1":
        save_icon(sprite_image(sp.group(1), sp.group(2)), iid)
        potions.append({"id": iid, "name": name, "effect": int(field(t, "_potionEffect")),
                        "power": num(t, "_potionPower")})
        continue
    stats = {k: num(t, r"    " + k) for k in ("Damage", "MagicDamage", "Health", "Armor", "CritChance", "HealBonus")}
    slot = SLOTS[int(field(t, "_equipSlot"))]
    key = (name, slot, json.dumps(stats))
    if key in seen:
        continue  # Кольцо I и Кольцо II — одна и та же вещь
    seen.add(key)
    # Картинка на каждый уровень (у мечей одна на все уровни — тогда одна)
    refs = re.findall(r"- \{fileID: (-?\d+), guid: ([0-9a-f]+)", t.split("_levelSprites:")[1].split("_potionEffect")[0])
    for lv, (fid, g) in enumerate(refs if len(set(refs)) > 1 else refs[:1], 1):
        save_icon(sprite_image(fid, g), iid if lv == 1 else "%s_%d" % (iid, lv))
    m = re.match(r"sword_t(\d)_", iid)
    gear.append({"id": iid, "name": name, "slot": slot, "tier": int(m.group(1)) if m else 0,
                 "mult": num(t, "_evolutionMultiplier"), "s": stats,
                 "dur": [int(num(t, "_baseDurability")), int(num(t, "_durabilityPerLevel"))],
                 "pics": len(set(refs))})

with open(SITE + "/data/items.js", "w") as out:
    out.write("// Выгрузка из Assets/Configs/Items (export_items.py). Не править руками.\n")
    j = lambda xs: ",\n".join(json.dumps(x, ensure_ascii=False) for x in xs)
    out.write("window.ITEMS = {\n\"gear\": [\n" + j(gear) + "\n],\n\"potions\": [\n" + j(potions) + "\n]};\n")
print("вещей", len(gear), "зелий", len(potions))
