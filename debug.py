import requests
import json
import pandas as pd
import logging

# 로깅 설정 (INFO 레벨로 변경)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_bytes(bytes_value):
    units = ['B', 'kB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while bytes_value >= 1000 and i < len(units) - 1:
        bytes_value /= 1000
        i += 1
    return f"{bytes_value:.2f} {units[i]}"

def get_zone_ids(csv_file):
    df = pd.read_csv(csv_file)
    zone_ids = df[df['Domain Name'].isin(['farfetchplatform.cn', 'harrods.cn'])]['Zone ID'].tolist()
    return zone_ids

def fetch_data(zone_id, start_date, end_date):
    url = 'https://api.cloudflare.com/client/v4/graphql'
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Email': 'hakang@mz.co.kr',
        'X-Auth-Key': 'f6f652701a00dc80fc3c5e764adb1b84461e3'
    }
    query = """
    {
      viewer {
        zones(filter: {zoneTag: $zoneTag}) {
          requests: httpRequestsAdaptiveGroups(limit: 5000, filter: $filter) {
            sum {
              edgeResponseBytes
            }
            dimensions {
              clientCountryName
            }
          }
        }
      }
    }
    """
    variables = {
        "zoneTag": zone_id,
        "filter": {
            "AND": [
                {"date_geq": start_date, "date_leq": end_date},
                {"clientCountryName": "CN"},
                {"requestSource": "eyeball"}
            ]
        }
    }
    response = requests.post(url, headers=headers, json={"query": query, "variables": variables})
    
    if response.status_code != 200:
        logger.error(f"API request failed for Zone ID {zone_id} with status code: {response.status_code}")
        return None

    try:
        return response.json()
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response for Zone ID {zone_id}: {e}")
        return None

def main():
    csv_file = 'enterprise_domains_98d26011d91e2c6c00a1fe006dc4b865.csv'
    zone_ids = get_zone_ids(csv_file)

    start_date = input("Enter start date (YYYY-MM-DD): ")
    end_date = input("Enter end date (YYYY-MM-DD): ")

    total_data_transfer = 0

    for zone_id in zone_ids:
        data = fetch_data(zone_id, start_date, end_date)
        
        if data is None or 'errors' in data and data['errors']:
            logger.error(f"Failed to fetch data for Zone ID {zone_id}")
            continue

        if 'data' not in data or 'viewer' not in data['data'] or 'zones' not in data['data']['viewer']:
            logger.error(f"Unexpected API response structure for Zone ID {zone_id}")
            continue

        zones = data['data']['viewer']['zones']
        if not zones or not zones[0]['requests']:
            print(f"No data for CN in Zone ID: {zone_id}")
            continue

        zone_data_transfer = zones[0]['requests'][0]['sum']['edgeResponseBytes']
        total_data_transfer += zone_data_transfer

        print(f"Zone ID: {zone_id}")
        print(f"Data_Transfer (CN): {convert_bytes(zone_data_transfer)} ({zone_data_transfer} bytes)")

    print(f"\nTotal Data_Transfer (CN): {convert_bytes(total_data_transfer)} ({total_data_transfer} bytes)")

if __name__ == "__main__":
    main()
