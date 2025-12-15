"""
DART API를 활용한 한국 종목 재무제표 조회 유틸리티
(Hybrid Strategy: KIS API + DART API)

제공 데이터:
- 부채비율 (debt_to_equity): 연결재무제표 & 자본총계 Max 로직 적용
- 매출성장률 (revenue_growth_yoy): 전년 동기 대비
- 영업이익률 (operating_margin): 매출액 대비 영업이익

참고:
- DART API 문서: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019018
"""

import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

load_dotenv()

DART_API_KEY = os.getenv("DART_API_KEY")


class DartFinancialAPI:
    """DART API를 사용한 재무제표 조회 클래스 (개선된 버전)"""
    
    BASE_URL = "https://opendart.fss.or.kr/api"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or DART_API_KEY
        # API 키가 없으면 경고만 출력하고 진행 (호출 시 에러 처리)
        if not self.api_key:
            print("[DartFinancialAPI] 경고: DART_API_KEY가 설정되지 않았습니다.")
    
    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """종목코드(6자리)로 DART 고유번호(corp_code) 조회"""
        try:
            # 1. 로컬 파일 확인
            xml_path = os.path.join(os.path.dirname(__file__), "..", "CORPCODE.xml")
            if os.path.exists(xml_path):
                tree = ET.parse(xml_path)
                root = tree.getroot()
                for corp in root.findall('.//list'):
                    if corp.findtext('stock_code') == stock_code:
                        return corp.findtext('corp_code')
            
            # 2. 파일 없으면 API로 다운로드 (최초 1회)
            print("[get_corp_code] CORPCODE.xml 파일이 없어 다운로드합니다...")
            self._download_corp_code_file(xml_path)
            
            # 다시 시도
            if os.path.exists(xml_path):
                tree = ET.parse(xml_path)
                root = tree.getroot()
                for corp in root.findall('.//list'):
                    if corp.findtext('stock_code') == stock_code:
                        return corp.findtext('corp_code')
            
            return None
        except Exception as e:
            print(f"[get_corp_code] 오류: {e}")
            return None

    def _download_corp_code_file(self, target_path: str):
        """DART 기업 고유번호 파일 다운로드 및 압축 해제"""
        import zipfile
        import io
        
        url = "https://opendart.fss.or.kr/api/corpCode.xml"
        params = {'crtfc_key': self.api_key}
        
        try:
            res = requests.get(url, params=params)
            with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                # 압축 파일 내의 CORPCODE.xml을 꺼내서 target_path로 저장
                with z.open('CORPCODE.xml') as f_in, open(target_path, 'wb') as f_out:
                    f_out.write(f_in.read())
            print(f"[DartFinancialAPI] CORPCODE.xml 다운로드 완료: {target_path}")
        except Exception as e:
            print(f"[DartFinancialAPI] CORPCODE.xml 다운로드 실패: {e}")

    def _get_financial_data(self, corp_code: str, year: str, reprt_code: str) -> Dict[str, float]:
        """
        특정 연도/보고서의 재무 데이터 조회 (연결재무제표 기준)
        반환: {'sales': ..., 'op_income': ..., 'net_income': ..., 'equity': ..., 'liabilities': ...}
        """
        url = f"{self.BASE_URL}/fnlttSinglAcntAll.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': year,
            'reprt_code': reprt_code,
            'fs_div': 'CFS'  # 무조건 연결재무제표
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data.get('status') != '000':
                return {}
            
            result = {}
            equity_max = 0.0
            net_income_max = 0.0
            
            for item in data.get('list', []):
                nm = item.get('account_nm', '').strip()
                amt = item.get('thstrm_amount', '').replace(',', '').strip()
                
                if not amt: continue
                val = float(amt)
                
                # 1. 매출액
                if nm in ['매출액', '수익(매출액)']:
                    result['sales'] = val
                
                # 2. 영업이익
                elif nm in ['영업이익', '영업이익(손실)']:
                    result['op_income'] = val
                
                # 3. 당기순이익 (누적치 중 절댓값 가장 큰 것 선택)
                elif nm in ['당기순이익', '당기순이익(손실)', '분기순이익', '분기순이익(손실)', '반기순이익', '반기순이익(손실)']:
                    if abs(val) > abs(net_income_max):
                        net_income_max = val
                        result['net_income'] = val
                
                # 4. 부채총계
                elif nm == '부채총계':
                    result['liabilities'] = val
                
                # 5. 자본총계 (가장 큰 값 선택 - 지배/비지배 이슈 해결)
                elif nm in ['자본총계', '자본']:
                    if val > equity_max:
                        equity_max = val
                        result['equity'] = val
            
            return result
        except Exception as e:
            print(f"[_get_financial_data] API 호출 실패: {e}")
            return {}

    def calculate_fundamentals(self, stock_code: str) -> Dict[str, Any]:
        """
        종목코드로 주요 재무지표 계산 (최신 분기 기준)
        """
        if not self.api_key:
            return {}

        corp_code = self.get_corp_code(stock_code)
        if not corp_code:
            return {}
        
        # 현재 시점 기준 최신 보고서 찾기 전략
        # 1. 올해 3분기 -> 반기 -> 1분기 -> 작년 사업보고서 순으로 시도
        current_year = datetime.now().year
        strategies = [
            (str(current_year), '11014'), # 3분기
            (str(current_year), '11012'), # 반기
            (str(current_year), '11013'), # 1분기
            (str(current_year - 1), '11011'), # 작년 사업보고서
        ]
        
        curr_data = {}
        curr_year = ""
        curr_reprt = ""
        
        # 최신 데이터 조회 시도
        for year, reprt in strategies:
            data = self._get_financial_data(corp_code, year, reprt)
            if data:
                curr_data = data
                curr_year = year
                curr_reprt = reprt
                break
        
        if not curr_data:
            return {}
            
        result = {}
        
        # 1. 부채비율 (Liabilities / Equity)
        if 'liabilities' in curr_data and 'equity' in curr_data and curr_data['equity'] > 0:
            result['debt_to_equity'] = curr_data['liabilities'] / curr_data['equity']
            result['total_liabilities'] = curr_data['liabilities']
            result['total_equity'] = curr_data['equity']
            
        # 2. 영업이익률 (Operating Income / Sales)
        if 'op_income' in curr_data and 'sales' in curr_data and curr_data['sales'] > 0:
            result['operating_margin'] = curr_data['op_income'] / curr_data['sales']
            
        # 3. 매출성장률 (YoY)
        # 전년 동기 데이터 조회 필요
        if curr_year and curr_reprt:
            prev_year = str(int(curr_year) - 1)
            prev_data = self._get_financial_data(corp_code, prev_year, curr_reprt)
            
            if 'sales' in curr_data and 'sales' in prev_data and prev_data['sales'] > 0:
                result['revenue_growth_yoy'] = (curr_data['sales'] - prev_data['sales']) / prev_data['sales']
        
        # 기타 데이터
        if 'net_income' in curr_data:
            result['net_income'] = curr_data['net_income']
        if 'sales' in curr_data:
            result['revenue'] = curr_data['sales']
            
        return result

if __name__ == "__main__":
    # 테스트
    dart = DartFinancialAPI()
    # SK하이닉스
    print(dart.calculate_fundamentals("000660"))
