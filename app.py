import string
from datetime import datetime
from logging.config import dictConfig
from random import random
from urllib.parse import urljoin

from flask import Flask, request, jsonify, json
from jsonschema import validate
from werkzeug.utils import secure_filename

from error_code import ErrorCode, ErrorElement
from main import main
import os

from utils.utils import allowed_file, json_response_element

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
app.config['SECRET_KEY'] = 'secret!'
app.config["JSON_AS_ASCII"] = False  # 한국어 지원을 위한 설정
app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'
app.json.sort_keys = True

ALLOWED_EXTENSIONS = {'txt'}


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
            file_url = urljoin(config.SERVICE_URL,
                               os.path.join(config.UPLOAD_FOLDER, folder, date_str, new_file))  # 다운로드 가능한 URL

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


@app.route("/")
def index():
    return "Hello, World!"


@app.route("/processing", methods=["POST"])
def processing():
    ## 보안 키 header로 전달되었는지 확인
    auth_token = request.headers.get("Authorization")
    if not auth_token:
        return jsonify({"error": "Missing authorization token"}), 401
    if not auth_token == "kimandhong":
        return jsonify({"error": "Invalid Authentication"}), 401

    ## json 형식이 맞는지 확인
    # try:
    #     contents = request.get_json(force=True)
    # except:
    #     return jsonify({"error": "Invalid Json Type"}), 400
    results = save_file_from_request(request, folder='speech')
    if type(results) == ErrorElement:
        return json_response_element(results)
    else:
        file_path, file_url = results

    print(file_path)


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


if __name__ == "__main__":
    try:
        import config

        port = config.SERVER_PORT
    except ImportError:
        port = 5000

    app.run(host="0.0.0.0", port=port, debug=True)
