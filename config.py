"""Load config from config.yaml."""
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def get_search_params(cfg=None):
    cfg = cfg or load_config()
    loc = cfg["location"]
    pu = cfg["pickup"]
    do = cfg["dropoff"]
    return {
        "location": "",
        "dropLocation": "",
        "locationName": loc["name"],
        "locationIata": loc["iata"],
        "dropLocationName": loc["name"],
        "dropLocationIata": loc["iata"],
        "coordinates": loc["coordinates"],
        "dropCoordinates": loc["coordinates"],
        "driversAge": cfg["drivers_age"],
        "puDay": pu["day"],
        "puMonth": pu["month"],
        "puYear": pu["year"],
        "puMinute": pu["minute"],
        "puHour": pu["hour"],
        "doDay": do["day"],
        "doMonth": do["month"],
        "doYear": do["year"],
        "doMinute": do["minute"],
        "doHour": do["hour"],
        "ftsType": "A",
        "dropFtsType": "A",
        "filterCriteria_transmission": cfg["transmission"],
        "filterCriteria_carCategory": cfg["car_category"],
    }


def build_search_url(cfg=None):
    import urllib.parse
    params = get_search_params(cfg)
    qs = urllib.parse.urlencode(params)
    return f"https://www.rentalcars.com/search-results?{qs}"
