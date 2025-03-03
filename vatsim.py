import requests

def get_vatsim_data():
    url = "https://data.vatsim.net/v3/vatsim-data.json"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None
