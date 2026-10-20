"""
Conexión y operaciones con Google Drive.
Incluye refresh_token (acceso offline) para automatización.
"""

import io

import pandas as pd
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

from .config import (
    CLIENT_SECRETS,
    CREDS_FILE,
    DRIVE_FILE_NAME,
    FOLDER_ID,
)


def get_drive() -> GoogleDrive:
    """Autentica y devuelve GoogleDrive con refresh_token offline."""
    from pathlib import Path

    gauth = GoogleAuth()

    client_secrets = str(CLIENT_SECRETS)
    creds_file = str(CREDS_FILE)

    # Solo client secrets + refresh token (NO configurar backend file aún)
    gauth.DEFAULT_SETTINGS["client_config_file"] = client_secrets
    gauth.DEFAULT_SETTINGS["get_refresh_token"] = True
    gauth.DEFAULT_SETTINGS["oauth_scope"] = ["https://www.googleapis.com/auth/drive"]

    # Cargar token previo si existe
    if Path(creds_file).exists():
        try:
            gauth.LoadCredentialsFile(creds_file)
        except Exception:
            gauth.credentials = None

    if gauth.credentials is None:
        print("Se abrirá el navegador para autorizar Google Drive...")
        print("(Acceso offline: se guardará refresh_token)")
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        try:
            print("Token expirado → renovando...")
            gauth.Refresh()
        except Exception as e:
            print(f"No se pudo renovar ({e}). Reautorizando...")
            if Path(creds_file).exists():
                Path(creds_file).unlink()
            gauth.credentials = None
            gauth.LocalWebserverAuth()
    else:
        gauth.Authorize()

    # Guardar credenciales DESPUÉS de autenticar
    gauth.SaveCredentialsFile(creds_file)
    return GoogleDrive(gauth)

def download_existing_historial(drive: GoogleDrive) -> pd.DataFrame | None:
    """
    Busca el archivo de historial en Drive.
    Si existe, lo descarga en memoria y lo devuelve como DataFrame.
    Si no existe, devuelve None.
    """
    query = (
        f"'{FOLDER_ID}' in parents and "
        f"title = '{DRIVE_FILE_NAME}' and "
        f"trashed = false"
    )
    file_list = drive.ListFile({"q": query}).GetList()

    if not file_list:
        print("No se encontró historial previo en Drive.")
        return None

    gfile = file_list[0]
    print(f"Historial encontrado en Drive (ID: {gfile['id']}) → descargando...")

    content = gfile.GetContentString(encoding="utf-8")
    df_old = pd.read_csv(io.StringIO(content))
    print(f"   → {len(df_old):,} filas históricas cargadas")
    return df_old


def merge_with_historial(
    df_new: pd.DataFrame, df_old: pd.DataFrame | None
) -> pd.DataFrame:
    """
    Combina los datos nuevos con el historial.
    - Reemplaza en el histórico los años que se acaban de extraer.
    - Conserva el resto de años que ya estaban en Drive.
    """
    if df_new is None or df_new.empty:
        print("No hay datos nuevos → se conserva el historial actual.")
        return df_old if df_old is not None else pd.DataFrame()

    if df_old is None or df_old.empty:
        print("No hay historial previo → se usarán solo los datos nuevos.")
        return df_new

    years_extracted = sorted(df_new["year"].unique().tolist())
    print(f"   → Años extraídos en esta corrida: {years_extracted}")

    df_old_clean = df_old[~df_old["year"].isin(years_extracted)].copy()
    print(f"   → Filas de otros años conservadas: {len(df_old_clean):,}")

    df_final = pd.concat([df_old_clean, df_new], ignore_index=True)

    df_final = df_final.sort_values(
        by=["year", "cancer_id", "population_code", "sex_code", "type_code"]
    ).reset_index(drop=True)

    return df_final


def upload_to_drive(drive: GoogleDrive, df: pd.DataFrame) -> None:
    """
    Sube (o actualiza) el DataFrame como CSV en la carpeta de Google Drive.
    No guarda nada en local.
    """
    if df is None or df.empty:
        print("✗ No hay datos para subir. Se cancela la subida a Drive.")
        return

    print("\n=== Subiendo archivo a Google Drive ===")

    buffer = io.StringIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig")
    csv_content = buffer.getvalue()

    query = (
        f"'{FOLDER_ID}' in parents and "
        f"title = '{DRIVE_FILE_NAME}' and "
        f"trashed = false"
    )
    file_list = drive.ListFile({"q": query}).GetList()

    if file_list:
        gfile = file_list[0]
        print(f"Archivo existente encontrado → se actualizará (ID: {gfile['id']})")
    else:
        gfile = drive.CreateFile(
            {
                "title": DRIVE_FILE_NAME,
                "parents": [{"id": FOLDER_ID}],
            }
        )
        print("Archivo nuevo → se creará en la carpeta de Drive")

    gfile.SetContentString(csv_content)
    gfile.Upload()

    print("✅ Archivo subido correctamente a Google Drive")
    print(f"   Nombre : {DRIVE_FILE_NAME}")
    print(f"   Filas  : {len(df):,}")
    print(f"   Años   : {sorted(df['year'].unique().tolist())}")
    print(f"   Link   : https://drive.google.com/file/d/{gfile['id']}/view")
