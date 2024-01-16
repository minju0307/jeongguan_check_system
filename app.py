from flask import Flask, request, jsonify, json
import pandas as pd
from main import main

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 한국어 지원을 위한 설정

# 정관 문서를 받아서 분석을 수행하고, 결과를 json 형태로 반환
@app.route('/upload', methods=['POST'])
def input_jeongguan(): 
    
    contents = request.get_json()
    outputs = main (input_id=contents["id"], input_text=contents["text"])
    
    return jsonify(outputs)

# 정관 문서 당 split된 문단들을 반환
@app.route('/paragraph', methods=['GET']) 
def get_paragraph(): ## parameter : doc_id, paragraph_id  
    
    parameter_dict = request.args.to_dict()
    print(parameter_dict)
    
    ## db 파일 불러오기
    with open(f"db/{parameter_dict['doc_id']}.json", "r", encoding="utf-8") as f:
        outputs = json.load(f)  
    
    if "paragraph_id" in parameter_dict.keys():
        return jsonify(outputs["doc_paragraphs"][int(parameter_dict["paragraph_id"])])
    
    else:  
        return jsonify(outputs["doc_paragraphs"])  

# 확인해야 하는 전체 checklist를 반환
@app.route('/checklist', methods=['GET'])
def get_checklist(): ## parameter : checklist_id
    
    parameter_dict = request.args.to_dict()
    print(parameter_dict)
    
    ## checklist 파일 불러오기 
    with open("data/jeongguan_questions_56.json", "r", encoding="utf-8-sig") as f:
        questions = json.load(f)
    
    if "checklist_id" in parameter_dict.keys():
        return jsonify(list(questions.keys())[int(parameter_dict["checklist_id"])])
    else:
        return jsonify(list(questions.keys()))
    
    
# reference에 해당하는 상법들의 리스트를 반환
@app.route('/reference_sangbub', methods=['GET'])
def get_sangbub(): ## parameter : sangbub_id
    
    parameter_dict = request.args.to_dict()
    print(parameter_dict)
    
    ## 상법 파일 불러오기
    with open("data/reference_sangbub.json", "r", encoding="utf-8-sig") as f:
        reference = json.load(f)
        
    if "sangbub_id" in parameter_dict.keys():
        return jsonify(reference[int(parameter_dict["sangbub_id"])])
    else:
        return jsonify(reference)

# 정관 문서 당 질문 - 정관 맵핑 결과를 반환
@app.route('/qna/question_paragraph', methods=['GET'])
def get_mapping_paragraph(): ## paramter : doc_id, checklist_id
    
    parameter_dict = request.args.to_dict()
    print(parameter_dict)
    
    ## db 파일 불러오기
    with open(f"db/{parameter_dict['doc_id']}.json", "r", encoding="utf-8") as f:
        outputs = json.load(f) 
        
    if "checklist_id" in parameter_dict.keys():
        results = []
        idx = int(parameter_dict["checklist_id"])
        result={}
        result["question"]=outputs["checklist_questions"][idx]
        result["paragraph"]=outputs["mapping_paragraphs"][idx]
        results.append(result)
        
        return jsonify(results)
    
    else:
        results = []
        for idx, mapping_paragraph in enumerate(outputs["mapping_paragraphs"]):
            result={}
            result["question"]=outputs["checklist_questions"][idx]
            result["paragraph"]=mapping_paragraph
            results.append(result)
            
        return jsonify(results)

# 정관 문서 당 체크리스트 질문 - 답변을 반환
@app.route('/qna/mrc_answer', methods=['GET'])
def get_mrc_answer(): ## paramter : doc_id, checklist_id
    
    parameter_dict = request.args.to_dict()
    print(parameter_dict)
    
    ## db 파일 불러오기
    with open(f"db/{parameter_dict['doc_id']}.json", "r", encoding="utf-8") as f:
        outputs = json.load(f)
    
    if "checklist_id" in parameter_dict.keys():
        results = []
        idx = int(parameter_dict["checklist_id"])
        result={}
        result["question"]=outputs["checklist_questions"][idx]
        result["answer"]=outputs["mrc_answer"][idx]
        results.append(result)
        
        return jsonify(results)
    else:
        results = []
        for idx, mrc_answer in enumerate(outputs["mrc_answer"]):
            result={}
            result["question"]=outputs["checklist_questions"][idx]
            result["answer"]=mrc_answer
            results.append(result)
            
        return jsonify(results)

# 정관 문서 당 체크리스트 질문 - 상법 맵핑 결과를 반환
@app.route('/advice/question_sangbub', methods=['GET'])
def get_checklist_sangbub(): ## paramter : doc_id, checklist_id
    
    parameter_dict = request.args.to_dict()
    print(parameter_dict)
    
    ## db 파일 불러오기
    with open(f"db/{parameter_dict['doc_id']}.json", "r", encoding="utf-8") as f:
        outputs = json.load(f)
    
    if "checklist_id" in parameter_dict.keys():
        results = []
        idx = int(parameter_dict["checklist_id"])
        result={}
        result["question"]=outputs["checklist_questions"][idx]
        result["sangbub"]=outputs["sangbub"][idx]
        results.append(result)
        
        return jsonify(results)
    else:
        results = []
        for idx, sangbub in enumerate(outputs["sangbub"]):
            result={}
            result["question"]=outputs["checklist_questions"][idx]
            result["sangbub"]=sangbub
            results.append(result)
            
        return jsonify(results)
    

# 정관 문서 당 체크리스트 질문 - 변호사 조언을 반환
@app.route('/advice/question_advice', methods=['GET'])
def get_checklist_advice(): ## paramter : doc_id, checklist_id
    
    parameter_dict = request.args.to_dict()
    print(parameter_dict)
    
    ## db 파일 불러오기
    with open(f"db/{parameter_dict['doc_id']}.json", "r", encoding="utf-8") as f:
        outputs = json.load(f)
    
    if "checklist_id" in parameter_dict.keys():
        results = []
        idx = int(parameter_dict["checklist_id"])
        result={}
        result["question"]=outputs["checklist_questions"][idx]
        result["advice"]=outputs["advice"][idx]
        results.append(result)
        
        return jsonify(results)
    else:
        results = []
        for idx, advice in enumerate(outputs["advice"]):
            result={}
            result["question"]=outputs["checklist_questions"][idx]
            result["advice"]=advice
            results.append(result)
            
        return jsonify(results)

if __name__ == '__main__':
    app.run(host='163.239.28.21', port=5000, debug=True)