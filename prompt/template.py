RETRIEVAL_REWRITE_TEMPLATE = """너는 변호사로서, 회사 [정관]과 관련된 질문에 답해야해. 이때 [정관]에 대한 질문이 주어지면 '[정관 조항]: '으로 시작하고 해당 질문과 관련된 정관 조항 한 개를 직접 작성해봐. 단, 300자 이내로 작성해야해. 모든 답변은 한국어로 작성하시오
[질문]: {question}

{format_instructions}
"""

ANSWER_TEMPLATE = """정관 문서: {paragraph}
질문: {question}
===
너는 변호사로서, 회사 정관을 검토해야 한다. 선생님께 정관 문서를 힌트로 받았다. 다음 질문에 대한 답은? 진위형 질문이면 예, 또는 아니오로 대답하고, 주관식 질문이면 한 줄로 대답하시오.
"""

ANSWER_TEMPLATE_v2 = """정관 문서: {paragraph}
question: {question}
===
너는 변호사로서, 회사 정관을 검토해야 한다. 선생님께 정관 문서를 힌트로 받았다. 다음 질문에 대한 답변은? 진위형 질문이면 예, 또는 아니오로 대답하고, 주관식 질문이면 한 줄로 대답하시오. 근거 문장이 포함된 조항 문장을 있는 그대로 출력하시오.

{format_instructions}
"""

ANSWER_TEMPLATE_v3 = """Answer the question based only on the following context:
Context: {paragraph}
Question: {question}
===
진위형 질문이면 '예', 또는 '아니오'로 대답하고, 주관식 질문이면 한 줄로 대답하시오. context와 question의 관련이 없을 경우 '없음'을 출력하시오. 답의 근거가 되는 문장을 있는 그대로 출력하시오. 모든 답변은 한국어로 작성하시오.

{format_instructions}
"""

ANSWER_TEMPLATE_v4 = """Answer the question based only on the following context:
Context: {paragraph}
Question: {question}
===
Answer '예' or '아니오' for true questions, or a single line for open-ended questions. If the context is not relevant to the question, print 'N/A'. Print the sentence you are basing your answer on verbatim. Write all answers in Korean.

{format_instructions}
"""

ADVICE_TEMPLATE = """[회사의 정관 검토 내역]
Q.감사의 임기는 얼마인가? A.2년

[법령]
상법 제410조
 감사의 임기는 취임 후 3년내의 최종의 결산기에 관한 정기총회의 종결시까지로 한다.

상법 제312조
 감사는 한 명이상이어야 하지만, 자본금 총액 10억원 미만의 회사의 경우에는 감사를 선임하지 않을 수있다. 

상법 제383조 제2항
 이사의 임기는 3년을 초과하지 못한다.

[hint]
 가장 관련있는 1가지의 [법령]을 reference해서 변호사로서 정관 체크리스트의 결과가 법적으로 올바른지 적절한 조언을 생성해줘. 직접적으로 관련이 없는 법령은 참고하지마. you should generate in 256 tokens. 한국어로 답변 해줘.

[question]
회사의 정관을 검토해본 결과 'Q.감사의 임기는 얼마인가? A.2년'라는 것을 알 수 있었어. 이 정관이 법적으로 올바르게 쓰여진거야? 이에 대한 답변을 해야 해. [hint]를 활용하여 답변해봐.

[조언]
귀사의 정관은 감사의 임기를 2년이라고 규정하고 있습니다. 상법 제410조는 감사의 임기를 취임 후 3년내의 최종의 결산기에 관한 정기총회의 종결시까지로 정하고 있습니다.

[회사의 정관 검토 내역]
Q.{question} A.{answer}

[법령]
{retrieval_results}

[hint]
 가장 관련있는 1가지의 [법령]을 reference해서 변호사로서 정관 체크리스트의 결과가 법적으로 올바른지 적절한 조언을 생성해줘. 직접적으로 관련이 없는 법령은 참고하지마. you should generate in 256 tokens. 한국어로 답변 해줘.

[question]
회사의 정관을 검토해본 결과 'Q.{question} A.{answer}'라는 것을 알 수 있었어. 이 정관이 법적으로 올바르게 쓰여진거야? 이에 대한 답변을 해야 해. [hint]를 활용하여 답변해봐.

[조언]
"""

