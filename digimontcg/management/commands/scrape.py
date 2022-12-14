from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from itertools import groupby
import os
from pprint import pprint

from django.core.management.base import BaseCommand, CommandError
import requests

from digimontcg import models

# Alphamon: Ouryuken
# http https://api.bandai-tcg-plus.com/api/user/card/36243
#
# Custom digivoluion cost / reqs
# Multiple effects

# Kimeramon
# http https://api.bandai-tcg-plus.com/api/user/card/35813
#
# Custom digivolution cost / reqs
# Multiple effects

# Greymon (X Antibody)
# http https://api.bandai-tcg-plus.com/api/user/card/36144
#
# Custom digivolution cost / reqs
# Inheritable effect

# MetalGreymon: Alterous Mode
# http https://api.bandai-tcg-plus.com/api/user/card/36666
#
# Custom digivolution cost / reqs
# Alternative name
# Inheritable effect

# All card types
# --------------
# Name
# Set
# Number
# Rarity
# Block
# Type
# Color(s)
# Image(s)
# Traits
#   Form
#   Attribute(s)
#   Type(s)

# Digi-eggs
# ---------
# Level
# Inherited Effect(s)

# Options
# -------
# Cost
# Effect(s)
# Security Effect(s)
# Inherited Effect(s)

# Tamers
# ------
# Play Cost
# Effect(s)
# Security Effect(s)
# Inherited Effect(s)

# Digimon
# -------
# NameIncludes (Gaiomon)
# NameTreatedAs (MetalGreymon: Alterous Mode)
# Level
# Play Cost
# DP
# Abilities (Rush, Sec+, etc)
# Effect(s)
# Security Effect(s)
# Inherited Effect(s)
# Digivolution Reqs
#   Cost
#   Color
#   Level
#   DNA (multiple)
#   Custom (0 from specific mon, or from mon w/ specific source)
#   Tamer (hybrids, or should this be a static effect?)

#DigivolveCost = namedtuple('DigivolveCost', 'cost from_')
#DigivolveFrom = namedtuple('DigivolveFrom', 'color level name sources tamer')

# Alphamon: Ouryuken
# [
#   {cost: 7, from: [{color: "black", level: 6}]},
#   {cost: 3, from: [{name: "Alphamon", sources: ["Ouryumon"]}]},
# ]

# MetalKabuterimon
# [
#   {cost: 3, from: [{color: "green", level: 3}]},
#   {cost: 1, from: [{color: "green", level: 4}]},
#   {cost: 2, from: [{color: "green", tamer: true}]},
# ]

# Kimeramon
# [
#   {cost: 4, from: [{level: 4}]},
#   {cost: 0, from: [{level: 4}, {level: 4}]},
# ]

# Effects
# -------
# List of fields:
#   triggers? (OR logic)
#   once? (boolean)
#   text (w/ keywords)

# What is an effect?
#   List of trigger(s) (OR logic) and effect(s) + OPT bool (modifier / restriction?)?
#     [Trigger][...] -> Plain text effects w/ keywords (like <Security Attack +1>)
# Are Security Effects a separate type or just a regular effect
#   with a [Security] trigger? Hybrid tamers infer the latter.
# Even if so, should they be called out in a separate field? So hybrid
#   tamers would have both "security_effect" and "inherited_effect"? As
#   well as their normal effects.
# Even some options have both security and inherited (X Antibody).
# Inherited Effects _are_ special.
# How are static effects (effects without triggers) handled (X Antibody)?
#   Just an effect without a trigger in the JSON?
#   Can all static effects be represented by other means? Alt names, etc?

# Triggers
# --------
# Main
# Security
# All Turns
# When Divivolving
# When Attacking
# On Play
# On Deletion


# mapping of set codes to btcg+ IDs
BTCGP_SET_IDS = {
    "ST1": [28],
    "ST2": [25],
    "ST3": [32],
    "ST4": [30],
    "ST5": [33],
    "ST6": [38],
    "ST7": [29],
    "ST8": [37],
    "ST9": [225],
    "ST10": [226],
    "ST12": [245],
    "ST13": [246],
    "BT1": [35, 36],
    "BT2": [35, 36],
    "BT3": [35, 36],
    "BT4": [31],
    "BT5": [23],
    "BT6": [27],
    "BT7": [170],
    "BT8": [221],
    "BT9": [222],
    "BT10": [250],
    "EX1": [171],
    "EX2": [223],
    "EX3": [251],
    "P": [39],
}


