from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.export_report_data import export_report
from automation.render_tiktok_assets import TEMPLATES_DIR, TEMPLATE_NAME, load_json, render_report_async
from automation.run_daily_pipeline import build_caption


ASSETS_DIR = ROOT / "tiktok_assets"
QUEUE_DIR = ROOT / "publish_queue"


@dataclass(frozen=True)
class CommanderSpec:
    key: str
    commander: str
    bracket: int
    playstyle: str
    difficulty: str
    price_value: str
    price_url: str
    summary: str
    early: str
    mid: str
    late: str
    notes: list[str]
    risks: list[str]
    deck_sections: dict[str, list[str]]


SPECS: dict[str, CommanderSpec] = {
    "kaalia": CommanderSpec(
        key="kaalia",
        commander="Kaalia of the Vast",
        bracket=4,
        playstyle="Mardu cheat fatties de angeles, demonios y dragones con presion explosiva",
        difficulty="Media",
        price_value="$14.99",
        price_url="https://www.cardkingdom.com/mtg/commander/kaalia-of-the-vast",
        summary="Kaalia convierte cada ataque en una amenaza gigante gratis. El plan es proteger al commander, atacar una sola vez sin trabas y llenar la mesa con angels, demons y dragons que normalmente llegarian demasiado tarde.",
        early="Abre con rocas y proteccion. Kaalia casi siempre quiere entrar con botas o mana abierto para evitar perder el turno completo a un removal barato.",
        mid="Cuando Kaalia conecta, el mazo despega con bodies enormes y triggers de combate. Cada turno fuerza respuestas muy concretas de la mesa.",
        late="Si los ataques siguen entrando, la partida se inclina sola. Incluso despues de un wipe, el deck puede reconstruir con reanimation puntual o volver a presionar con otra gran amenaza.",
        notes=["Rotacion diaria nueva para evitar comandantes ya publicados.","La lista prioriza impacto inmediato y amenazas faciles de explicar en TikTok.","Kaalia necesita poca mesa previa, asi que el hook del contenido llega rapido."],
        risks=["Depende mucho de que Kaalia ataque al menos una vez.","Removal puntual o taxes altos pueden frenar el plan.","Sin aceleracion, la mano puede verse pesada."],
        deck_sections={
            "Criaturas": ["Avacyn, Angel of Hope","Aurelia, the Warleader","Balefire Dragon","Archfiend of Despair","Rakdos the Defiler","Terror of the Peaks","Gisela, Blade of Goldnight","Angel of Despair","Rune-Scarred Demon","Master of Cruelties","Sephara, Sky's Blade","Hellkite Tyrant","Ancient Brass Dragon","Bloodgift Demon","Lyra Dawnbringer"],
            "Artefactos": ["Sol Ring","Arcane Signet","Boros Signet","Orzhov Signet","Rakdos Signet","Lightning Greaves","Swiftfoot Boots","Talisman of Conviction"],
            "Encantamientos": ["Sneak Attack","Necromancy","Animate Dead","Phyrexian Arena"],
            "Instantaneos": ["Swords to Plowshares","Path to Exile","Anguished Unmaking","Boros Charm","Deflecting Swat"],
            "Conjuros": ["Reanimate","Victimize","Blasphemous Act","Faithless Looting","Sevinne's Reclamation"],
            "Tierras": ["Command Tower","Nomad Outpost","Savai Triome","Vault of Champions","Luxury Suite","Spectator Seating","Godless Shrine","Blood Crypt","Sacred Foundry","Plains","Swamp","Mountain"],
        },
    ),
    "chulane": CommanderSpec(
        key="chulane",
        commander="Chulane, Teller of Tales",
        bracket=4,
        playstyle="Bant creature combo-light de value, bounce y desarrollo abrumador",
        difficulty="Alta",
        price_value="$7.99",
        price_url="https://www.cardkingdom.com/mtg/throne-of-eldraine/chulane-teller-of-tales",
        summary="Chulane convierte cada criatura en carta, tierra y tempo. El mazo encadena ETB creatures, efectos de rebote y ramp hasta que la mesa ya no puede seguir el ritmo.",
        early="Acelera con dorks y criaturas baratas de valor. Chulane quiere entrar cuando todavia puedes jugar otra criatura ese mismo turno.",
        mid="Con Chulane activo, cada body barato roba y pone tierras. El mazo crece la mano, la mesa y el mana al mismo tiempo.",
        late="El cierre llega con Craterhoof, con value imposible de remontar o con lineas de bounce repetido que convierten la mesa en una maquina de cartas.",
        notes=["Comandante nuevo en la rotacion diaria completa.","El arquetipo genera clips muy claros de snowball y value incremental.","No depende de una sola linea de combo para verse poderoso."],
        risks=["Si Chulane cuesta demasiado mana varias veces, el ritmo baja bastante.","Wraths repetidos castigan la sobreextension.","Puede jugar turnos largos si se sobrecarga de triggers."],
        deck_sections={
            "Criaturas": ["Birds of Paradise","Llanowar Elves","Coiling Oracle","Wall of Blossoms","Whitemane Lion","Shrieking Drake","Eternal Witness","Knight of Autumn","Aether Channeler","Elvish Visionary","Reflector Mage","Beast Whisperer","Tireless Provisioner","Oracle of Mul Daya","End-Raze Forerunners"],
            "Artefactos": ["Sol Ring","Arcane Signet","Simic Signet","Selesnya Signet","Azorius Signet"],
            "Encantamientos": ["Guardian Project","Rhystic Study","Smothering Tithe","Aura Shards"],
            "Instantaneos": ["Swords to Plowshares","Cyclonic Rift","Beast Within","Heroic Intervention"],
            "Conjuros": ["Cultivate","Kodama's Reach","Finale of Devastation","Green Sun's Zenith","Time Wipe"],
            "Tierras": ["Command Tower","Breeding Pool","Temple Garden","Hallowed Fountain","Exotic Orchard","Yavimaya Coast","Adarkar Wastes","Brushland","Forest","Island","Plains"],
        },
    ),
    "giada": CommanderSpec(
        key="giada",
        commander="Giada, Font of Hope",
        bracket=3,
        playstyle="Mono white angels de curva limpia, counters y superioridad aerea",
        difficulty="Media",
        price_value="$3.49",
        price_url="https://www.cardkingdom.com/mtg/streets-of-new-capenna/giada-font-of-hope",
        summary="Giada acelera a los angeles y hace que todos entren sobredimensionados. El mazo busca una curva elegante de amenazas voladoras que escalan solas con cada nuevo cuerpo.",
        early="Giada en turno dos es ideal. Desde ahi, cualquier angel entra antes de tiempo y con counters extra.",
        mid="La mesa se llena de amenazas evasivas con lifelink, vigilancia o anthem natural. El rival empieza a perder carreras rapidamente.",
        late="Un par de angeles grandes o una pieza como Lyra bastan para cerrar por aire. El deck gana por consistencia y presion, no por loops complejos.",
        notes=["Perfecto para un flujo diario porque la identidad visual del deck es muy clara.","La curva de juego es facil de leer y mostrar en slides.","Cada angel nuevo hace mejor al siguiente."],
        risks=["Las wraths limpian mucho valor acumulado.","Mono white puede quedarse corto de robo si no aparecen motores.","Depende del combate para cerrar."],
        deck_sections={
            "Criaturas": ["Resplendent Angel","Youthful Valkyrie","Righteous Valkyrie","Inspiring Overseer","Serra Paragon","Archangel of Tithes","Lyra Dawnbringer","Angel of Jubilation","Baneslayer Angel","Sunblast Angel","Sephara, Sky's Blade","Angel of Serenity","Emeria Shepherd","Metropolis Reformer","Herald of War"],
            "Artefactos": ["Sol Ring","Arcane Signet","Pearl Medallion","Mind Stone","Herald's Horn","Skullclamp"],
            "Encantamientos": ["Smothering Tithe","Marshal's Anthem","Sigarda's Splendor","Luminarch Ascension"],
            "Instantaneos": ["Swords to Plowshares","Path to Exile","Clever Concealment","Flawless Maneuver"],
            "Conjuros": ["Wrath of God","Austere Command","Cosmic Intervention","Open the Armory"],
            "Tierras": ["Emeria, the Sky Ruin","Nykthos, Shrine to Nyx","War Room","Myriad Landscape","Eiganjo, Seat of the Empire","Plains","Plains","Plains","Plains","Plains","Plains"],
        },
    ),
    "yarok": CommanderSpec(
        key="yarok",
        commander="Yarok, the Desecrated",
        bracket=4,
        playstyle="Sultai ETB de value duplicado, ramp y control por permanentes",
        difficulty="Media-Alta",
        price_value="$5.99",
        price_url="https://www.cardkingdom.com/mtg/core-set-2020/yarok-the-desecrated",
        summary="Yarok duplica los ETB y convierte criaturas y tierras utilitarias en absurdos motores de ventaja. El plan es rampear, encadenar permanentes de valor y dejar que cada entrada al campo valga por dos.",
        early="Ramp y setup con criaturas de utilidad. Yarok entra mejor cuando ya hay algo listo para duplicar inmediatamente.",
        mid="Coiling Oracle, Mulldrifter, Ravenous Chupacabra y Tireless Provisioner escalan fortisimo bajo Yarok. El tablero empieza a jugar por dos jugadores a la vez.",
        late="El cierre llega por value imposible de responder, por Avenger of Zendikar duplicado o por loops de ETB con bounce y reanimation ligera.",
        notes=["Nuevo comandante para la rotacion automatica.","Muy util para contenido visual porque los dobles triggers son faciles de vender.","El mazo se ve poderoso incluso sin remates de combo."],
        risks=["Sin Yarok, varias cartas son solo justas.","Removal al commander en respuesta a ETBs importantes puede cortar el impulso.","La curva puede ponerse pesada si faltan piezas de ramp."],
        deck_sections={
            "Criaturas": ["Coiling Oracle","Solemn Simulacrum","Eternal Witness","Ravenous Chupacabra","Mulldrifter","Tireless Provisioner","Tireless Tracker","Acidic Slime","Gray Merchant of Asphodel","Avenger of Zendikar","Agent of Treachery","Shriekmaw","Wood Elves","Springbloom Druid","Oracle of Mul Daya"],
            "Artefactos": ["Sol Ring","Arcane Signet","Dimir Signet","Golgari Signet","Simic Signet"],
            "Encantamientos": ["Guardian Project","Panharmonicon","Deadbridge Chant","Necromancy"],
            "Instantaneos": ["Beast Within","Hero's Downfall","Cyclonic Rift","Reality Shift"],
            "Conjuros": ["Cultivate","Kodama's Reach","Casualties of War","Living Death","Finale of Devastation"],
            "Tierras": ["Command Tower","Zagoth Triome","Watery Grave","Breeding Pool","Overgrown Tomb","Rejuvenating Springs","Undergrowth Stadium","Morphic Pool","Bojuka Bog","Field of the Dead","Forest","Island","Swamp"],
        },
    ),
    "omnath": CommanderSpec(
        key="omnath",
        commander="Omnath, Locus of Rage",
        bracket=4,
        playstyle="Gruul landfall de elementales, ramp explosivo y dano de salida",
        difficulty="Media",
        price_value="$2.49",
        price_url="https://www.cardkingdom.com/mtg/battle-for-zendikar/omnath-locus-of-rage",
        summary="Omnath convierte cada tierra en un 5/5 y cada elemental muerto en daño directo. El mazo gana por masa de permanentes, explosiones de landfall y castigo cuando la mesa intenta limpiarte.",
        early="Ramp clasico con hechizos de tierras. Omnath no necesita presionar pronto: necesita llegar con muchas tierras por delante.",
        mid="Cuando Omnath entra, cualquier fetch, Harrow o Scapeshift se convierte en una lluvia de elementales. La mesa cambia de escala de inmediato.",
        late="La partida se cierra por alpha strike o porque los elementales muertos disparan suficiente daño para rematar. Incluso los wipes del rival pueden ser peligrosos para ellos.",
        notes=["Nuevo comandante para la diaria automatica.","Landfall y tokens grandes dan material muy claro para los slides.","Omnath convierte recursos basicos en un cierre muy visible."],
        risks=["La curva alta exige mucho ramp para verse realmente poderosa.","Sin payoff de tierras extra, algunas manos pueden ser lentas.","Exilio masivo evita parte del daño de salida."],
        deck_sections={
            "Criaturas": ["Lotus Cobra","Tireless Provisioner","Tireless Tracker","Springbloom Druid","Mina and Denn, Wildborn","Oracle of Mul Daya","Ancient Greenwarden","Avenger of Zendikar","Rampaging Baloths","Terror of the Peaks","Moraug, Fury of Akoum","Titania, Protector of Argoth","World Shaper","Scute Swarm","Dockside Extortionist"],
            "Artefactos": ["Sol Ring","Arcane Signet","Gruul Signet","Swiftfoot Boots","Crucible of Worlds"],
            "Encantamientos": ["Valakut Exploration","Warstorm Surge","Zendikar's Roil","Burgeoning"],
            "Instantaneos": ["Harrow","Beast Within","Heroic Intervention","Chaos Warp"],
            "Conjuros": ["Cultivate","Kodama's Reach","Migration Path","Explosive Vegetation","Scapeshift","Splendid Reclamation","Blasphemous Act"],
            "Tierras": ["Command Tower","Stomping Ground","Cinder Glade","Rockfall Vale","Game Trail","Sheltered Thicket","Temple of Abandon","Valakut, the Molten Pinnacle","Field of the Dead","Fabled Passage","Myriad Landscape","Forest","Forest","Mountain","Mountain","Mountain"],
        },
    ),
    "meren": CommanderSpec(
        key="meren",
        commander="Meren of Clan Nel Toth",
        bracket=4,
        playstyle="Golgari sacrifice de recursion incremental y toolbox de cementerio",
        difficulty="Media-Alta",
        price_value="$8.49",
        price_url="https://www.cardkingdom.com/mtg/commander-2015/meren-of-clan-nel-toth",
        summary="Meren convierte cada sacrificio en experiencia y cada experiencia en recursion gratis. El plan es ciclar criaturas de valor, drenar recursos de la mesa y convertir el cementerio en una segunda mano que nunca se acaba.",
        early="Abre con mana dorks, Stitcher's Supplier, Sakura-Tribe Elder y un sac outlet barato. Meren quiere que el cementerio empiece a trabajar desde turno dos o tres.",
        mid="Cuando Meren entra, cada criatura de utilidad se vuelve repetible. Plaguecrafter, Eternal Witness, Ravenous Chupacabra y Skullwinder te dan removal y valor sin gastar la mano.",
        late="La partida se cierra por loops de sacrificio, por aristocrats con Blood Artist o Zulaport Cutthroat, o por una masa de ventaja imposible de seguir con Living Death y reanimator pesado.",
        notes=[
            "Prueba programada para validar generacion completa y publicacion sin intervencion manual.",
            "La lista se centra en criaturas de valor y recursion repetible por encima de explosiones de combo rapido.",
            "El cementerio es parte central del plan, asi que casi todas las cartas malas en mano se convierten en recurso futuro.",
        ],
        risks=[
            "Rest in Peace y otros efectos de hate al cementerio reducen mucho el techo del mazo.",
            "Sin sac outlet, Meren pierde bastante control sobre el ritmo de recursion.",
            "Puede verse lenta si no encuentra aceleracion o formas de llenar el grave temprano.",
        ],
        deck_sections={
            "Criaturas": [
                "Llanowar Elves","Elvish Mystic","Stitcher's Supplier","Viscera Seer","Carrion Feeder","Sakura-Tribe Elder","Satyr Wayfinder",
                "Blood Artist","Zulaport Cutthroat","Skullwinder","Priest of Forgotten Gods","Reclamation Sage","Eternal Witness",
                "Wood Elves","Yavimaya Elder","Fleshbag Marauder","Plaguecrafter","Grim Haruspex","Midnight Reaper","Pitiless Plunderer",
                "Woe Strider","Merciless Executioner","Ravenous Chupacabra","Sidisi, Undead Vizier","Gray Merchant of Asphodel","Protean Hulk",
            ],
            "Artefactos": ["Sol Ring","Arcane Signet","Golgari Signet","Skullclamp","Altar of Dementia","Ashnod's Altar","Birthing Pod"],
            "Encantamientos": ["Animate Dead","Necromancy","Moldervine Reclamation","Survival of the Fittest","Greater Good","Phyrexian Reclamation"],
            "Instantaneos": ["Assassin's Trophy","Abrupt Decay","Beast Within","Village Rites","Deadly Dispute","Krosan Grip"],
            "Conjuros": ["Cultivate","Kodama's Reach","Buried Alive","Victimize","Living Death","Final Parting","Demonic Tutor"],
            "Tierras": ["Command Tower","Llanowar Wastes","Undergrowth Stadium","Temple of Malady","Woodland Cemetery","Necroblossom Snarl","Bojuka Bog","Myriad Landscape","Nurturing Peatland","Takenuma, Abandoned Mire","Castle Locthwain","Forest","Forest","Forest","Forest","Swamp","Swamp","Swamp","Swamp"],
        },
    ),
    "isshin": CommanderSpec(
        key="isshin",
        commander="Isshin, Two Heavens as One",
        bracket=4,
        playstyle="Mardu attack triggers de presion ancha, tokens y snowball de combate",
        difficulty="Media",
        price_value="$4.99",
        price_url="https://www.cardkingdom.com/mtg/kamigawa-neon-dynasty-commander/isshin-two-heavens-as-one",
        summary="Isshin dobla los triggers de ataque y convierte cada paso de combate en una explosion de valor. El mazo presiona con tokens, anthems temporales y criaturas que castigan a la mesa por dejarte atacar libremente.",
        early="Busca rocas, una o dos amenazas de coste bajo y algo que produzca valor al atacar. El primer objetivo es que Isshin llegue con mesa ya montada.",
        mid="Con Isshin en campo, Adeline, Hero of Bladehold, Anim Pakal y Myrel generan demasiada presencia para cualquier mesa casual-media. Cada ataque empieza a parecer un turno extra.",
        late="La partida se cierra con Shared Animosity, Adriana o ataques repetidos que disparan enteros de tokens y drains. Si la mesa se traba, Reconnaissance y la ventaja incremental hacen el resto.",
        notes=[
            "Prueba de flujo completo usando un comandante centrado en combate y triggers visibles para TikTok.",
            "La lista prioriza secuencias de ataque claras y cartas que escalan fuerte con Isshin pero siguen sirviendo sin el commander.",
            "Las cartas fueron escogidas para generar slides con identidad visual y ganchos faciles de explicar.",
        ],
        risks=[
            "Wraths en el momento justo pueden dejarte sin inercia.",
            "El mazo sufre si Isshin cuesta demasiado mana varias veces seguidas.",
            "Mesas con pillow-fort o muchos bloqueadores obligan a cerrar por valor en lugar de alpha strike.",
        ],
        deck_sections={
            "Criaturas": [
                "Esper Sentinel","Professional Face-Breaker","Anim Pakal, Thousandth Moon","Krenko, Tin Street Kingpin","Adeline, Resplendent Cathar","Hero of Bladehold",
                "Myrel, Shield of Argive","Alesha, Who Smiles at Death","Adriana, Captain of the Guard","Brutal Hordechief","Skyknight Vanguard","Hanweir Garrison",
                "Loyal Apprentice","Captain Lannery Storm","Caesar, Legion's Emperor","Firemane Commando","Tectonic Giant","Aurelia, the Warleader","Combat Celebrant","Drana, Liberator of Malakir",
            ],
            "Artefactos": ["Sol Ring","Arcane Signet","Boros Signet","Orzhov Signet","Rakdos Signet","Skullclamp","Sword of the Animist","Lightning Greaves"],
            "Encantamientos": ["Impact Tremors","Shared Animosity","Reconnaissance","Fervent Charge","Assemble the Legion"],
            "Instantaneos": ["Swords to Plowshares","Path to Exile","Anguished Unmaking","Boros Charm","Chaos Warp","Wear // Tear"],
            "Conjuros": ["Jeska's Will","Blasphemous Act","Spectacular Showdown","Seize the Day","Faithless Looting","Damn"],
            "Tierras": ["Command Tower","Nomad Outpost","Savai Triome","Clifftop Retreat","Dragonskull Summit","Isolated Chapel","Battlefield Forge","Caves of Koilos","Sulfurous Springs","Vault of Champions","Spectator Seating","Luxury Suite","Myriad Landscape","Rogue's Passage","Plains","Plains","Swamp","Swamp","Mountain","Mountain"],
        },
    ),
    "tatyova": CommanderSpec(
        key="tatyova",
        commander="Tatyova, Benthic Druid",
        bracket=3,
        playstyle="Simic lands value de ramp constante, robo facil y cierre por ventaja abrumadora",
        difficulty="Media",
        price_value="$0.89",
        price_url="https://www.cardkingdom.com/mtg/dominaria/tatyova-benthic-druid",
        summary="Tatyova hace que cada tierra sea cantrip y ganancia de vida, asi que el mazo simplemente convierte ramp en cartas reales. La partida se gana por volumen: mas mana, mas tierras, mas permanentes y mas turnos relevantes que nadie mas.",
        early="Ramp clasico con Cultivate, Sakura-Tribe Scout y rocas ligeras. La idea es que Tatyova entre cuando ya puedes bajar una tierra extra o activar algo en el mismo turno.",
        mid="Con Tatyova activa, cartas como Growth Spiral, Explore, Roiling Regrowth y los bounce lands transforman el deck en una cadena de robo casi continua.",
        late="Field of the Dead, Avenger of Zendikar, Scute Swarm o una Hydroid Krasis gigante cierran la mesa. No hace falta combo si el motor de tierras ya produjo demasiadas cartas.",
        notes=[
            "Esta prueba usa un arquetipo facil de seguir visualmente y muy consistente para contenido corto.",
            "La lista esta enfocada en valor puro de tierras, no en turns infinitos ni piezas de combo duras.",
            "Tatyova es ideal para mostrar metricas de presupuesto, cartas clave y crecimiento del plan.",
        ],
        risks=[
            "Sin Tatyova, varias piezas de ramp se sienten menos explosivas.",
            "Puede perder ritmo contra estrategias mucho mas rapidas o con heavy land hate.",
            "Exceso de ramp sin payoff puede hacer turnos poderosos pero poco decisivos.",
        ],
        deck_sections={
            "Criaturas": ["Lotus Cobra","Sakura-Tribe Scout","Azusa, Lost but Seeking","Courser of Kruphix","Ramunap Excavator","Tireless Provisioner","Tireless Tracker","Coiling Oracle","Scute Swarm","Aesi, Tyrant of Gyre Strait","Oracle of Mul Daya","Avenger of Zendikar","Roil Elemental","Eternal Witness","Hydroid Krasis"],
            "Artefactos": ["Sol Ring","Arcane Signet","Simic Signet","Wayfarer's Bauble","Exploration Map"],
            "Encantamientos": ["Burgeoning","Exploration","Retreat to Coralhelm","Zendikar's Roil","Guardian Project"],
            "Instantaneos": ["Growth Spiral","Crop Rotation","Roiling Regrowth","Beast Within","Pongify","Reality Shift"],
            "Conjuros": ["Cultivate","Kodama's Reach","Nature's Lore","Three Visits","Explosive Vegetation","Urban Evolution","Boundless Realms","Finale of Devastation"],
            "Tierras": ["Command Tower","Breeding Pool","Hinterland Harbor","Yavimaya Coast","Temple of Mystery","Dreamroot Cascade","Simic Growth Chamber","Misty Rainforest","Fabled Passage","Field of the Dead","Reliquary Tower","Mystic Sanctuary","Bojuka Bog","Forest","Forest","Forest","Forest","Island","Island","Island","Island"],
        },
    ),
    "wilhelt": CommanderSpec(
        key="wilhelt",
        commander="Wilhelt, the Rotcleaver",
        bracket=4,
        playstyle="Dimir zombies de sacrificio, recursion y grind constante",
        difficulty="Media",
        price_value="$2.99",
        price_url="https://www.cardkingdom.com/mtg/innistrad-midnight-hunt-commander/wilhelt-the-rotcleaver",
        summary="Wilhelt convierte cada zombie muerto en otro cuerpo y hace que la mesa nunca se quede sin material. El plan es atacar o sacrificar fichas, recargar mano al final del turno y ahogar a la mesa con recursion y triggers de muerte.",
        early="Baja zombies baratos, un sac outlet y alguna pieza de draw o mana. Wilhelt entra mejor cuando ya tienes algo que transformar en Decayed y una forma de aprovecharlo.",
        mid="Diregraf Captain, Headless Rider, Cryptbreaker y The Meathook Massacre convierten cada intercambio en ventaja. Los tokens Decayed dejan de ser un problema cuando se usan para robar, drenar o volver a poblar la mesa.",
        late="Zombie Apocalypse, Patriarch's Bidding o Living Death reconstruyen el board de golpe. Si la mesa no limpia, Rooftop Storm y las sinergias tribales terminan enterrando a todos por volumen.",
        notes=[
            "El arquetipo de zombies es muy estable para pruebas programadas porque siempre produce mesa y hooks visuales claros.",
            "La lista mezcla tribal clasico con sacrifice value para que Wilhelt tenga decisiones reales y no solo flood de criaturas.",
            "Los triggers de muerte ayudan a convertir incluso una derrota de mesa en contenido interesante.",
        ],
        risks=[
            "Sin un motor de robo, el deck puede llenarse de cuerpos medianos sin remate claro.",
            "Hate al cementerio o exile masivo afectan la capacidad de reconstruccion.",
            "Los tokens Decayed presionan menos si no aparecen anthem effects o drain pieces.",
        ],
        deck_sections={
            "Criaturas": ["Cryptbreaker","Champion of the Perished","Diregraf Ghoul","Lazotep Reaver","Undead Augur","Headless Rider","Diregraf Captain","Death Baron","Lord of the Accursed","Cemetery Reaper","Midnight Reaper","Plague Belcher","Gravecrawler","Relentless Dead","Liliana's Standard Bearer","Murderous Rider","Geralf, Visionary Stitcher","Noxious Ghoul","Gray Merchant of Asphodel","Sidisi, Undead Vizier"],
            "Artefactos": ["Sol Ring","Arcane Signet","Dimir Signet","Skullclamp","Ashnod's Altar","Altar of Dementia"],
            "Encantamientos": ["Rooftop Storm","The Meathook Massacre","Kindred Discovery","Open the Graves"],
            "Instantaneos": ["Counterspell","Reality Shift","Infernal Grasp","Go for the Throat","Negate"],
            "Conjuros": ["Zombie Apocalypse","Patriarch's Bidding","Living Death","Victimize","Dread Summons","Feed the Swarm"],
            "Tierras": ["Command Tower","Watery Grave","Drowned Catacomb","Choked Estuary","Shipwreck Marsh","Temple of Deceit","Underground River","Sunken Hollow","Path of Ancestry","Bojuka Bog","Takenuma, Abandoned Mire","Otawara, Soaring City","Island","Island","Swamp","Swamp","Swamp","Swamp"],
        },
    ),
    "feather": CommanderSpec(
        key="feather",
        commander="Feather, the Redeemed",
        bracket=3,
        playstyle="Boros spellslinger de trucos reciclables, heroic y tempo agresivo",
        difficulty="Media",
        price_value="$1.79",
        price_url="https://www.cardkingdom.com/mtg/war-of-the-spark/feather-the-redeemed",
        summary="Feather convierte cada truco barato en una carta repetible, asi que el mazo juega casi como si tuviera una mano eterna. El plan es proteger amenazas, crecer criaturas y generar ventaja al recastear los mismos hechizos turno tras turno.",
        early="Busca una o dos criaturas que premien ser objetivo y prepara mana abierto. Feather quiere entrar con protección o con al menos un spell de valor listo para recuperar.",
        mid="Defiant Strike, Shelter, Expedite y Reckless Rage se vuelven absurdos cuando regresan a tu mano al final del turno. Young Pyromancer y Monastery Mentor convierten esa rutina en mesa real.",
        late="El cierre suele llegar por una criatura enorme con double strike, por un turno de storm ligero con múltiples cantrips o por una mesa ancha de tokens respaldada por protección constante.",
        notes=[
            "Feather es una buena prueba de control porque mezcla velocidad, resiliencia y spells cortos muy visibles en las slides.",
            "La lista prioriza reciclaje de trucos y presencia en mesa por encima de combos poco interactivas.",
            "Cada turno deja recursos abiertos, asi que la percepcion de tempo es parte importante del atractivo del deck.",
        ],
        risks=[
            "Si Feather no permanece en mesa, la mano puede vaciarse rapido.",
            "Los wipes globales castigan mucho si la proteccion no aparece a tiempo.",
            "Contra mazos muy grandes, ganar por daño de combate puede requerir varias secuencias impecables.",
        ],
        deck_sections={
            "Criaturas": ["Monastery Swiftspear","Soul-Scar Mage","Dreadhorde Arcanist","Tenth District Legionnaire","Akroan Crusader","Leonin Lightscribe","Young Pyromancer","Monastery Mentor","Illuminator Virtuoso","Storm-Kiln Artist","Seasoned Pyromancer","Zada, Hedron Grinder","Dualcaster Mage","Defiant Vanguard","Benevolent Bodyguard"],
            "Artefactos": ["Sol Ring","Arcane Signet","Boros Signet","Talisman of Conviction","Swiftfoot Boots","Sunforger"],
            "Encantamientos": ["Defiant Strike","Launch the Fleet","Impact Tremors","Sentinel Tower"],
            "Instantaneos": ["Gods Willing","Shelter","Emerge Unscathed","Expedite","Acceleration","Titan's Strength","Reckless Rage","Boros Charm","Ajani's Presence","Temur Battle Rage"],
            "Conjuros": ["Faithless Looting","Seize the Day","Twinferno","Reckless Impulse","Wrenn's Resolve","Blasphemous Act"],
            "Tierras": ["Command Tower","Sacred Foundry","Clifftop Retreat","Battlefield Forge","Sunbaked Canyon","Temple of Triumph","Needleverge Pathway // Pillarverge Pathway","Furycalm Snarl","Den of the Bugbear","Eiganjo, Seat of the Empire","Sokenzan, Crucible of Defiance","Plains","Plains","Mountain","Mountain","Mountain","Mountain"],
        },
    ),
}


