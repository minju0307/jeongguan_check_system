import re
import openai
import numpy as np
import json
from rank_bm25 import BM25Okapi
from transformers import AutoTokenizer
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

def txt_to_json(file_content):
    '''
    입력된 정관 텍스트 파일을 json 형식으로 변환

    input:
        file_content: 정관 텍스트 파일
        
    output:
        clauses: json 형식의 정관
    '''
    lines = file_content.split('\n')
    clauses = {}
    index = -1

    for line in lines:
        if line.startswith('제') and '조' in line:
            index += 1
            clauses[str(index)] = line.strip()
        elif line.strip() and index >= 0:
            clauses[str(index)] += ' ' + line.strip()

    return clauses

def remove_first_match(text, pattern):
    '''
    전처리 - 텍스트에서 패턴과 첫 번째 매칭되는 부분을 제거

    input:
        text: 전처리할 텍스트
        pattern: 제거할 패턴

    output:
        text: 전처리된 텍스트
    '''
    # 패턴을 컴파일
    regex = re.compile(pattern)    
    # 첫 번째 매칭 찾기
    match = regex.search(text)    
    # 매칭된 부분이 있으면 제거
    if match:
        start, end = match.span()
        text = text[:start] + text[end:]
    
    return text

def split_json_objects(json_string):
    '''
    txt 형태로 저장된 json 파일을 json object 단위로 분리

    input:
        json_string: txt 형태로 저장된 json 파일

    output:
        objects: 분리된 json object 리스트
    '''
    objects = []
    balance = 0
    start = 0

    for i, char in enumerate(json_string):
        if char == '{':
            if balance == 0:
                start = i
            balance += 1
        elif char == '}':
            balance -= 1
            if balance == 0:
                objects.append(json_string[start:i+1])

    return objects

def to_vector_list(json_objects):
    '''
    json object 리스트에서 벡터 리스트 추출

    input:
        json_objects: json object 리스트

    output:
        result: 벡터 리스트 (여기서는 보통 임베딩 벡터를 활용한다.)
    '''
    result = []
    for obj in json_objects:
        tmp = json.loads(obj)
        result.append(tmp['embedding'])
    
    return np.array(result)
        
def open_vector(file_path):
    '''
    입력받은 파일을 읽어서 벡터 리스트로 변환

    input:
        file_path: 벡터 파일 경로(확장자 무관한지 확인필요)

    output:
        file_list: 벡터 리스트 
    '''
    try:
        with open(file_path, "r") as fd:
            file = fd.read()
    except FileNotFoundError:
        raise FileNotFoundError("There is no embedding vector file. Check the file path.")
    
    file = split_json_objects(file)
    file_list = to_vector_list(file)
    return file_list

def getting_bm25_with_cosine_sim(corpus, query_list, paragraph_vectors, doc_vectors):
    '''
    query_list와 paragraph_vectors를 이용하여 BM25와 Cosine Similarity를 이용하여 문서를 추출하는 함수
    
    input:
        corpus: list, 표준 정관 + 리라이트 정관
        query_list: list, 입력 회사 정관
        paragraph_vectors: np.array, 입력 회사 정관 벡터 리스트
        doc_vectors: np.array, 표준 정관 + 리라이트 정관 벡터 리스트

    output:
        idx_list: list, 추출된 문서 인덱스 리스트
    '''
    # 오류 검증
    if len(corpus) != len(doc_vectors):
        raise ValueError(f"Length of corpus and doc_vectors should be same.\nCorpus: {len(corpus)}, Doc_vectors: {len(doc_vectors)}")
    if len(query_list) != len(paragraph_vectors):
        raise ValueError(f"Length of query_list and paragraph_vectors should be same.\nQuery_list: {len(query_list)}, Paragraph_vectors: {len(paragraph_vectors)}")
    
    # 토크나이저
    tokenizer = AutoTokenizer.from_pretrained("beomi/llama-2-ko-7b")
    tokenized_corpus = [tokenizer.tokenize(doc) for doc in corpus]

    # BM25 모델 생성
    bm25 = BM25Okapi(tokenized_corpus)

    # 쿼리
    tokenized_query = [tokenizer.tokenize(doc) for doc in query_list]

    # 각 문서에 대한 BM25 점수 계산
    doc_scores = [bm25.get_scores(query) for query in tokenized_query]

    #Normalization
    scaler = MinMaxScaler()
    normalized_doc_scores = [scaler.fit_transform(np.array(scores).reshape(-1, 1)).flatten() for scores in doc_scores]

    bm25_weight = 0.5
    embedding_weight = 0.5

    idx_list = []

    for idx, i in enumerate(paragraph_vectors):
        vec = i.reshape(1, -1)
        cosine_sim = cosine_similarity(vec, doc_vectors)[0]
        #print(idx)
        bm25_score = normalized_doc_scores[idx]
        combined_score = bm25_weight*bm25_score + embedding_weight*cosine_sim
        sorted_indices = np.argsort(combined_score)[::-1]
        idx_list.append(sorted_indices[:5])
        
    return idx_list

