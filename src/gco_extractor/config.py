"""
Configuración central del proyecto.
Diseñado para automatización sin mantenimiento manual de años.
"""

from datetime import datetime
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv() 

# =============================================================================
# AÑOS A EXTRAER (automático, cada 2 años desde 2020)
# =============================================================================
#
# Si un año no tiene datos en la API, se omite automáticamente.
YEARS = [y for y in range(2020, datetime.now().year + 1, 2)]

# =============================================================================
# API GLOBOCAN
# =============================================================================
AGES_GROUP = "0_3"  # 0-19 años

SEXES = {
    0: "Both sexes",
    1: "Male",
    2: "Female",
}

TYPES = {
    0: "Incidence",
    1: "Mortality",
}


def base_url(year: int) -> str:
    """URL base de la API para un año concreto."""
    return f"{os.getenv("DATAURL")}/{year}"


# =============================================================================
# GOOGLE DRIVE
# =============================================================================
# ID de la carpeta de Drive
FOLDER_ID = os.getenv("FOLDER_ID")

# Nombre del archivo de historial en Drive
DRIVE_FILE_NAME = os.getenv("DRIVE_FILE_NAME")

# Archivos de credenciales 
ROOT_DIR = Path(__file__).resolve().parents[2]
CLIENT_SECRETS = ROOT_DIR /  os.getenv("CLIENT_SECRETS")
CREDS_FILE = ROOT_DIR /  os.getenv("CREDS_FILE")
