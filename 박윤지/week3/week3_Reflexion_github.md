## Reflexion Method 정리
- 에이전트 :추가적인 맥락을 제공하는 메모리 구성 요소인 mem 추가
### 1. Actor : M_a
```plain text
    궤적 t_t 생성 생성 : 시간 t 에서
    - 현재 정책 π_θ → 행동 or 생성물 샘플링 : **a_t**
    - 환경 → 관찰 : **o_t**
```
- 실패 경험(mem)을 반영하여 다음 trial의 행동을 수정

### 2. Evaluator : M_e
```plain text
    r_t = M_e(t_t)
```
- r_t는 시행 t 에 대한 스칼라 보상으로, 작업별 성능 향상에 따라 개선
- 과제별 기준에 따라 성공/실패 또는 보상 신호 생성
    - 추론 과제 : Exact Match 기반 보상 함수
    - 의사결정 과제 : 사정 정의된 휴리스틱 함수 등…

### 3. Self-Reflection : M_sr
```plain text
    sr_t = M_sr({t_t, r_t}, mem)
```
- sr_t는 시행 t에 대한 언어적 경험 피드백
    - 피드백 : 다음 trial에서 Actor가 개선할 행동과 전략을 자연어로 생성한 것
- 각 시행 t 이후, 에이전트의 mem에 sr_t 추가

### Memory
- 추론 시점의 Actor : Memory(단기 기억 + 장기 기억)으로 결정
- 단기 기억 (trajectory)
- 장기 기억 (mem)
    - M_sr의 출력물
    - LLM의 최대 컨텍스트 제한을 준수하기 위해 mem을 최대 저장 경험 수 Ω (보통 1-3으로 설정)로 제한

## LangGraph
### 1. Reflexion과 LangGraph의 관계
- LangGraph는 2024년 1월에 처음 발표된 프레임워크로, Reflexion이 발표된 당시 (2023년 3월)에는 순수 python 코드로 구현되어 있었음.
- Reflexion의 핵심인 **순환 구조**와 **상태 유지**를 깔끔하게 표현할 수 있는 최신 에이전트 프레임워크가 바로 LangGraph
- 즉 Reflexion은 에이전트의 알고리즘이고, LangGraph는 이를 실행하기 유리한 프레임워크

### 2. LangGraph 핵심 개념 및 동작 원리
- 자연어 처리와 AI 용응 프로그램 개발을 위한 프레임워크
- 에이전트 로직을 상태 기반 방향성 그래프(Stateful Multi-Actor Directed Graph)로 모델링

1. State (상태)
   - 그래프 전체의 노드 간에 공유되고 전달되는 중앙 데이터 구조
   - 각 노드가 실행될 때마다 State의 값을 읽어 작업을 수행하며, 작업 결과로 State를 업데이트
2. Nodes (노드)
   - 실제 로직 및 LLM 호출을 담당하는 Python 함수
   - 입력으로 현재 State를 받아 수행한 뒤, 수정되거나 추가될 State의 키-값 쌍을 반환

3. Edges (엣지) & Conditional Edges (조건부 엣지)
   - 노드 간의 이동 경로 및 제어 흐름(Control Flow)을 정의
   - Edges : 한 노드의 작업이 끝난 후 정해진 다음 노드로 무조건 이동 (A ➔ B).
   - Conditional Edges : 노드의 실행 결과(State)에 따라 제어 흐름을 분기 (예: 성공 시 END, 실패 시 Reflector로 이동).

4. Persistence & Checkpointer (지속성 및 체크포인터)
   - 각 단계마다 State의 스냅샷을 저장하여 대화 세션/trial 간에 상태를 자동으로 유지
   - 에이전트가 중단되거나 반복 시도를 해야 할 때 이전 실행 기록을 손실 없이 복원 및 이어받기 가능

### LangGraph 구성 요소 ↔ Reflexion 비교
| LangGraph | Reflexion | 상세 역할 및 동작 |
| :--- | :--- | :--- |
| State | Trajectory + mem | 단기 실행 기록, 장기 반성문 메모리, 시도 횟수 저장 |
|Actor Node | $M_a$ (Actor) | 현재 State의 단기 실행 기록과 장기 반성 메모리 를 프롬프트로 수신하여 행동/응답/코드 생성 |
| Evaluator Node | $M_e$ (Evaluator) | Actor의 결과물을 검증하여 성공/실패 여부를 State에 업데이트 |
| Reflector Node | $M_{sr}$ (Self-Reflection) | 실패 원인을 분석하여 자연어 오답노트(sr_t)를 작성하고, State의 장기 반성 메모리 리스트에 append |
| Conditional Edge | Trial Loop & Exit Logic | Evaluator 결과 판정 ➔ [Pass]: END / [Fail]: Reflector Node ➔ Actor Node 재시도 |

### LangGraph 도입 시 얻는 구조적 장점
- 순환 제어의 명시화: 복잡한 while 문 대신 노드와 조건부 엣지로 명확한 대시보드 형태의 흐름 파악 가능.
- 메모리 지속성 자동화: Checkpointer를 통해 슬라이딩 윈도우 및 에피소드 간 오답노트 누적이 코드 복잡도 없이 처리됨.