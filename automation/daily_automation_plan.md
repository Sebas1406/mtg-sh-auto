# Daily TikTok Automation Plan

Este flujo deja el contenido listo todos los dias y separa claramente generacion de publicacion.

## Horario recomendado

Zona horaria: `America/Lima`

- Generacion diaria: `08:05`
- Publicacion:
  - Monday: `13:00`
  - Tuesday: `12:00`
  - Wednesday: `17:00`
  - Thursday: `17:00`
  - Friday: `18:00`
  - Saturday: `17:00`
  - Sunday: `09:00`

## Flujo

1. `run_daily_pipeline.py`
   - genera reportes
   - exporta JSON
   - renderiza 5 imagenes
   - crea un archivo en `publish_queue/` con caption e imagenes

2. `show_publish_window.py`
   - lee la cola
   - muestra el horario recomendado del dia
   - muestra caption y assets listos

## Estado actual

El proyecto ya deja listo el paquete diario de publicacion.

## Estado futuro

TikTok ya soporta posting de fotos en su Content Posting API oficial, pero para automatizar el envio real necesitas:

- una app registrada en TikTok for Developers
- aprobacion del scope `video.publish`
- auditoria de la app para salir de modo privado
- dominio verificado para URLs de medios

Fuentes oficiales:

- https://developers.tiktok.com/products/content-posting-api
- https://developers.tiktok.com/doc/content-posting-api-get-started/
- https://developers.tiktok.com/doc/content-posting-api-reference-direct-post

## Comandos manuales

Pipeline completo:

```powershell
python automation/run_daily_pipeline.py
```

Ver la cola del dia:

```powershell
python automation/show_publish_window.py
```

Registrar tareas de Windows:

```powershell
powershell -ExecutionPolicy Bypass -File automation/create_windows_scheduled_tasks.ps1
```
