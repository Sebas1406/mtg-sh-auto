# TikTok Python Setup

## Important security note

Si compartiste el `Client secret` fuera del portal, rota ese secreto en TikTok for Developers antes de usar este backend en serio.

## 1. Configuracion local

1. Copia `.env.example` a `.env`.
2. Rellena:
   - `TIKTOK_CLIENT_KEY`
   - `TIKTOK_CLIENT_SECRET`
3. Verifica que estas URLs coincidan con tu configuracion de TikTok:
   - `TIKTOK_REDIRECT_URI=https://sebas1406.github.io/mtg-sh-auto/tiktok-callback.html`
   - `TIKTOK_VERIFY_PREFIX=https://sebas1406.github.io/mtg-sh-auto/`
   - `TIKTOK_MEDIA_BASE_URL=https://sebas1406.github.io/mtg-sh-auto/media/`

Si migras a GitHub Pages, esas tres URLs deben cambiar al nuevo host publico antes de publicar por API.

## 2. Instalar dependencias

```powershell
python -m pip install -r requirements-tiktok.txt
```

## 3. Publicar el callback actualizado

La pagina [legal-site/tiktok-callback.html](C:/Users/SebastianHurtado/Documents/New%20project/legal-site/tiktok-callback.html)
ahora reenvia el `code` de TikTok a tu backend local.

Debes volver a desplegar la carpeta `legal-site` a tu host publico para que el cambio exista en:

`https://mtgsh.netlify.app/tiktok-callback.html`

## 4. Iniciar el backend local

```powershell
python -m tiktok_integration.app
```

Abre luego:

[http://127.0.0.1:8765/](http://127.0.0.1:8765/)

## 5. Conectar la cuenta de TikTok

1. Abre [http://127.0.0.1:8765/auth/tiktok/start](http://127.0.0.1:8765/auth/tiktok/start)
2. Autoriza tu cuenta de TikTok
3. TikTok te devolvera al host publico configurado
4. La pagina de Netlify te reenviara automaticamente al backend local
5. El backend guardara tus tokens en `.secrets/tiktok_tokens.json`

Si piensas publicar desde GitHub Actions, guarda luego ese contenido como secreto:

- `TIKTOK_TOKEN_JSON`

o al menos extrae y guarda:

- `TIKTOK_REFRESH_TOKEN`

## 6. Revisar el estado de conexion

```powershell
Invoke-WebRequest http://127.0.0.1:8765/auth/tiktok/status | Select-Object -Expand Content
```

## 7. Preparar imagenes para publicar por URL

TikTok `PULL_FROM_URL` requiere que las imagenes sean publicas bajo el prefijo verificado.

Para copiar las imagenes de una cola lista al sitio publico:

```powershell
python automation/stage_tiktok_media.py 2026-04-27-0804-torbran-thane-of-red-fell
```

Eso copia las imagenes convertidas a `JPG` dentro de `legal-site/media/<report_id>/`.

Despues:

1. vuelve a desplegar `legal-site` a tu host publico o usa el deploy automatizado
2. verifica que las imagenes abren en navegador

### Deploy automatizado de `legal-site`

```powershell
python automation/deploy_legal_site_to_netlify.py
```

Ese script sigue siendo util si mantienes Netlify. Si migras a GitHub, usa los workflows de `.github/workflows/`.

## 8. Obtener las URLs publicas

```powershell
Invoke-WebRequest http://127.0.0.1:8765/api/tiktok/public-urls/2026-04-27-0804-torbran-thane-of-red-fell | Select-Object -Expand Content
```

## 9. Consultar creator info

```powershell
Invoke-WebRequest http://127.0.0.1:8765/api/tiktok/creator-info | Select-Object -Expand Content
```

## 10. Publicar un photo post

```powershell
Invoke-WebRequest -Method Post http://127.0.0.1:8765/api/tiktok/publish/2026-04-27-0804-torbran-thane-of-red-fell | Select-Object -Expand Content
```

Por defecto el backend intenta `DIRECT_POST` y, si TikTok bloquea por app no auditada, reintenta automaticamente con `MEDIA_UPLOAD` para mandar un borrador al inbox del creador.

Tambien puedes forzarlo asi:

```powershell
python automation/publish_tiktok_queue_item.py 2026-04-27-0804-torbran-thane-of-red-fell media_upload
```

## 11. Consultar estado de un publish_id

```powershell
python automation/check_tiktok_publish_status.py p_inbox_url~v2.7634331656496629781
```

## 12. Pipeline completo hasta inbox

```powershell
python automation/run_tiktok_inbox_pipeline.py 2026-04-27-0804-torbran-thane-of-red-fell
```

Este comando:

1. convierte y copia slides a `JPG`
2. despliega `legal-site/` a Netlify por API
3. envia el carrusel a TikTok con `MEDIA_UPLOAD`
4. consulta el estado hasta `SEND_TO_USER_INBOX` o `FAILED`
5. guarda el resultado en `publish_runs/<report_id>.json`

## GitHub Actions

Para publicar sin backend local y dejando la generacion en Codex/local:

1. Codex genera el contenido y deja listo `publish_queue/<report_id>.json`
2. Codex o tu automatizacion local copia las imagenes a `legal-site/media/<report_id>/`
3. haces `push` de esos artefactos al repo
4. `.github/workflows/deploy-pages-from-local-assets.yml` despliega `legal-site/`
5. `.github/workflows/publish-tiktok.yml` publica el queue item mas reciente despues del deploy

Secrets recomendados en GitHub:

- `TIKTOK_CLIENT_KEY`
- `TIKTOK_CLIENT_SECRET`
- `TIKTOK_TOKEN_JSON` o `TIKTOK_REFRESH_TOKEN`

Variables recomendadas en GitHub:

- `TIKTOK_REDIRECT_URI`
- `TIKTOK_VERIFY_PREFIX`
- `TIKTOK_MEDIA_BASE_URL`
- `TIKTOK_SCOPES`

Recomendacion operativa:

- no hagas push hasta que el bundle local este completo
- el workflow valida que existan `publish_queue/<report_id>.json` y al menos 5 imagenes en `legal-site/media/<report_id>/`
- el workflow de publicacion se dispara al terminar correctamente el deploy de Pages

Repositorio recomendado:

- `https://github.com/Sebas1406/mtg-sh-auto`

Automatizacion local minima:

1. inicializa el remoto con `automation/bootstrap_github_remote.ps1`
2. cuando Codex termine de generar y copiar el bundle publico, ejecuta `automation/push_publish_bundle.ps1`
3. GitHub Pages despliega `legal-site/`
4. el workflow de TikTok publica automaticamente despues del deploy

## Rutas importantes

- `GET /auth/tiktok/start`
- `GET /auth/tiktok/local-callback`
- `GET /auth/tiktok/status`
- `POST /api/tiktok/refresh`
- `GET /api/tiktok/creator-info`
- `POST /api/tiktok/stage-media/<report_id>`
- `GET /api/tiktok/public-urls/<report_id>`
- `POST /api/tiktok/publish/<report_id>`
- `GET /api/tiktok/publish-status/<publish_id>`
