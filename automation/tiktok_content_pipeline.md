# TikTok Content Pipeline

Este documento define la segunda fase del proyecto: convertir cada informe Markdown de Commander en 5 imagenes verticales listas para publicar en TikTok.

## Objetivo

Por cada archivo en `reports/` se generara:

- un archivo JSON estructurado en `report_data/`
- una carpeta de assets visuales en `tiktok_assets/`
- cinco imagenes PNG verticales de `1080x1920`

## Estructura de carpetas

```text
reports/
report_data/
tiktok_assets/
automation/
```

## Flujo recomendado

1. La automatizacion principal genera el informe Markdown en `reports/`.
2. `export_report_data.py` lee el Markdown, lo normaliza y lo enriquece con datos de Scryfall.
3. El script guarda un JSON por informe en `report_data/`.
4. `render_tiktok_assets.py` lee ese JSON y produce 5 imagenes PNG en `tiktok_assets/<report-stem>/`.

## Esquema JSON propuesto

Cada archivo JSON debe contener como minimo:

```json
{
  "report_id": "2026-04-27-0800-sythis-harvests-hand",
  "source_markdown": "C:/.../reports/2026-04-27-0800-sythis-harvests-hand.md",
  "generated_at": "2026-04-27 08:00",
  "commander": {
    "name": "Sythis, Harvest's Hand",
    "mana_cost": "{G}{W}",
    "type_line": "Legendary Enchantment Creature — Nymph",
    "oracle_text": "...",
    "color_identity": ["G", "W"],
    "image_url": "https://..."
  },
  "summary": "...",
  "bracket": 2,
  "bracket_note": "...",
  "playstyle": "...",
  "difficulty": "Media",
  "price": {
    "value": "$4.49",
    "source_url": "https://..."
  },
  "gameplan": {
    "early": "...",
    "mid": "...",
    "late": "..."
  },
  "deck_sections": {
    "Criaturas": [],
    "Artefactos": [],
    "Encantamientos": [],
    "Instantaneos": [],
    "Conjuros": [],
    "Planeswalkers": [],
    "Tierras": []
  },
  "cards": [
    {
      "name": "Sol Ring",
      "quantity": 1,
      "section": "Artefactos",
      "role": "ramp",
      "mana_cost": "{1}",
      "type_line": "Artifact",
      "image_url": "https://...",
      "scryfall_uri": "https://..."
    }
  ]
}
```

## Roles funcionales recomendados

Para TikTok funciona mejor agrupar por funcion que por tipo de carta. Los roles sugeridos son:

- `ramp`
- `draw`
- `interaction`
- `protection`
- `value`
- `tokens`
- `recursion`
- `finisher`
- `utility_land`
- `core_synergy`
- `support`

## Distribucion recomendada de las 5 slides

### Slide 1

Portada del mazo:

- arte del commander
- nombre
- bracket
- estilo de juego
- dificultad
- precio
- resumen corto

### Slide 2

Base del mazo:

- ramp
- robo
- interaccion
- proteccion
- hasta 6 cartas clave con miniatura

### Slide 3

Motor del mazo:

- sinergias principales
- hasta 6 cartas del rol `core_synergy`, `value` o `tokens`

### Slide 4

Cierres y presion:

- finishers
- recursion
- piezas de ventaja tardia

### Slide 5

Plan final:

- early game
- mid game
- late game
- riesgos o puntos debiles

## Automatizacion objetivo

La automatizacion diaria de las 8:00 deberia ejecutar:

1. generacion del informe Markdown
2. exportacion del JSON estructurado
3. render de las 5 imagenes
4. validacion de salida en `tiktok_assets/`

## Criterios de exito

- cada Markdown produce exactamente un JSON
- cada JSON produce exactamente 5 PNG
- si una imagen de carta falla, el renderer usa placeholder en vez de detener el pipeline
- los nombres de salida deben conservar el `report_id`
