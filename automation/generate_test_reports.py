from __future__ import annotations

import json
import textwrap
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
BASIC_LANDS = {"plains", "island", "swamp", "mountain", "forest", "wastes"}


@dataclass
class ReportSpec:
    commander: str
    slug: str
    timestamp: str
    bracket: int
    playstyle: str
    difficulty: str
    summary: str
    early_game: str
    mid_game: str
    late_game: str
    build_notes: list[str]
    weaknesses: list[str]
    price_value: str
    price_url: str
    sections: dict[str, list[str]]


TEST_REPORTS: list[ReportSpec] = [
    ReportSpec(
        commander="Sythis, Harvest's Hand",
        slug="sythis-harvests-hand",
        timestamp="2026-04-27 08:00",
        bracket=2,
        playstyle="Enchantress de mesa estable, value incremental y tokens evasivos",
        difficulty="Media",
        summary=(
            "Sythis convierte cada encantamiento en robo y vida, asi que el plan es encadenar "
            "permanentes baratos, proteger la mesa y cerrar la partida con tokens, auras enormes "
            "o un lock suave de impuestos."
        ),
        early_game=(
            "Bajar a Sythis pronto y priorizar encantamientos de aceleracion como Wild Growth, "
            "Utopia Sprawl y Fertile Ground para empezar a robar mientras desarrollas mana."
        ),
        mid_game=(
            "Con dos o tres motores de encantamientos en mesa, estabiliza con Ghostly Prison, "
            "Authority of the Consuls y removal en forma de encantamiento mientras amplias tu mano."
        ),
        late_game=(
            "Cierra con Sigil of the Empty Throne, Hallowed Haunting, Ancestral Mask o una mesa "
            "intocable con Sphere of Safety y Mirari's Wake."
        ),
        build_notes=[
            "Bracket 2 asignado aleatoriamente por la automatizacion para esta prueba.",
            "La lista prioriza permanentes baratos, consistencia y presion gradual en lugar de combos explosivos.",
            "La curva esta cargada en costes 1 a 4 para aprovechar al maximo cada disparo de Sythis.",
        ],
        weaknesses=[
            "Sufre contra wipes repetidos si no encuentra recursion.",
            "Depende bastante del commander para mantener el flujo de cartas.",
        ],
        price_value="$4.49",
        price_url="https://www.cardkingdom.com/mtg/modern-horizons-2/sythis-harvests-hand?partner_args=Sythis%2C+Harvest%27s+Hand+%5BMH2%5D",
        sections={
            "Criaturas": [
                "Sanctum Weaver",
                "Setessan Champion",
                "Eidolon of Blossoms",
                "Satyr Enchanter",
                "Sram, Senior Edificer",
                "Jukai Naturalist",
                "Destiny Spinner",
                "Herald of the Pantheon",
                "Mesa Enchantress",
                "Calix, Guided by Fate",
                "Archon of Sun's Grace",
                "Starfield Mystic",
                "Spirited Companion",
                "Weaver of Harmony",
                "Danitha, New Benalia's Light",
                "Ajani's Chosen",
                "Dryad of the Ilysian Grove",
                "Kami of Transience",
            ],
            "Artefactos": [
                "Sol Ring",
                "Arcane Signet",
                "Selesnya Signet",
                "Swiftfoot Boots",
                "Lightning Greaves",
                "Thought Vessel",
                "Skullclamp",
            ],
            "Encantamientos": [
                "Wild Growth",
                "Utopia Sprawl",
                "Fertile Ground",
                "Overgrowth",
                "Smothering Tithe",
                "Ghostly Prison",
                "Sterling Grove",
                "Greater Auramancy",
                "Blind Obedience",
                "Authority of the Consuls",
                "Abundant Growth",
                "Kenrith's Transformation",
                "Darksteel Mutation",
                "Seal of Cleansing",
                "Seal of Primordium",
                "Sigil of the Empty Throne",
                "Hallowed Haunting",
                "Sphere of Safety",
                "Ethereal Armor",
                "All That Glitters",
                "Ancestral Mask",
                "Felidar Retreat",
                "Mirari's Wake",
                "Song of the Dryads",
                "Court of Grace",
            ],
            "Instantaneos": [
                "Swords to Plowshares",
                "Generous Gift",
                "Heroic Intervention",
                "Teferi's Protection",
            ],
            "Conjuros": [
                "Cultivate",
                "Kodama's Reach",
                "Open the Armory",
                "Idyllic Tutor",
                "Retether",
                "Brilliant Restoration",
                "Austere Command",
                "Harmonize",
            ],
            "Tierras": [
                "Command Tower",
                "Temple Garden",
                "Sunpetal Grove",
                "Canopy Vista",
                "Fortified Village",
                "Scattered Groves",
                "Brushland",
                "Razorverge Thicket",
                "Wooded Bastion",
                "Overgrown Farmland",
                "Branchloft Pathway // Boulderloft Pathway",
                "Myriad Landscape",
                "Hall of Heliod's Generosity",
                "Command Beacon",
                "Boseiju, Who Endures",
                "Eiganjo, Seat of the Empire",
                "Nykthos, Shrine to Nyx",
                "Yavimaya, Cradle of Growth",
                "Temple of Plenty",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Plains",
                "Plains",
                "Plains",
                "Plains",
                "Plains",
                "Plains",
                "Plains",
                "Plains",
                "Plains",
            ],
        },
    ),
    ReportSpec(
        commander="Brago, King Eternal",
        slug="brago-king-eternal",
        timestamp="2026-04-27 08:01",
        bracket=3,
        playstyle="Blink azorius de control blando y acumulacion de ETB",
        difficulty="Media-Alta",
        summary=(
            "Brago busca conectar en combate para resetear permanentes propios y explotar "
            "habilidades de entrada al campo de batalla. La lista mezcla value, taxes ligeros "
            "y cierre por ventaja abrumadora."
        ),
        early_game=(
            "Acelera con rocas, baja criaturas de valor como Thraben Inspector o Wall of Omens "
            "y prepara una ventana segura para que Brago ataque."
        ),
        mid_game=(
            "Cuando Brago conecta, recicla ETB de robo, removal y mana rocks para despegar en "
            "cartas y tempo. Strionic Resonator y Panharmonicon amplifican mucho la mesa."
        ),
        late_game=(
            "La partida se cierra por attrition con Sun Titan, Approach of the Second Sun o una "
            "mesa imposible de remontar gracias a blink repetido de Stonehorn Dignitary y Meteor Golem."
        ),
        build_notes=[
            "Bracket 3 asignado aleatoriamente por la automatizacion para esta prueba.",
            "La lista evita loops infinitos como Strionic Resonator mas mana infinito, aunque mantiene piezas potentes.",
            "El mazo recompensa mucha planificacion de triggers y secuencias de combate.",
        ],
        weaknesses=[
            "Si Brago no puede conectar, el mazo pierde gran parte de su explosividad.",
            "Las mesas muy rapidas o con mucho removal puntual pueden frenarlo al inicio.",
        ],
        price_value="$3.49",
        price_url="https://www.cardkingdom.com/mtg/kaldheim-commander-decks/brago-king-eternal",
        sections={
            "Criaturas": [
                "Thraben Inspector",
                "Spirited Companion",
                "Charming Prince",
                "Wall of Omens",
                "Watcher for Tomorrow",
                "Aether Channeler",
                "Reflector Mage",
                "Stonehorn Dignitary",
                "Inspiring Overseer",
                "Solemn Simulacrum",
                "Recruiter of the Guard",
                "Archaeomancer",
                "Elite Guardmage",
                "Mulldrifter",
                "Peregrine Drake",
                "Felidar Guardian",
                "Restoration Angel",
                "Yorion, Sky Nomad",
                "Cloudblazer",
                "Angel of Condemnation",
                "Meteor Golem",
                "Sun Titan",
                "Aerial Extortionist",
                "Scholar of the Ages",
            ],
            "Artefactos": [
                "Sol Ring",
                "Arcane Signet",
                "Azorius Signet",
                "Talisman of Progress",
                "Thought Vessel",
                "Mind Stone",
                "Wayfarer's Bauble",
                "Commander's Sphere",
                "Strionic Resonator",
                "Panharmonicon",
                "Conjurer's Closet",
                "Swiftfoot Boots",
                "Lightning Greaves",
            ],
            "Encantamientos": [
                "Teleportation Circle",
                "Omen of the Sea",
                "Touch the Spirit Realm",
                "Propaganda",
                "Ghostly Prison",
                "Mystic Remora",
            ],
            "Instantaneos": [
                "Swords to Plowshares",
                "Path to Exile",
                "Counterspell",
                "Dovin's Veto",
                "Ephemerate",
                "Ghostly Flicker",
                "Eerie Interlude",
            ],
            "Conjuros": [
                "Ponder",
                "Preordain",
                "Windfall",
                "Fabricate",
                "Supreme Verdict",
                "Cleansing Nova",
                "Time Wipe",
                "Approach of the Second Sun",
                "Dance of the Manse",
                "Austere Command",
            ],
            "Planeswalkers": [
                "Teferi, Time Raveler",
            ],
            "Tierras": [
                "Command Tower",
                "Prairie Stream",
                "Port Town",
                "Glacial Fortress",
                "Hallowed Fountain",
                "Adarkar Wastes",
                "Seachrome Coast",
                "Deserted Beach",
                "Irrigated Farmland",
                "Skycloud Expanse",
                "Temple of Enlightenment",
                "Nimbus Maze",
                "Mystic Gate",
                "Celestial Colonnade",
                "Hall of Heliod's Generosity",
                "Reliquary Tower",
                "Rogue's Passage",
                "Myriad Landscape",
                "Evolving Wilds",
                "Terramorphic Expanse",
                "Azorius Chancery",
                "Tranquil Cove",
                "Secluded Steppe",
                "Lonely Sandbar",
                "Plains",
                "Plains",
                "Plains",
                "Plains",
                "Plains",
                "Plains",
                "Plains",
                "Plains",
                "Island",
                "Island",
                "Island",
                "Island",
                "Island",
                "Island",
            ],
        },
    ),
    ReportSpec(
        commander="Prosper, Tome-Bound",
        slug="prosper-tome-bound",
        timestamp="2026-04-27 08:02",
        bracket=4,
        playstyle="Rakdos de tesoros y cartas desde el exilio con turns de value explosivo",
        difficulty="Alta",
        summary=(
            "Prosper convierte impulsive draw en mana real. El mazo busca encadenar cartas desde "
            "el exilio, multiplicar tesoros y terminar la mesa con drenaje, burst damage o turns "
            "largos apoyados en artefactos."
        ),
        early_game=(
            "Desarrolla rocas y efectos baratos de exilio temporal como Reckless Impulse para que "
            "Prosper empiece a generar tesoros en cuanto entre."
        ),
        mid_game=(
            "Apila triggers de treasure con Professional Face-Breaker, Xorn, Rain of Riches y "
            "Nalfeshnee para convertir cada turno en una cadena de recursos."
        ),
        late_game=(
            "Bolas's Citadel, Marionette Master, Mayhem Devil o Etali suelen cerrar cuando ya "
            "tienes una masa critica de tesoros y cartas jugables desde el exilio."
        ),
        build_notes=[
            "Bracket 4 asignado aleatoriamente por la automatizacion para esta prueba.",
            "La lista mantiene lineas fuertes de valor y cierre, pero no esta planteada como cEDH.",
            "Requiere administrar bien timing, mana flotante y ventanas para jugar cartas exiliadas.",
        ],
        weaknesses=[
            "El mazo puede vaciarse si gasta demasiados recursos antes de estabilizar la mesa.",
            "Las piezas de odio contra artefactos o tesoros reducen bastante su techo explosivo.",
        ],
        price_value="$24.99",
        price_url="https://www.cardkingdom.com/mtg/adventures-in-the-forgotten-realms-commander-decks-variants/prosper-tome-bound-extended-art",
        sections={
            "Criaturas": [
                "Birgi, God of Storytelling // Harnfel, Horn of Bounty",
                "Professional Face-Breaker",
                "Reckless Fireweaver",
                "Ingenious Artillerist",
                "Disciple of the Vault",
                "Nadier's Nightblade",
                "Mayhem Devil",
                "Xorn",
                "Grim Hireling",
                "Dire Fleet Daredevil",
                "Gonti, Lord of Luxury",
                "Chaos Channeler",
                "Laelia, the Blade Reforged",
                "Wild-Magic Sorcerer",
                "Storm-Kiln Artist",
                "Academy Manufactor",
                "Nalfeshnee",
                "Atsushi, the Blazing Sky",
                "Etali, Primal Storm",
                "Solemn Simulacrum",
                "Marionette Master",
                "Keeper of Secrets",
                "Lobelia, Defender of Bag End",
                "Chittering Witch",
            ],
            "Artefactos": [
                "Sol Ring",
                "Arcane Signet",
                "Rakdos Signet",
                "Talisman of Indulgence",
                "Thought Vessel",
                "Mind Stone",
                "Wayfarer's Bauble",
                "Commander's Sphere",
                "Lightning Greaves",
                "Swiftfoot Boots",
                "The Reaver Cleaver",
                "Bolas's Citadel",
                "Treasure Map // Treasure Cove",
            ],
            "Encantamientos": [
                "Outpost Siege",
                "Black Market Connections",
                "Rain of Riches",
                "Passionate Archaeologist",
                "Visions of Phyrexia",
                "Theater of Horrors",
                "Curse of Opulence",
            ],
            "Instantaneos": [
                "Deadly Dispute",
                "Big Score",
                "Unexpected Windfall",
                "Terminate",
                "Bedevil",
                "Chaos Warp",
                "Abrade",
                "Village Rites",
            ],
            "Conjuros": [
                "Jeska's Will",
                "Reckless Impulse",
                "Wrenn's Resolve",
                "Light Up the Stage",
                "Seize the Spoils",
                "Feed the Swarm",
                "Sign in Blood",
                "Read the Bones",
                "Blasphemous Act",
                "Ignite the Future",
                "Reforge the Soul",
                "Night's Whisper",
            ],
            "Tierras": [
                "Command Tower",
                "Luxury Suite",
                "Haunted Ridge",
                "Dragonskull Summit",
                "Foreboding Ruins",
                "Smoldering Marsh",
                "Temple of Malice",
                "Canyon Slough",
                "Tainted Peak",
                "Sulfurous Springs",
                "Blightstep Pathway // Searstep Pathway",
                "Shadowblood Ridge",
                "Path of Ancestry",
                "Command Beacon",
                "Exotic Orchard",
                "Myriad Landscape",
                "Spinerock Knoll",
                "Takenuma, Abandoned Mire",
                "Sokenzan, Crucible of Defiance",
                "Reliquary Tower",
                "War Room",
                "Swamp",
                "Swamp",
                "Swamp",
                "Swamp",
                "Swamp",
                "Swamp",
                "Swamp",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
            ],
        },
    ),
    ReportSpec(
        commander="Goreclaw, Terror of Qal Sisma",
        slug="goreclaw-terror-of-qal-sisma",
        timestamp="2026-04-27 08:03",
        bracket=3,
        playstyle="Mono green stompy con aceleracion agresiva y remates por sobrecarga de combate",
        difficulty="Baja-Media",
        summary=(
            "Goreclaw abarata amenazas grandes y convierte cada combate ancho en un martillazo. "
            "La idea es rampear pronto, encadenar criaturas enormes y cerrar con uno o dos ataques."
        ),
        early_game=(
            "El mazo quiere abrir con dorks y ramp barato para bajar a Goreclaw cuanto antes y "
            "empezar a reducir el coste de las amenazas pesadas."
        ),
        mid_game=(
            "Cada bicho grande entra antes de curva y roba cartas con Garruk's Uprising, Elemental "
            "Bond y Guardian Project, manteniendo la presion constante."
        ),
        late_game=(
            "Finale of Devastation, Overwhelming Stampede, Pathbreaker Ibex o Decimator of the "
            "Provinces convierten una mesa ya desarrollada en un cierre inmediato."
        ),
        build_notes=[
            "Bracket 3 asignado aleatoriamente por la automatizacion para esta prueba.",
            "La lista es directa y muy funcional para mesas casuales que disfrutan de combate.",
            "Se priorizo redundancia de ramp y robo antes que paquetes de combo.",
        ],
        weaknesses=[
            "Puede sufrir bastante contra wipes encadenados si no roba un motor de cartas.",
            "Tiene menos interaccion puntual que listas verdes mas sofisticadas.",
        ],
        price_value="$1.29",
        price_url="https://www.cardkingdom.com/mtg/commander-masters/goreclaw-terror-of-qal-sisma",
        sections={
            "Criaturas": [
                "Llanowar Elves",
                "Elvish Mystic",
                "Birds of Paradise",
                "Sakura-Tribe Elder",
                "Whisperer of the Wilds",
                "Paradise Druid",
                "Llanowar Tribe",
                "Somberwald Sage",
                "Reclamation Sage",
                "Eternal Witness",
                "Beast Whisperer",
                "Toski, Bearer of Secrets",
                "Steel Leaf Champion",
                "Old-Growth Troll",
                "Yorvo, Lord of Garenbrig",
                "Yeva, Nature's Herald",
                "Ulvenwald Oddity // Ulvenwald Behemoth",
                "Surrak and Goreclaw",
                "Acidic Slime",
                "Ulvenwald Hydra",
                "Kogla, the Titan Ape",
                "Pathbreaker Ibex",
                "Avenger of Zendikar",
                "World Breaker",
                "Bane of Progress",
                "Apex Altisaur",
                "End-Raze Forerunners",
                "Terastodon",
                "Decimator of the Provinces",
                "Gigantosaurus",
                "Ghalta, Primal Hunger",
                "Vorinclex, Voice of Hunger",
                "Elder Gargaroth",
            ],
            "Artefactos": [
                "Sol Ring",
                "Arcane Signet",
                "Thought Vessel",
                "Mind Stone",
                "Commander's Sphere",
                "Swiftfoot Boots",
                "Lightning Greaves",
                "Emerald Medallion",
                "Lifecrafter's Bestiary",
            ],
            "Encantamientos": [
                "Garruk's Uprising",
                "Elemental Bond",
                "Tribute to the World Tree",
                "Greater Good",
                "Guardian Project",
                "Asceticism",
                "Zendikar Resurgent",
            ],
            "Instantaneos": [
                "Heroic Intervention",
                "Return of the Wildspeaker",
                "Beast Within",
                "Tamiyo's Safekeeping",
            ],
            "Conjuros": [
                "Cultivate",
                "Kodama's Reach",
                "Three Visits",
                "Nature's Lore",
                "Harmonize",
                "Rishkar's Expertise",
                "Overwhelming Stampede",
                "Finale of Devastation",
                "Green Sun's Zenith",
                "Traverse the Outlands",
            ],
            "Tierras": [
                "Command Tower",
                "Castle Garenbrig",
                "Nykthos, Shrine to Nyx",
                "Rogue's Passage",
                "Oran-Rief, the Vastwood",
                "Mosswort Bridge",
                "Yavimaya, Cradle of Growth",
                "Boseiju, Who Endures",
                "Blighted Woodland",
                "Myriad Landscape",
                "War Room",
                "Reliquary Tower",
                "Lair of the Hydra",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
                "Forest",
            ],
        },
    ),
    ReportSpec(
        commander="Torbran, Thane of Red Fell",
        slug="torbran-thane-of-red-fell",
        timestamp="2026-04-27 08:04",
        bracket=5,
        playstyle="Mono red de dano incremental, pingers y remates explosivos",
        difficulty="Media",
        summary=(
            "Torbran transforma cualquier chispa, ping o trigger en una amenaza real. El plan es "
            "llenar la mesa de fuentes pequenas de dano y luego multiplicar su impacto con lord "
            "effects y encantamientos de dano."
        ),
        early_game=(
            "Despliega mana rocks y permanentes baratos que peguen de uno en uno para que Torbran "
            "convierta esos disparos pequenos en presion inmediata."
        ),
        mid_game=(
            "Con Torbran en mesa, cada ataque, ping y spell de burn escala muy rapido. Las piezas "
            "de wheel y impulsive draw evitan que te quedes sin gas."
        ),
        late_game=(
            "Fiery Emancipation, Angrath's Marauders, Toralf o un wipe como Blasphemous Act con "
            "Brash Taunter suelen funcionar como cierres de una sola secuencia."
        ),
        build_notes=[
            "Bracket 5 asignado aleatoriamente por la automatizacion para esta prueba.",
            "Aunque no es cEDH, esta version si busca cierres muy violentos y castiga mesas lentas.",
            "La curva es compacta para que Torbran entre rapido y convierta cada topdeck en alcance.",
        ],
        weaknesses=[
            "Si Torbran se neutraliza varias veces, muchas cartas vuelven a ser dano modesto.",
            "Los mazos con mucha ganancia de vida pueden exigir un cierre explosivo en vez de attrition.",
        ],
        price_value="$6.49",
        price_url="https://www.cardkingdom.com/mtg/throne-of-eldraine/torbran-thane-of-red-fell",
        sections={
            "Criaturas": [
                "Goblin Arsonist",
                "Vulshok Sorcerer",
                "Kessig Flamebreather",
                "Thermo-Alchemist",
                "Firebrand Archer",
                "Sardian Avenger",
                "Runaway Steam-Kin",
                "Birgi, God of Storytelling // Harnfel, Horn of Bounty",
                "Professional Face-Breaker",
                "Guttersnipe",
                "Dualcaster Mage",
                "Tectonic Giant",
                "Embermaw Hellion",
                "Atsushi, the Blazing Sky",
                "Treasonous Ogre",
                "Magus of the Wheel",
                "Brash Taunter",
                "Chandra's Incinerator",
                "Neheb, the Eternal",
                "Toralf, God of Fury // Toralf's Hammer",
                "Rampaging Ferocidon",
                "Immolation Shaman",
                "Angrath's Marauders",
            ],
            "Artefactos": [
                "Sol Ring",
                "Arcane Signet",
                "Mind Stone",
                "Thought Vessel",
                "Fire Diamond",
                "Ruby Medallion",
                "Wayfarer's Bauble",
                "Lightning Greaves",
                "Swiftfoot Boots",
                "Caged Sun",
                "Gauntlet of Power",
                "Extraplanar Lens",
                "Basilisk Collar",
                "Skullclamp",
            ],
            "Encantamientos": [
                "Impact Tremors",
                "Roiling Vortex",
                "Burning Earth",
                "Furnace of Rath",
                "Fiery Emancipation",
                "Court of Ire",
                "Warstorm Surge",
                "Valakut Exploration",
                "Mana Barbs",
                "Urabrask's Saga",
            ],
            "Instantaneos": [
                "Lightning Bolt",
                "Abrade",
                "Chaos Warp",
                "Bolt Bend",
                "Comet Storm",
                "Reverberate",
                "Seething Song",
                "Wild Magic Surge",
                "Shatterskull Smashing // Shatterskull, the Hammer Pass",
            ],
            "Conjuros": [
                "Blasphemous Act",
                "Chain Reaction",
                "Jeska's Will",
                "Faithless Looting",
                "Light Up the Stage",
                "Reckless Impulse",
                "Wrenn's Resolve",
                "Wheel of Misfortune",
            ],
            "Tierras": [
                "Valakut, the Molten Pinnacle",
                "Hanweir Battlements",
                "Sokenzan, Crucible of Defiance",
                "Spinerock Knoll",
                "Den of the Bugbear",
                "Castle Embereth",
                "Buried Ruin",
                "Myriad Landscape",
                "Dwarven Mine",
                "War Room",
                "Reliquary Tower",
                "Flamekin Village",
                "Forgotten Cave",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
                "Mountain",
            ],
        },
    ),
]


