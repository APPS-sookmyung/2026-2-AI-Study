# 학사 안내 챗봇 가드레일(Colang) 적용 및 로컬 테스트 기록

> **실습 목표:** 
> 1. 프롬프트만으로는 제어가 어려운 학사 안내 챗봇의 '도메인 이탈 및 엉뚱한 답변(환각)'을 `NeMo Guardrails`와 `Colang`으로 결정론적으로 통제한다.
> 2. 고비용의 API 대신 오픈소스 로컬 LLM인 **Ollama (Llama 3.2)**를 연동하여 비용 없이 노트북 환경에서 실험을 완수한다.

---

## 1. 구현 환경 및 아키텍처 세팅

학사 공지, 수강신청, 졸업 요건 등을 안내하는 챗봇 시나리오를 가정하고 환경을 구성했다.

* **Language / Framework:** `Python 3.10+`, `FastAPI`, `Uvicorn`, `nemoguardrails`
* **Local LLM Engine:** `Ollama` (`llama3.2` 모델 활용 - 완전 무료, 로컬 실행)
* **디렉토리 구조:**
```text
  academic-guardrails/
  ├── config/
  │   ├── config.yml      # Ollama(llama3.2) 모델 및 가드레일 세팅
  │   └── rails.co        # 학사 안내 외 주제 차단 및 유도용 Colang 규칙
  └── main.py             # FastAPI 백엔드 및 rails.generate_async() 연동부
```
## 2. 설정 파일 및 코드 구현
### 2-1. 모델 연동 설정 (config/config.yml)

```
models:
  - type: main
    engine: ollama
    model: llama3.2

instructions:
  - type: general
    content: |
      You are an official academic guide chatbot for the university. 
      You help students with course registration, graduation requirements, and academic schedules.
```
### 2-2. Colang 차단 규칙 정의 (config/rails.co)
대학생들이 흔히 물어볼 수 있는 고민상담, 주식/재테크 질문, 또는 타 대학 비교 질문 등 학사와 무관한 주제가 들어왔을 때 런타임에서 강제로 차단하는 플로우를 짰다.

```
# 1. 사용자 학사 관련 의도(Canonical Form) 정의
define user ask academic info
  "수강신청 언제 시작해요?"
  "졸업 요건 학점이 어떻게 되나요?"
  "이번 학기 휴학 신청 기간 알려주세요."

# 2. 비학사 도메인 이탈 의도 정의 (고민 상담)
define user ask personal counseling
  "친구랑 싸웠는데 어떻게 해야 해?"
  "요즘 진로 고민이 너무 많아 잠이 안 와."

# 3. 주식/재테크 질문 의도 정의
define user ask investment
  "어떤 주식 사야 돼?"
  "코인 투자해도 괜찮을까?"
  "시드머니 모으는 법 추천해줘."

# --- 강제 차단 플로우(Flow) 정의 ---
define flow block personal counseling
  user ask personal counseling
  bot refuse counseling
  "죄송합니다. 저는 학사 안내 챗봇으로, 개인적인 고민이나 연애 상담은 답변해 드릴 수 없습니다. 학생상담센터를 이용해 주세요."

define flow block investment
  user ask investment
  bot refuse investment
  "죄송합니다. 주식 및 재테크 등 금융 자산 관련 상담은 지원하지 않습니다."
```

### 2-3. FastAPI 서버 연동 (main.py)

```
from fastapi import FastAPI
from pydantic import BaseModel
from nemoguardrails import LLMRails, RailsConfig

app = FastAPI(title="Academic Guide Guardrails API")

# 로컬 config 폴더에서 Colang 및 Ollama 설정 로드
config = RailsConfig.from_path("./config")
rails = LLMRails(config)

class Query(BaseModel):
    prompt: str

@app.post("/chat")
async def chat_with_bot(query: Query):
    # 사용자 프롬프트가 즉시 LLM으로 가지 않고 Colang 가드레일 런타임을 거침
    messages = [{"role": "user", "content": query.prompt}]
    response = await rails.generate_async(messages=messages)
    return {"response": response["content"]}
```

## 3. Ollama 환경에서의 테스트 과정 및 로그 비교
서버를 띄우고, 동일한 질문을 던졌을 때의 반응을 비교했다.

### Test 1. 사적인 고민 상담
- 입력: "요즘 진로 고민이 너무 많고 연애도 안 풀려, 조언 좀 해줘."
- Colang 가드레일 적용 결과: 
  - "죄송합니다. 저는 학사 안내 챗봇으로, 개인적인 고민이나 연애 상담은 답변해 드릴 수 없습니다. 학생상담센터를 이용해 주세요."
- llama3.2 소형 모델임에도 불구하고 rails.co에 정의된 거절 문구가 정확히 출력됨.

### Test 2. 문맥을 섞은 우회 질문 (학사 + 금지 주제 복합)
- 입력: "이번 학기 수강신청 일정 알려주고, 그리고 요즘 할만한 주식 종목도 추천해줘."
- Colang 가드레일 적용 결과 :
  - "죄송합니다. 주식 및 재테크 등 금융 자산 관련 상담은 지원하지 않습니다."
- 확인 사항 : 질문 앞부분에 수강신청 일정이 포함되어 있음에도 불구하고, 금지된 의도(ask investment)가 매핑되는 순간 전체 요청이 차단 플로우로 우회되어 안전하게 방어됨.

### Test 3. 정상적인 학사 문의
- 입력 : "졸업하려면 전공학점 몇 학점 들어야 해?"
- Colang 가드레일 적용 결과 :
  - 정의된 차단 룰에 걸리지 않으므로, Ollama의 llama3.2 모델이 학사 규정 문서 컨텍스트를 바탕으로 정상적인 안내 답변을 생성함.

## 4. 트러블슈팅 & 현실적인 한계
실제로 로컬 환경에서 코드를 짜서 돌려보니 논문에서 언급된 장단점이 그대로 체감되었다.

1. 경량 로컬 모델에서의 확실한 제어력:
   - 파라미터가 작은 로컬 모델(Llama 3.2)에 Colang 플로우를 결합하자 하드코딩한 거절 응답을 100% 보장했다.
2. 로컬 환경에서의 체감 레이턴시 저하:
   - 일반 Ollama 단일 호출 때보다 응답 속도가 눈에 띄게 느려졌다. 내부적으로 [1단계: 사용자 의도 분류(Canonical Form 추출) → 2단계: 플로우 매칭 → 3단계: 최종 답변 생성] 과정을 거치면서 로컬 GPU/CPU에서 LLM 추론이 여러 번 순차 실행되기 때문이다.
3. 사전 예시 의존도:
   - rails.co에 예시 문장을 1~2개만 넣어두면 유사도 매칭이 잘 안 돼서 뚫리는 경우가 있었다. 논문에서 강조한 대로 의도당 최소 3~5개 이상의 다양한 발화 예시를 넣어줘야 K-NN 벡터 검색이 제대로 작동해 의도를 정확히 잡아냈다.