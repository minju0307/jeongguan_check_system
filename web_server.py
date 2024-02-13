import logging
import os
import ssl
import string
import time
from datetime import datetime
from distutils.file_util import write_file
from logging.config import dictConfig
import random
from urllib.parse import urljoin

import openai
from celery import Celery, signature
from flask import Flask, request, jsonify, json, render_template, Blueprint
from jsonschema import validate
from werkzeug.utils import secure_filename

from error_code import ErrorCode, ErrorElement
from inference_paragraph import SemanticSearch
from inference_reference import RetrievalSearch
from main import main, split_document_shorter
from config import SERVER_PORT, APP_ROOT, UPLOAD_FOLDER, SERVICE_URL, OPENAI_API_KEY, MQ_CELERY_BROKER_URL, \
    CELERY_TASK_NAME, DEFAULT_CALLBACK_URL, MULTILABEL_MODEL_PATH, DPR_MODEL_PATH, SSL_CERT, SSL_KEY, DEBUG

from utils.utils import allowed_file, json_response_element, json_response, read_file, load_json

dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s (%(module)s:%(lineno)d) %(levelname)s: %(message)s',
        }
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'web_server.log',
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi', 'file']
    },
    'loggers': {
        'waitress': {
            'level': 'INFO'
        }
    }
})

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
app.config['SECRET_KEY'] = 'secret!'
app.config['UPLOAD_FOLDER'] = os.path.join(APP_ROOT, UPLOAD_FOLDER)
app.config["JSON_AS_ASCII"] = False  # 한국어 지원을 위한 설정
app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'
app.json.sort_keys = True

ALLOWED_EXTENSIONS = {'txt'}
xai = Blueprint('xai', __name__, url_prefix='/xai_law')

semantic_search_model = SemanticSearch(model_path=MULTILABEL_MODEL_PATH)
retrieval_search_model = RetrievalSearch(model_path=DPR_MODEL_PATH)

task = Celery('tasks', broker=MQ_CELERY_BROKER_URL)


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
    return render_template('index.html')


@xai.route("/analyze", methods=["POST"])
def analyze():
    # get flask post data
    mode = request.form.get('mode')
    callback_url = request.form.get('callback_url')

    if mode == 'test':
        input_text = '\n'.join(read_file('input_samples/1.txt'))
    else:
        results = save_file_from_request(request, folder='jeongguan')
        if type(results) == ErrorElement:
            return json_response_element(results)
        else:
            file_path, file_url = results['file']

        input_text = '\n'.join(read_file(file_path))

    if callback_url is None:
        callback_url = DEFAULT_CALLBACK_URL

    outputs = dict()

    # generate doc_id with date and random number
    uid = datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))
    outputs["uid"] = uid

    # create empty dir for uid (for callback test)
    os.makedirs(os.path.join('tmp', uid), exist_ok=True)

    # 체크리스트 -> 문단 서치
    # 정관 문단 나누기
    input_texts = split_document_shorter(input_text)
    outputs["doc_paragraphs"] = input_texts
    outputs["mapping_paragraphs"] = []

    # 체크리스트 DB 불러오기
    questions_dict = load_json('data/jeongguan_questions_56.json')
    questions = list(questions_dict.keys())

    outputs["checklist_questions"] = questions

    start_time = time.time()

    top_k_jeongguan = 3
    top_k_sangbub = 3

    paragraph_results = []

    questions = questions[:1] if DEBUG else questions

    # 체크리스트 질문 - 정관 맵핑
    for idx, q in enumerate(questions):
        # create empty dir for idx (for callback test)
        os.makedirs(os.path.join('tmp', uid, str(idx)), exist_ok=True)

        # 모델을 이용해 체크리스트 질문 - 정관 검색
        paragraph_idxs = semantic_search_model.semantic_search(q, input_texts, top_k_jeongguan)
        outputs["mapping_paragraphs"].append(paragraph_idxs)
        paragraph_results.append(paragraph_idxs)

    app.logger.debug(f"Elapsed Time(Question-Paragraph): {time.time() - start_time:.2f} sec")

    start_time = time.time()

    answer_task = f'{CELERY_TASK_NAME}.llm_answer'
    advice_task = f'{CELERY_TASK_NAME}.llm_advice'

    for idx, (q, paragraph_idxs) in enumerate(zip(questions, paragraph_results)):
        # paragraph_idxs to paragraphs
        paragraphs = [input_texts[i] for i in paragraph_idxs]

        sangbub = retrieval_search_model.retrieval_query(q, top_k_sangbub)

        chain = (
                signature(answer_task, args=[uid, idx, paragraphs, q, callback_url], app=task, queue=CELERY_TASK_NAME) |
                signature(advice_task, args=[uid, idx, q, sangbub, callback_url], app=task, queue=CELERY_TASK_NAME)
        )

        result = chain()
        app.logger.debug(f"  Celery Result ID: {result.id}")

    app.logger.debug(f"Elapsed Time(Question-Sangbub): {time.time() - start_time:.2f} sec")

    return json_response(msg=ErrorCode.SUCCESS.msg, code=ErrorCode.SUCCESS.code, data=outputs)


