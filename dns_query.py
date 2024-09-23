import csv
import requests
from datetime import datetime, timedelta
import logging
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_zone_ids(csv_file):
    zone_ids = []
    try:
        with open(csv_file, 'r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                zone_ids.append(row['Zone ID'])
        logging.info(f"Loaded {len(zone_ids)} zone IDs from {csv_file}")
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}")
    return zone_ids[:7]  # 처음 7개의 zone ID만 반환

def get_query_count(zone_id, start_date, end_date):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_analytics/report"
    params = {
        "metrics": "queryCount",
        "sort": "-queryCount",
        "limit": 100,
        "since": start_date.isoformat() + "Z",
        "until": end_date.isoformat() + "Z"
    }
    headers = {
        "X-Auth-Email": "hakang@mz.co.kr",
        "X-Auth-Key": "f6f652701a00dc80fc3c5e764adb1b84461e3",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if 'result' in data and 'totals' in data['result']:
            return data['result']['totals'].get('queryCount', 0)
        else:
            logging.warning(f"Unexpected response structure for zone {zone_id}")
            return 0
    except requests.exceptions.RequestException as e:
        logging.error(f"Error for zone {zone_id}: {e}")
        return 0

def main():
    csv_file = 'enterprise_domains_98d26011d91e2c6c00a1fe006dc4b865.csv'
    zone_ids = get_zone_ids(csv_file)
    
    periods = [
        (datetime(2024, 6, 18), datetime(2024, 7, 17)),
        (datetime(2024, 7, 18), datetime(2024, 8, 17)),
        (datetime(2024, 8, 18), datetime(2024, 9, 17))
    ]
    
    for start_date, end_date in periods:
        print(f"\n[쿼리 기간: {start_date.date()} ~ {end_date.date()}]")
        total_query_count = 0
        for zone_id in zone_ids:
            query_count = get_query_count(zone_id, start_date, end_date)
            total_query_count += query_count
            print(f"zone id: {zone_id}")
            print(f"Query count: {query_count}")
        
        print(f"Total (7개 존 카운트 모두 합산): {total_query_count}")

if __name__ == "__main__":
    main()
