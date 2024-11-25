import json
import csv
import requests
from datetime import datetime

# GraphQL 쿼리
QUERY = """
{
  viewer {
    zones(filter: { zoneTag: $zoneTag }) {
      httpRequestsOverviewAdaptiveGroups(limit: 10000, filter: $filter) {
        dimensions {
          clientCountryName
        }
        sum {
          bytes
          requests
        }
      }
    }
  }
}
"""

def fetch_data(api_email, api_key, zone_tag, start_date, end_date):
    url = "https://api.cloudflare.com/client/v4/graphql"
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Email": api_email,
        "X-Auth-Key": api_key
    }
    variables = {
        "zoneTag": zone_tag,
        "filter": {
            "date_geq": start_date,
            "date_leq": end_date
        }
    }
    payload = {
        "query": QUERY,
        "variables": variables
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed for zone {zone_tag} with status code {response.status_code}: {response.text}")

def format_bytes(bytes):
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    for unit in units:
        if bytes < 1000.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1000.0
    return f"{bytes:.2f} PB"

def format_requests(requests):
    if requests >= 1000000:
        return f"{requests/1000000:.2f}M"
    else:
        return f"{requests}"

def process_data(all_data, output_file):
    country_data = {}
    total_bytes = 0
    total_requests = 0

    for data in all_data:
        for group in data['data']['viewer']['zones'][0]['httpRequestsOverviewAdaptiveGroups']:
            country = group['dimensions']['clientCountryName']
            bytes = group['sum']['bytes']
            requests = group['sum']['requests']
            
            if country in country_data:
                country_data[country]['bytes'] += bytes
                country_data[country]['requests'] += requests
            else:
                country_data[country] = {'bytes': bytes, 'requests': requests}

            total_bytes += bytes
            total_requests += requests

    # CSV 파일로 결과 저장 및 콘솔에 출력
    print(f"{'Country':<20} {'Bytes':<30} {'Requests':<20}")
    print("-" * 70)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Country', 'Bytes', 'Formatted Bytes', 'Requests', 'Formatted Requests'])
        for country, data in country_data.items():
            formatted_bytes = format_bytes(data['bytes'])
            formatted_requests = format_requests(data['requests'])
            writer.writerow([country, data['bytes'], formatted_bytes, data['requests'], formatted_requests])
            print(f"{country:<20} {formatted_bytes:<15}({data['bytes']:<14}) {formatted_requests:<10}({data['requests']})")

    print("-" * 70)
    formatted_total_bytes = format_bytes(total_bytes)
    formatted_total_requests = format_requests(total_requests)
    print(f"{'Total':<20} {formatted_total_bytes:<15}({total_bytes:<14}) {formatted_total_requests:<10}({total_requests})")

    # CSV 파일에 Total 행 추가
    with open(output_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Total', total_bytes, formatted_total_bytes, total_requests, formatted_total_requests])

    print(f"\n데이터가 {output_file}에 저장되었습니다.")

def read_zone_ids(file_path):
    zone_ids = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            zone_ids.append(row['Zone ID'])
    return zone_ids

def get_date_input(prompt):
    while True:
        date_str = input(prompt)
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            print("올바르지 않은 날짜 형식입니다. YYYY-MM-DD 형식으로 입력해주세요.")

def main():
    api_email = "hakang@mz.co.kr"  # 여기에 실제 이메일 주소를 입력하세요
    api_key = "f6f652701a00dc80fc3c5e764adb1b84461e3"  # 여기에 실제 API 키를 입력하세요
    output_file = 'output.csv'
    zone_id_file = 'enterprise_domains_8a215d1828c45f48abeb1d966d35faa0.csv'

    start_date = get_date_input("시작 날짜를 입력하세요 (YYYY-MM-DD 형식): ")
    end_date = get_date_input("종료 날짜를 입력하세요 (YYYY-MM-DD 형식): ")

    try:
        zone_ids = read_zone_ids(zone_id_file)
        all_data = []
        for zone_id in zone_ids:
            print(f"Fetching data for zone ID: {zone_id}")
            data = fetch_data(api_email, api_key, zone_id, start_date, end_date)
            all_data.append(data)
        process_data(all_data, output_file)
    except Exception as e:
        print(f"에러 발생: {str(e)}")

if __name__ == "__main__":
    main()