def bullet_lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def numbered_lines(items: list[str]) -> str:
    return "\n".join(f"1x {item}" for item in items)


def build_markdown(spec: CommanderSpec, now: datetime) -> str:
    sections = []
    for section_name, cards in spec.deck_sections.items():
        sections.append(f"### {section_name}\n{numbered_lines(cards)}")
    sections_block = "\n\n".join(sections)
    return (
        f"# {spec.commander}\n\n"
        f"- Fecha de generacion: {now.strftime('%Y-%m-%d')}\n"
        f"- Hora de generacion: {now.strftime('%H:%M')}\n"
        f"- Bracket objetivo: {spec.bracket}\n"
        "- Nota de bracket: Esta prueba fue programada automaticamente para validar el flujo completo local y remoto.\n"
        f"- Tipo de juego: {spec.playstyle}\n"
        f"- Dificultad: {spec.difficulty}\n"
        f"- Precio actual en Card Kingdom: {spec.price_value}\n"
        f"- Fuente de precio: {spec.price_url}\n\n"
        "## Resumen\n\n"
        f"{spec.summary}\n\n"
        "## Commander\n\n"
        f"- Nombre: {spec.commander}\n"
        "- Coste de mana: se completa desde Scryfall en la exportacion\n"
        "- Identidad de color: se completa desde Scryfall en la exportacion\n"
        "- Tipo de carta: se completa desde Scryfall en la exportacion\n"
        "- Texto relevante: se completa desde Scryfall en la exportacion\n"
        f"- Fuente del commander: https://scryfall.com/search?q=%21%22{spec.commander.replace(' ', '+').replace(',', '%2C')}%22\n\n"
        "## Plan de juego\n\n"
        f"### Early game\n{spec.early}\n\n"
        f"### Mid game\n{spec.mid}\n\n"
        f"### Late game\n{spec.late}\n\n"
        "## Decklist\n\n"
        f"### Commander\n1x {spec.commander}\n\n"
        f"{sections_block}\n\n"
        "## Notas de construccion\n\n"
        f"{bullet_lines(spec.notes)}\n\n"
        "## Riesgos y puntos debiles\n\n"
        f"{bullet_lines(spec.risks)}\n\n"
        "## Fuentes\n\n"
        f"- Scryfall: https://scryfall.com/search?q=%21%22{spec.commander.replace(' ', '+').replace(',', '%2C')}%22\n"
        f"- Card Kingdom: {spec.price_url}\n"
    )


