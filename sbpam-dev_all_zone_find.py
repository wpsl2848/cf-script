import requests
import json
import csv
import os
import re
from typing import List, Dict
from dataclasses import dataclass
import pandas as pd
from datetime import datetime

@dataclass
class ZoneInfo:
    domain: str
    plan: str
    zone_id: str

@dataclass
class RuleDetails:
    domain: str  # zone domain or 'Account Level'
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
        self.account_id = "8a215d1828c45f48abeb1d966d35faa0"
        self.target_domain = "spam-dev.coupangcorp.com"  # 변경된 타겟 도메인
        self.rules_found: List[RuleDetails] = []
        
        # Create reports directory
        os.makedirs('reports', exist_ok=True)

    def read_zones_from_csv(self, csv_file: str) -> List[ZoneInfo]:
        """Read zone information from CSV file"""
        zones = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                zones.append(ZoneInfo(
                    domain=row['Domain Name'],
                    plan=row['Plan'],
                    zone_id=row['Zone ID']
                ))
        return zones

    def check_rule_for_target(self, rule: Dict, ruleset_name: str, ruleset_phase: str, domain: str = 'Account Level') -> None:
        """Check if rule contains target domain and store if found"""
        expression = rule.get('expression', '')
        description = rule.get('description', 'No description')
        
        # 대소문자 구분 없이 검색하도록 수정
        if self.target_domain.lower() in expression.lower():
            rule_details = RuleDetails(
                domain=domain,
                ruleset_name=ruleset_name,
                ruleset_phase=ruleset_phase,
                rule_id=rule.get('id', 'Unknown'),
                rule_description=description,
                rule_expression=expression,
                rule_action=rule.get('action', 'Unknown'),
                rule_enabled=rule.get('enabled', True)
            )
            self.rules_found.append(rule_details)

    def process_account_rulesets(self):
        """Process account level rulesets"""
        print(f"\nProcessing account level rulesets for domain: {self.target_domain}...")
        
        url = f"{self.base_url}/accounts/{self.account_id}/rulesets"
        response = requests.get(url, headers=self.headers)
        account_rulesets = response.json().get('result', [])

        for ruleset in account_rulesets:
            ruleset_id = ruleset.get('id')
            ruleset_name = ruleset.get('name', 'Unnamed ruleset')
            ruleset_phase = ruleset.get('phase', 'Unknown phase')
            
            print(f"Checking account ruleset: {ruleset_name}")
            
            # Get detailed rules
            details_url = f"{self.base_url}/accounts/{self.account_id}/rulesets/{ruleset_id}"
            details = requests.get(details_url, headers=self.headers).json()
            
            if not details.get('success'):
                print(f"Failed to get details for ruleset: {ruleset_name}")
                continue

            rules = details.get('result', {}).get('rules', [])
            for rule in rules:
                self.check_rule_for_target(rule, ruleset_name, ruleset_phase)

    def process_zone_rulesets(self):
        """Process zone level rulesets"""
        print(f"\nProcessing zone level rulesets for domain: {self.target_domain}...")
        
        zones = self.read_zones_from_csv('enterprise_domains_8a215d1828c45f48abeb1d966d35faa0.csv')
        
        for zone in zones:
            print(f"Processing zone: {zone.domain}")
            url = f"{self.base_url}/zones/{zone.zone_id}/rulesets"
            response = requests.get(url, headers=self.headers)
            rulesets = response.json()
            
            if not rulesets.get('success'):
                print(f"Failed to get rulesets for zone: {zone.domain}")
                continue

            for ruleset in rulesets.get('result', []):
                ruleset_id = ruleset.get('id')
                ruleset_name = ruleset.get('name', 'Unnamed ruleset')
                ruleset_phase = ruleset.get('phase', 'Unknown phase')

                details_url = f"{self.base_url}/zones/{zone.zone_id}/rulesets/{ruleset_id}"
                details = requests.get(details_url, headers=self.headers).json()
                
                if not details.get('success'):
                    print(f"Failed to get details for zone ruleset: {ruleset_name}")
                    continue

                rules = details.get('result', {}).get('rules', [])
                for rule in rules:
                    self.check_rule_for_target(rule, ruleset_name, ruleset_phase, zone.domain)

    def export_to_excel(self):
        """Export found rules to Excel"""
        if not self.rules_found:
            print("No rules found containing the target domain.")
            return

        # Convert rules to DataFrame
        df = pd.DataFrame([vars(rule) for rule in self.rules_found])
        
        # Reorder columns for better readability
        columns = [
            'domain', 'ruleset_name', 'ruleset_phase', 'rule_id',
            'rule_description', 'rule_expression', 'rule_action', 'rule_enabled'
        ]
        df = df[columns]
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'reports/spam_dev_rules_{timestamp}.xlsx'
        
        # Export to Excel
        df.to_excel(filename, index=False, sheet_name='Rules')
        
        print(f"\nFound {len(self.rules_found)} rules containing '{self.target_domain}'")
        print(f"Results exported to: {filename}")

def main():
    finder = CloudflareRuleFinder()
    
    # Process both account and zone rulesets
    finder.process_account_rulesets()
    finder.process_zone_rulesets()
    
    # Export results to Excel
    finder.export_to_excel()

if __name__ == "__main__":
    main()
