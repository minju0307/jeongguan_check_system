import os
import json
import pandas as pd

class DataCache:
    @staticmethod
    def load_data(current_id):
        '''
        회사에 따라 새로운 파일을 업로드 하는 경우, 해당 파일 및 공통 사용 파일을 불러오는 함수

        input:
            current_id: str, 회사 id

        output:
            input_jg: dict, 정관 데이터
            jg_sb_dict: dict, 상법 데이터
            ref_sb: dict, 상법 본문
            idx_sb_dict: dict, 상법 이름 - 인덱스 태깅
            standard_jg_list: dict, 정관 데이터
            jg_category: dict, 카테고리 태깅
            rewritting_query: pd.DataFrame, 카테고리 태깅
        '''
        with open(f"./data/company/{current_id}_list_jo.json", "r") as f:
            input_jg = json.load(f)
        with open("./data/기재사항_final.json", "r") as f:
            jg_sb_dict = json.load(f)
        with open("./data/sangbub_jo_prompt.json", "r") as f:
            ref_sb = json.load(f)
        with open("./data/sb_name_index.json", "r") as f:
            idx_sb_dict = json.load(f)
        with open("./data/standard_large_list_jo.json", "r") as f:
            standard_jg_list = json.load(f)
        with open("./data/category_rewriting_include_sb_0729.json", "r") as f:
            jg_category = json.load(f)
        with open("./data/law_articles.json", "r") as f:
            sb_law = json.load(f)
        with open("./data/matched_laws.json", "r") as f:
            sb_law_dict = json.load(f)

        rewritting_query = pd.read_csv("./data/category_rewriting_include_sb_0729.csv")

        return input_jg, jg_sb_dict, ref_sb, idx_sb_dict, standard_jg_list, jg_category, rewritting_query, sb_law, sb_law_dict


    @staticmethod
    def load_company_list(companies=str):
        '''
        주어진 회사 리스트를 불러오는 함수
        input:
            companies: str, 회사 리스트 (ex: 1,1149,1981,2541)

        output:
            comp: list, 회사 리스트의 각 줄을 저장한 리스트
        '''
        comp = []

        if companies == 'all.txt':
            with open(f"./data/{companies}", "r") as f:
                for line in f:
                    comp.append(line.strip())
        else:
            comp = companies.split(',')
        return comp

    @staticmethod
    def get_law_text():
        law_text = """
제289조 (정관의 작성, 절대적 기재사항)
①발기인은 정관을 작성하여 다음의 사항을 적고 각 발기인이 기명날인 또는 서명하여야 한다. 
1. 목적 2. 상호 3. 회사가 발행할 주식의 총수 4. 액면주식을 발행하는 경우 1주의 금액 5. 회사의 설립시에 발행하는 주식의 총수 6. 본점의 소재지 7. 회사가 공고를 하는 방법 8. 발기인의 성명·주민등록번호 및 주소 
③ 회사의 공고는 관보 또는 시사에 관한 사항을 게재하는 일간신문에 하여야 한다. 다만, 회사는 그 공고를 정관으로 정하는 바에 따라 전자적 방법으로 할 수 있다. <개정 2009. 5. 28.> 
④ 회사는 제3항에 따라 전자적 방법으로 공고할 경우 대통령령으로 정하는 기간까지 계속 공고하고, 재무제표를 전자적 방법으로 공고할 경우에는 제450조에서 정한 기간까지 계속 공고하여야 한다. 다만, 공고기간 이후에도 누구나 그 내용을 열람할 수 있도록 하여야 한다. <신설 2009. 5. 28.> 
⑤ 회사가 전자적 방법으로 공고를 할 경우에는 게시 기간과 게시 내용에 대하여 증명하여야 한다. <신설 2009. 5. 28.> 
⑥ 회사의 전자적 방법으로 하는 공고에 관하여 필요한 사항은 대통령령으로 정한다.

제329조(자본금의 구성)① 회사는 정관으로 정한 경우에는 주식의 전부를 무액면주식으로 발행할 수 있다. 다만, 무액면주식을 발행하는 경우에는 액면주식을 발행할 수 없다.
② 액면주식의 금액은 균일하여야 한다.
③ 액면주식 1주의 금액은 100원 이상으로 하여야 한다.
④ 회사는 정관으로 정하는 바에 따라 발행된 액면주식을 무액면주식으로 전환하거나 무액면주식을 액면주식으로 전환할 수 있다.
⑤ 제4항의 경우에는 제440조, 제441조 본문 및 제442조를 준용한다.
        """
        return law_text