async def render_single_report(json_path: Path) -> None:
    data = load_json(json_path)
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=select_autoescape(["html"]))
    template = env.get_template(TEMPLATE_NAME)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            await render_report_async(browser, template, data, ASSETS_DIR / data["report_id"])
        finally:
            await browser.close()


def build_queue_entry_for_report(json_path: Path) -> Path:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    asset_dir = ASSETS_DIR / data["report_id"]
    pngs = sorted(asset_dir.glob("*.png"))
    if len(pngs) != 5:
        raise RuntimeError(f"Expected 5 PNG files in {asset_dir}, found {len(pngs)}.")

    payload = {
        "report_id": data["report_id"],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "timezone": "America/Lima",
        "publish_times": {"daily": "07:00"},
        "caption": build_caption(data),
        "commander": data.get("commander", {}).get("name", ""),
        "cover_image": str(pngs[0].resolve()),
        "images": [str(path.resolve()) for path in pngs],
        "status": "ready_for_publish",
        "notes": [
            "Generated from scheduled control test flow.",
            "Images are ready for TikTok photo post publishing.",
        ],
    }
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    queue_path = QUEUE_DIR / f"{data['report_id']}.json"
    queue_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return queue_path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: python {Path(__file__).name} <key>")

    key = sys.argv[1].strip().lower()
    if key not in SPECS:
        raise SystemExit(f"Unknown commander key: {key}. Available: {', '.join(sorted(SPECS))}")

    spec = SPECS[key]
    now = datetime.now()
    report_id = f"{now.strftime('%Y-%m-%d-%H%M')}-{spec.commander.lower().replace(',', '').replace(' ', '-')}"
    report_path = ROOT / "reports" / f"{report_id}.md"
    report_path.write_text(build_markdown(spec, now), encoding="utf-8")

    json_path = export_report(report_path)
    asyncio.run(render_single_report(json_path))
    queue_path = build_queue_entry_for_report(json_path)

    print(json.dumps({"report_id": report_id, "report_path": str(report_path), "json_path": str(json_path), "queue_path": str(queue_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
