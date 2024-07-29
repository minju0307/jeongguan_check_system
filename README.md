# XAI 정관 분석 시스템

## 설치 방법

### 프로젝트 clone

```bash
git clone git@github.com:sogang-isds/XAI_Jeongguan.git
```

### 가상환경 설정

```bash
cd XAI_Jeongguan
virtualenv venv
. venv/bin/activate

pip install -r requirements.txt
```

### config.py 파일 생성

루트에 있는 `config.py.example` 파일을 복사하여 `config.py`를 생성합니다. 

#### OpenAI 정보

- `OPENAI_API_KEY`: GPT 사용을 위한 OpenAI 키 값을 넣습니다.

#### RabbitMQ 정보

RabbitMQ 서버가 설치된 HOST의 주소 및 계정 정보를 기입합니다.

```python
# RabbitMQ Info
MQ_HOST = ''
MQ_USER_ID = ''
MQ_USER_PW = ''
MQ_PORT = 5672
```

#### Celery 태스크 정보

- `CELERY_TASK_NAME`: 메시지큐에서 사용할 태스크 prefix를 정의합니다.

### 테스트 코드 실행

#### 함수 테스트

```bash
pytest --log-cli-level=DEBUG tests/unit_test.py
```

#### LLM 테스트

```bash
pytest --log-cli-level=DEBUG tests/llm_test.py
```

#### Celery 테스트

```bash
pytest --log-cli-level=DEBUG tests/celery_test.py
```

#### 개별 메소드 테스트 방법

```bash
pytest --log-cli-level=DEBUG tests/llm_test.py::TestLLM::test_get_embeddings
```