def fetch_commander_card(name: str) -> dict:
    url = f"https://api.scryfall.com/cards/named?exact={urllib.parse.quote(name)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "codex-mtg-agent/0.1",
            "Accept": "application/json;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def validate_report(spec: ReportSpec) -> None:
    cards = []
    for section_cards in spec.sections.values():
        cards.extend(section_cards)

    total = len(cards) + 1
    if total != 100:
        raise ValueError(f"{spec.commander}: total {total} en vez de 100")

    seen: set[str] = set()
    for card in cards:
        key = card.lower()
        if key in BASIC_LANDS:
            continue
        if key in seen:
            raise ValueError(f"{spec.commander}: carta duplicada detectada: {card}")
        seen.add(key)


def bullet_lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def numbered_lines(items: list[str]) -> str:
    return "\n".join(f"1x {item}" for item in items)


def build_markdown(spec: ReportSpec, card: dict) -> str:
    color_identity = ", ".join(card.get("color_identity", [])) or "Incolora"
    oracle_text = card.get("oracle_text", "").replace("\n", " ").replace("—", "-")
    type_line = card.get("type_line", "").replace("—", "-")
    sections_md = []
    for section_name, cards in spec.sections.items():
        sections_md.append(f"### {section_name}\n{numbered_lines(cards)}")
    sections_block = "\n\n".join(sections_md)
    lines = [
        f"# {spec.commander}",
        "",
        f"- Fecha de generacion: {spec.timestamp.split()[0]}",
        f"- Hora de generacion: {spec.timestamp.split()[1]}",
        f"- Bracket objetivo: {spec.bracket}",
        "- Nota de bracket: Este bracket fue asignado aleatoriamente por la automatizacion para fines del proyecto.",
        f"- Tipo de juego: {spec.playstyle}",
        f"- Dificultad: {spec.difficulty}",
        f"- Precio actual en Card Kingdom: {spec.price_value}",
        f"- Fuente de precio: {spec.price_url}",
        "",
        "## Resumen",
        "",
        spec.summary,
        "",
        "## Commander",
        "",
        f"- Nombre: {spec.commander}",
        f"- Coste de mana: {card.get('mana_cost', '')}",
        f"- Identidad de color: {color_identity}",
        f"- Tipo de carta: {type_line}",
        f"- Texto relevante: {oracle_text}",
        f"- Fuente del commander: {card.get('scryfall_uri', '')}",
        "",
        "## Plan de juego",
        "",
        "### Early game",
        spec.early_game,
        "",
        "### Mid game",
        spec.mid_game,
        "",
        "### Late game",
        spec.late_game,
        "",
        "## Decklist",
        "",
        "### Commander",
        f"1x {spec.commander}",
        "",
        sections_block,
        "",
        "## Notas de construccion",
        "",
        bullet_lines(spec.build_notes),
        "",
        "## Riesgos y puntos debiles",
        "",
        bullet_lines(spec.weaknesses),
        "",
        "## Fuentes",
        "",
        f"- Scryfall: {card.get('scryfall_uri', '')}",
        f"- Card Kingdom: {spec.price_url}",
    ]
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for spec in TEST_REPORTS:
        validate_report(spec)
        card = fetch_commander_card(spec.commander)
        filename = f"{spec.timestamp.split()[0]}-{spec.timestamp.split()[1].replace(':', '')}-{spec.slug}.md"
        path = REPORTS_DIR / filename
        path.write_text(build_markdown(spec, card), encoding="utf-8")
        written.append(path.name)

    print("Generated reports:")
    for name in written:
        print(name)


if __name__ == "__main__":
    main()
