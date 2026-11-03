"""The painted nesting dolls of rung 22, written as frames: no model is called.

    uv run python examples/matryoshka.py

Five dolls, each describing itself in its own voice and its own design,
none saying whether it is a boy or a girl. The second holds a piece of paper
on which that is written, but the paper's words are lost: its hole. The
smallest holds that paper, and says it is not its own. Each line a doll says
is one span, and the drawing paints exactly those lines.

The pools hold every design, decoy and name a set may draw; `DEFAULT` is the
set the kept frames are written from. Names are ones used for boys and girls
alike, from many parts of the world, so a name never decides.

Writes examples/dolls/ (the five dolls as unpacked, walked and never asked)
and the three frames rung 22 asks: Kiran asked again with the paper, the
same with a decoy beside it, and Mirza, who holds the paper.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from midwife.frame import parse
from midwife.recoil import found, sha256, successor

HERE = Path(__file__).parent
MUSE = "openrouter/meta/muse-spark-1.3-contributor"
BATTERY = {"kind": "unified", "model": MUSE, "reasoning": "low", "trainsOnInputs": [MUSE]}
STANDING = {"quorum": 3, "agree": 2}  # asked lightly, and again only until firm

# Names used for boys and girls alike, by where they are used.
NAMES = {
    "England and the English-speaking world": ["Robin", "Charlie", "Jamie", "Morgan", "Riley"],
    "Russia": ["Sasha", "Zhenya", "Valya"],
    "the Balkans": ["Mirza", "Vanja", "Saša"],
    "East Africa": ["Amani", "Bahati"],
    "West Africa": ["Ayo", "Tobi", "Ebere"],
    "South Asia": ["Kiran", "Navjot", "Harpreet"],
    "Tibet and the Himalaya": ["Tenzin", "Pema", "Dawa", "Nima"],
    "China": ["Wen", "Yu"],
    "Japan": ["Hikaru", "Kaoru", "Makoto", "Yuki"],
    "Korea": ["Ji-min", "Ji-woo"],
    "Vietnam": ["Minh", "An"],
    "the Arab world": ["Nur", "Salam"],
    "Israel": ["Shai", "Tal", "Eden", "Ariel"],
    "Turkey": ["Deniz", "Evren"],
    "Latin America": ["Cruz", "Guadalupe"],
    "Italy": ["Andrea", "Celeste"],
    "France": ["Camille", "Dominique", "Claude"],
    "Germany and Scandinavia": ["Kai", "Kim", "Eike"],
    "Hawaii": ["Kalani", "Noa"],
}
# Lines that point to girl without deciding anything: never the doll's own word.
DECOYS = [
    "Children who play with me call me their little sister.",
    "Visitors always say what a pretty girl I am.",
    "My headscarf was my grandmother's.",
    "I was painted by a woman who only ever painted girls.",
]
# Each doll's design, in the words its lines use.
THEMES = [
    {"body": "pink", "scarf": "red", "trim": "pale pink", "dots": "White polka", "hair": "yellow",
     "eyes": "blue", "hem": "red", "motif": "rose", "flower": "tulip"},
    {"body": "yellow", "scarf": "green", "trim": "pale yellow", "dots": "Pale yellow",
     "hair": "brown", "eyes": "brown", "hem": "green", "motif": "strawberry", "flower": "daisy"},
    {"body": "pale blue", "scarf": "blue", "trim": "white", "dots": "White", "hair": "light brown",
     "eyes": "grey", "hem": "blue", "motif": "cornflower", "flower": "buttercup"},
    {"body": "cream", "scarf": "yellow", "trim": "orange", "dots": "Red", "hair": "dark brown",
     "eyes": "green", "hem": "yellow", "motif": "cherry", "flower": "bluebell"},
    {"body": "teal", "scarf": "purple", "trim": "lilac", "dots": "White", "hair": "yellow",
     "eyes": "blue", "hem": "purple", "motif": "none", "flower": "sunflower"},
]  # fmt: skip
FLOWER = {
    "tulip": ("A red tulip is painted on my front.", "Smaller tulips are painted on my sides."),
    "daisy": ("A white daisy with a yellow heart is painted on my front.",
              "Smaller daisies are painted on my sides."),
    "buttercup": ("Yellow buttercups are painted on my front.",
                  "Smaller buttercups are painted on my sides."),
    "bluebell": ("A stem of blue bluebells is painted on my front.",
                 "Smaller bluebells are painted on my sides."),
    "sunflower": ("A sunflower with a brown heart is painted on my front.",
                  "Smaller sunflowers are painted on my sides."),
}  # fmt: skip
MOTIF = {
    "rose": ("A large red rose is painted on my front.",
             "Each of my roses is swirled with darker red.",
             "A second rose blooms beside the first.", "A third rose sits low on my side."),
    "strawberry": ("A large strawberry is painted on my front.",
                   "My strawberries are dotted with yellow seeds.",
                   "A second strawberry hangs beside the first.",
                   "A third strawberry sits low on my side."),
    "cornflower": ("A large blue cornflower is painted on my front.",
                   "Each of my cornflowers has a dark blue heart.",
                   "A second cornflower opens beside the first.",
                   "A third cornflower sits low on my side."),
    "cherry": ("A pair of red cherries is painted on my front.", None, None, None),
}  # fmt: skip
FRUIT = {"strawberry", "cherry"}
# Each line a doll may say, and the smallest doll (by place, 0 the largest)
# still painted with it: the fine work drops out as the dolls shrink.
LINES = [
    ("shape", 4, "shape", lambda t: "My shape is that of a famous doll."),
    ("name", 4, "name", None),
    ("body", 4, "paint", lambda t: f"Below my headscarf I am painted {t['body']}."),
    ("scarf", 4, "paint",
     lambda t: f"My headscarf is {t['scarf']} and covers my head and shoulders."),
    ("face", 4, "paint", lambda t: "My face is painted cream."),
    ("hair", 4, "paint", lambda t: f"My hair is {t['hair']}, parted in the middle."),
    ("eyes", 4, "paint", lambda t: f"My eyes are large and {t['eyes']}."),
    ("cheeks", 4, "paint", lambda t: "My cheeks are painted pink."),
    ("lips", 4, "paint", lambda t: "My lips are a small red bow."),
    ("flower", 4, "paint", lambda t: FLOWER[t["flower"]][0]),
    ("trim", 4, "paint", lambda t: f"My headscarf ends in a row of {t['trim']} scallops."),
    ("motif", 3, "paint", lambda t: MOTIF[t["motif"]][0]),
    ("leaves", 3, "paint", lambda t: "Green leaves spread around my "
     + ("fruit and flowers." if t["motif"] in FRUIT else "flowers.")),
    ("glints", 3, "paint", lambda t: "A white glint shines in each of my eyes."),
    ("dots", 3, "paint", lambda t: f"{t['dots']} dots are scattered over my headscarf."),
    ("lashes", 2, "paint", lambda t: "Long dark lashes curl above my eyes."),
    ("brows", 2, "paint", lambda t: "My brows are thin brown arcs."),
    ("fine", 2, "paint", lambda t: MOTIF[t["motif"]][1]),
    ("motif2", 1, "paint", lambda t: MOTIF[t["motif"]][2]),
    ("flowers", 4, "paint", lambda t: FLOWER[t["flower"]][1]),
    ("nose", 2, "paint", lambda t: "My nose is a single small stroke."),
    ("hem", 1, "paint", lambda t: f"A thin {t['hem']} band runs around my hem."),
    ("motif3", 0, "paint", lambda t: MOTIF[t["motif"]][3]),
    ("seam", 0, "paint", lambda t: "I open at my waist."),
    ("shine", 0, "paint", lambda t: "My lacquer shines."),
]  # fmt: skip
DEFAULT = {"names": ["Amani", "Kiran", "Sasha", "Robin", "Mirza"], "decoy": DECOYS[0]}
INSTRUCTION = (
    "A painted nesting doll describes itself. Use only what is given. Answer boy if it shows "
    "the doll is a boy, girl if it shows the doll is a girl, unknown if it does not decide."
)


def span(id: str, text: str, kind: str, quoted: bool = False) -> dict:
    source = {"source": {"sha256": sha256(text)}} if quoted else {}
    return {"id": id, "text": text, "kind": kind, **source}


def lines(n: int, name: str) -> list[dict]:
    """What the doll at place `n` says of itself, one span a line."""
    theme, out = THEMES[n], []
    for id, keep, kind, say in LINES:
        if n > keep:
            continue
        text = f"My name is {name}." if id == "name" else say(theme)
        if text:  # a motif the doll is too small for, or has none of
            out.append(span(id, text, kind))
    return out


def dolls(names: list[str]) -> list[dict]:
    """The five dolls as unpacked: each quotes the line that says it sits
    inside the doll above, and only the second and the smallest hold paper."""
    second = names[1]
    frames = []
    for n, name in enumerate(names):
        body = lines(n, name)
        if n:
            body.insert(2, span("inside", f"{name} sits inside {names[n - 1]}.", "inside", True))
        if n < 4:
            body.append(span("holds-next", f"{names[n + 1]} sits inside {name}.", "inside"))
        raw = {
            "name": name,
            "relation": f"whether {name} is a boy or a girl rests on what {name} says, "
            "not on paint",
            "locus": f"what {name} says of itself",
            "role": "a collector cataloguing a set of nesting dolls",
            "grain": "one line a doll says",
            "purpose": "catalogue each doll as a boy or a girl",
            "trajectory": "the dolls as unpacked, what each says, the collector's entry",
            "crossing": "the doll's entry in the catalogue",
            "promise": f"{name} is catalogued by what {name} says; without it, unknown, "
            "however the doll is painted",
            "baseline": "the doll as unpacked; nothing changed",
            "body": {"spans": body},
            "anchors": [],
            "inputs": [{"id": "what", "text": "What am I?"}],
            "observe": {"labels": ["boy", "girl", "unknown"], "instruction": INSTRUCTION},
            "interventions": {"repeat": True, "ablation": True},
            "allowed": {"ablation": ["unknown"]},
            "standing": STANDING,
            "materialized": True,
            "carriage": "listed",
            "battery": BATTERY,
        }
        if n == 0:  # the set's own question: whose set it is waits on who is inside
            raw["relation"] = f"whose set {name} opens rests on what its dolls say of themselves"
            raw["inputs"] = [{"id": "set", "text": "Is this a set of girls?"}]
            raw["observe"] = {
                "labels": ["girls", "unknown"],
                "instruction": "The largest of a set of painted nesting dolls describes itself. "
                "Use only what is given. Answer girls if it shows every doll of the set is a "
                "girl, unknown if it does not decide.",
            }
            raw["allowed"] = {"ablation": ["unknown"]}
            raw["holes"] = [{"id": "inside", "kind": "role"}]
        elif n == 1:
            raw["body"]["spans"].append(span(
                "holds", "I hold a piece of paper on which my name and whether I am a boy or a "
                "girl are written.", "holds"))  # fmt: skip
            raw["holes"] = [{"id": "paper", "kind": f"{second.lower()}-paper"}]
            raw["offers"] = "role"
        elif n == 4:
            raw["body"]["spans"] += [
                span("slip", "I hold a piece of paper.", "holds"),
                span("says", f'The paper says: "My name is {second}, and I am a boy."',
                     f"{second.lower()}-paper"),
                span("notmine", "This paper is not mine.", "owner"),
            ]  # fmt: skip
            raw["anchors"] = ["notmine"]
            raw["relation"] = f"that {name} is unknown rests on {name} disowning the paper"
            raw["promise"] = f"{name} is not catalogued by a paper {name} says is not {name}'s"
        else:  # a doll whose own word is missing too, and never found
            raw["holes"] = [{"id": "word", "kind": f"{name.lower()}-word"}]
        frames.append(raw)
    return frames


def asked(names: list[str], decoy: str) -> dict[str, dict]:
    """Rung 22's three frames: Kiran asked again with the paper's words
    found in Mirza, the same with a decoy beside them, and Mirza."""
    unpacked = [parse(raw) for raw in dolls(names)]
    second, smallest = unpacked[1], unpacked[4]
    paint = [s.id for s in second.spans if s.kind == "paint"]
    trials = {
        "interventions": {
            "repeat": True,
            "ablation": True,
            "sham": {"draws": 2, "kind": {"paper": "paint"}},
            "presentation": {"paper": "note"},
            "control": [*paint, "paper"],
        },
        "baseline": f"{second.name} as unpacked, with the paper's words found in "
        f"{smallest.name}; nothing changed",
    }
    plain = successor(second, "paper", found(smallest, "says"), **trials)
    decoyed = copy.deepcopy(plain)
    at = next(i for i, s in enumerate(decoyed["body"]["spans"]) if s["id"] == "holds")
    decoyed["body"]["spans"].insert(at, span("decoy", decoy, "decoy"))
    decoyed["baseline"] = plain["baseline"].replace("; nothing", ", a decoy beside them; nothing")
    mirza = copy.deepcopy(smallest.raw)
    mirza["interventions"] = {
        "repeat": True,
        "ablation": True,
        "cumulative": ["name"],
        "sham": {"draws": 2, "kind": {"notmine": "paint"}},
        "presentation": {"paper": "note"},
    }
    mirza["allowed"] = {"ablation": ["boy"]}
    return {
        f"22-{second.name.lower()}-paper": plain,
        f"22b-{second.name.lower()}-paper-decoy": decoyed,
        f"22c-{smallest.name.lower()}-not-mine": mirza,
    }


def write(raw: dict, path: Path) -> None:
    parse(raw)  # a frame that would not parse is never written
    text = json.dumps(raw, indent=2, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise SystemExit(f"{path.name} exists and differs: a kept frame is never changed")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    names = DEFAULT["names"]
    out = HERE / "dolls"
    out.mkdir(exist_ok=True)
    for n, raw in enumerate(dolls(names), 1):
        write(raw, out / f"{n}-{raw['name'].lower()}.json")
    for stem, raw in asked(names, DEFAULT["decoy"]).items():
        write(raw, HERE / f"{stem}.json")
        print(f"{stem}: {parse(raw).hash[:12]}")


if __name__ == "__main__":
    main()
