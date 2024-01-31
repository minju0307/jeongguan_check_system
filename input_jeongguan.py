import requests

with open("../all/3.txt", "r", encoding="utf-8") as f:
    input_text = f.read()

data = {"id": "0003", "text": input_text}


## 정관 업로드 기능 테스트
res = requests.post("http://163.239.28.21:5000/upload", json=data)

print(res)