@xai.route("/callback_result", methods=["POST"])
def callback_result():
    # get flask post data
    uid = request.form.get('uid')
    idx = request.form.get('idx')
    answer = request.form.get('answer')
    advice = request.form.get('advice')

    if not uid or not idx:
        return json_response(msg=ErrorCode.INVALID_PARAMETER.msg, code=ErrorCode.INVALID_PARAMETER.code)

    # check uid in tmp folder
    if not os.path.exists(os.path.join('tmp', uid)):
        return json_response(msg=ErrorCode.NOT_EXIST_UID.msg, code=ErrorCode.NOT_EXIST_UID.code)

    # create idx dir
    dest_dir = os.path.join('tmp', uid, idx)
    os.makedirs(dest_dir, exist_ok=True)

    if answer:
        write_file(os.path.join(dest_dir, 'answer.txt'), [answer])

    if advice:
        write_file(os.path.join(dest_dir, 'advice.txt'), [advice])

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

    results = dict()

    questions_dict = load_json('data/jeongguan_questions_56.json')
    questions = list(questions_dict.keys())

    for idx, q in enumerate(questions):
        # check if idx dir exists
        idx = str(idx)

        results[idx] = dict()
        results[idx]['question'] = q

        if str(idx) not in subdirs:
            results[idx]['answer'] = '분석 중...'
            results[idx]['advice'] = '분석 중...'
        else:
            try:
                results[idx]['answer'] = ' '.join(read_file(os.path.join(dest_dir, idx, 'answer.txt')))
            except FileNotFoundError:
                results[idx]['answer'] = '분석 중...'

            try:
                results[idx]['advice'] = ' '.join(read_file(os.path.join(dest_dir, idx, 'advice.txt')))
            except FileNotFoundError:
                results[idx]['advice'] = '분석 중...'

    return json_response(msg=ErrorCode.SUCCESS.msg, code=ErrorCode.SUCCESS.code, data=results)


# 정관 문서를 받아서 분석을 수행하고, 결과를 json 형태로 반환
@app.route("/upload", methods=["POST"])
def input_jeongguan():
    ## 보안 키 header로 전달되었는지 확인
    auth_token = request.headers.get("Authorization")
    if not auth_token:
        return jsonify({"error": "Missing authorization token"}), 401
    if not auth_token == "kimandhong":
        return jsonify({"error": "Invalid Authentication"}), 401

    ## json 형식이 맞는지 확인
    try:
        contents = request.get_json(force=True)
    except:
        return jsonify({"error": "Invalid Json Type"}), 400

    ## json 스키마가 맞는지 확인
    json_schema = {
        "title": "jeongguan",
        "version": 1,
        "type": "object",
        "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
        "required": ["id", "text"],
    }

    try:
        validate(schema=json_schema, instance=contents)
    except:
        return (
            jsonify(
                {"error": "Invalid JSON schema. Required fields are 'id' and 'text'."}
            ),
            400,
        )

    content_id = contents["id"]
    content_text = contents["text"]

    ## 이미 있는 아이디의 정관을 입력한 경우
    files = [i[:-5] for i in os.listdir("db")]
    if content_id != "0000" and content_id in files:  # 0000은 테스트용
        return jsonify({"error": "Existing Article"}), 400

    outputs = main(input_id=content_id, input_text=content_text)

    return jsonify(outputs)


