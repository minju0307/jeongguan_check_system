import pickle

from logger import logger
import os
import ssl
import string
import time
from datetime import datetime
import random
from urllib.parse import urljoin

import pandas as pd
from celery import Celery, signature
from flask import Flask, request, jsonify, json, render_template, Blueprint
from flask_cors import CORS
from werkzeug.utils import secure_filename

from error_code import ErrorCode, ErrorElement
from inference_paragraph import SemanticSearch
from inference_reference import RetrievalSearch

from config import SERVER_PORT, APP_ROOT, UPLOAD_FOLDER, SERVICE_URL, OPENAI_API_KEY, MQ_CELERY_BROKER_URL, \
    CELERY_TASK_NAME, DEFAULT_CALLBACK_URL, MULTILABEL_MODEL_PATH, DPR_MODEL_PATH, SSL_CERT, SSL_KEY, DEBUG, URL_PREFIX, \
    TEST_MODE, QUESTION_DB_FILE, GPT_MODEL
from utils.document_similarity import JeongguanSimilarity, retrieve_top3
from utils.langchain_llm import LawLLM
from utils.splitter import JeongguanSplitterText
from utils.utils import allowed_file, json_response_element, json_response, read_file, load_json, save_to_json

logger.info('Start XAI_Law Web Server!')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['UPLOAD_FOLDER'] = os.path.join(APP_ROOT, UPLOAD_FOLDER)
app.config["JSON_AS_ASCII"] = False  # 한국어 지원을 위한 설정
app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'
app.json.sort_keys = True

CORS(app, resources={f'/{URL_PREFIX}/*': {'origins': '*'}})

ALLOWED_EXTENSIONS = {'txt'}
xai = Blueprint('xai', __name__, url_prefix=f'/{URL_PREFIX}')

with app.app_context():
    semantic_search_model: SemanticSearch = None
    retrieval_search_model: RetrievalSearch = None

task = Celery('tasks', broker=MQ_CELERY_BROKER_URL)


def init_models():
    global semantic_search_model, retrieval_search_model

    if semantic_search_model is None:
        semantic_search_model = SemanticSearch(model_path=MULTILABEL_MODEL_PATH)
    if retrieval_search_model is None:
        retrieval_search_model = RetrievalSearch(model_path=DPR_MODEL_PATH)


def save_file_from_request(request, field='file', folder='temp'):
    # check if the post request has the file part
    if type(field) == str:
        field = [field]
    elif type(field) == list:
        pass
    else:
        raise ValueError('field must be str or list')

    for f in field:
        if f not in request.files:
            return ErrorCode.NO_FILE_PART

    files = [request.files[f] for f in field]

    output_dict = dict()

    for f, file in zip(field, files):
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            return ErrorCode.NO_SELECTED_FILE

        if file and allowed_file(file.filename, ALLOWED_EXTENSIONS):
            filename = secure_filename(file.filename)
            file_name, file_ext = os.path.splitext(filename)

            #
            # 파일을 웹에서 접근 가능한 경로에 저장(ASR Worker에서 받아가는 경로)
            #
            date_str = datetime.now().strftime("%Y%m%d")
            letters = string.ascii_lowercase
            rand_str = ''.join(random.choice(letters) for i in range(5))

            file_dir = os.path.join(app.config['UPLOAD_FOLDER'], folder, date_str)
            new_file = f'{file_name}_{rand_str}{file_ext}'
            file_url = urljoin(SERVICE_URL,
                               os.path.join(UPLOAD_FOLDER, folder, date_str, new_file))  # 다운로드 가능한 URL

            os.makedirs(file_dir, exist_ok=True)
            file_path = os.path.join(file_dir, new_file)
            file.save(file_path)

            output_dict[f] = (file_path, file_url)
        else:
            return ErrorCode.NOT_ALLOWED_FILE_EXTENSION

    if len(output_dict) == 0:
        return ErrorCode.NO_SELECTED_FILE
    else:
        return output_dict


@xai.route("/")
def index():
    init_models()

    return render_template('index.html', debug=DEBUG)


