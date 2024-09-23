import csv
import requests
import json
from datetime import datetime

def query_cloudflare_api(zone_id, start_date, end_date):
    url = 'https://api.cloudflare.com/client/v4/graphql'
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Email': 'hakang@mz.co.kr',
        'X-Auth-Key': 'f6f652701a00dc80fc3c5e764adb1b84461e3'
    }
    query = """
    {
      viewer {
        zones(filter: { zoneTag: $zoneTag }) {
          httpRequestsOverviewAdaptiveGroups(limit: 10000, filter: $filter) {
            sum {
              bytes
              requests
            }
          }
        }
      }
    }
    """
    variables = {
        "zoneTag": zone_id,
        "filter": {
            "date_geq": start_date,
            "date_leq": end_date
        },
        "json-csv-email": "hakang@mz.co.kr"
    }
    data = {
        "query": query,
        "variables": variables
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def bytes_to_human_readable(bytes_value):
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    for unit in units:
        if bytes_value < 1000:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1000.0
    return f"{bytes_value:.2f} {units[-1]}"

def requests_to_millions(requests_value):
    return f"{requests_value / 1_000_000:.2f}M"

def get_date_input(prompt):
    while True:
        date_str = input(prompt)
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

def main():
    start_date = get_date_input("Enter start date (YYYY-MM-DD): ")
    end_date = get_date_input("Enter end date (YYYY-MM-DD): ")
    csv_file = 'enterprise_domains_8a215d1828c45f48abeb1d966d35faa0.csv'

    total_bytes = 0
    total_requests = 0
    count = 1

    try:
        with open(csv_file, 'r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                zone_id = row['Zone ID']
                zone_name = row['Domain Name']
                result = query_cloudflare_api(zone_id, start_date, end_date)
                
                if 'data' in result and 'viewer' in result['data'] and 'zones' in result['data']['viewer']:
                    zones = result['data']['viewer']['zones']
                    if zones and zones[0]['httpRequestsOverviewAdaptiveGroups']:
                        data = zones[0]['httpRequestsOverviewAdaptiveGroups'][0]['sum']
                        bytes_value = data['bytes']
                        requests_value = data['requests']
                        total_bytes += bytes_value
                        total_requests += requests_value
                        print(f"{count}. Zone ID: {zone_id}")
                        print(f"   Zone Name: {zone_name}")
                        print(f"   Bytes: {bytes_value}")
                        print(f"   Converted: {bytes_to_human_readable(bytes_value)}")
                        print(f"   Requests: {requests_value}")
                        print(f"   Requests (Millions): {requests_to_millions(requests_value)}")
                        count += 1
                    else:
                        print(f"No data for Zone ID: {zone_id}, Zone Name: {zone_name}")
                else:
                    print(f"Error querying Zone ID: {zone_id}, Zone Name: {zone_name}")
                    print(f"Response: {result}")
                
                print()  # Add a blank line for better readability

        print(f"\n{count}. Total (Ent) : {count-1}")
        print(f"Total Bytes: {total_bytes}")
        print(f"Converted: {bytes_to_human_readable(total_bytes)}")
        print(f"Total Requests: {total_requests}")
        print(f"Total Requests (Millions): {requests_to_millions(total_requests)}")

    except FileNotFoundError:
        print(f"Error: The file '{csv_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
