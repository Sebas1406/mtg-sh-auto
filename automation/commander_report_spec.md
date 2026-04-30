# Commander Report Spec

Cada archivo generado por la automatizacion debe ser un Markdown autocontenido y facil de reutilizar despues.

## Nombre del archivo

Formato recomendado:

`reports/YYYY-MM-DD-HHMM-commander-slug.md`

Ejemplo:

`reports/2026-04-27-0800-atraxa-praetors-voice.md`

## Estructura minima del documento

```md
# [Nombre del commander]

- Fecha de generacion:
- Hora de generacion:
- Bracket objetivo:
- Tipo de juego:
- Dificultad:
- Precio actual en Card Kingdom:
- Fuente de precio:

## Resumen

Breve descripcion del plan del mazo, condiciones de victoria y filosofia de construccion.

## Commander

- Nombre:
- Coste de mana:
- Identidad de color:
- Tipo de carta:
- Texto relevante:

## Plan de juego

### Early game
### Mid game
### Late game

## Decklist

### Commander
1x ...

### Criaturas
...

### Artefactos
...

### Encantamientos
...

### Instantaneos
...

### Conjuros
...

### Planeswalkers
...

### Tierras
...

## Notas de construccion

- Razonamiento del bracket asignado.
- Curva de mana aproximada.
- Sinergias principales.
- Riesgos o puntos debiles.

## Fuentes

- ...
```

## Reglas de contenido

- La carta elegida debe poder ser commander de forma legal en Commander.
- La decklist debe contener exactamente 100 cartas contando el commander.
- La identidad de color debe respetarse en toda la lista.
- El bracket entre 2 y 5 se asigna de forma aleatoria para este proyecto.
- El informe debe indicar explicitamente que el bracket fue asignado por la automatizacion para fines del proyecto.
- El precio debe citar Card Kingdom y el enlace usado para consultarlo.
