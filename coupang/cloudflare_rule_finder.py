import requests
import json
import csv
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
import pandas as pd
from datetime import datetime

@dataclass(frozen=True)
class ZoneInfo:
    domain: str
    plan: str
    zone_id: str

@dataclass
class RuleDetails:
    domain: str
    ruleset_name: str
    ruleset_phase: str
    rule_id: str
    rule_description: str
    rule_expression: str
    rule_action: str
    rule_enabled: bool
    target_domain: str

class CloudflareRuleFinder:
    def __init__(self):
        self.headers = {
            "X-Auth-Email": "hakang@mz.co.kr",
            "X-Auth-Key": "f6f652701a00dc80fc3c5e764adb1b84461e3",
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.account_id = "8a215d1828c45f48abeb1d966d35faa0"
        self.target_domains: List[str] = []
        self.rules_found: List[RuleDetails] = []
        self.related_zones: Dict[str, List[ZoneInfo]] = {}
        
        os.makedirs('reports', exist_ok=True)

    def get_check_domains(self, domain: str) -> List[str]:
        """검사할 도메인 목록을 반환
        3단계 도메인: 전체 도메인과 루트 도메인 반환
        4단계 이상 도메인: 2depth부터 순차적으로 반환"""
        parts = domain.split('.')
        
        # 2단계 이하 도메인은 그대로 반환 (예: coupang.com)
        if len(parts) <= 2:
            return [domain]
            
        # 3단계 도메인 (예: cmapi.coupang.com)
        if len(parts) == 3:
            return [
                domain,  # 전체 도메인 (cmapi.coupang.com)
                '.'.join(parts[-2:])  # 루트 도메인 (coupang.com)
            ]
        
        # 4단계 이상 도메인 (예: ljc.jp.coupang.com)
        root_domain = '.'.join(parts[-2:])  # coupang.com
        second_level = '.'.join(parts[-3:])  # jp.coupang.com
        
        return [second_level, root_domain]

    def set_target_domains(self):
        """사용자로부터 검색할 도메인들을 입력받음"""
        print("\n검색할 도메인들을 입력해주세요.")
        print("여러 도메인을 검색하려면 쉼표(,)로 구분하여 입력하세요.")
        print("예시: cmapi.coupang.com, ljc.jp.coupang.com")
        
        domains_input = input("\n도메인 입력: ").strip()
        self.target_domains = [domain.strip() for domain in domains_input.split(',') if domain.strip()]
        
        if not self.target_domains:
            raise ValueError("최소 하나의 도메인을 입력해야 합니다.")
        
        print(f"\n검색할 도메인 목록:")
        for domain in self.target_domains:
            print(f"- {domain}")

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

    def identify_related_zones(self, zones: List[ZoneInfo]):
        """각 검색 도메인과 관련된 zone들을 식별"""
        for target_domain in self.target_domains:
            check_domains = self.get_check_domains(target_domain)
            found_zone = False
            related_zones = []
            
            print(f"\n도메인 '{target_domain}'에 대한 검사 범위:")
            print(f"- Account 레벨 규칙")
            
            # 도메인을 순차적으로 확인
            for check_domain in check_domains:
                for zone in zones:
                    if zone.domain == check_domain:
                        related_zones.append(zone)
                        found_zone = True
                        print(f"- Zone: {zone.domain} (ID: {zone.zone_id})")
                        break  # 현재 도메인에서 zone을 찾았으면 다음은 확인하지 않음
                
                if found_zone:
                    break  # zone을 찾았으면 더 이상 확인하지 않음
            
            if not found_zone:
                print("- 관련된 zone이 없습니다.")
            
            self.related_zones[target_domain] = related_zones

    def check_rule_for_targets(self, rule: Dict, ruleset_name: str, ruleset_phase: str, domain: str = 'Account Level') -> None:
        """Check if rule contains any of the target domains and store if found"""
        expression = rule.get('expression', '')
        description = rule.get('description', 'No description')
        
        for target_domain in self.target_domains:
            if target_domain.lower() in expression.lower():
                rule_details = RuleDetails(
                    domain=domain,
                    ruleset_name=ruleset_name,
                    ruleset_phase=ruleset_phase,
                    rule_id=rule.get('id', 'Unknown'),
                    rule_description=description,
                    rule_expression=expression,
                    rule_action=rule.get('action', 'Unknown'),
                    rule_enabled=rule.get('enabled', True),
                    target_domain=target_domain
                )
                self.rules_found.append(rule_details)

    def process_account_rulesets(self):
        """Process account level rulesets"""
        print("\nAccount 레벨 룰셋 처리 중...")
        
        url = f"{self.base_url}/accounts/{self.account_id}/rulesets"
        response = requests.get(url, headers=self.headers)
        account_rulesets = response.json().get('result', [])

        for ruleset in account_rulesets:
            ruleset_id = ruleset.get('id')
            ruleset_name = ruleset.get('name', 'Unnamed ruleset')
            ruleset_phase = ruleset.get('phase', 'Unknown phase')
            
            print(f"룰셋 확인 중: {ruleset_name}")
            
            details_url = f"{self.base_url}/accounts/{self.account_id}/rulesets/{ruleset_id}"
            details = requests.get(details_url, headers=self.headers).json()
            
            if not details.get('success'):
                print(f"룰셋 상세 정보 조회 실패: {ruleset_name}")
                continue

            rules = details.get('result', {}).get('rules', [])
            for rule in rules:
                self.check_rule_for_targets(rule, ruleset_name, ruleset_phase)

    def process_zone_rulesets(self):
        """Process zone level rulesets only for related zones"""
        print("\nZone 레벨 룰셋 처리 중...")
        
        for target_domain, zones in self.related_zones.items():
            if zones:  # zones가 있는 경우에만 처리
                parent_domain = zones[0].domain  # 찾은 가장 가까운 상위 도메인
                print(f"\n도메인 '{target_domain}'에 대한 zone 룰셋 처리 중... (상위 도메인: {parent_domain})")
                
                for zone in zones:
                    print(f"Zone 처리 중: {zone.domain}")
                    url = f"{self.base_url}/zones/{zone.zone_id}/rulesets"
                    response = requests.get(url, headers=self.headers)
                    rulesets = response.json()
                    
                    if not rulesets.get('success'):
                        print(f"Zone 룰셋 조회 실패: {zone.domain}")
                        continue

                    for ruleset in rulesets.get('result', []):
                        ruleset_id = ruleset.get('id')
                        ruleset_name = ruleset.get('name', 'Unnamed ruleset')
                        ruleset_phase = ruleset.get('phase', 'Unknown phase')

                        details_url = f"{self.base_url}/zones/{zone.zone_id}/rulesets/{ruleset_id}"
                        details = requests.get(details_url, headers=self.headers).json()
                        
                        if not details.get('success'):
                            print(f"Zone 룰셋 상세 정보 조회 실패: {ruleset_name}")
                            continue

                        rules = details.get('result', {}).get('rules', [])
                        for rule in rules:
                            self.check_rule_for_targets(rule, ruleset_name, ruleset_phase, zone.domain)

    def export_to_excel(self):
        """Export found rules to Excel with separate sheets for each domain"""
        if not self.rules_found:
            print("검색된 규칙이 없습니다.")
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        main_domain = self.target_domains[0].replace('.', '_')
        filename = f'reports/{main_domain}_cloudflare_rule_validation_{timestamp}.xlsx'
        
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            for target_domain in self.target_domains:
                domain_rules = [rule for rule in self.rules_found if rule.target_domain == target_domain]
                
                if domain_rules:
                    df = pd.DataFrame([vars(rule) for rule in domain_rules])
                    
                    columns = [
                        'target_domain', 'domain', 'ruleset_name', 'ruleset_phase', 'rule_id',
                        'rule_description', 'rule_expression', 'rule_action', 'rule_enabled'
                    ]
                    df = df[columns]
                    
                    sheet_name = target_domain[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    worksheet = writer.sheets[sheet_name]
                    worksheet.set_column('A:A', 30)
                    worksheet.set_column('B:B', 30)
                    worksheet.set_column('C:C', 20)
                    worksheet.set_column('D:D', 15)
                    worksheet.set_column('E:E', 20)
                    worksheet.set_column('F:F', 40)
                    worksheet.set_column('G:G', 50)
                    worksheet.set_column('H:H', 15)
                    worksheet.set_column('I:I', 10)
                    
                    print(f"\n도메인 '{target_domain}'에 대해 {len(domain_rules)}개의 규칙이 발견되었습니다.")
                else:
                    print(f"\n도메인 '{target_domain}'에 대한 규칙이 없습니다.")
        
        print(f"\n결과가 다음 파일에 저장되었습니다: {filename}")

def main():
    try:
        finder = CloudflareRuleFinder()
        finder.set_target_domains()
        zones = finder.read_zones_from_csv('enterprise_domains_8a215d1828c45f48abeb1d966d35faa0.csv')
        finder.identify_related_zones(zones)
        finder.process_account_rulesets()
        finder.process_zone_rulesets()
        finder.export_to_excel()
        
    except Exception as e:
        print(f"\n오류가 발생했습니다: {str(e)}")
        
    input("\n엔터 키를 눌러 프로그램을 종료하세요...")

if __name__ == "__main__":
    main()
