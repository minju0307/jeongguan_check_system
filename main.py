import re
import json
import argparse
import openai

from mrc import generate_answer
import inference_checklist as inference_checklist
from inference_reference import main as retrieval_reference
from generate_advice import prompt_generator, generate_advice
from inference_paragraph import semantic_search 


def assign_api_key(key_dir="./resources/openai_key.json"):
    """ Assign OpenAI API key. """
    with open(key_dir, "r") as f:
        file = json.load(f)
    openai.api_key = file["key"]


def split_document(input_text):
    # 긴 정관 문서 나누기 (장 기준)
    paragraphs = re.split("제[\s]?[\d][\s]?장", input_text)
    clean_para=[]
    
    for para in paragraphs[1:]:
        if '보칙' in para or '보 칙' in para or '보  칙' in para:
            continue
        para = para.strip()
        para = re.sub("[\n]+", "", para)
        clean_para.append(para)
        # print(para)
        # print()

    return clean_para

def split_sentence(sentence, max_length):
    words = sentence.split()
    result = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= max_length:
            current_line += word + " "
        else:
            result.append(current_line.strip())
            current_line = word + " "
    
    if current_line:
        result.append(current_line.strip())

    return result


def split_document_shorter(input_text):
    # 긴 정관 문서 나누기 (장 기준)
    paragraphs = re.split("제[\s]?[\d][\s]?장", input_text)
    clean_para=[]
    
    for para in paragraphs[1:]:
        if '보칙' in para or '보 칙' in para or '보  칙' in para:
            continue
        para = para.strip()
        para = re.sub("[\n]+", "", para)
        if len(para) > 1200:
            clean_para.extend(split_sentence(para, 1200))
        else:
            clean_para.append(para)
            
    # for p in clean_para:
    #     print(p)
    #     model_path = 'multilabel_model'
    #     tokenizer = AutoTokenizer.from_pretrained(model_path)
    #     print(len(tokenizer.tokenize(p)))
    #     print()

    return clean_para


def get_checklist(input_text):
    # 정관 문서와 관련된 변호사 질문 리스트 검색
    questions = inference_checklist.inference(input_text, model_path="./multilabel_model")

    return questions

def get_paragraph(question, input_texts, top_k):
    # 체크리스트 질문과 관련된 문단을 검색 (@top_k) 
    paragraphs = semantic_search(question, input_texts, top_k)
    
    return paragraphs

def get_mrc_answer(gpt_ver, input_text, question):
    # 정관 검토 질문에 대한 기계 독해 문제 풀이
    return generate_answer(gpt_ver, input_text, question)


def get_advice(gpt_ver, question, mrc_answer, top_k=3):
    # 질문과 관련된 상법 조항 검색
    references = retrieval_reference(top_k, question)

    # 변호사 조언 생성
    prompt = prompt_generator(question, mrc_answer, references)
    advice = generate_advice(gpt_ver, prompt)

    return advice


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--input_file_path", type=str, help="input text file path", default="input_samples/jeongguan_1.txt")
    parser.add_argument("--top_k_jeongguan", type=int, help="Top k references checklist question-paragraph retrieval", default="3")
    parser.add_argument("--top_k_sangbub", type=int, help="Top k references checklist question-law retrieval", default="3")
    parser.add_argument("--gpt_ver", type=str, help="openai gpt version", default="gpt-4-1106-preview")
    parser.add_argument("--openai_key_file_path", type=str, default="resources/openai_key.json", help="OpenAI key file path")
    args = parser.parse_args()

    assign_api_key(args.openai_key_file_path)

    # with open(args.input_file_path, "r", encoding="utf-8") as f:
    with open("../all/1.txt", "r", encoding="utf-8") as f:
        input_text = f.read()

    # 체크리스트 -> 문단 서치 
    # 정관 문단 나누기 
    input_texts = split_document_shorter(input_text)
    
    # 체크리스트 DB 불러오기
    with open("data/jeongguan_questions_56.json", "r", encoding="utf-8-sig") as f:
        questions = json.load(f)
    questions = list(questions.keys())
    
    # 정관 기계 독해 문제 풀이 
    for q in questions:
        print("**체크리스트 질문**")
        print(q)
        print()
        # 체크리스트 질문 - 정관 맵핑 
        paragraphs = get_paragraph(q, input_texts, args.top_k_jeongguan)
        print("**체크리스트 질문의 답을 할 수 있는 top-k 개의 문단 서치**")
        print('\n'.join(paragraphs))
        print()

        # mrc
        answer = get_mrc_answer(args.gpt_ver, '\n'.join(paragraphs), q)
        print("**체크리스트 질문과 답변 mrc 결과**")
        print(q)
        print(answer)
        print()
        print()
        
        # 변호사 조언 생성
        print("**변호사 조언 생성 결과**")
        advice = get_advice(args.gpt_ver, q, answer, args.top_k_sangbub)
        print(advice)
        print()
        print()
        
    
    '''
    # 문단 -> 체크리스트 서치
    # 정관 문단 나누기 
    input_texts = split_document(input_text)
    
    for text in input_texts[:1]:
        print("**정관 문단**")
        print(text)
        print()
        # 체크리스트 서치하기
        checklist = get_checklist(text)
        print("**정관 문단과 관련된 checklist**")
        print(checklist)
        print()
        
        # 정관 기계 독해 문제 풀이
        for c in checklist[:1]:
            question = c
            answer = get_mrc_answer(text, question)
            print("**체크리스트 질문과 답변 mrc 결과**")
            print(question)
            print(answer)
            print()
        
            advice = get_advice(question, answer, args.top_k)
            print("**변호사 조언 생성 결과**")
            print(advice)
            print() 
        
    
    print()
    print()
    '''