# 정관 문서 당 split된 문단들을 반환
@app.route("/paragraph", methods=["GET"])
def get_paragraph():  ## parameter : doc_id, paragraph_id
    ## 보안 키 header로 전달되었는지 확인
    try:
        auth_token = request.headers["Authorization"]
        if auth_token != "kimandhong":
            return jsonify({"error": "Invalid Authentication"}), 401
    except KeyError:
        return jsonify({"error": "Missing authorization token"}), 401

    parameter_dict = request.args.to_dict()

    ## required 파라미터 확인
    try:
        doc_id = parameter_dict["doc_id"]
    except KeyError:
        return jsonify({"error": "'doc_id' Parameter Required"}), 400

    ## 없는 정관 아이디를 입력한 경우
    try:
        ## db 파일 불러오기
        with open(f"db/{doc_id}.json", "r", encoding="utf-8") as f:
            outputs = json.load(f)
    except:
        return (
            jsonify(
                {
                    "error": "The 'doc_id' you have entered does not exist. Please upload the document first."
                }
            ),
            400,
        )

    if "paragraph_id" in parameter_dict.keys():
        paragraph_id = int(parameter_dict["paragraph_id"])

        ## optional parameter 확인
        try:
            jsonify(outputs["doc_paragraphs"][paragraph_id])
        except:
            return (
                jsonify(
                    {
                        "error": f'Invalid Paragraph ID: \'paragraph_id\' must be a value between 0 and {len(outputs["doc_paragraphs"]) - 1}'
                    }
                ),
                401,
            )

    else:
        return jsonify(outputs["doc_paragraphs"])


# 확인해야 하는 전체 checklist를 반환
@app.route("/checklist", methods=["GET"])
def get_checklist():  ## parameter : checklist_id
    ## 보안 키 header로 전달되었는지 확인
    try:
        auth_token = request.headers["Authorization"]
        if auth_token != "kimandhong":
            return jsonify({"error": "Invalid Authentication"}), 401
    except KeyError:
        return jsonify({"error": "Missing authorization token"}), 401

    parameter_dict = request.args.to_dict()

    ## checklist 파일 불러오기
    with open("data/jeongguan_questions_56.json", "r", encoding="utf-8-sig") as f:
        questions = json.load(f)

    if "checklist_id" in parameter_dict.keys():
        checklist_id = int(parameter_dict["checklist_id"])

        ## optional parameter 확인
        try:
            return jsonify(list(questions.keys())[checklist_id])
        except:
            return (
                jsonify(
                    {
                        "error": f"Invalid checklist_id : 'checklist_id ' must be a value between 0 and 55"
                    }
                ),
                401,
            )
    else:
        return jsonify(list(questions.keys()))


# reference에 해당하는 상법들의 리스트를 반환
@app.route("/reference_sangbub", methods=["GET"])
def get_sangbub():  ## parameter : sangbub_id
    ## 보안 키 header로 전달되었는지 확인
    try:
        auth_token = request.headers["Authorization"]
        if auth_token != "kimandhong":
            return jsonify({"error": "Invalid Authentication"}), 401
    except KeyError:
        return jsonify({"error": "Missing authorization token"}), 401

    parameter_dict = request.args.to_dict()

    ## 상법 파일 불러오기
    with open("data/reference_sangbub.json", "r", encoding="utf-8-sig") as f:
        reference = json.load(f)

    if "sangbub_id" in parameter_dict.keys():
        sangbub_id = int(parameter_dict["sangbub_id"])

        ## optional parameter 확인
        try:
            return jsonify(reference[sangbub_id])
        except:
            return (
                jsonify(
                    {
                        "error": f"Invalid sangbub_id : 'sangbub_id ' must be a value between 0 and 30"
                    }
                ),
                401,
            )
    else:
        return jsonify(reference)