# type returned from the scraper
Set = namedtuple("Set", "number name release_date")
SETS = [
    Set(number="ST1", name="Gaia Red", release_date=date(2021, 1, 29)),
    Set(number="ST2", name="Cocytus Blue", release_date=date(2021, 1, 29)),
    Set(number="ST3", name="Heaven's Yellow", release_date=date(2021, 1, 29)),
    Set(number="ST4", name="Giga Green", release_date=date(2021, 6, 11)),
    Set(number="ST5", name="Machine Black", release_date=date(2021, 6, 11)),
    Set(number="ST6", name="Venomous Violet", release_date=date(2021, 6, 11)),
    Set(number="ST7", name="Gallantmon", release_date=date(2021, 12, 1)),
    Set(number="ST8", name="Ulforceveedramon", release_date=date(2021, 12, 1)),
    Set(number="ST9", name="Ultimate Ancient Dragon", release_date=date(2022, 5, 27)),
    Set(number="ST10", name="Parallel World Tactician", release_date=date(2022, 5, 27)),
    Set(number="ST12", name="Jesmon", release_date=date(2022, 10, 14)),
    Set(number="ST13", name="Ragnaloardmon", release_date=date(2022, 10, 14)),
    Set(number="BT1", name="New Evolution", release_date=date(2021, 3, 12)),
    Set(number="BT2", name="Ultimate Power", release_date=date(2021, 3, 12)),
    Set(number="BT3", name="Union Impact", release_date=date(2021, 3, 12)),
    Set(number="BT4", name="Great Legend", release_date=date(2021, 6, 11)),
    Set(number="BT5", name="Battle Of Omni", release_date=date(2021, 8, 6)),
    Set(number="BT6", name="Double Diamond", release_date=date(2021, 11, 26)),
    Set(number="BT7", name="Next Adventure", release_date=date(2022, 3, 22)),
    Set(number="BT8", name="New Awakening", release_date=date(2022, 5, 27)),
    Set(number="BT9", name="X Record", release_date=date(2022, 7, 29)),
    Set(number="BT10", name="Xros Encounter", release_date=date(2022, 10, 21)),
    Set(number="EX1", name="Classic Collection", release_date=date(2022, 1, 21)),
    Set(number="EX2", name="Digital Hazard", release_date=date(2022, 6, 24)),
    Set(number="EX3", name="Draconic Roar", release_date=date(2022, 11, 11)),
    Set(number="P", name="Promotion Card", release_date=None),
]

Effect = namedtuple("Effect", "trigger text once")
DigivolveCost = namedtuple('DigivolveCost', 'cost from_')
DigivolveFrom = namedtuple('DigivolveFrom', 'color level name sources tamer')

# type returned from the scraper
Card = namedtuple("Card", [
    "name",
    "name_includes",
    "name_treated_as",
    "number",
    "set",
    "rarity",
    "type",
    "colors",
    "images",
    "form",
    "attributes",
    "types",
    "effects",
    "inherited_effects",
    "security_effects",
    "cost",
    "play_cost",
    "dp",
    "level",
    "abilities",
    "digivolution_requirements",
])


def get_card_list(*set_ids):
    url = "https://api.bandai-tcg-plus.com/api/user/card/list"
    params = {
        "card_set[]": set_ids,
        "game_title_id": 2,
        "limit": 500,
        "offset": 0,
    }
    resp = requests.get(url, params=params)
    return resp.json()["success"]["cards"]


def get_card_details(card_id: int):
    url = f"https://api.bandai-tcg-plus.com/api/user/card/{card_id}"
    resp = requests.get(url)
    return resp.json()["success"]["card"]


def get_all_details(card_ids: list[int]):
    max_workers = os.cpu_count() * 2
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for details in pool.map(get_card_details, card_ids):
            yield details


