"""
Punto de entrada principal.
Ejecuta: uv run main.py
"""

from pathlib import Path

from .api import extract_all_data
from .config import SERVICE_ACCOUNT_FILE, FOLDER_ID, YEARS
from .drive import (
    download_existing_historial,
    get_drive,
    merge_with_historial,
    upload_to_drive,
)


def main() -> None:
    print(f"Años configurados para extracción: {YEARS}\n")

    if FOLDER_ID == "PEGA_AQUI_EL_ID_DE_TU_CARPETA":
        print("❌ ERROR: Debes configurar FOLDER_ID en src/gco_extractor/config.py")
        print("   Ejemplo: FOLDER_ID = '1a2b3c4d5e6f7g8h9i0j'")
        return

    if not Path(SERVICE_ACCOUNT_FILE).exists():
        print(f"❌ ERROR: No se encontró el archivo '{SERVICE_ACCOUNT_FILE}'.")
        print("   Descárgalo desde Google Cloud Console (OAuth client ID - Desktop app)")
        print("   y colócalo en la raíz del proyecto.")
        return

    # 1. Extraer datos
    df_new = extract_all_data()

    if df_new.empty:
        print("\n✗ No se extrajo ningún dato. No se subirá nada a Drive.")
        return

    # 2. Conectar a Google Drive
    print("\nConectando a Google Drive...")
    drive = get_drive()

    # 3. Descargar historial existente
    df_old = download_existing_historial(drive)

    # 4. Combinar
    df_final = merge_with_historial(df_new, df_old)
    print(f"\nTotal de filas en el historial final: {len(df_final):,}")

    # 5. Subir a Drive
    upload_to_drive(drive, df_final)

    print("\n✅ Proceso terminado correctamente.")


if __name__ == "__main__":
    main()
