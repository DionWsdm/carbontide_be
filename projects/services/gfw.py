# projects/services/gfw.py
import requests
from decouple import config

GFW_BASE_URL = "https://data-api.globalforestwatch.org"
GFW_API_KEY = config("GFW_API_KEY")


class GFWServiceError(Exception):
    """Dilempar kalau request ke GFW API gagal."""
    pass


def get_tree_cover_loss(geojson_polygon: dict, year: int = 2024) -> float:
    if not geojson_polygon:
        raise GFWServiceError("area_geojson proyek masih kosong.")

    sql = f"SELECT SUM(area__ha) FROM results WHERE umd_tree_cover_loss__year = {year}"

    try:
        response = requests.post(
            f"{GFW_BASE_URL}/dataset/umd_tree_cover_loss/v1.11/query/json",
            headers={
                "x-api-key": GFW_API_KEY,
                "Content-Type": "application/json",
                "User-Agent": "curl/8.4.0",  # <-- coba ini
            },
            json={"sql": sql, "geometry": geojson_polygon},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise GFWServiceError(f"Gagal menghubungi GFW API: {e}")
    ...

    data = response.json().get("data", [])
    return float(data[0]["area__ha"]) if data and data[0]["area__ha"] else 0.0