import csv
import requests
import json

def query_cloudflare_api(zone_id):
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
            "date_geq": "2024-07-18",
            "date_leq": "2024-08-17"
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

def main():
    total_bytes = 0
    total_requests = 0
    count = 1

    with open('enterprise_domains_98d26011d91e2c6c00a1fe006dc4b865.csv', 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            zone_id = row['Zone ID']
            zone_name = row['Domain Name']
            result = query_cloudflare_api(zone_id)
            
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

if __name__ == "__main__":
    main()