def norm_card(card):
    config = card["card_config"]
    config = {conf["config_name"]: conf["value"] for conf in config if "value" in conf}

    name = card["card_name"]
    number = card["card_number"]
    set_ = card["card_number"].split("-")[0]

    # fix missing rarity on a few promos
    rarity = config.get("Rarity")
    if not rarity and set == "P":
        rarity = models.Card.Rarity.PROMO

    type_ = config.get("Card type")
    colors = [config.get("Color")]
    images = [card["image_url"]]

    # traits (form, attributes, types)
    form = config.get('Form')
    attributes = config.get('Attributes')
    if attributes:
        attributes = attributes.split('/')
    types = config.get('Type')
    if types:
        types = types.split('/')

    effects = card.get('card_text')
    if effects:
        effects = effects.replace('\r\n', '').split('<br>')

    name_includes = []
    name_treated_as = []

    inherited_effects = config.get('Digivolve effect')
    if inherited_effects:
        inherited_effects = [inherited_effects]

    security_effects = config.get('Security effect')
    if security_effects:
        security_effects = [security_effects]

    cost = config.get('Cost')
    play_cost = config.get('Play Cost')

    dp = config.get('DP')

    level = config.get('Lv.')
    if level:
        level = level.split('.')[-1]

    # no good way to check these?
    abilities = []

    # parse basic digi reqs (no DNA or special)
    digi_reqs = []
    for i in range(1, 3):
        key = 'Digivolve Cost ' + str(i)
        if config.get(key):
            digi_cost = config[key].split()[0]

            # don't specify a color if all are valid (Kimeramon)
            color = config.get(key + ' Evolution source Color')
            if color == 'All Color':
                color = None

            level = config.get(key + ' Evolution source Lv.')
            if level:
                level = level.split('.')[-1]

            req = {
                'cost': digi_cost,
                'from': [{
                    'color': color,
                    'level': level,
                }],
            }
            digi_reqs.append(req)

    return Card(
        name=name,
        name_includes=name_includes,
        name_treated_as=name_treated_as,
        number=number,
        set=set_,
        rarity=rarity,
        type=type_,
        colors=colors,
        images=images,
        form=form,
        attributes=attributes,
        types=types,
        effects=effects,
        inherited_effects=inherited_effects,
        security_effects=security_effects,
        cost=cost,
        play_cost=play_cost,
        dp=dp,
        level=level,
        abilities=abilities,
        digivolution_requirements=digi_reqs,
    )


class Command(BaseCommand):
    help = "Scrape Digimon TCG data from BTCG+"

    def add_arguments(self, parser):
        parser.add_argument("sets", nargs="*")
        parser.add_argument("--dry-run", dest="dry_run", action="store_true")

    def handle(self, *args, **options):
        sets: list[str] = options["sets"]
        sets = [s.upper() for s in sets]

        # gather list of sets to scrape, error if invalid set is found
        btcgp_set_ids = []
        for s in sets:
            if s not in BTCGP_SET_IDS:
                raise CommandError(f"Invalid set ID: {s}")
            btcgp_set_ids.extend(BTCGP_SET_IDS[s])

        # get or create each set within the database
        set_cache = {}
        for set in SETS:
            # skip set creation if doing a dry run
            if options["dry_run"]:
                break

            obj, created = models.Set.objects.get_or_create(
                number=set.number,
                name=set.name,
                release_date=set.release_date,
            )
            set_cache[obj.number] = obj

            if created:
                self.stdout.write(f"CREATE {obj}")
            else:
                self.stdout.write(f"EXISTS {obj}")

        # exist early if no specific sets were provided
        if not btcgp_set_ids:
            return

        known_cards = {c.number: c for c in models.Card.objects.all()}

        found_cards = get_card_list(btcgp_set_ids)
        found_cards = sorted(found_cards, key=lambda c: c["card_number"])
        found_cards = groupby(found_cards, key=lambda c: c["card_number"])
        found_cards = {number: list(cards) for number, cards in found_cards}

        # check for new cards / update card images
        new_card_ids = []
        for number, cards in found_cards.items():
            # check if card is already known (or doing a dry run)
            obj = known_cards.get(number)
            if not obj or options["dry_run"]:
                new_card_ids.append(cards[0]["id"])
                continue

            # check for new images / alt arts
            images = [c["image_url"] for c in cards]
            images = sorted(images, key=len)
            if not images:
                continue

            # update images / alt arts
            obj.images = images
            obj.save()

            self.stdout.write(f"EXISTS {obj}")

        # fetch details for new cards
        cards = get_all_details(new_card_ids)
        for card in cards:
            # normalize card data
            card = norm_card(card)

            # print and continue if doing a dry run
            if options["dry_run"]:
                card = {k: v for k, v in card._asdict().items() if v}
                pprint(card)
                continue

            # collect and sort images / alt arts
            images = [c["image_url"] for c in found_cards[card.number]]
            images = sorted(images, key=len)

            set = set_cache[card.set]
            obj = models.Card(
                set=set,
                number=card.number,
                name=card.name,
                rarity=card.rarity,
                type=card.type,
                color=card.color,
                images=images,
            )
            try:
                obj.save()
                self.stdout.write(f"CREATE {obj}")
            except:
                self.stdout.write(f"ERROR {card}")
