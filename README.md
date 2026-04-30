# MTG Commander Report Agent

Proyecto base para generar informes automatizados de mazos Commander en formato Markdown.

## Objetivo inicial

Dos veces al dia, a las 8:00 y a las 20:00, una automatizacion debe:

1. Elegir una carta al azar que pueda ser commander en Magic: The Gathering.
2. Asignarle aleatoriamente un bracket entre 2, 3, 4 o 5.
3. Construir una decklist completa de 100 cartas alrededor de esa carta.
4. Consultar el precio actual de la carta commander en Card Kingdom.
5. Generar un archivo Markdown con el informe del mazo.

## Estructura

- `automation/commander_report_spec.md`: especificacion del contenido esperado en cada informe.
- `automation/tiktok_content_pipeline.md`: especificacion de la fase visual para TikTok.
- `automation/export_report_data.py`: transforma un reporte Markdown en JSON estructurado.
- `automation/render_tiktok_assets.py`: genera 5 imagenes verticales por reporte con una plantilla tipo `Deck Case`.
- `automation/run_daily_pipeline.py`: ejecuta la generacion diaria completa y prepara la cola de publicacion.
- `automation/show_publish_window.py`: muestra el paquete diario listo para publicar.
- `automation/daily_automation_plan.md`: plan diario de horarios y ejecucion.
- `automation/daily_publish_schedule.json`: horarios diarios de publicacion.
- `automation/create_windows_scheduled_tasks.ps1`: registra tareas programadas en Windows.
- `automation/templates/`: plantillas HTML/CSS para render.
- `reports/`: salida generada por la automatizacion.
- `report_data/`: salida JSON estructurada para la fase visual.
- `tiktok_assets/`: imagenes listas para publicar.
- `publish_queue/`: cola de publicaciones diarias listas.
- `publish_runs/`: resultados de envios a TikTok y estados finales.
- `tiktok_integration/`: backend Python local para OAuth y publicacion a TikTok.
- `legal-site/`: sitio estatico para legal pages, callback y media publica.
- `TIKTOK_SETUP.md`: guia operativa para conectar TikTok y publicar por API.
- `requirements-image-rendering.txt`: dependencias recomendadas para el render visual.
- `requirements-tiktok.txt`: dependencias del backend Python de TikTok.

## Alcance de esta primera fase

Esta fase deja preparado el proyecto y registra la automatizacion recurrente.
En la siguiente fase podemos agregar validaciones mas estrictas, plantillas mas avanzadas, exportes, pipelines posteriores o publicacion automatica.

## Pipeline TikTok

Despues de generar reportes en `reports/`, el flujo recomendado es:

1. `python automation/generate_test_reports.py`
2. `python automation/export_report_data.py`
3. `python automation/render_tiktok_assets.py`

El resultado final son 5 PNG por commander dentro de `tiktok_assets/`.

## Dependencias del renderer visual

Instalacion recomendada:

1. `python -m pip install -r requirements-image-rendering.txt`
2. `python -m playwright install chromium`

El renderer actual usa Playwright y plantillas HTML/CSS para acercarse al formato visual tipo `Commander Deck Case`.

## Automatizacion diaria

Pipeline diario:

1. `python automation/run_daily_pipeline.py`
2. revisar salida en `publish_queue/`
3. `python automation/show_publish_window.py`

Para registrar tareas en Windows:

1. `powershell -ExecutionPolicy Bypass -File automation/create_windows_scheduled_tasks.ps1`

Horarios configurados:

- Monday `13:00`
- Tuesday `12:00`
- Wednesday `17:00`
- Thursday `17:00`
- Friday `18:00`
- Saturday `17:00`
- Sunday `09:00`

## GitHub Actions

La generacion de contenido puede quedarse por completo en Codex/local.
GitHub Actions queda solo para la parte publica y TikTok.

Workflows:

1. `.github/workflows/deploy-pages-from-local-assets.yml`
2. `.github/workflows/publish-tiktok.yml`

Flujo recomendado:

1. Codex genera reportes, JSON, assets y `publish_queue/` en tu carpeta local conectada
2. Codex o tu flujo local deja las imagenes publicas dentro de `legal-site/media/<report_id>/`
3. haces `push` al repo con esos artefactos ya preparados
4. GitHub Actions despliega `legal-site/` a GitHub Pages
5. cuando el deploy termina bien, GitHub Actions envia el `queue item` listo a TikTok

Importante:

- GitHub ya no genera contenido ni renderiza imagenes
- para publicar desde CI ya no hace falta el backend Flask local
- GitHub Actions usa `TIKTOK_TOKEN_JSON` o `TIKTOK_REFRESH_TOKEN` como secretos
- debes actualizar en TikTok el prefijo verificado y el `redirect_uri` al host publico que uses

Repositorio objetivo:

- `Sebas1406/mtg-sh-auto`

Scripts locales de apoyo:

1. `powershell -ExecutionPolicy Bypass -File automation/bootstrap_github_remote.ps1`
2. `powershell -ExecutionPolicy Bypass -File automation/push_publish_bundle.ps1`