# 정관 문서 당 질문 - 정관 맵핑 결과를 반환
@app.route("/qna/question_paragraph", methods=["GET"])
def get_mapping_paragraph():  ## paramter : doc_id, checklist_id
    ## 보안 키 header로 전달되었는지 확인
    try:
        auth_token = request.headers["Authorization"]
        if auth_token != "kimandhong":
            return jsonify({"error": "Invalid Authentication"}), 401
    except KeyError:
        return jsonify({"error": "Missing authorization token"}), 401

    parameter_dict = request.args.to_dict()

    ## required 파라미터 확인
    try:
        doc_id = parameter_dict["doc_id"]
    except KeyError:
        return jsonify({"error": "'doc_id' Parameter Required"}), 400

    ## 없는 정관 아이디를 입력한 경우
    try:
        ## db 파일 불러오기
        with open(f"db/{doc_id}.json", "r", encoding="utf-8") as f:
            outputs = json.load(f)
    except:
        return (
            jsonify(
                {
                    "error": "The 'doc_id' you have entered does not exist. Please upload the document first."
                }
            ),
            400,
        )

    ## db 파일 불러오기
    with open(f"db/{parameter_dict['doc_id']}.json", "r", encoding="utf-8") as f:
        outputs = json.load(f)

    if "checklist_id" in parameter_dict.keys():
        try:
            results = []
            idx = int(parameter_dict["checklist_id"])
            result = {}
            result["question"] = outputs["checklist_questions"][idx]
            result["paragraph"] = outputs["mapping_paragraphs"][idx]
            results.append(result)
        except:
            return (
                jsonify(
                    {
                        "error": f"Invalid checklist_id : 'checklist_id ' must be a value between 0 and 55"
                    }
                ),
                400,
            )

        return jsonify(results)

    else:
        results = []
        for idx, mapping_paragraph in enumerate(outputs["mapping_paragraphs"]):
            result = {}
            result["question"] = outputs["checklist_questions"][idx]
            result["paragraph"] = mapping_paragraph
            results.append(result)

        return jsonify(results)


# 정관 문서 당 체크리스트 질문 - 답변을 반환
@app.route("/qna/mrc_answer", methods=["GET"])
def get_mrc_answer():  ## paramter : doc_id, checklist_id
    ## 보안 키 header로 전달되었는지 확인
    try:
        auth_token = request.headers["Authorization"]
        if auth_token != "kimandhong":
            return jsonify({"error": "Invalid Authentication"}), 401
    except KeyError:
        return jsonify({"error": "Missing authorization token"}), 401

    parameter_dict = request.args.to_dict()

    ## required 파라미터 확인
    try:
        doc_id = parameter_dict["doc_id"]
    except KeyError:
        return jsonify({"error": "'doc_id' Parameter Required"}), 400

    ## 없는 정관 아이디를 입력한 경우
    try:
        ## db 파일 불러오기
        with open(f"db/{doc_id}.json", "r", encoding="utf-8") as f:
            outputs = json.load(f)
    except:
        return (
            jsonify(
                {
                    "error": "The 'doc_id' you have entered does not exist. Please upload the document first."
                }
            ),
            400,
        )

    ## db 파일 불러오기
    with open(f"db/{parameter_dict['doc_id']}.json", "r", encoding="utf-8") as f:
        outputs = json.load(f)

    if "checklist_id" in parameter_dict.keys():
        try:
            results = []
            idx = int(parameter_dict["checklist_id"])
            result = {}
            result["question"] = outputs["checklist_questions"][idx]
            result["answer"] = outputs["mrc_answer"][idx]
            results.append(result)
        except:
            return (
                jsonify(
                    {
                        "error": f"Invalid checklist_id : 'checklist_id ' must be a value between 0 and 55"
                    }
                ),
                400,
            )

        return jsonify(results)
    else:
        results = []
        for idx, mrc_answer in enumerate(outputs["mrc_answer"]):
            result = {}
            result["question"] = outputs["checklist_questions"][idx]
            result["answer"] = mrc_answer
            results.append(result)

        return jsonify(results)


