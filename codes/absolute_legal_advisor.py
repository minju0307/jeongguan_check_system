import json
import pandas as pd
import openai
import os
from .jb_use_files import *
from .jb_import_file import *

class ABSLegalAdvisor:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.data_cache = {}
        os.makedirs(self.cache_dir, exist_ok=True)

    def process_data(self, current_id, input_jg, rewritting_query, standard_jg_list, jg_category):
        filter_input_jg = []
        pattern = r'\s*제\d+조(?:의\d+)?\s*\('
        standard_idx_list = [0, 1, 2, 3, 5, 6, 7, 53]
        corpus = [standard_jg_list[str(i)] for i in standard_idx_list]
        corpus += list(rewritting_query['generated 조항'])
        
        for i in range(len(input_jg)):
            filter_input_jg.append(remove_first_match(input_jg[str(i)], pattern))
        
        paragraph_vectors = open_vector(f"./data/company/{current_id}_paragrph_embedding.txt")
        doc_vectors = open_vector("./data/embedding_category_rewriting_include_sb_0729.txt")

        search_index_list = getting_bm25_with_cosine_sim(corpus, filter_input_jg, paragraph_vectors, doc_vectors)
        result_list = [[], [], [], [], []]
        
        for tmp_list in search_index_list:
            for i in range(5):
                result_list[i].append(corpus[tmp_list[i]])

        category_list = []
        for i in range(len(result_list[0])):
            tmp_idx_list = [result_list[j][i] for j in range(5)]
            category_list.append(tmp_idx_list)
        
        res_list = []
        list_jo = [input_jg[str(i)] for i in input_jg]

        for idx, i in enumerate(list_jo):
            tmp_result = generate_label('gpt-4o', i, category_list[idx], jg_category)
            result_json = json.loads(tmp_result)
            res_list.append(result_json['category'])  

        first_result = pd.DataFrame({
            '정관': list_jo,
            'Category': res_list
        })

        return first_result

    def ad_advice(self, cate_df):
        df_text = ""
        for index, row in cate_df.iterrows():
            df_text += f"index: {index}\n정관 조항: {row['정관']}\n"
        
        prompt = f"""#Category#
[items]:
{df_text}

다음은 정관의 절대적 기재사항과 관련된 정관조항들이다. 이때 절대적 기재사항과 관련된 상법은 다음과 같다. 

######

[상법] 제289조 (정관의 작성, 절대적 기재사항)①발기인은 정관을 작성하여 다음의 사항을 적고 각 발기인이 기명날인 또는 서명하여야 한다. 
1. 목적 2. 상호 3. 회사가 발행할 주식의 총수 4. 액면주식을 발행하는 경우 1주의 금액 5. 회사의 설립시에 발행하는 주식의 총수 6. 본점의 소재지 7. 회사가 공고를 하는 방법 8. 발기인의 성명·주민등록번호 및 주소 
2. ③ 회사의 공고는 관보 또는 시사에 관한 사항을 게재하는 일간신문에 하여야 한다. 다만, 회사는 그 공고를 정관으로 정하는 바에 따라 전자적 방법으로 할 수 있다. <개정 2009. 5. 28.> 
3. ④ 회사는 제3항에 따라 전자적 방법으로 공고할 경우 대통령령으로 정하는 기간까지 계속 공고하고, 재무제표를 전자적 방법으로 공고할 경우에는 제450조에서 정한 기간까지 계속 공고하여야 한다. 다만, 공고기간 이후에도 누구나 그 내용을 열람할 수 있도록 하여야 한다. <신설 2009. 5. 28.> 
4. ⑤ 회사가 전자적 방법으로 공고를 할 경우에는 게시 기간과 게시 내용에 대하여 증명하여야 한다. <신설 2009. 5. 28.> ⑥ 회사의 전자적 방법으로 하는 공고에 관하여 필요한 사항은 대통령령으로 정한다. 
[항목] 1. 목적 2. 상호 3. 회사가 발행할 주식의 총수 4. 액면주식을 발행하는 경우 1주의 금액 5. 회사의 설립시에 발행하는 주식의 총수 6. 본점의 소재지 7. 회사가 공고를 하는 방법 8. 발기인의 성명·주민등록번호 및 주소 

[상법] 제329조(자본금의 구성)① 회사는 정관으로 정한 경우에는 주식의 전부를 무액면주식으로 발행할 수 있다. 다만, 무액면주식을 발행하는 경우에는 액면주식을 발행할 수 없다.
② 액면주식의 금액은 균일하여야 한다.
③ 액면주식 1주의 금액은 100원 이상으로 하여야 한다.
④ 회사는 정관으로 정하는 바에 따라 발행된 액면주식을 무액면주식으로 전환하거나 무액면주식을 액면주식으로 전환할 수 있다.
⑤ 제4항의 경우에는 제440조, 제441조 본문 및 제442조를 준용한다.
######

위 상법 제289조의 주어진 [항목]들이 모두 적절히 기재되어 있는지 확인하고, 특히 [항목] 4.의 경우 상법 제329조에 기반하여 확인하고, 모두 적절히 작성되어 있는지 그렇지 않은 지에 대해서 답변하시오. 이 때, 발기인의 주민등록번호는 작성하지 않아도 됩니다.
존재하지 않는다면 어느 항목이 존재하지 않는지, 해당 항목에 대해서 어떤 수정사항이 존재하는지 답변하시오.
        """
        res = generate_gpt("gpt-4o", prompt)
        return res

    def generate_advice(self, selected_id):
        input_jg, jg_sb_dict, ref_sb, idx_sb_dict, standard_jg_list, jg_category, rewritting_query, sb_law, sb_law_dict = DataCache.load_data(selected_id)
        first_result = self.process_data(selected_id, input_jg, rewritting_query, standard_jg_list, jg_category)
        
        cate_list = ['회사의 상호 및 명칭', '회사의 목적', '회사의 소재지', '회사의 공고방법', '회사가 발행할 주식의 총수', '회사가 액면주식을 발행하는 경우 1주의 금액', '회사의 설립시에 발행하는 주식의 총수', '발기인의 성명, 주소, 주민등록번호']

        cate_df = pd.DataFrame(columns=first_result.columns)
        for idx, i in enumerate(first_result['Category']):
            categories = i.split('#')
            for category in categories:
                if category in cate_list:
                    cate_df.loc[len(cate_df)] = first_result.loc[idx]
        
        advice = self.ad_advice(cate_df)
        
        return cate_df, advice

    def cache_data(self, selected_id):
        cache_file = os.path.join(self.cache_dir, f"{selected_id}_abs_cache.csv")
        
        
        if os.path.exists(cache_file):
            cache_df = pd.read_csv(cache_file)
            advice = cache_df.at[0, 'advice']
            cate_df = cache_df.drop(columns=['advice'])
        else:
            cate_df, advice = self.generate_advice(selected_id)
            cache_df = cate_df.copy()
            cache_df['advice'] = advice
            cache_df.to_csv(cache_file, index=False)

        #고정값: 상법 제289조
        law_text = DataCache.get_law_text()
        self.data_cache[selected_id] = (cate_df, law_text, advice)
        return [str(i) for i in cate_df.index], "데이터가 성공적으로 캐싱되었습니다."

    def display_results(self, selected_id, selected_index):
        if selected_id in self.data_cache:
            cate_df, law_text, advice = self.data_cache[selected_id]
            final_df = cate_df.copy()
            selected_index = int(selected_index)  # Ensure the index is an integer
            
            if selected_index in final_df.index:
                selected_row = final_df.loc[selected_index]
                return selected_row['정관'], law_text, advice
            else:
                return "선택된 인덱스가 유효하지 않습니다.", "변호사 조언을 생성할 수 없습니다."
        else:
            return "선택된 ID에 대한 데이터가 없습니다.", "변호사 조언을 생성할 수 없습니다."
