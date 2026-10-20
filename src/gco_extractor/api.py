"""
Conexión y extracción de datos desde la API de GLOBOCAN (IARC).
Soporta múltiples años. Omite automáticamente los años sin datos.
"""

import time
from datetime import datetime

import pandas as pd
import requests

from .config import AGES_GROUP, SEXES, TYPES, YEARS, base_url


def year_has_data(year: int) -> bool:
    """Comprueba si un año tiene datos reales en la API."""
    url = f"{base_url(year)}/meta/cancers/all/"
    try:
        r = requests.get(url, timeout=20)
        if not r.ok:
            return False
        data = r.json()
        if isinstance(data, list) and len(data) > 5:
            return True
        return False
    except Exception:
        return False


def get_cancer_list(year: int) -> list:
    """Obtiene la lista de tipos de cáncer para un año."""
    url = f"{base_url(year)}/meta/cancers/all/"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError(f"Sin datos de cánceres para el año {year}")
    return data


def get_populations(year: int) -> dict:
    """Obtiene la lista de países indexada por country_code."""
    url = f"{base_url(year)}/meta/populations/all/"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()

    if not isinstance(data, list):
        raise ValueError(f"Sin datos de poblaciones para el año {year}")

    populations = {}
    for p in data:
        key = p.get("country") or p.get("country_code")
        if key is not None:
            populations[key] = p
    return populations


def fetch_data(year: int, cancer_id: int, sex: int, type_: int) -> list:
    """Descarga los datos de un cáncer + sexo + tipo para un año."""
    url = (
        f"{base_url(year)}/data/rate/{type_}/{sex}/all/{cancer_id}/"
        f"?ages_group={AGES_GROUP}"
    )
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.json().get("dataset", [])


def extract_year(year: int) -> pd.DataFrame:
    """Extrae todos los datos de un año. DataFrame vacío si no hay datos."""
    print(f"\n{'='*60}")
    print(f"  Año {year}")
    print(f"{'='*60}")

    if not year_has_data(year):
        print(f"  ⚠ Año {year} no tiene datos en la API → se omite")
        return pd.DataFrame()

    print("  1. Lista de cánceres...")
    cancers = get_cancer_list(year)
    print(f"     → {len(cancers)} tipos")

    print("  2. Lista de países...")
    populations = get_populations(year)
    print(f"     → {len(populations)} poblaciones")

    all_data = []
    total = len(cancers) * len(SEXES) * len(TYPES)
    current = 0

    for cancer in cancers:
        cancer_id = cancer["cancer"]
        cancer_label = cancer["label"]

        for sex_code, sex_label in SEXES.items():
            for type_code, type_label in TYPES.items():
                current += 1
                if current % 20 == 0 or current == total:
                    print(
                        f"     [{current:3d}/{total}] "
                        f"{cancer_label[:30]:<30} | {sex_label:<12} | {type_label}"
                    )

                try:
                    data = fetch_data(year, cancer_id, sex_code, type_code)

                    for row in data:
                        country_code = row.get("country_code")
                        pop_info = populations.get(country_code, {})

                        all_data.append(
                            {
                                "year": year,
                                "cancer_id": cancer_id,
                                "cancer_label": cancer_label,
                                "population_code": country_code,
                                "population": pop_info.get("label", ""),
                                "alpha3": pop_info.get("country_iso3", ""),
                                "sex_code": sex_code,
                                "sex": sex_label,
                                "type_code": type_code,
                                "type": type_label,
                                "asr_world": row.get("asr"),
                                "crude_rate": row.get("crude_rate"),
                                "cum_risk": row.get("cum_risk"),
                                "total": row.get("total"),
                                "total_pop": row.get("total_pop"),
                                "rank": row.get("rank"),
                                "extraction_date": datetime.now().strftime("%Y-%m-%d"),
                            }
                        )

                    time.sleep(0.30)

                except Exception as e:
                    print(f"     ✗ Error ({cancer_label} / {sex_label} / {type_label}): {e}")

    df = pd.DataFrame(all_data)
    print(f"  → Año {year}: {len(df):,} filas extraídas")
    return df


def extract_all_data() -> pd.DataFrame:
    """Extrae datos de todos los años en YEARS. Omite los que no tienen datos."""
    print("=== Extracción GLOBOCAN | Edad 0-19 ===")
    print(f"Años a intentar: {YEARS}\n")

    frames = []
    years_ok = []
    years_skip = []

    for year in YEARS:
        df_year = extract_year(year)
        if df_year.empty:
            years_skip.append(year)
        else:
            frames.append(df_year)
            years_ok.append(year)

    print(f"\n{'='*60}")
    print("Resumen:")
    print(f"  Años con datos : {years_ok}")
    print(f"  Años omitidos  : {years_skip}")

    if not frames:
        print("  ✗ No se extrajo ningún dato.")
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    print(f"  Total filas    : {len(df):,}")
    return df
