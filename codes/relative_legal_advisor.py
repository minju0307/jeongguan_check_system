import json
import re
import os
import pandas as pd
import openai
from .jb_import_file import *
from .jb_use_files import *

class RELLegalAdvisor:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.data_cache = {}
        os.makedirs(self.cache_dir, exist_ok=True)

    def res_advice(self, df):
        results = []
        for index, row in df.iterrows():
            prompt = f"""#사용자 정관 조항#
{row['정관']}

#관련 상법#
{row['상법']}
{row['상법시행령']}

#RESPONSE FORMAT#
{{"적법성" : "",
"정관과 상법의 비교": "",
"관련상법 존재 유무" : "",
"타 정관 조항" : "",
"총평" : ""
}}
######
다음은 #사용자 정관 조항#과 그 분류, 분류에 따른 #관련 상법#이다. 너는 한국 법률 전문가로서 주어진 정관이 적절하게 작성되었는지 여부를 #관련 상법#과 비교하여 검토하여야 한다.
#관련 상법#이 있는지 없는지 확인하라. #관련 상법#이 "관련 조항 없음" 으로 나타난 경우, "정관과 상법의 비교" 란에 "검색된 상법 없음" 으로 적어라. 그렇지 않다면 #사용자 정관 조항#에서 언급하는 것이 해당되는 모든 #관련 상법#의 조항과 비교하여 적법성을 면밀히 판단하라. 법령이 규정한 내용을 확대 해석한 정관 조항은 법령 위반 소지사항이 우려되므로 수정을 제안하라. 적법하다고 판단하였더라도, 법에서 규정한 숫자나 값을 위배하지는 않았는지 #관련 상법#의 다른 부분을 확인하고 다시 한 번 검토하여 확실한 것만 "적법성"에 상세히 이유를 적어라. (예를 들어, "~의 2분의 1 범위 내에서" 라는 말은 "~의 4분의 1 범위 내에서" 라는 범위를 초과하는 것으로, 법령 위반 소지가 우려된다.) #사용자 정관 조항#이 여러 항으로 구분되어 있다 하더라도, 전체를 고려하며 한번에 모든 조언을 생성하라.
"정관과 상법의 비교"에는 #관련 상법#의 어떤 부분이 #사용자 정관 조항#의 적법성을 판단하는데 사용되었는지만 간략하게 적고, "관련상법 존재 유무"는 "True"로 답하라. 만약 실질적으로 #관련 상법#의 내용이 #사용자 정관 조항#의 적법성을 판단하는데 관련이 없는 경우, 그 이유를 "정관과 상법의 비교"에 적고, "관련상법 존재 유무"는 "False"로 답하라.
만약 #사용자 정관 조항#에서 언급하고 있는 다른 정관 조항이 있다면 "타 정관 조항"에 해당 조항 번호(예: 제25조,제11조의2)를 '조' 단위까지만 기입하라. 언급하는 정관 조항의 갯수가 여러 개일 경우, #로 구분하여 답하라. 없다면 "타 정관 조항"에 "없음"이라고 답하라.
연관된 상법이 없으면 없기 때문에 평가할 수 없다고 총평을 작성하고, 수정사항이 있다면 수정사항에 집중하여 총평을 작성하라.
위의 요구사항을 모두 만족하는 JSON 형식으로 #RESPONSE FORMAT#에 맞게 답하라."""
            res = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            results.append(res.choices[0].message["content"])
        
        df['적법성'], df['정관과 상법의 비교'], df['관련상법 존재 유무'], df['타 정관 조항'], df['총평'] = self.formatting_response(results)

        return df

    def formatting_response(self, results):
        final_res = []
        for res in results:
            try:
                res = res.replace('```json', '').replace('```', '')
                res = json.loads(res)
                final_res.append([res['적법성'], res['정관과 상법의 비교'], res['관련상법 존재 유무'], res['타 정관 조항'], res['총평']])
            except:
                final_res.append(['', '', '', '', ''])
                
        return zip(*final_res)
    
    def process_data(self, current_id, standard_jg_list, rewritting_query, jg_category):
        with open(f"./data/company/{current_id}_list_jo.json", "r") as f:
            input_jg = json.load(f)

        pattern = r'\s*제\d+조(?:의\d+)?\s*\('
        filter_input_jg = []

        standard_idx_list = [0, 1, 2, 3, 5, 6, 7, 53]
        corpus = [standard_jg_list[str(i)] for i in standard_idx_list]
        corpus += list(rewritting_query['generated 조항'])

        for i in range(len(input_jg)):
            filter_input_jg.append(re.sub(pattern, '', input_jg[str(i)])) 

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

    def cache_data(self, selected_id):
        input_jg, jg_sb_dict, ref_sb, idx_sb_dict, standard_jg_list, jg_category, rewritting_query, sb_law, sb_law_dict = DataCache.load_data(selected_id)
        cache_file = os.path.join(self.cache_dir, f"{selected_id}_res_cache.csv")

        if os.path.exists(cache_file):
            df = pd.read_csv(cache_file)
            self.data_cache[selected_id] = (df['정관'], df['상법'], df['적법성'], df['정관과 상법의 비교'], df['관련상법 존재 유무'], df['타 정관 조항'], df['총평'])
            return [str(i) for i in df.index], "데이터가 성공적으로 캐싱되었습니다."

        first_result = self.process_data(selected_id, standard_jg_list, rewritting_query, jg_category)

        cate_list = ['회사의 상호 및 명칭', '회사의 목적', '회사의 소재지', '회사의 공고방법', '회사가 발행할 주식의 총수', '회사가 액면주식을 발행하는 경우 1주의 금액', '회사의 설립시에 발행하는 주식의 총수', '발기인의 성명, 주소, 주민등록번호']
        standard_list = []
        full_list = [i for i in range(len(first_result))]

        for idx, i in enumerate(first_result['Category']):
            categories = i.split('#')
            for category in categories:
                if category in cate_list:
                    standard_list.append(idx)
        
        corpus = rewritting_query['generated 조항']
        query_list = []

        for i in range(len(first_result)):
            if i in standard_list:
                continue
            query_list.append(first_result['정관'][i])

        total_paragraph_vector = open_vector(f"./data/company/{selected_id}_paragrph_embedding.txt")
        doc_vectors = open_vector("./data/embedding_category_rewriting_include_sb_0729.txt")[8:]
        use_list = list(set(full_list) - set(standard_list))
        paragraph_vectors = total_paragraph_vector[use_list]

        search_index_list = getting_bm25_with_cosine_sim(corpus, query_list, paragraph_vectors, doc_vectors)
        result_list = [[], [], [], [], []]

        for tmp_list in search_index_list:
            for i in range(5):
                result_list[i].append(rewritting_query['generated 조항'][tmp_list[i]])

        category_list = []
        for i in range(len(result_list[0])):
            tmp_idx_list = [result_list[j][i] for j in range(5)]
            category_list.append(tmp_idx_list)

        res_list = []
        tmp_list_jo = [first_result['정관'][i] for i in range(len(first_result)) if i not in standard_list]

        for idx, i in enumerate(tmp_list_jo):
            tmp_result = generate_label_2('gpt-4o', i, category_list[idx], jg_category)
            result_json = json.loads(tmp_result)
            res_list.append(result_json['category'])

        res_df = pd.DataFrame({
            '정관': tmp_list_jo,
            'Category': res_list
        })

        res_df['상법'] = res_df['Category'].apply(lambda x: get_jg_value(x, jg_sb_dict))

        ref_sb_dict = {}
        for line in ref_sb:
            match = re.match(r'(제\d+조의?\d*)', line)
            if match:
                ref_sb_dict[match.group(1)] = line

        data_dict = {}
        for entry in sb_law:
            match = re.match(r'(제\d+조의?\d*)', entry)
            if match:
                article = match.group(1)
                content = entry
                data_dict[article] = content

        res_df['상법'] = res_df['상법'].apply(lambda x: replace_jg_value(x, ref_sb_dict))
        res_df['상법시행령'] = res_df['상법'].apply(lambda x: get_sb(x, sb_law_dict, data_dict))
        final_df = self.res_advice(res_df)

        final_df.to_csv(cache_file, index=False)
        self.data_cache[selected_id] = (final_df['정관'], final_df['상법'], final_df['적법성'], final_df['정관과 상법의 비교'], final_df['관련상법 존재 유무'], final_df['타 정관 조항'], final_df['총평'])
        return [str(i) for i in final_df.index], "데이터가 성공적으로 캐싱되었습니다."
    
    def display_results(self, selected_id, selected_index):
        if selected_id not in self.data_cache:
            raise ValueError("Data not found. Please cache the data first.")
        idx = int(selected_index)
        return self.data_cache[selected_id][0][idx], self.data_cache[selected_id][1][idx], str(self.data_cache[selected_id][2][idx])+'\n'+str(self.data_cache[selected_id][3][idx])+'\n'+str(self.data_cache[selected_id][5][idx])+'\n'+str(self.data_cache[selected_id][6][idx])