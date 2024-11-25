import csv
import requests
import json
from datetime import datetime
import os

def read_zone_ids(file_path):
    zone_ids = []
    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            zone_ids.append(row['Zone ID'])
    return zone_ids

def get_date_input(prompt):
    while True:
        date_str = input(prompt)
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

def make_graphql_request(zone_id, start_date, end_date):
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
          Total: httpRequestsAdaptiveGroups(filter: $filter, limit: 10000) {
            count
          }
          automated: httpRequestsAdaptiveGroups(filter: {AND: [
            {botManagementDecision_neq: "verified_bot"}, $automatedFilter
          ]}, limit: 10000) {
            count
          }
          likely_automated: httpRequestsAdaptiveGroups(filter: {AND: [
            {botManagementDecision_neq: "verified_bot"}, $likelyAutomatedFilter
          ]}, limit: 10000) {
            count
          }
          likely_human: httpRequestsAdaptiveGroups(filter: {AND: [
            {botManagementDecision_neq: "verified_bot"}, $likelyHumanFilter
          ]}, limit: 10000) {
            count
          }
          verified_bot: httpRequestsAdaptiveGroups(filter: {AND: [
            {botManagementDecision: "verified_bot"}, $verifiedBotFilter
          ]}, limit: 10000) {
            count
          }
        }
      }
    }
    """
    
    variables = {
        "zoneTag": zone_id,
        "filter": {
            "requestSource": "eyeball",
            "date_geq": start_date,
            "date_leq": end_date,
            "botManagementDecision_neq": "other"
        },
        "automatedFilter": {
            "requestSource": "eyeball",
            "botScore": 1,
            "date_geq": start_date,
            "date_leq": end_date,
            "botManagementDecision_neq": "other"
        },
        "likelyAutomatedFilter": {
            "requestSource": "eyeball",
            "botScore_geq": 2,
            "botScore_leq": 29,
            "date_geq": start_date,
            "date_leq": end_date,
            "botManagementDecision_neq": "other"
        },
        "likelyHumanFilter": {
            "requestSource": "eyeball",
            "botScore_geq": 30,
            "botScore_leq": 99,
            "date_geq": start_date,
            "date_leq": end_date,
            "botManagementDecision_neq": "other"
        },
        "verifiedBotFilter": {
            "requestSource": "eyeball",
            "date_geq": start_date,
            "date_leq": end_date,
            "botManagementDecision_neq": "other",
            "botScoreSrcName": "verified_bot"
        }
    }
    
    data = {
        "query": query,
        "variables": variables
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def format_number(number):
    if number >= 1000000:
        return f"{number/1000000:.2f} MM ({number})"
    else:
        return f"{number}"

def process_zone_data(zone_id, response_data):
    if 'errors' in response_data and response_data['errors']:
        for error in response_data['errors']:
            if 'does not have access to the field' in error.get('message', ''):
                return f"Zone ID: {zone_id}, Data: Access Restricted", 0
        return f"Zone ID: {zone_id}, Data: Error occurred", 0

    zones = response_data.get('data', {}).get('viewer', {}).get('zones', [])
    if not zones:
        return f"Zone ID: {zone_id}, Data: No data available", 0

    likely_human = zones[0].get('likely_human', [])
    if not likely_human:
        return f"Zone ID: {zone_id}, Data: No 'likely_human' data", 0

    likely_human_count = likely_human[0].get('count', 0)
    formatted_count = format_number(likely_human_count)
    return f"Zone ID: {zone_id}, Likely Human Count: {formatted_count}", likely_human_count

def save_query_result(zone_id, start_date, end_date, response_data):
    # reports/bot 폴더 구조 생성
    os.makedirs('reports/bot', exist_ok=True)
    
    filename = f"reports/bot/bot_{start_date}_{end_date}_{zone_id}.json"
    with open(filename, 'w') as f:
        json.dump(response_data, f, indent=2)
    print(f"Query result saved to {filename}")

def main():
    file_path = 'enterprise_domains_8a215d1828c45f48abeb1d966d35faa0.csv'
    if not os.path.exists(file_path):
        print(f"Error: The file '{file_path}' was not found.")
        return
    
    zone_ids = read_zone_ids(file_path)
    
    start_date = get_date_input("Enter start date (YYYY-MM-DD): ")
    end_date = get_date_input("Enter end date (YYYY-MM-DD): ")
    
    total_likely_human = 0
    
    for zone_id in zone_ids:
        response_data = make_graphql_request(zone_id, start_date, end_date)
        
        # Save query result to JSON file
        save_query_result(zone_id, start_date, end_date, response_data)
        
        try:
            result, count = process_zone_data(zone_id, response_data)
            print(result)
            if isinstance(count, int):
                total_likely_human += count
        except Exception as e:
            print(f"Error processing data for Zone ID: {zone_id}")
            print(f"Error details: {str(e)}")
    
    formatted_total = format_number(total_likely_human)
    print(f"\nTotal Likely Human: {formatted_total}")

if __name__ == "__main__":
    main()
