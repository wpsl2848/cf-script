import requests
import json
from datetime import datetime

def get_cloudflare_metrics(start_date, end_date, account_tag):
    url = 'https://api.cloudflare.com/client/v4/graphql'
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Email': 'hakang@mz.co.kr',
        'X-Auth-Key': 'f6f652701a00dc80fc3c5e764adb1b84461e3'
    }

    query = """
    query getBillingMetrics($accountTag: string!, $filter: AccountWorkersInvocationsAdaptiveFilter_InputObject, $overviewFilter: AccountWorkersInvocationsAdaptiveFilter_InputObject) {
      viewer {
        accounts(filter: {accountTag: $accountTag}) {
          workersInvocationsAdaptive(limit: 10000, filter: $filter) {
            sum {
              Standatd_request: requests
              __typename
            }
            dimensions {
              usageModel
              __typename
            }
            __typename
          }
          workersOverviewRequestsAdaptiveGroups(limit: 1000, filter: $overviewFilter) {
            sum {
              CPU_Time: cpuTimeUs
              __typename
            }
            dimensions {
              usageModel
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
    }
    """

    variables = {
        "accountTag": account_tag,
        "filter": {
            "date_geq": start_date,
            "date_leq": end_date
        },
        "overviewFilter": {
            "datetime_geq": f"{start_date}T00:00:00.000Z",
            "datetime_leq": f"{end_date}T15:00:00.000Z"
        }
    }

    payload = {
        "query": query,
        "variables": variables
    }

    response = requests.post(url, headers=headers, json=payload)
    return response.json()

def save_to_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def format_metric(value, unit):
    """Format metric with different units"""
    k_value = round(value / 1000, 2)
    if unit == 'μs':
        ms_value = round(value / 1000, 2)
        mm_value = round(ms_value / 1000000, 2)  # 밀리초를 기준으로 밀리언 계산
        return f"{value} {unit} ({ms_value:.2f} ms, {mm_value:.2f} MM)"
    else:
        mm_value = round(value / 1000000, 6)
        return f"{value} ({k_value:.2f}k, {mm_value:.6f} MM)"

def main():
    start_date = input("Enter the start date (YYYY-MM-DD): ")
    end_date = input("Enter the end date (YYYY-MM-DD): ")
    account_tag = input("Enter the account tag: ")

    try:
        # Validate date format
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Please use YYYY-MM-DD.")
        return

    result = get_cloudflare_metrics(start_date, end_date, account_tag)

    # Save the entire query result to JSON file
    filename = f"workers_{start_date}_{end_date}_{account_tag}.json"
    save_to_json(result, filename)
    print(f"\nQuery results saved to {filename}")

    # Extract and print specific metrics
    if 'data' in result and 'viewer' in result['data']:
        accounts = result['data']['viewer'].get('accounts', [])
        if accounts:
            # Extract CPU_Time for usageModel 3
            cpu_time = None
            for group in accounts[0].get('workersOverviewRequestsAdaptiveGroups', []):
                if group['dimensions']['usageModel'] == 3:
                    cpu_time = group['sum']['CPU_Time']
                    break

            # Extract Standard_request for usageModel "standard"
            standard_requests = None
            for group in accounts[0].get('workersInvocationsAdaptive', []):
                if group['dimensions']['usageModel'] == "standard":
                    standard_requests = group['sum']['Standatd_request']
                    break

            # Print results
            print(f"\nResults for period {start_date} to {end_date}:")
            if cpu_time is not None:
                print(f"CPU Time for usageModel 3: {format_metric(cpu_time, 'μs')}")
            else:
                print("CPU Time for usageModel 3: Not found")
            
            if standard_requests is not None:
                print(f"Standard requests for usageModel 'standard': {format_metric(standard_requests, '')}")
            else:
                print("Standard requests for usageModel 'standard': Not found")
        else:
            print("No account data found in the response.")
    else:
        print("Unexpected API response structure. 'data' or 'viewer' key missing.")

if __name__ == "__main__":
    main()