ADVICE_TEMPLATE_v2 = """[회사의 정관 검토 내역]
Q.감사의 임기는 얼마인가? A.2년

[법령]
상법 제410조
 감사의 임기는 취임 후 3년내의 최종의 결산기에 관한 정기총회의 종결시까지로 한다.

상법 제312조
 감사는 한 명이상이어야 하지만, 자본금 총액 10억원 미만의 회사의 경우에는 감사를 선임하지 않을 수있다. 

상법 제383조 제2항
 이사의 임기는 3년을 초과하지 못한다.

[hint]
 가장 관련있는 1가지의 [법령]을 reference해서 변호사로서 정관 체크리스트의 결과가 법적으로 올바른지 적절한 조언을 생성해줘. 직접적으로 관련이 없는 법령은 참고하지마. you should generate in 256 tokens. 한국어로 답변 해줘.

[question]
회사의 정관을 검토해본 결과 'Q.감사의 임기는 얼마인가? A.2년'라는 것을 알 수 있었어. 이 정관이 법적으로 올바르게 쓰여진거야? 이에 대한 답변을 해야 해. [hint]를 활용하여 답변해봐.

[조언]
귀사의 정관은 감사의 임기를 2년이라고 규정하고 있습니다. 상법 제410조는 감사의 임기를 취임 후 3년내의 최종의 결산기에 관한 정기총회의 종결시까지로 정하고 있습니다.

[회사의 정관 검토 내역]
Q.{question} A.{answer}

[법령]
{retrieval_results}

[hint]
 가장 관련있는 1가지의 [법령]을 reference해서 변호사로서 정관 체크리스트의 결과가 법적으로 올바른지 적절한 조언을 생성해줘. 직접적으로 관련이 없는 법령은 참고하지마. you should generate in 256 tokens. 한국어로 답변 해줘.

[question]
회사의 정관을 검토해본 결과 'Q.{question} A.{answer}'라는 것을 알 수 있었어. 이 정관이 법적으로 올바르게 쓰여진거야? 이에 대한 답변을 해야 해. [hint]를 활용하여 답변해봐.

{format_instructions}
"""

ADVICE_TEMPLATE_v3 = """[회사의 정관 검토 내역]
Q.감사의 임기는 얼마인가? A.2년

[법령]
상법 제410조
 감사의 임기는 취임 후 3년내의 최종의 결산기에 관한 정기총회의 종결시까지로 한다.

상법 제312조
 감사는 한 명이상이어야 하지만, 자본금 총액 10억원 미만의 회사의 경우에는 감사를 선임하지 않을 수있다. 

상법 제383조 제2항
 이사의 임기는 3년을 초과하지 못한다.

[hint]
 가장 관련있는 1가지의 [법령]을 reference해서 변호사로서 정관 체크리스트의 결과가 법적으로 올바른지 적절한 조언을 생성해줘. 직접적으로 관련이 없는 법령은 참고하지마. you should generate in 256 tokens. 한국어로 답변 해줘.

[question]
회사의 정관을 검토해본 결과 'Q.감사의 임기는 얼마인가? A.2년'라는 것을 알 수 있었어. 이 정관이 법적으로 올바르게 쓰여진거야? 이에 대한 답변을 해야 해. [hint]를 활용하여 답변해봐.

[조언]
귀사의 정관은 감사의 임기를 2년이라고 규정하고 있습니다. 상법 제410조는 감사의 임기를 취임 후 3년내의 최종의 결산기에 관한 정기총회의 종결시까지로 정하고 있습니다.

[회사의 정관 검토 내역]
Q.{question} A.{answer}

[법령]
{retrieval_results}

[hint]
 가장 관련있는 1가지의 [법령]을 reference해서 변호사로서 정관 체크리스트의 결과가 법적으로 올바른지 적절한 조언을 생성해줘. 직접적으로 관련이 없는 법령은 참고하지마. you should generate in 256 tokens. 한국어로 답변 해줘.

[question]
회사의 정관을 검토해본 결과 'Q.{question} A.{answer}'라는 것을 알 수 있었어. 이 정관이 법적으로 올바르게 쓰여진거야? 이에 대한 답변을 해야 해. [hint]를 활용하여 답변해봐.

{format_instructions}
"""
