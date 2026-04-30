# Automation Prompt

Genera un nuevo informe Markdown de Commander para este proyecto.

En cada ejecucion:

1. Busca en internet una carta de Magic: The Gathering que pueda ser commander de forma legal en Commander/EDH y elige una al azar.
2. Asigna aleatoriamente a ese mazo un bracket entre 2, 3, 4 o 5.
3. Deja claro en el informe que ese bracket fue asignado por la automatizacion para fines del proyecto.
4. Construye una decklist completa y coherente de exactamente 100 cartas contando el commander, respetando identidad de color y legalidad de Commander.
5. Consulta el precio actual de la carta commander en Card Kingdom e incluye el valor y el enlace utilizado como fuente.
6. Indica el tipo de juego del mazo y la dificultad de pilotaje.
7. Redacta un informe Markdown autocontenido en espanol.
8. Guarda el archivo en `reports/` con nombre `YYYY-MM-DD-HHMM-commander-slug.md`.
9. Si el archivo ya existe, agrega un sufijo numerico para no sobrescribirlo.

## Contenido minimo del informe

- Titulo con el nombre del commander
- Fecha y hora de generacion
- Bracket objetivo
- Tipo de juego
- Dificultad
- Precio actual en Card Kingdom
- Resumen del mazo
- Datos del commander
- Plan de juego por early game, mid game y late game
- Decklist agrupada por categorias
- Notas de construccion
- Fuentes
