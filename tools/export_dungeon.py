#!/usr/bin/env python3
"""Справочник оружия подземелья: парсит DungeonGame.Weapons.cs (M(...)/G(...)), картинки → img/dungeon/, страница dungeon.html.
Перезапускать после правки оружия в игре."""
import html, os, re
from PIL import Image

PROJ = "/home/fladver/Documents/My project"
SITE = os.path.expanduser("~/Documents/castle-defenders-site")
SRC = PROJ + "/Assets/Scripts/Dungeon/DungeonGame.Weapons.cs"
ART = PROJ + "/Assets/Resources/Dungeon/Weapons"
OUT_IMG = SITE + "/img/dungeon"

G_POS = ["name", "sprite", "kind", "dmg", "cd", "mana", "speed", "proj", "rarity", "tint",
         "pellets", "spread", "pierce", "explode", "range", "size", "angle", "shake"]
M_POS = ["name", "sprite", "dmg", "cd", "mana", "reach", "arc", "rarity", "tint", "size", "shake"]
GROUPS = [("Ближний бой", "melee"), ("Огнестрел и луки", "ranged"), ("Магия", "magic"), ("Бластеры", "blaster")]
RARITY = {1: ("обычное", "#d9d9d9"), 2: ("необычное", "#66ff66"), 3: ("редкое", "#66b3ff"),
          4: ("эпическое", "#cc73ff"), 5: ("легендарное", "#ff9933")}
KIND = {"Bullet": "пули", "Spread": "веер снарядов", "Beam": "луч", "Flame": "огнемёт", "Rocket": "снаряд со взрывом",
        "Homing": "самонаводящиеся снаряды", "Summon": "призыв"}


def split_args(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([": depth += 1
        if ch in ")]": depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip()); cur = ""
        else:
            cur += ch
    if cur.strip(): out.append(cur.strip())
    return out


def num(v):
    return float(v.rstrip("f"))


def parse():
    weapons = []
    for line in open(SRC, encoding="utf-8"):
        m = re.match(r'\s*([MG])\((.*)\),\s*(//.*)?$', line)
        if not m: continue
        args = split_args(m.group(2))
        names = M_POS if m.group(1) == "M" else G_POS
        w = {"kind": "Melee", "pellets": 1, "pierce": 0, "explode": 0.0, "range": 12.0}
        pos = 0
        for a in args:
            if re.match(r"^\w+:", a):
                k, v = a.split(":", 1); w[k.strip()] = v.strip()
            else:
                w[names[pos]] = a; pos += 1
        w["name"] = w["name"].strip('"'); w["sprite"] = w["sprite"].strip('"')
        w["kind"] = w["kind"].replace("Shot.", "")
        for k in ("dmg", "cd", "explode", "range"): w[k] = num(str(w[k]))
        for k in ("mana", "rarity", "pellets", "pierce"): w[k] = int(num(str(w[k])))
        if w["kind"] == "Melee": w["reach"] = num(w["reach"]); w["arc"] = num(w["arc"])
        weapons.append(w)
    return weapons


def one(v):
    return ("%.1f" % v).rstrip("0").rstrip(".").replace(".", ",")


def card(w):
    rname, rcol = RARITY[w["rarity"]]
    rate = one(1.0 / max(0.01, w["cd"]))
    lines = []
    if w["kind"] == "Summon":
        who = "скелета" if "некроманта" in w["name"] else "волка"
        lines.append("Призывает " + who + ": удар ×" + one(w["dmg"]) + " от урона героя")
    else:
        lines.append("Урон ×" + one(w["dmg"]) + (" ×" + str(w["pellets"]) + " снарядов" if w["pellets"] > 1 else "") +
                     " от урона героя")
        lines.append(rate + " атак в секунду")
    if w["kind"] == "Melee":
        lines.append("Удар по дуге " + one(w["arc"]) + "°, дальность " + one(w["reach"]))
    elif w["kind"] != "Summon":
        bow = str(w.get("proj", "")).strip() in ("8", "9", "14")  # луки, арбалеты, гарпун — как ShotSound в игре
        lines.append("Тип: " + ("стрелы" if bow and w["kind"] == "Bullet" else KIND.get(w["kind"], "")))
    lines.append("Мана за выстрел: " + str(w["mana"]) if w["mana"] > 0 else "Без маны")
    if w["explode"] > 0: lines.append("Взрыв радиусом " + one(w["explode"]))
    if w["pierce"] >= 99: lines.append("Прошивает всех врагов на пути")
    elif w["pierce"] > 0: lines.append("Прошивает врагов: " + str(w["pierce"]))
    if w["kind"] not in ("Melee", "Summon") and abs(w["range"] - 12.0) > 0.01:
        lines.append("Дальность " + one(w["range"]))
    items = "".join("<li>" + html.escape(l) + "</li>" for l in lines)
    return ('<div class="card icard"><div class="mtop" style="background:#1d1a26"><img src="img/dungeon/%s.png" alt=""></div>'
            '<h3>%s</h3><div class="slot" style="color:%s">%s</div><ul>%s</ul></div>'
            % (w["sprite"], html.escape(w["name"]), rcol, rname, items))


def export_images(weapons):
    os.makedirs(OUT_IMG, exist_ok=True)
    for w in weapons:
        src = ART + "/" + w["sprite"] + ".png"
        if not os.path.exists(src): continue
        im = Image.open(src).convert("RGBA")
        im.thumbnail((160, 160))
        im.save(OUT_IMG + "/" + w["sprite"] + ".png", optimize=True)


def main():
    weapons = parse()
    export_images(weapons)
    sections = []
    for title, prefix in GROUPS:
        group = sorted([w for w in weapons if w["sprite"].startswith(prefix)], key=lambda w: (w["rarity"], w["name"]))
        sections.append('<h2 id="%s">%s <span class="muted">(%d)</span></h2>\n<div class="cards">%s</div>'
                        % (prefix, title, len(group), "".join(card(w) for w in group)))
    legend = "".join('<span class="q"><b style="color:%s">%d</b> — %s</span>' % (c, r, n) for r, (n, c) in RARITY.items())
    tpl = open(SITE + "/tools/dungeon_template.html", encoding="utf-8").read()
    page = tpl.replace("{{COUNT}}", str(len(weapons))).replace("{{LEGEND}}", legend).replace("{{SECTIONS}}", "\n\n".join(sections))
    open(SITE + "/dungeon.html", "w", encoding="utf-8").write(page)
    print("Оружия:", len(weapons))


if __name__ == "__main__":
    main()