# 정관 문서 당 체크리스트 질문 - 상법 맵핑 결과를 반환
@app.route("/advice/question_sangbub", methods=["GET"])
def get_checklist_sangbub():  ## paramter : doc_id, checklist_id
    ## 보안 키 header로 전달되었는지 확인
    try:
        auth_token = request.headers["Authorization"]
        if auth_token != "kimandhong":
            return jsonify({"error": "Invalid Authentication"}), 401
    except KeyError:
        return jsonify({"error": "Missing authorization token"}), 401

    parameter_dict = request.args.to_dict()
    print(parameter_dict)

    ## required 파라미터 확인
    try:
        doc_id = parameter_dict["doc_id"]
    except KeyError:
        return jsonify({"error": "'doc_id' Parameter Required"}), 400

    ## 없는 정관 아이디를 입력한 경우
    try:
        ## db 파일 불러오기
        with open(f"db/{doc_id}.json", "r", encoding="utf-8") as f:
            outputs = json.load(f)
    except:
        return (
            jsonify(
                {
                    "error": "The 'doc_id' you have entered does not exist. Please upload the document first."
                }
            ),
            400,
        )

    ## db 파일 불러오기
    with open(f"db/{parameter_dict['doc_id']}.json", "r", encoding="utf-8") as f:
        outputs = json.load(f)

    if "checklist_id" in parameter_dict.keys():
        try:
            results = []
            idx = int(parameter_dict["checklist_id"])
            result = {}
            result["question"] = outputs["checklist_questions"][idx]
            result["sangbub"] = outputs["sangbub"][idx]
            results.append(result)
        except:
            return (
                jsonify(
                    {
                        "error": f"Invalid checklist_id : 'checklist_id ' must be a value between 0 and 55"
                    }
                ),
                400,
            )

        return jsonify(results)
    else:
        results = []
        for idx, sangbub in enumerate(outputs["sangbub"]):
            result = {}
            result["question"] = outputs["checklist_questions"][idx]
            result["sangbub"] = sangbub
            results.append(result)

        return jsonify(results)


# 정관 문서 당 체크리스트 질문 - 변호사 조언을 반환
@app.route("/advice/question_advice", methods=["GET"])
def get_checklist_advice():  ## paramter : doc_id, checklist_id
    ## 보안 키 header로 전달되었는지 확인
    try:
        auth_token = request.headers["Authorization"]
        if auth_token != "kimandhong":
            return jsonify({"error": "Invalid Authentication"}), 401
    except KeyError:
        return jsonify({"error": "Missing authorization token"}), 401

    parameter_dict = request.args.to_dict()
    print(parameter_dict)

    ## required 파라미터 확인
    try:
        doc_id = parameter_dict["doc_id"]
    except KeyError:
        return jsonify({"error": "'doc_id' Parameter Required"}), 400

    ## 없는 정관 아이디를 입력한 경우
    try:
        ## db 파일 불러오기
        with open(f"db/{doc_id}.json", "r", encoding="utf-8") as f:
            outputs = json.load(f)
    except:
        return (
            jsonify(
                {
                    "error": "The 'doc_id' you have entered does not exist. Please upload the document first."
                }
            ),
            400,
        )

    ## db 파일 불러오기
    with open(f"db/{parameter_dict['doc_id']}.json", "r", encoding="utf-8") as f:
        outputs = json.load(f)

    if "checklist_id" in parameter_dict.keys():
        try:
            results = []
            idx = int(parameter_dict["checklist_id"])
            result = {}
            result["question"] = outputs["checklist_questions"][idx]
            result["advice"] = outputs["advice"][idx]
            results.append(result)
        except:
            return (
                jsonify(
                    {
                        "error": f"Invalid checklist_id : 'checklist_id ' must be a value between 0 and 55"
                    }
                ),
                400,
            )

        return jsonify(results)
    else:
        results = []
        for idx, advice in enumerate(outputs["advice"]):
            result = {}
            result["question"] = outputs["checklist_questions"][idx]
            result["advice"] = advice
            results.append(result)

        return jsonify(results)


app.register_blueprint(xai)

if __name__ == "__main__":
    openai_api_key = os.environ.get("OPENAI_API_KEY", OPENAI_API_KEY)
    openai.api_key = openai_api_key

    try:
        port = SERVER_PORT
    except ImportError:
        port = 5000

    upload_folder = os.path.join(APP_ROOT, UPLOAD_FOLDER)
    os.makedirs(upload_folder, exist_ok=True)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    ssl_context.load_cert_chain(certfile=SSL_CERT, keyfile=SSL_KEY)

    app.run(host="0.0.0.0", port=port, debug=DEBUG, ssl_context=ssl_context)