@xai.route("/analyze", methods=["POST"])
def analyze():
    init_models()

    # get flask post data
    mode = request.form.get('mode')
    callback_url = request.form.get('callback_url')

    input_q_ids = request.form.get('q_ids')
    input_uid = request.form.get('uid')

    # split and to int
    q_id_list = [int(i) for i in input_q_ids.split(',')] if input_q_ids else None

    if mode == 'test':
        file_path = 'input_samples/1.txt'
    else:
        results = save_file_from_request(request, folder='jeongguan')
        if type(results) == ErrorElement:
            return json_response_element(results)
        else:
            file_path, file_url = results['file']

    if callback_url is None:
        callback_url = DEFAULT_CALLBACK_URL

    outputs = dict()

    if input_uid:
        uid = input_uid
    else:
        # generate doc_id with date and random number
        uid = datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))

    # create empty dir for uid (for callback test)
    os.makedirs(os.path.join('tmp', uid), exist_ok=True)

    # 체크리스트 -> 문단 서치
    # 정관 문단 나누기
    # input_texts = split_document_shorter(input_text)

    try:
        splitter = JeongguanSplitterText(file_path, verbose=True)
    except AssertionError:
        return json_response(msg=ErrorCode.INVALID_DOCUMENT.msg, code=ErrorCode.INVALID_DOCUMENT.code)

    merged_chapters = splitter.get_merged_chapters()

    # document 유사도 분석
    # reference_doc = load_json(os.path.join(APP_ROOT, 'data/reference_document.json'))
    # doc_sim = JeongguanSimilarity(semantic_search_model, splitter=splitter, ref_doc=reference_doc)
    # sub_scores = doc_sim.get_result()
    # splitter.set_scores(sub_scores)

    document = splitter.get_document(sub_chapter=True)

    # 체크리스트 DB 불러오기
    questions_df = pd.read_csv(QUESTION_DB_FILE)
    questions_list = questions_df['question'].tolist()
    questions_type = questions_df['type'].tolist()

    questions_dict = [{'question': q, 'type': t} for q, t in zip(questions_list, questions_type)]

    # qustions tuple with id and question
    questions_tuple = list(enumerate(questions_list))

    if q_id_list:
        questions_list = [questions_list[i] for i in q_id_list]
        questions_tuple = [questions_tuple[i] for i in q_id_list]

    start_time = time.time()

    top_k_jeongguan = 3
    top_k_sangbub = 3

    paragraph_results = []

    # 문단 임베딩
    paragraphs_list, paragraphs_idxs = splitter.get_paragraphs()

    law_llm = LawLLM(model_name=GPT_MODEL)
    paragraph_vectors = law_llm.get_embedding_from_documents(paragraphs_list)

    # load pickle file
    vector_file = os.path.join(APP_ROOT, 'data/rewrite_query_vectors.pkl')
    rewrite_query_vectors = pickle.load(open(vector_file, 'rb'))

    # 체크리스트 질문 - 문단 맵핑
    for idx, question in questions_tuple:
        rewrite_query_vector = rewrite_query_vectors[idx]

        # create empty dir for idx (for callback test)
        os.makedirs(os.path.join('tmp', uid, str(idx)), exist_ok=True)

        top_3_indices, top_3_values = retrieve_top3(rewrite_query_vector, paragraph_vectors)
        # to list
        top_3_indices = top_3_indices.tolist()
        paragraph_results.append(top_3_indices)

    app.logger.debug(f"Elapsed Time(Question-Paragraph): {time.time() - start_time:.2f} sec")

    start_time = time.time()

    answer_task = f'{CELERY_TASK_NAME}.llm_answer'
    advice_task = f'{CELERY_TASK_NAME}.llm_advice'

    count = 0
    for (idx, question), paragraph_idxs in zip(questions_tuple, paragraph_results):
        if TEST_MODE:
            if count > 2:
                break
            count += 1

        # paragraph_idxs to paragraphs
        paragraphs = [paragraphs_list[i] for i in paragraph_idxs]

        sangbub = retrieval_search_model.retrieval_query(question, top_k_sangbub)

        chain = (
                signature(answer_task, args=[uid, idx, paragraphs, question, callback_url], app=task,
                          queue=CELERY_TASK_NAME) |
                signature(advice_task, args=[uid, idx, question, sangbub, callback_url], app=task,
                          queue=CELERY_TASK_NAME)
        )

        result = chain()
        app.logger.debug(f"  Celery Result ID: {result.id}")

    app.logger.debug(f"Elapsed Time(Question-Sangbub): {time.time() - start_time:.2f} sec")

    outputs["uid"] = uid
    outputs["checklist_questions"] = questions_dict

    if input_uid is None:
        outputs["document"] = document
        outputs["doc_paragraphs"] = paragraphs_list
        outputs["mapping_paragraphs"] = paragraph_results

    # save outputs to json (for later test)
    outputs_path = os.path.join('tmp', uid, 'outputs.json')
    save_to_json(outputs, outputs_path)

    return json_response(msg=ErrorCode.SUCCESS.msg, code=ErrorCode.SUCCESS.code, data=outputs)


