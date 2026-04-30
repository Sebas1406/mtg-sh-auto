from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.export_report_data import export_report
from automation.render_tiktok_assets import TEMPLATES_DIR, TEMPLATE_NAME, load_json, render_report_async
from automation.run_daily_pipeline import build_queue_entry


REPORT_TEMPLATE = """# Celes, Rune Knight

- Fecha de generacion: {date}
- Hora de generacion: {time}
- Bracket objetivo: 4
- Nota de bracket: Este bracket fue asignado manualmente para una prueba completa programada del flujo.
- Tipo de juego: Mardu reanimator de discard selectivo, persist combo y value de cementerio
- Dificultad: Alta
- Precio actual en Card Kingdom: $12.99
- Fuente de precio: https://www.cardkingdom.com/mtg/commander-final-fantasy/celes-rune-knight

## Resumen

Celes filtra la mano en cuanto entra y recompensa las lineas donde criaturas vuelven desde el cementerio o se lanzan desde ahi. El plan es descartar piezas pesadas o persist creatures temprano, reanimarlas con eficiencia y convertir cada vuelta desde el graveyard en counters, triggers de sacrificio y cierre por combo o combate.

## Commander

- Nombre: Celes, Rune Knight
- Coste de mana: {{1}}{{R}}{{W}}{{B}}
- Identidad de color: R, W, B
- Tipo de carta: Legendary Creature - Human Wizard Knight
- Texto relevante: Cuando Celes entra, descarta cualquier numero de cartas y luego roba esa cantidad mas una. Siempre que una o mas otras criaturas entren bajo tu control, si al menos una entro desde un cementerio o fue lanzada desde un cementerio, pon un contador +1/+1 sobre cada criatura que controlas.
- Fuente del commander: https://scryfall.com/search?q=%21%22Celes%2C+Rune+Knight%22

## Plan de juego

### Early game
Prioriza piezas baratas de seleccion y cementerio como Faithless Looting, Stitcher's Supplier, Priest of Fell Rites y los talismanes. Celes quiere entrar con al menos una criatura util para descartar y algun reanimation spell listo para convertir su ETB en ventaja real.

### Mid game
El mazo despega cuando empiezas a reciclar persist creatures, value bodies y amenazas grandes. Ashnod's Altar, Goblin Bombardment, Pitiless Plunderer y los sac outlets convierten cada vuelta del cementerio en mana, dano o cartas mientras Celes crece la mesa.

### Late game
La partida se cierra con lineas de persist como Murderous Redcap o Lesser Masticore mas sac outlet, con Living Death para reconstruir de golpe o con una mesa enorme que ya recibio multiples oleadas de counters. Si hace falta grindear, Rune-Scarred Demon, Sun Titan y Archon of Cruelty sostienen el valor.

## Decklist

### Commander
1x Celes, Rune Knight

### Criaturas
1x Priest of Fell Rites
1x Anger
1x Putrid Goblin
1x Murderous Redcap
1x Lesser Masticore
1x Obstinate Gargoyle
1x Viscera Seer
1x Carrion Feeder
1x Blood Artist
1x Elas il-Kor, Sadistic Pilgrim
1x Pitiless Plunderer
1x Imperial Recruiter
1x Ranger-Captain of Eos
1x Grand Abolisher
1x Esper Sentinel
1x Stitcher's Supplier
1x Archon of Cruelty
1x Sun Titan
1x Abdel Adrian, Gorion's Ward
1x Solemn Simulacrum
1x Combustible Gearhulk
1x Flayer of the Hatebound
1x Rune-Scarred Demon
1x Puppeteer Clique
1x Karmic Guide
1x Alesha, Who Smiles at Death
1x Garna, Bloodfist of Keld
1x Dockside Chef

### Artefactos
1x Sol Ring
1x Arcane Signet
1x Orzhov Signet
1x Rakdos Signet
1x Boros Signet
1x Talisman of Hierarchy
1x Talisman of Indulgence
1x Talisman of Conviction
1x Ashnod's Altar
1x Blasting Station
1x Skullclamp

### Encantamientos
1x Goblin Bombardment
1x Outpost Siege
1x Phyrexian Arena
1x Animate Dead
1x Necromancy
1x Dance of the Dead
1x Bastion of Remembrance
1x Impact Tremors

### Instantaneos
1x Swords to Plowshares
1x Path to Exile
1x Chaos Warp
1x Anguished Unmaking
1x Wear // Tear
1x Boros Charm
1x Village Rites
1x Deadly Dispute

### Conjuros
1x Faithless Looting
1x Thrilling Discovery
1x Persist
1x Victimize
1x Unburial Rites
1x Buried Alive
1x Dread Return
1x Blasphemous Act
1x Living Death
1x Sevinne's Reclamation
1x Jeska's Will

### Tierras
1x Command Tower
1x Nomad Outpost
1x Savai Triome
1x Clifftop Retreat
1x Dragonskull Summit
1x Isolated Chapel
1x Temple of Silence
1x Temple of Malice
1x Temple of Triumph
1x Godless Shrine
1x Blood Crypt
1x Sacred Foundry
1x Caves of Koilos
1x Battlefield Forge
1x Sulfurous Springs
1x Path of Ancestry
1x Exotic Orchard
1x Vault of Champions
1x Spectator Seating
1x Luxury Suite
1x Fabled Passage
1x Evolving Wilds
1x Terramorphic Expanse
1x Myriad Landscape
1x Takenuma, Abandoned Mire
1x Sokenzan, Crucible of Defiance
1x Eiganjo, Seat of the Empire
1x Plains
1x Plains
1x Swamp
1x Swamp
1x Mountain
1x Mountain

## Notas de construccion

- Esta prueba esta pensada para validar una ejecucion totalmente programada desde generacion local hasta envio a TikTok.
- La lista busca una mezcla de lineas honestas de reanimator con un paquete de persist suficientemente claro para que el contenido visual tenga identidad.
- Celes hace que descartar amenazas no sea un costo tan duro porque el mazo esta construido para explotarlo enseguida.

## Riesgos y puntos debiles

- El mazo puede atascarse si roba reanimation sin objetivos o payoffs sin enablers de descarte.
- Los efectos de hate al cementerio frenan mucho el plan principal y obligan a ganar por valor mas lento.
- Exige ordenar bien triggers y recursos; una secuencia mal medida puede gastar el turno entero sin cerrar.

## Fuentes

- Scryfall: https://scryfall.com/search?q=%21%22Celes%2C+Rune+Knight%22
- Card Kingdom: https://www.cardkingdom.com/mtg/commander-final-fantasy/celes-rune-knight
"""


def write_report(now: datetime) -> Path:
    report_id = f"{now.strftime('%Y-%m-%d-%H%M')}-celes-rune-knight"
    path = ROOT / "reports" / f"{report_id}.md"
    content = REPORT_TEMPLATE.format(date=now.strftime("%Y-%m-%d"), time=now.strftime("%H:%M"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


async def render_single_report(json_path: Path) -> None:
    data = load_json(json_path)
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template(TEMPLATE_NAME)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            await render_report_async(browser, template, data, ROOT / "tiktok_assets" / data["report_id"])
        finally:
            await browser.close()


def main() -> None:
    now = datetime.now()
    report_path = write_report(now)
    json_path = export_report(report_path)
    asyncio.run(render_single_report(json_path))
    queue_path = build_queue_entry()
    payload = json.loads(queue_path.read_text(encoding="utf-8"))
    print(json.dumps({"report_path": str(report_path), "json_path": str(json_path), "queue_path": str(queue_path), "report_id": payload["report_id"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
