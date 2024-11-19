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
        self.coupang_zone_id = None
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

    def check_rule_condition(self, rule: Dict, ruleset_name: str, ruleset_phase: str) -> None:
        """Check if rule doesn't contain http.host condition"""
        expression = rule.get('expression', '')
        description = rule.get('description', 'No description')
        
        # Skip rules that contain http.host
        if 'http.host' not in expression:
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

        total_rules = 0
        rules_without_host = 0

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
            total_rules += len(rules)
            
            for rule in rules:
                before_count = len(self.rules_found)
                self.check_rule_condition(rule, ruleset_name, ruleset_phase)
                if len(self.rules_found) > before_count:
                    rules_without_host += 1

        print(f"\nProcessed {total_rules} total rules")
        print(f"Found {rules_without_host} rules without http.host condition")

    def export_to_excel(self):
        """Export found rules to Excel"""
        if not self.rules_found:
            print("No rules found without host condition.")
            return

        # Convert rules to DataFrame
        df = pd.DataFrame([vars(rule) for rule in self.rules_found])
        
        # Reorder columns for better readability
        columns = [
            'ruleset_name', 
            'ruleset_phase', 
            'rule_id',
            'rule_description', 
            'rule_expression', 
            'rule_action', 
            'rule_enabled'
        ]
        df = df[columns]
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'reports/rules_without_host_{timestamp}.xlsx'
        
        # Export to Excel
        df.to_excel(filename, index=False, sheet_name='Rules')
        
        print(f"Results exported to: {filename}")
        
        # Print summary of rule phases
        print("\nRules by phase:")
        phase_counts = df['ruleset_phase'].value_counts()
        for phase, count in phase_counts.items():
            print(f"  {phase}: {count} rules")

def main():
    finder = CloudflareRuleFinder()
    finder.process_zone_rulesets()
    finder.export_to_excel()

if __name__ == "__main__":
    main()