def generate_gpt(model, input_text):
    '''
    어떤 prompt가 들어오든, GPT 모델을 활용하여 답변을 생성하는 함수

    input:
        model: GPT 모델(gpt-4o, gpt-4o-mini 등)
        input_text: 사용자 입력 문장

    output:
        res: 생성된 답변
    '''
    messages = [
        {"role": "system", "content": "You are a professional Lawyer"},
        {"role": "user", "content": input_text}
    ]
    response = openai.chat.completions.create(model=model, messages=messages, temperature=0.5)
    res = response.choices[0].message.content
    return res

def generate_label(model, jg, category_list, jg_category):
    category = f"""* {jg_category[category_list[0]]}
* {jg_category[category_list[1]]}
* {jg_category[category_list[2]]}
* {jg_category[category_list[3]]}
* {jg_category[category_list[4]]}
* 관련 조항 없음"""
    sys_prompt = "You are a professional Korean Laywer. You must answer in JSON FORMAT."
    user_prompt = """#RESPONSE FORMAT#
{{"category" : ""}}
######

#OBJECT#
As a lawyer, you are required to determine which #CATEGORY# a given Article of Incorporation (AOI) falls under. The AOI may fall under one or more categories, or it may not fall under any category. However, the AOI can belong to a maximum of two categories. When deciding which category the AOI falls under, focus on the title.

If the AOI does not fall under any category, respond with '관련 조항 없음'. If the AOI falls under multiple categories, mention all applicable categories. When listing multiple categories, use '#' as the separator. Ensure that you use the exact names of the categories when responding. Follow the #RESPONSE FORMAT# for your answers.

The response should be in Korean, where given categories are all in Korean.

#CATEGORY#
{category}
######

[Articles of Incorporations]
{jg}
#######
"""
    input = user_prompt.format(category=category, jg=jg)
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": input}
    ]
    print(input)
    response = openai.chat.completions.create(model=model, messages=messages, temperature=0.3, response_format={"type": "json_object"})
    res = response.choices[0].message.content
    print(res)
    return res


def generate_label_2(model, jg, category_list, jg_category):
    '''
    상대적 기재사항인 경우, 카테고리를 한번 더 확인하는 함수

    input:
        - model: GPT 모델(gpt-4o, gpt-4o-mini 등)
        - jg: 정관
        - category_list: 카테고리 리스트
        - jg_category: 카테고리 사전

    output:
        - res: 생성된 답변
    '''
    category = f"""* {jg_category[category_list[0]]}
* {jg_category[category_list[1]]}
* {jg_category[category_list[2]]}
* {jg_category[category_list[3]]}
* {jg_category[category_list[4]]}
* 관련 조항 없음"""
    sys_prompt = "You are a professional Korean Laywer. You must answer in json FORMAT."
