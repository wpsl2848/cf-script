import requests
import json
import csv
import os
from typing import List, Dict
from dataclasses import dataclass
import pandas as pd
from datetime import datetime

@dataclass
class RuleDetails:
    ruleset_name: str
    ruleset_phase: str
    rule_id: str
    rule_description: str
    rule_expression: str
    rule_action: str
    rule_enabled: bool

class CloudflareRuleFinder:
    def __init__(self):
        self.headers = {
            "X-Auth-Email": "hakang@mz.co.kr",
            "X-Auth-Key": "f6f652701a00dc80fc3c5e764adb1b84461e3",
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.target_domain = "api-gateway.coupang.com"
        self.coupang_zone_id = None  # Will be set when reading zones
        self.rules_found: List[RuleDetails] = []
        
        # Create reports directory
        os.makedirs('reports', exist_ok=True)

    def get_coupang_zone_id(self) -> str:
        """Get zone ID for coupang.com from CSV file"""
        with open('enterprise_domains_8a215d1828c45f48abeb1d966d35faa0.csv', 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                if row['Domain Name'] == 'coupang.com':
                    return row['Zone ID']
        raise ValueError("Could not find zone ID for coupang.com")

    def check_rule_for_target(self, rule: Dict, ruleset_name: str, ruleset_phase: str) -> None:
        """Check if rule contains target domain and store if found"""
        expression = rule.get('expression', '')
        description = rule.get('description', 'No description')
        
        if self.target_domain in expression or self.target_domain in description:
            rule_details = RuleDetails(
                ruleset_name=ruleset_name,
                ruleset_phase=ruleset_phase,
                rule_id=rule.get('id', 'Unknown'),
                rule_description=description,
                rule_expression=expression,
                rule_action=rule.get('action', 'Unknown'),
                rule_enabled=rule.get('enabled', True)
            )
            self.rules_found.append(rule_details)

    def process_zone_rulesets(self):
        """Process coupang.com zone rulesets"""
        print("\nProcessing coupang.com zone rulesets...")
        
        # Get coupang.com zone ID
        self.coupang_zone_id = self.get_coupang_zone_id()
        print(f"Found coupang.com zone ID: {self.coupang_zone_id}")
        
        # Get all rulesets for coupang.com
        url = f"{self.base_url}/zones/{self.coupang_zone_id}/rulesets"
        response = requests.get(url, headers=self.headers)
        rulesets = response.json()
        
        if not rulesets.get('success'):
            print("Failed to get rulesets")
            return

        # Process each ruleset
        for ruleset in rulesets.get('result', []):
            ruleset_id = ruleset.get('id')
            ruleset_name = ruleset.get('name', 'Unnamed ruleset')
            ruleset_phase = ruleset.get('phase', 'Unknown phase')
            
            print(f"Checking ruleset: {ruleset_name} ({ruleset_phase})")

            # Get detailed rules for this ruleset
            details_url = f"{self.base_url}/zones/{self.coupang_zone_id}/rulesets/{ruleset_id}"
            details = requests.get(details_url, headers=self.headers).json()
            
            if not details.get('success'):
                print(f"Failed to get details for ruleset: {ruleset_name}")
                continue

            rules = details.get('result', {}).get('rules', [])
            for rule in rules:
                self.check_rule_for_target(rule, ruleset_name, ruleset_phase)

    def export_to_excel(self):
        """Export found rules to Excel"""
        if not self.rules_found:
            print("No rules found containing the target domain.")
            return

        # Convert rules to DataFrame
        df = pd.DataFrame([vars(rule) for rule in self.rules_found])
        
        # Reorder columns for better readability
        columns = [
            'ruleset_name', 'ruleset_phase', 'rule_id',
            'rule_description', 'rule_expression', 'rule_action', 'rule_enabled'
        ]
        df = df[columns]
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'reports/api_gateway_rules_{timestamp}.xlsx'
        
        # Export to Excel
        df.to_excel(filename, index=False, sheet_name='Rules')
        
        print(f"\nFound {len(self.rules_found)} rules containing '{self.target_domain}'")
        print(f"Results exported to: {filename}")

def main():
    finder = CloudflareRuleFinder()
    finder.process_zone_rulesets()
    finder.export_to_excel()

if __name__ == "__main__":
    main()
