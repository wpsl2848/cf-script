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
    search_term: str

class CloudflareRuleFinder:
    def __init__(self):
        self.headers = {
            "X-Auth-Email": "hakang@mz.co.kr",
            "X-Auth-Key": "f6f652701a00dc80fc3c5e764adb1b84461e3",
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.account_id = "8a215d1828c45f48abeb1d966d35faa0"
        self.search_terms: List[str] = []
        self.rules_found: List[RuleDetails] = []
        self.zones: List[ZoneInfo] = []
        self.custom_filename: str = ""
        
        os.makedirs('reports', exist_ok=True)

    def sanitize_sheet_name(self, sheet_name: str) -> str:
        """Excel 시트 이름에서 사용할 수 없는 문자를 제거하거나 대체"""
        # Excel에서 시트 이름으로 사용할 수 없는 문자: [ ] : * ? / \
        invalid_chars = ['[', ']', ':', '*', '?', '/', '\\']
        result = sheet_name
        for char in invalid_chars:
            result = result.replace(char, '_')
        return result[:31]  # Excel 시트 이름 길이 제한 31자

    def set_search_terms(self):
        """사용자로부터 검색할 규칙 이름들과 저장할 파일 이름을 입력받음"""
        print("\n검색할 규칙 이름들을 입력해주세요.")
        print("여러 규칙을 검색하려면 쉼표(,)로 구분하여 입력하세요.")
        print("예시: block_ip, allow_traffic")
        
        terms_input = input("\n규칙 이름 입력: ").strip()
        self.search_terms = [term.strip() for term in terms_input.split(',') if term.strip()]
        
        if not self.search_terms:
            raise ValueError("최소 하나의 규칙 이름을 입력해야 합니다.")
        
        # 파일 이름 입력 받기
        print("\n저장할 엑셀 파일의 이름을 입력해주세요 (확장자 제외)")
        print("입력하지 않으면 기본 이름으로 저장됩니다.")
        self.custom_filename = input("파일 이름 입력: ").strip()
        
        print(f"\n검색할 규칙 이름 목록:")
        for term in self.search_terms:
            print(f"- {term}")

    def read_zones_from_csv(self, csv_file: str):
        """CSV 파일에서 zone 정보 읽기"""
        with open(csv_file, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            self.zones = [
                ZoneInfo(
                    domain=row['Domain Name'],
                    plan=row['Plan'],
                    zone_id=row['Zone ID']
                ) for row in csv_reader
            ]
        print(f"\n총 {len(self.zones)}개의 zone을 로드했습니다.")

    def check_rule_for_terms(self, rule: Dict, ruleset_name: str, ruleset_phase: str, domain: str = 'Account Level'):
        """규칙이 검색어와 일치하는지 확인하고 저장"""
        description = rule.get('description', 'No description')
        expression = rule.get('expression', '')
        rule_id = rule.get('id', 'Unknown')
        
        for search_term in self.search_terms:
            if (search_term.lower() in ruleset_name.lower() or 
                search_term.lower() in description.lower() or 
                search_term.lower() in expression.lower() or
                search_term.lower() in rule_id.lower()):
                
                rule_details = RuleDetails(
                    domain=domain,
                    ruleset_name=ruleset_name,
                    ruleset_phase=ruleset_phase,
                    rule_id=rule_id,
                    rule_description=description,
                    rule_expression=expression,
                    rule_action=rule.get('action', 'Unknown'),
                    rule_enabled=rule.get('enabled', True),
                    search_term=search_term
                )
                self.rules_found.append(rule_details)

    def process_account_rulesets(self):
        """Account 레벨 룰셋 처리"""
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
                self.check_rule_for_terms(rule, ruleset_name, ruleset_phase)

    def process_zone_rulesets(self):
        """모든 zone의 룰셋 처리"""
        print("\nZone 레벨 룰셋 처리 중...")
        
        for zone in self.zones:
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
                    self.check_rule_for_terms(rule, ruleset_name, ruleset_phase, zone.domain)

    def export_to_excel(self):
        """검색된 규칙을 Excel로 내보내기"""
        if not self.rules_found:
            print("검색된 규칙이 없습니다.")
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 사용자가 입력한 파일 이름이 있으면 사용, 없으면 기본 이름 사용
        if self.custom_filename:
            base_filename = self.custom_filename
        else:
            base_filename = f"rule_search_{self.search_terms[0].replace(' ', '_')}"
        
        filename = f'reports/{base_filename}_{timestamp}.xlsx'
        
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            # 요약 정보를 저장할 데이터 준비
            summary_data = []
            
            # 각 검색어별 규칙 수 집계
            for search_term in self.search_terms:
                term_rules = [rule for rule in self.rules_found if rule.search_term == search_term]
                rule_count = len(term_rules)
                
                summary_data.append({
                    '검색어': search_term,
                    '발견된 규칙 수': rule_count,
                    '상태': f"{rule_count}개의 규칙 발견됨" if rule_count > 0 else "규칙 없음"
                })
                print(f"\n검색어 '{search_term}'에 대해 {rule_count}개의 규칙이 발견되었습니다.")

            # 1. 먼저 요약 시트 생성 (첫 번째 시트)
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='검색 결과 요약', index=False)
            
            # 요약 시트 스타일링
            summary_sheet = writer.sheets['검색 결과 요약']
            summary_sheet.set_column('A:A', 40)
            summary_sheet.set_column('B:B', 15)
            summary_sheet.set_column('C:C', 25)
            
            # 헤더 스타일
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D9E1F2',
                'border': 1
            })
            
            # 헤더 스타일 적용
            for col_num, value in enumerate(summary_df.columns.values):
                summary_sheet.write(0, col_num, value, header_format)

            # 2. 그 다음 각 검색어별 상세 시트 생성
            for search_term in self.search_terms:
                term_rules = [rule for rule in self.rules_found if rule.search_term == search_term]
                
                if term_rules:
                    df = pd.DataFrame([vars(rule) for rule in term_rules])
                    
                    columns = [
                        'search_term', 'domain', 'ruleset_name', 'ruleset_phase', 'rule_id',
                        'rule_description', 'rule_expression', 'rule_action', 'rule_enabled'
                    ]
                    df = df[columns]
                    
                    # 시트 이름에서 사용할 수 없는 문자 처리
                    safe_sheet_name = self.sanitize_sheet_name(search_term)
                    df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                    
                    worksheet = writer.sheets[safe_sheet_name]
                    worksheet.set_column('A:A', 20)
                    worksheet.set_column('B:B', 30)
                    worksheet.set_column('C:C', 20)
                    worksheet.set_column('D:D', 15)
                    worksheet.set_column('E:E', 20)
                    worksheet.set_column('F:F', 40)
                    worksheet.set_column('G:G', 50)
                    worksheet.set_column('H:H', 15)
                    worksheet.set_column('I:I', 10)
        
        print(f"\n결과가 다음 파일에 저장되었습니다: {filename}")
        print("'검색 결과 요약' 시트가 첫 번째 시트로 배치되었습니다.")

def main():
    try:
        finder = CloudflareRuleFinder()
        finder.set_search_terms()
        finder.read_zones_from_csv('enterprise_domains_8a215d1828c45f48abeb1d966d35faa0.csv')
        finder.process_account_rulesets()
        finder.process_zone_rulesets()
        finder.export_to_excel()
        
    except Exception as e:
        print(f"\n오류가 발생했습니다: {str(e)}")
        
    input("\n엔터 키를 눌러 프로그램을 종료하세요...")

if __name__ == "__main__":
    main()