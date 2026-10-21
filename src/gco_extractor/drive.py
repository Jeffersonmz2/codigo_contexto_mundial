"""
Conexión a Google Drive con Service Account (sirve en local y en GitHub Actions).
"""
import io
from pathlib import Path

import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.files import ApiRequestError

from .config import DRIVE_FILE_NAME, FOLDER_ID, SERVICE_ACCOUNT_FILE


def get_drive() -> GoogleDrive:
    """Autentica con Service Account (sin navegador)."""
    sa_path = Path(SERVICE_ACCOUNT_FILE)

    # En GitHub Actions el secreto se escribe como service_account.json en la raíz
    if not sa_path.exists():
        sa_path = Path("service_account.json")

    if not sa_path.exists():
        raise FileNotFoundError(
            "No se encontró service_account.json.\n"
            "- En local: ponlo en la raíz del proyecto.\n"
            "- En GitHub: configura el secreto GOOGLE_SERVICE_ACCOUNT_JSON."
        )

    gauth = GoogleAuth()
    scopes = ["https://www.googleapis.com/auth/drive"]
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
        str(sa_path), scopes
    )
    return GoogleDrive(gauth)


def download_existing_historial(drive: GoogleDrive) -> pd.DataFrame | None:
    try:
        # Intento 1: Buscar por carpeta contenedora y nombre
        query = (
            f"'{FOLDER_ID}' in parents and "
            f"title = '{DRIVE_FILE_NAME}' and "
            f"trashed = false"
        )
        file_list = drive.ListFile({"q": query}).GetList()

        # Intento 2: Búsqueda global por nombre (fallback para cuentas de servicio)
        if not file_list:
            query_alt = f"title = '{DRIVE_FILE_NAME}' and trashed = false"
            file_list = drive.ListFile({"q": query_alt}).GetList()

        if not file_list:
            print("No se encontró historial previo en Drive.")
            return None

        gfile = file_list[0]
        print(f"Historial encontrado en Drive (ID: {gfile['id']}) → descargando...")
        content = gfile.GetContentString(encoding="utf-8")
        df_old = pd.read_csv(io.StringIO(content))
        print(f"   → {len(df_old):,} filas históricas cargadas")
        return df_old

    except ApiRequestError as e:
        print(f"Advertencia al consultar Google Drive (404 / Permisos): {e}")
        print("Continuando como primera ejecución (sin historial previo)...")
        return None


def merge_with_historial(
    df_new: pd.DataFrame, df_old: pd.DataFrame | None
) -> pd.DataFrame:
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
    if df is None or df.empty:
        print("✗ No hay datos para subir.")
        return

    print("\n=== Subiendo archivo a Google Drive ===")
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig")
    csv_content = buffer.getvalue()

    gfile = None
    try:
        query = (
            f"'{FOLDER_ID}' in parents and "
            f"title = '{DRIVE_FILE_NAME}' and "
            f"trashed = false"
        )
        file_list = drive.ListFile({"q": query}).GetList()

        if not file_list:
            query_alt = f"title = '{DRIVE_FILE_NAME}' and trashed = false"
            file_list = drive.ListFile({"q": query_alt}).GetList()

        if file_list:
            gfile = file_list[0]
            print(f"Archivo existente → se actualizará (ID: {gfile['id']})")
    except ApiRequestError as e:
        print(f"Aviso al buscar archivo existente en Drive: {e}")

    if gfile is None:
        gfile = drive.CreateFile(
            {"title": DRIVE_FILE_NAME, "parents": [{"id": FOLDER_ID}]}
        )
        print("Archivo nuevo → se creará en Drive")

    gfile.SetContentString(csv_content)
    gfile.Upload()

    print("✅ Subido a Google Drive")
    print(f"   Nombre : {DRIVE_FILE_NAME}")
    print(f"   Filas  : {len(df):,}")
    print(f"   Años   : {sorted(df['year'].unique().tolist())}")
    print(f"   Link   : https://drive.google.com/file/d/{gfile['id']}/view")