#     user_prompt = """#EXAMPLE#
# #CATEGORY#
# * 감사위원회 설치
# * 최대주주 등의 주식의 합계로 감사 또는 사외이사가 아닌 감사위원회위원을 선임하거나 해임할 때 의결권 행사의 제한비율 인하
# * 이사회내 위원회의 설치
# * 이사회 의장의 선임
# * 이사회(청산인회)의 소집통지기간의 단축
# * 관련 조항 없음
# #######

# [Articles of Incorporations]
# 제40조(감사위원회의 구성) ① 회사는 감사에 갈음하여 제39조의 규정에 의한 감사위원회를 둔다. 

# ② 감사위원회는 3인 이상의 이사로 구성한다. 

# ③ 위원의 3분의 2 이상은 사외이사이어야 하고, 사외이사가 아닌 위원은 「자본시장법」 제26조 제3항의 요건을 갖추어야 한다. 

# ④ 감사위원회는 그 결의로 위원회를 대표할 자를 선정하여야 한다. 

# ⑤ 감사위원의 임기는 1년으로 한다. 다만, 감사위원의 임기 만료 전 이사로서의 임기만료, 사임, 해임의 사유가 발생하는 경우에는 이사의 임기까지로 한다. 

# ⑥ 감사위원회의 위원후보는 임원후보추천위원회에서 추천한다. 이 경우 위원 총수의 3분2이상의 찬성으로 의결한다.
# ######

# {{"category" : "감사위원회 설치#최대주주 등의 주식의 합계로 감사 또는 사외이사가 아닌 감사위원회위원을 선임하거나 해임할 때 의결권 행사의 제한비율 인하"}}
# ######
    user_prompt = """#RESPONSE FORMAT#
{{"category" : ""}}
######

#OBJECT#
As a lawyer, you are required to determine which #CATEGORY# a given Article of Incorporation (AOI) falls under. The AOI may fall under one or more categories, or it may not fall under any category. However, the AOI can belong to a maximum of two categories. When deciding which category the AOI falls under, focus on the title.
1
If the AOI does not fall under any category, respond with '관련 조항 없음'. If the AOI falls under multiple categories, mention all applicable categories. When listing multiple categories, use '#' as the separator. Ensure that you use the exact names of the categories when responding. Follow the #RESPONSE FORMAT# for your answers.

The response should be in Korean, where given categories are all in Korean.

#CATEGORY#
{category}
######

[Articles of Incorporations]
{jg}
#######
"""
    input = user_prompt.format(category = category, jg = jg)
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": input}
    ]
    print(input)
    response = openai.chat.completions.create(model=model, messages=messages, temperature=0.3,response_format={"type": "json_object"})
    res = response.choices[0].message.content

    print(res)
    return res

def get_jg_value(category, jg_dict):
    categories = category.split('#')
    for cat in categories:
        for key, value in jg_dict['상대적 기재사항'].items():
            if cat in value:
                return value[cat]
        for key, value in jg_dict['임의적 기재사항'].items():
            if cat in key:
                return value
    return '관련 조항 없음'

def replace_jg_value(jg_value, ref_dict):
    keys = jg_value.split(',')
    replaced_values = [ref_dict.get(key.strip(), key) for key in keys]
    return ', '.join(replaced_values)

def get_sb(article, sb_law_dict, data_dict):
        '''
        상법 조항을 참조하는 상법 시행령을 반환하는 함수

        input:
            - article: str, 정관 조항
            - sb_law_dict: dict, 상법 조항 - 상법 시행령 매칭
            - data_dict: dict, 상법 시행령 전문
        
        output:
            - str, 검색된 상법 시행령 전문 (default: "\n")
        '''
        article_match = re.match(r'(제\d+조의?\d*)', article)
        if article_match:
            law_article = article_match.group(1)
            sb_article = sb_law_dict.get(law_article)
            if sb_article:
                return data_dict.get(sb_article, "\n")
        return "\n"
    