@xai.route("/callback_test", methods=["POST"])
def callback_test():
    callback_url = request.form.get('callback_url', DEFAULT_CALLBACK_URL)
    input_uid = request.form.get('uid')
    idx = 0

    if input_uid:
        uid = input_uid
    else:
        # generate doc_id with date and random number
        uid = datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))

    # log callback test
    app.logger.debug(f'Callback Test: {callback_url}')

    paragraphs = [
        '신고의 접수, 기타 주식에 관한 사무절차는 이사회 결의로 정하는 「주식사무규정」에 따른다.② 회사는 명의개서 등에 관한 일체의 업무를 명의개서대리인에게 위임할 수 있다. 이 경우 제1항의 주식사무처리절차는 명의개서대리인의 「유가증권의 명의개서대행 등에 관한 규정」에 따른다.제13조(주주 등의 성명, 주소 및 인감 또는 서명의 신고) ① 주주 또는 등록질권자 및 그들의 법정대리인은 성명, 주소 및 인감 또는 서명을 회사에 신고하여야 하며 그 변경이 있을 때도 또한 같다.② 주주 또는 등록질권자가 외국에 거주할 때는 한국 내에 가주소 또는 대리인을 정하여 회사에 신고하여야 하고, 그 변경이 있을 때도 또한 같다.③ 법정대리인은 그 대리권을 증명할 서면을 제출하여야 하며 변경신고를 할 때에는 회사가 인정하는 증명서를 첨부하여야 한다.④ 회사가 명의개서대리인을 지정한 경우에는 제1항 내지 제3항에 불구하고 명의개서대리인에게 신고하여야 한다.⑤ 제1항 내지 제4항의 신 고를 태만함으로 인하여 생긴 손해에 대하여는 회사가 책임을 지지 아니한다.제14조(주주명부의 폐쇄) ① 회사는 결산기가 끝나는 다음 날로부터 그 결산에 관한 정기주주총회 종료일까지 권리에 관한 주주명부의 기재변경을 정지한다.② 회사는 임시주주총회의 소집 기타 필요한 경우 이사회의 결의로 3월을 경과하지 아니하는 일정한 기간을 정하여 권리에 관한 주주명부의 기재변경을 정지하거나 이사회의 결의로 정한 날에 주주명부에 기재되어 있는 주주를 그 권리를 행사할 주주로 할 수 있으며, 이사회가 필요하다고 인정하는 경우에는 주주명부의 기재변경 정지와 기준일의 지정을 함께 할 수 있다. 회사는 이를 2주간 전에 공고하여야 한다. 다만, 주주 전원의 동의가 있을 시에는 상기 공고절차를 생략할 수 있다.③ 회사는 매 결산기 최종일의 주주명부에 기재되어 있는 주주를 그 결산기에 관한 정기주주총회에서 권리를 행사할 주주로 한다.',
        '주주총회제19조(총회의 소집) ① 정기주주총회는 매 결산기가 끝난 후 3월 내에 소집하고 임시주주총회는 필요에 따라 이사회 결의 또는 법령에 정한 바에 의하여 수시 이를 소집한다.② 주주총회를 소집함에는 그 일시, 장소 및 회의의 목적사항을 총회일의 2주간 전에 각 주주에게 서면 또는 전자문서로 통지를 발송하여야 한다. 다만, 그 통지가 주주명부상의 주주의 주소에 계속 3년간 도달하지 아니한 때에는 해당 주주에게 주주총회의 소집을 통지하지 아니할 수 있다.③ 제2항 본문에도 불구하고 주주 전원의 동의가 있는 경우에는 통지 기간을 단축하거나 통지 절차를 생략할 수 있다.④ 주주총회는 미리 주주에게 통지한 회의의 목적사항 이외에는 결의하지 못한다. 다만, 주주 전원의 동의가 있는 경우에는 그러하지 아니하다.제20조(총회의 의장) 주주총회의 의장은 대표이사 사장으로 한다. 다만, 대표이사 사장의 유고 시에는 제31조 제5항의 규정을 준용한다.제21조(의장의 질서유지권) ① 주주총회의 의장은 고의로 의사진행을 방해하기 위한 발언·행동을 하는 등 현저히 질서를 문란하게 하는 자에 대하여 그 발언의 정지 또는 퇴장을 명할 수 있다.② 주주총회의 의장은 의사진행의 원활을 기하기 위하여 필요하다고 인정할 때에는 주주의 발언의 시간 및 회수를 제한할 수 있다.제22조(총회의 결의) 총회의 결의는 법령에 따로 규정이 있는 것을 제외하고는 출석한 주주의 의결권의 과반수와 발행주식총수의 4분의 1 이상의 수로써 하여야 한다.제23조(의결권의 대리행사) 주주는 대리인으로 하여금 의결권을 행사하게 할 수 있다. 다만, 대리인은 주주총회 전에 그 대리권을 증명하는 서면을 제출하여야 한다.제24조(총회의사록) 주주총회의 의사에 대하여는 그 경과의 요령 및 결과를 의사록에 기재하고 의장과 출석한 이사가 기명날인 또는 서명하여 본점 및 지점에 비치하여야 한다.',
        '계 산제43조 (사업연도) 회사의 사업연도는 매년 1월 1일부터 12월 31일까지로 한다.제44조 (재무제표등) ① 대표이사는 정기주주총회 회일 6주간 전에 다음 각 호의 서류와 그 부속명세서 및 영업보고서를 작성하여 감사위원회의 감사를 받아 정기주주총회에 제출하여야 한다.1. 대차대조표(주식회사의 외부감사에 관한 법률 제1조의2에서 규정하는 재무상태표)2. 손익계산서3. 그 밖에 회사의 재무상태와 경영성과를 표시하는 것으로서 「상법」시행령에서 정하는서류4. 「상법」시행령에서 정하는바에 따른 제1호 내지 제3호의 서류에 대한 연결재무제표② 감사위원회는 제1항의 서류를 받은 날로부터 4주간 내에 감사보고서를 대표이사에게 제출하여야 한다.③ 제1항에 불구하고 회사는 다음 각호의 요건을 모두 충족한 경우에는 이사회의 결의로 이를 승인할 수 있다.1. 제1항의 각 서류가 법령 및 정관에 따라 회사의 재무상태 및 경영성과를 적정하게 표시하고 있다는 외부감사인의 의견이 있을 때2. 감사위원회 위원 전원의 동의가 있을 때④ 제3항에 따라 이사회가 승인한 경우에는 대표이사는 제1항의 각 서류의 내용을 주주총 회에 보고하여야 한다.⑤ 회사는 제1항 각호의 서류를 영업보고서 및 감사보고서와 함께 정기주주총회 회일의 1주간 전부터 본점에 5년간, 그 등본을 지점에 3년간 비치하여야 한다.⑥ 회사는 제1항 각 호의 서류에 대한 정기주주총회의 승인 또는 제3항에 의한 이사회의 승인을 얻은 때에는 지체 없이 대차대조표를 공고하여야 한다.제45조(외부감사인의 선임) 회사는 감사위원회의 승인을 얻어 외부감사인을 선임하며, 선임 후 최초로 소집되는 정기주주총회에 그 사실을 보고하거나, 최근 주주명부 폐쇄일의 주주에게 서면이나 전자문서에 의한 통지 또는 회사의 인터넷 홈페이지에 공고한다.제46조(손익계산과 처분) 회사의 손익계산은 매결산기의 총수익으로부터 총비용을 공제한 나머지를 순이익금으로 하고 이에 전기이월이익잉여금을 합하여 다음 각 호의 방법에 따라 처분한다.1. 이익준비금 : 금전에 의한 이익배당액의 10분의 1 이상2. 기타의 법정적립금3. 배당금4. 임의적립금5. 기타의 이익잉여금처분액6. 차기이월이익잉여금제47조(이익배당) ① 이익의 배당은 금전과 주식 및 기타의 재산으로 할 수 있다. 다만, 주식에 의한 배당은 이익배당 총액의 2분의 1에 상당하는 금액을 초과하지 못한다.② 이익의 배당을 주식으로 하는 경우 회사가 종류주식을']

    question = '정기주주총회를 개최하는가?'

    sangbub = """제365조(총회의 소집)
    ①정기총회는 매년 1회 일정한 시기에 이를 소집하여야 한다.
    ②연 2회 이상의 결산기를 정한 회사는 매기에 총회를 소집하여야 한다.
    ③임시총회는 필요있는 경우에 수시 이를 소집한다.

    제542조의4(주주총회 소집공고 등)
    ① 상장회사가 주주총회를 소집하는 경우 대통령령으로 정하는 수 이하의 주식을 소유하는 주주에게는 정관으로 정하는 바에 따라 주주총회일의 2주 전에 주주총회를 소집하는 뜻과 회의의 목적사항을 둘 이상의 일간신문에 각각 2회 이상 공고하거나 대통령령으로 정하는 바에 따라 전자적 방법으로 공고함으로써 제363조제1항의 소집통지를 갈음할 수 있다.
    ② 상장회사가 이사ㆍ감사의 선임에 관한 사항을 목적으로 하는 주주총회를 소집통지 또는 공고하는 경우에는 이사ㆍ감사 후보자의 성명, 약력, 추천인, 그 밖에 대통령령으로 정하는 후보자에 관한 사항을 통지하거나 공고하여야 한다.
    ③ 상장회사가 주주총회 소집의 통지 또는 공고를 하는 경우에는 사외이사 등의 활동내역과 보수에 관한 사항, 사업개요 등 대통령령으로 정하는 사항을 통지 또는 공고하여야 한다. 다만, 상장회사가 그 사항을 대통령령으로 정하는 방법으로 일반인이 열람할 수 있도록 하는 경우에는 그러하지 아니하다.

    제388조(이사의 보수)
    이사의 보수는 정관에 그 액을 정하지 아니한 때에는 주주총회의 결의로 이를 정한다.
    """

    answer_task = f'{CELERY_TASK_NAME}.llm_answer'
    advice_task = f'{CELERY_TASK_NAME}.llm_advice'

    chain = (
            signature(answer_task, args=[uid, idx, paragraphs, question, callback_url], app=task,
                      queue=CELERY_TASK_NAME) |
            signature(advice_task, args=[uid, idx, question, sangbub, callback_url], app=task,
                      queue=CELERY_TASK_NAME)
    )

    result = chain()
    app.logger.debug(f"Celery Result ID: {result.id}")

    return json_response(msg=ErrorCode.SUCCESS.msg, code=ErrorCode.SUCCESS.code)


