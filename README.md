# MTG Commander Builder Automation

Automatización local que selecciona un commander aleatorio desde el universo vivo de Scryfall, construye y valida una lista completa de 100 cartas, genera un informe útil para deck builders y prepara un carrusel en inglés para TikTok.

## Principio operativo

El commander se elige aleatoriamente. La decklist no.

`deck_manifests/<report_id>.json` es la fuente de verdad. Ningún informe, imagen o queue item puede publicarse si no coincide con ese manifest y con una validación aprobada.

## Flujo diario

La tarea de Windows `MTG SH Full Generate And Publish Daily` se ejecuta todos los días a las 08:00, hora de Lima:

1. Scryfall selecciona una carta con `legal:commander is:commander game:paper -is:funny -is:digital`.
2. Se resuelve una configuración legal cuando la selección requiere Background, Partner with o Doctor's companion.
3. EDHREC aporta señales de sinergia y popularidad.
4. La página oficial de Commander aporta la lista viva de Game Changers.
5. El constructor arma exactamente 100 cartas por roles, curva, fuentes de color y utilidad.
6. El validador revisa legalidad, color identity, singleton, commander configuration, cantidad, mana, composición y bracket.
7. Solamente después de un `pass` se generan el informe, el decklist importable, seis slides y la cola.
8. La puerta final comprueba hashes, assets y cartas mostradas antes de cualquier push o publicación.

Entrada principal:

```powershell
powershell -ExecutionPolicy Bypass -File automation/run_full_daily_publish.ps1
```

Generación local sin finalizar/publicar:

```powershell
python automation/generate_random_daily_commander_bundle.py
```

## Artefactos

- `commander_selection_runs/`: evidencia del sorteo y configuración resuelta.
- `deck_manifests/`: lista canónica completa.
- `deck_validation/`: puertas, errores, fuentes de mana y estado final.
- `moxfield_decklists_100/`: listas completas listas para importar.
- `reports/`: informe Commander Builder V2 en Markdown inglés.
- `report_data/`: JSON enriquecido del informe.
- `tiktok_assets/`: seis PNG verticales por deck.
- `publish_queue/`: payload hash-locked.
- `legal-site/media/`: JPG públicos utilizados por TikTok.
- `publish_runs/`: resultados de publicación.

## Puertas críticas

La publicación queda bloqueada si ocurre cualquiera de estas condiciones:

- el total no es exactamente 100;
- una carta está fuera de la color identity;
- una carta no es paper-legal en Commander;
- existe una repetición no permitida;
- la configuración de commanders no es válida;
- nombre, Oracle ID o datos de Scryfall no coinciden;
- faltan lands, fuentes de color o roles funcionales;
- hay demasiados slots de una sola función o demasiadas cartas de coste alto;
- el deck viola su bracket o el límite de Game Changers;
- la política oficial no pudo actualizarse;
- los hashes del manifest, validation, report y queue no coinciden;
- una carta mostrada no pertenece a la lista completa;
- no existen exactamente seis imágenes.

No existe bypass para errores críticos. `ALLOW_SHADOW_BUNDLE=1` solamente permite verificar localmente una cola `shadow_ready`; nunca la habilita para TikTok.

## Report V2

Todo el contenido público está en inglés y sigue una dirección visual cálida de taberna, limpia y centrada en la construcción del deck:

1. Deck Promise
2. Deck Skeleton
3. Core Engine
4. Mana & Cards
5. Answers & Protection
6. How It Wins

El carrusel muestra 16 cartas estratégicamente importantes con una razón concreta. La lista completa permanece disponible en el export de 100 cartas.

## Verificación

```powershell
python -m unittest discover -s tests -v
python -m compileall -q automation tiktok_integration
python automation/stage_tiktok_media.py <report_id>
python automation/verify_publish_bundle.py <report_id>
```

Documentación detallada:

- `automation/commander_report_spec.md`
- `automation/tiktok_content_pipeline.md`
- `automation/automation_prompt.md`

## Publicación

`automation/finalize_and_publish_bundle.ps1` convierte los PNG a JPG, ejecuta la puerta final, prepara los artefactos auditables, hace commit y push. GitHub Pages publica las imágenes y el workflow de TikTok consume únicamente queue items `ready_for_publish`.

La hora registrada actualmente es 08:00 America/Lima.
