import requests
import csv
import sys

# Hardcoded credentials (Note: This is not recommended for production use)
EMAIL = "hakang@mz.co.kr"
API_KEY = "f6f652701a00dc80fc3c5e764adb1b84461e3"

def fetch_cloudflare_data():
    url = 'https://api.cloudflare.com/client/v4/zones?per_page=193'
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Email': EMAIL,
        'X-Auth-Key': API_KEY
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data: {response.status_code}")
        sys.exit(1)

def extract_domains(data, account_id):
    domains = []
    for zone in data['result']:
        if zone['account']['id'] == account_id and zone['plan']['name'] == "Enterprise Website":
            domains.append({
                'name': zone['name'],
                'plan': zone['plan']['name'],
                'id': zone['id']
            })
    return domains

def write_to_csv(domains, output_file):
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Domain Name', 'Plan', 'Zone ID'])  # Header
        for domain in domains:
            writer.writerow([domain['name'], domain['plan'], domain['id']])
            print(f"Domain: {domain['name']}, Plan: {domain['plan']}, Zone ID: {domain['id']}")

def main():
    print("Cloudflare Enterprise Domain Extractor")
    print("--------------------------------------")
    
    account_id = input("Please enter the account ID: ").strip()
    
    if not account_id:
        print("Error: Account ID cannot be empty.")
        sys.exit(1)

    output_file = f"enterprise_domains_{account_id}.csv"

    print("\nFetching data from Cloudflare API...")
    data = fetch_cloudflare_data()

    print(f"Extracting Enterprise domains for account ID: {account_id}")
    domains = extract_domains(data, account_id)

    if not domains:
        print(f"No Enterprise domains found for account ID: {account_id}")
        sys.exit(0)

    print(f"\nWriting Enterprise domains to {output_file} and printing to console:")
    write_to_csv(domains, output_file)

    print(f"\nTotal Enterprise domains found: {len(domains)}")
    print(f"Results have been saved to {output_file}")

if __name__ == "__main__":
    main()
