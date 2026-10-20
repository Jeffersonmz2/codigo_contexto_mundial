# GCO Cancer Extractor (completo y corregido)

Extractor de datos GLOBOCAN (0-19 años) con subida automática a Google Drive.

## Instalación

```bash
uv sync
```

## Configuración (solo una vez)

1. Coloca `client_secrets.json` en esta carpeta (raíz).
2. `FOLDER_ID` ya está configurado en `src/gco_extractor/config.py`.
3. Si existe `mycreds.txt` de un intento anterior, bórralo:
   ```bash
   del mycreds.txt
   ```

## Ejecutar

```bash
uv run main.py
```

## Estructura

```
gco_cancer_extractor_completo/
├── main.py
├── pyproject.toml
├── README.md
├── client_secrets.json   ← tú lo agregas
├── mycreds.txt           ← se crea solo al autorizar
└── src/gco_extractor/
    ├── config.py
    ├── api.py
    ├── drive.py          ← corregido (refresh_token offline)
    └── main.py
```

## Notas

- Años automáticos cada 2 años desde 2020.
- Si un año no tiene datos en la API, se omite.
- El historial se conserva y se actualiza en Drive.
