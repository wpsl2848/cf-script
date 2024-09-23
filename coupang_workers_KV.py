import requests
import json
from datetime import datetime, timedelta

def get_kv_operations_summary(account_tag, from_datetime, to_datetime):
    url = 'https://api.cloudflare.com/client/v4/graphql'
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Email': 'hakang@mz.co.kr',
        'X-Auth-Key': 'f6f652701a00dc80fc3c5e764adb1b84461e3'
    }

    query = """
    query KVOperationsSummaryByAccount($accountTag: string!, $fromDatetimeMinute: Date, $toDatetimeMinute: Date) {
      viewer {
        accounts(filter: {accountTag: $accountTag}) {
          reads: kvOperationsAdaptiveGroups(limit: 1, filter: {actionType: read, datetimeMinute_geq: $fromDatetimeMinute, datetimeMinute_leq: $toDatetimeMinute}) {
            sum {
              requests
            }
          }
          writes: kvOperationsAdaptiveGroups(limit: 1, filter: {actionType: write, datetimeMinute_geq: $fromDatetimeMinute, datetimeMinute_leq: $toDatetimeMinute}) {
            sum {
              requests
            }
          }
          lists: kvOperationsAdaptiveGroups(limit: 1, filter: {actionType: list, datetimeMinute_geq: $fromDatetimeMinute, datetimeMinute_leq: $toDatetimeMinute}) {
            sum {
              requests
            }
          }
          deletes: kvOperationsAdaptiveGroups(limit: 1, filter: {actionType: delete, datetimeMinute_geq: $fromDatetimeMinute, datetimeMinute_leq: $toDatetimeMinute}) {
            sum {
              requests
            }
          }
          storage: kvStorageAdaptiveGroups(limit: 744, filter: {datetimeMinute_geq: $fromDatetimeMinute, datetimeMinute_leq: $toDatetimeMinute}) {
            max {
              byteCount
            }
          }
        }
      }
    }
    """

    variables = {
        "accountTag": account_tag,
        "fromDatetimeMinute": from_datetime.isoformat() + "Z",
        "toDatetimeMinute": to_datetime.isoformat() + "Z"
    }

    response = requests.post(url, headers=headers, json={"query": query, "variables": variables})
    
    # 응답 상태 코드 확인 및 출력
    print(f"API Response Status Code: {response.status_code}")
    
    # 응답 내용 출력 (디버깅 목적)
    print("API Response Content:")
    print(json.dumps(response.json(), indent=2))
    
    return response.json()

def convert_to_millions(value):
    """Convert value to millions and round to 2 decimal places."""
    return round(value / 1000000, 2)

def convert_to_gb(bytes_value):
    """Convert bytes to GB and round to 2 decimal places."""
    return round(float(bytes_value) / (1000 * 1000 * 1000), 2)

def print_results(data):
    if 'data' not in data or 'viewer' not in data['data'] or 'accounts' not in data['data']['viewer'] or not data['data']['viewer']['accounts']:
        print("Error: Unexpected data structure in API response")
        print("Received data structure:")
        print(json.dumps(data, indent=2))
        return

    accounts = data['data']['viewer']['accounts'][0]
    
    def get_requests(operation_type):
        try:
            return accounts[operation_type][0]['sum']['requests']
        except (KeyError, IndexError):
            return 0

    print("Read:")
    print(f"  Read operations: {convert_to_millions(get_requests('reads'))} MM")

    try:
        storage = accounts['storage'][0]['max']
        byte_count = storage.get('byteCount', 'N/A')
        if byte_count != 'N/A':
            print(f"Storage:")
            print(f"  Current: {convert_to_gb(byte_count):.2f} GB")
        else:
            print("Storage:")
            print("  Current: N/A")
    except (KeyError, IndexError):
        print("Storage:")
        print("  Current: N/A")

    print("Write/list/delete:")
    print(f"  Write operations: {convert_to_millions(get_requests('writes'))} MM")
    print(f"  List operations: {convert_to_millions(get_requests('lists'))} MM")
    print(f"  Delete operations: {convert_to_millions(get_requests('deletes'))} MM")

def save_results(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Query results saved to {filename}")

def main():
    account_tag = "8a215d1828c45f48abeb1d966d35faa0"
    
    # 사용자로부터 날짜 입력 받기
    from_date = input("시작 날짜를 입력하세요 (YYYY-MM-DD): ")
    to_date = input("종료 날짜를 입력하세요 (YYYY-MM-DD): ")

    # 날짜 검증
    try:
        from_datetime = datetime.strptime(from_date, "%Y-%m-%d")
        to_datetime = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        
        # 날짜 범위 검사
        if (to_datetime - from_datetime).days > 365:
            raise ValueError("Date range exceeds 1 year")
        if to_datetime > datetime.now():
            raise ValueError("End date is in the future")
    except ValueError as e:
        print(f"Error: Invalid date input - {str(e)}")
        return

    result = get_kv_operations_summary(account_tag, from_datetime, to_datetime)
    
    # 결과를 JSON 파일로 저장
    filename = f"workers_KV_{from_date}_{to_date}_{account_tag}.json"
    save_results(result, filename)

    # 결과 출력
    print_results(result)

if __name__ == "__main__":
    main()