@xai.route("/callback_result", methods=["POST"])
def callback_result():
    # get flask post data
    uid = request.form.get('uid')
    idx = request.form.get('idx')

    # answer callback
    answer = request.form.get('answer')
    title = request.form.get('title')
    sentence = request.form.get('sentence')
    doc_idx_i = request.form.get('doc_idx_i')
    doc_idx_j = request.form.get('doc_idx_j')

    # advice callback
    advice = request.form.get('advice')
    is_satisfied = request.form.get('is_satisfied')

    if not uid or not idx:
        return json_response(msg=ErrorCode.INVALID_PARAMETER.msg, code=ErrorCode.INVALID_PARAMETER.code)

    # create idx dir
    dest_dir = os.path.join('tmp', uid, idx)
    os.makedirs(dest_dir, exist_ok=True)

    if answer:
        data_dict = {
            "answer": answer,
            "title": title,
            "sentence": sentence,
            "chapter_idx": (doc_idx_i, doc_idx_j)
        }

        save_to_json(data_dict, os.path.join(dest_dir, 'answer.json'))

    if advice:
        data_dict = {
            "advice": advice,
            "is_satisfied": is_satisfied
        }

        save_to_json(data_dict, os.path.join(dest_dir, 'advice.json'))

    return json_response(msg=ErrorCode.SUCCESS.msg, code=ErrorCode.SUCCESS.code)


