import os
import json
import openai


def prompt_generator(question, answer, retrieval_results):
    ## reference file 불러오기
    # with open("data/question_45.json") as f:
    #     question_label = json.load(f)

    ## 객관식 label을 따로따로 넣는 프롬프트 만들기
    ## todo : 주관식 프롬프트도 넣을 수 있게 하기
    # second_prompt = []

    # for dic in first_prompt:
    #     if type(dic['label']) == list:
    #         for l in dic['label']:
    #             new_dic = {}
    #             new_dic['ref_knowledge'] = dic['ref_knowledge']
    #             new_dic['pred_knowledge'] = dic['pred_knowledge']
    #             new_dic['question'] = dic['question']
    #             new_dic['label'] = l
    #             second_prompt.append(new_dic)

    ## prompt 형식에 맞춘 텍스트를 만들기
    ## few_shot 정의
    few_shot = ''
    few_shot += '\n\n[회사의 정관 검토 내역]\n'
    few_shot += "Q.감사의 임기는 얼마인가? A.2년"
    few_shot += '\n\n[법령]\n'
    few_shot += '상법 제410조\n 감사의 임기는 취임 후 3년내의 최종의 결산기에 관한 정기총회의 종결시까지로 한다.\n\n'
    few_shot += '상법 제312조\n 감사는 한 명이상이어야 하지만, 자본금 총액 10억원 미만의 회사의 경우에는 감사를 선임하지 않을 수있다. \n\n'
    few_shot += '상법 제383조 제2항\n 이사의 임기는 3년을 초과하지 못한다.\n\n'
    few_shot += "[hint]\n 가장 관련있는 1가지의 [법령]을 reference해서 변호사로서 정관 체크리스트의 결과가 법적으로 올바른지 적절한 조언을 생성해줘. 직접적으로 관련이 없는 법령은 참고하지마. you should generate in 256 tokens. 한국어로 답변 해줘."
    few_shot += '\n\n[question]\n'
    few_shot += f"회사의 정관을 검토해본 결과 'Q.감사의 임기는 얼마인가? A.2년'라는 것을 알 수 있었어. 이 정관이 법적으로 올바르게 쓰여진거야? 이에 대한 답변을 해야 해. [hint]를 활용하여 답변해봐."
    few_shot += '\n\n[조언]\n'
    few_shot += '귀사의 정관은 감사의 임기를 2년이라고 규정하고 있습니다. 상법 제410조는 감사의 임기를 취임 후 3년내의 최종의 결산기에 관한 정기총회의 종결시까지로 정하고 있습니다.'

    prompt = few_shot
    prompt += '\n\n[회사의 정관 검토 내역]\n'
    prompt += f"Q.{question} A.{answer}"
    prompt += '\n\n[법령]\n'
    prompt += retrieval_results[:2000] # 토큰 에러가 나지 않게 하기 위하여
    if type(answer == str):
        prompt += "\n\n[hint]\n 가장 관련있는 1가지의 [법령]을 reference해서 변호사로서 정관 체크리스트의 결과가 법적으로 올바른지 적절한 조언을 생성해줘. 직접적으로 관련이 없는 법령은 참고하지마. you should generate in 256 tokens. 한국어로 답변 해줘."
        prompt += '\n\n[question]\n'
        prompt += f"회사의 정관을 검토해본 결과 'Q.{question} A.{answer}'라는 것을 알 수 있었어. 이 정관이 법적으로 올바르게 쓰여진거야? 이에 대한 답변을 해야 해. [hint]를 활용하여 답변해봐."
        prompt += '\n\n[조언]\n'

    return prompt


def generate_gpt(gpt_ver, query):
    """ Generate a GPT response. """
    messages = [
        {"role": "system", "content": "you are a professional lawyer."},
        {"role": "user", "content": query}
    ]
    response = openai.ChatCompletion.create(model=gpt_ver, messages=messages)
    res = response["choices"][0]["message"]["content"]
    
    return res


def generate_advice(gpt_ver, prompt):
    try:
        answer = generate_gpt(gpt_ver, prompt)
        return answer
    except:
        print(f"\nadvice_error\n\n")
        return ""