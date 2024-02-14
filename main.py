import re
import json
import argparse
import openai
import os
import fire

from config import MULTILABEL_MODEL_PATH, DPR_MODEL_PATH
from mrc import generate_answer
import inference_checklist as inference_checklist
from inference_reference import main as retrieval_reference
from generate_advice import prompt_generator, generate_advice
from inference_paragraph import semantic_search


def assign_api_key(key_dir="./resources/openai_key.json"):
    """Assign OpenAI API key."""
    with open(key_dir, "r") as f:
        file = json.load(f)
    openai.api_key = file["key"]


def split_document(input_text):
    # 긴 정관 문서 나누기 (장 기준)
    paragraphs = re.split("제[\s]?[\d][\s]?장", input_text)
    clean_para = []

    for para in paragraphs[1:]:
        if "보칙" in para or "보 칙" in para or "보  칙" in para:
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
    clean_para = []

    for para in paragraphs[1:]:
        if "보칙" in para or "보 칙" in para or "보  칙" in para:
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
    questions = inference_checklist.inference(
        input_text, model_path="./multilabel_model"
    )

    return questions


def get_paragraph(question, input_texts, top_k):
    # 체크리스트 질문과 관련된 문단을 검색 (@top_k)
    paragraph_idxs = semantic_search(question, input_texts, top_k, model_path=MULTILABEL_MODEL_PATH)

    paragraphs = [input_texts[k] for k in paragraph_idxs]

    return paragraphs


def get_mrc_answer(gpt_ver, input_text, question):
    # 정관 검토 질문에 대한 기계 독해 문제 풀이
    return generate_answer(gpt_ver, input_text, question)


def get_reference(top_k, question):
    # 질문과 관련된 상법 조항 검색
    return retrieval_reference(top_k, question, model_path=DPR_MODEL_PATH)


def get_advice(gpt_ver, question, mrc_answer, references):
    # 변호사 조언 생성
    prompt = prompt_generator(question, mrc_answer, references)
    advice = generate_advice(gpt_ver, prompt)

    return advice


def main(
        input_id,
        input_text,
        top_k_jeongguan=3,
        top_k_sangbub=3,
        gpt_ver="gpt-4-1106-preview"
):
    outputs = {}

    outputs["doc_id"] = input_id
    outputs["doc_text"] = input_text

    # 체크리스트 -> 문단 서치
    # 정관 문단 나누기
    input_texts = split_document_shorter(input_text)
    outputs["doc_paragraphs"] = input_texts

    # 체크리스트 DB 불러오기
    with open("data/jeongguan_questions_56.json", "r", encoding="utf-8-sig") as f:
        questions = json.load(f)
    questions = list(questions.keys())
    outputs["checklist_questions"] = questions

    outputs["mapping_paragraphs"] = []
    outputs["mrc_answer"] = []
    outputs["sangbub"] = []
    outputs["advice"] = []

    # 정관 기계 독해 문제 풀이
    for q in questions[:1]:  # test 용으로 2개만
        print("**체크리스트 질문**")
        print(q)
        print()
        # 체크리스트 질문 - 정관 맵핑
        paragraphs = get_paragraph(q, input_texts, top_k_jeongguan)
        print("**체크리스트 질문의 답을 할 수 있는 top-k 개의 문단 서치**")
        print("\n".join(paragraphs))
        print()
        outputs["mapping_paragraphs"].append("\n".join(paragraphs))

        # mrc
        answer = get_mrc_answer(gpt_ver, "\n".join(paragraphs), q)
        print("**체크리스트 질문과 답변 mrc 결과**")
        print(q)
        print(answer)
        print()
        print()
        outputs["mrc_answer"].append(answer)

        # 변호사 조언 생성
        print("**변호사 조언 생성 결과**")
        sangbub = get_reference(top_k_sangbub, q)
        advice = get_advice(gpt_ver, q, answer, sangbub)
        print(advice)
        print()
        print()
        outputs["sangbub"].append(sangbub)
        outputs["advice"].append(advice)

    if not os.path.exists("./db"):
        os.makedirs("./db")

    with open(f"db/{input_id}.json", "w", encoding="utf-8") as fw:
        json.dump(outputs, fw, indent=4, ensure_ascii=False)

    return outputs


if __name__ == "__main__":
    fire.Fire(main)
