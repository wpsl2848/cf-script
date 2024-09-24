import csv
import requests
from datetime import datetime
import logging
import json
import sys

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

def get_zone_ids(csv_file):
    zone_ids = []
    try:
        with open(csv_file, 'r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                zone_ids.append(row['Zone ID'])
    except Exception as e:
        print(f"Error reading CSV file: {e}")
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
        return response.json()
    except requests.exceptions.RequestException:
        return {"error": "DNS partial"}

def get_date_input(prompt):
    while True:
        date_str = input(prompt)
        if date_str.lower() == 'q':
            return 'q'
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

def save_results(all_results):
    file_name = f"DNS_query_all_periods_98d26011d91e2c6c00a1fe006dc4b865.json"
    with open(file_name, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nAll results saved to {file_name}")

def main():
    csv_file = 'enterprise_domains_98d26011d91e2c6c00a1fe006dc4b865.csv'
    zone_ids = get_zone_ids(csv_file)
    
    all_results = {}

    try:
        while True:
            start_date = get_date_input("Enter start date (YYYY-MM-DD) or 'q' to quit: ")
            if start_date == 'q':
                break
            end_date = get_date_input("Enter end date (YYYY-MM-DD): ")
            if end_date == 'q':
                break
            
            period_key = f"{start_date.date()}_{end_date.date()}"
            all_results[period_key] = {
                "query_period": f"{start_date.date()} ~ {end_date.date()}",
                "zone_data": []
            }
            
            total_query_count = 0
            for zone_id in zone_ids:
                query_result = get_query_count(zone_id, start_date, end_date)
                if "error" in query_result:
                    query_count = "DNS partial"
                else:
                    query_count = query_result.get('result', {}).get('totals', {}).get('queryCount', 0)
                
                all_results[period_key]["zone_data"].append({
                    "zone_id": zone_id,
                    "query_count": query_count,
                    "full_result": query_result
                })
                
                print(f"Zone ID : {zone_id}")
                print(f"Query count : {query_count}")
                print()
                
                if query_count != "DNS partial":
                    total_query_count += query_count
            
            all_results[period_key]["total_query_count"] = total_query_count
            print(f"Total Query Count : {total_query_count}")
            print("\n" + "="*50 + "\n")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Saving results...")
    
    finally:
        if all_results:
            save_results(all_results)
        else:
            print("\nNo results to save.")

if __name__ == "__main__":
    main()