@xai.route("/get_result", methods=["GET"])
def get_result():
    """
    UI에서 결과를 확인하기 위한 API (for demo)
    :return:
    """
    uid = request.args.get('uid')

    if not uid:
        return json_response(msg=ErrorCode.INVALID_PARAMETER.msg, code=ErrorCode.INVALID_PARAMETER.code)

    dest_dir = os.path.join('tmp', uid)

    # get all subdirs
    subdirs = [f for f in os.listdir(dest_dir) if os.path.isdir(os.path.join(dest_dir, f))]

    output_dict = dict()
    results = []

    # read outputs.json
    outputs_path = os.path.join(dest_dir, 'outputs.json')
    outputs = load_json(outputs_path)
    doc_paragraphs = outputs.get('doc_paragraphs')
    mapping_paragraphs = outputs.get('mapping_paragraphs')

    # 체크리스트 질문
    questions = outputs.get('checklist_questions')

    satisfied_count = 0
    for idx, (question, paragraph_idxs) in enumerate(zip(questions, mapping_paragraphs)):
        # check if idx dir exists
        subdir = str(idx)

        result = dict()
        result['question'] = question

        if subdir not in subdirs:
            result['answer'] = '분석 중...'
            result['advice'] = '분석 중...'
        else:
            try:
                answer_path = os.path.join(dest_dir, subdir, 'answer.json')
                answer_result = load_json(answer_path)

                result.update(answer_result)

            except FileNotFoundError:
                result['answer'] = '분석 중...'
                result['title'] = '분석 중...'
                result['sentence'] = '분석 중...'

            try:
                advice_path = os.path.join(dest_dir, subdir, 'advice.json')
                advice_result = load_json(advice_path)

                result.update(advice_result)

                # count if answer is satisfied
                if advice_result['is_satisfied'] == '2':
                    satisfied_count += 1

            except FileNotFoundError:
                result['advice'] = '분석 중...'
                result['is_satisfied'] = '분석 중...'

        # 관련 문단 추가
        paragraph_list = [doc_paragraphs[i] for i in paragraph_idxs]
        result['paragraphs'] = paragraph_list

        results.append(result)

    output_dict['results'] = results
    output_dict['uid'] = uid

    # 체크리스트 만족 여부 계산
    unsatisfied_count = len(questions) - satisfied_count
    output_dict['checklist'] = {"satisfied_count": satisfied_count, "unsatisfied_count": unsatisfied_count}

    return json_response(msg=ErrorCode.SUCCESS.msg, code=ErrorCode.SUCCESS.code, data=output_dict)


app.register_blueprint(xai)

if __name__ == "__main__":
    # Set OpenAI environment variables
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if not openai_api_key:
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

    try:
        port = SERVER_PORT
    except ImportError:
        port = 5000

    upload_folder = os.path.join(APP_ROOT, UPLOAD_FOLDER)
    os.makedirs(upload_folder, exist_ok=True)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    ssl_context.load_cert_chain(certfile=SSL_CERT, keyfile=SSL_KEY)

    app.run(host="0.0.0.0", port=port, debug=DEBUG, ssl_context=ssl_context)
