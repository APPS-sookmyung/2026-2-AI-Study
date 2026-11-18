# Harness² 코드 분석

> 대상: `google-research/harness2` 저장소 (Apache 2.0)

---


## 1. 개요

Harness²가 하는 일:

> **"agent가 일하는 방식을 적어 둔 파일들(harness)을, 정답 없이 여러 번 실행해 보면서 고치고, 고친 경험을 다음 task에 참고용으로 남긴다."**

### 레포 구조

```
harness2/
├── core/                  ← 논문의 "방법" 자체. 여기가 핵심
│   ├── recursion.py       Propose–Probe–Compose (parallel / sequential)
│   ├── schedule.py        한 task를 처음부터 끝까지 진행 (run_task)
│   ├── selection.py       최종 후보 선택 + 경험(lesson) 추출
│   ├── library.py         경험 저장소 (= 논문의 improvement harness)
│   ├── tree.py            harness를 "파일 묶음"으로 다루는 도구
│   ├── context.py         Editor에게 보여줄 증거 폴더 만들기 + 정답 유출 차단
│   ├── prompts.py         Editor/Selector에게 주는 지시문(프롬프트)
│   └── spec.py            "벤치마크가 갖춰야 할 인터페이스" 정의
├── benchmarks/            JobBench, LAB, WorkBuddy-Bench 어댑터
├── substrate/             실제 agent 실행기 (OpenCode, Codex)
└── demo.py                모델 없이 도는 장난감 예제
```

### 논문 용어 ↔ 코드 이름

| 논문 | 코드 |
|---|---|
| Harness (8 components) | `Tree` (`dict[str, str]`, 파일경로 → 내용) |
| Propose | `_run_stage(...)` 에서 `dim="INV"` / `"DOM"` |
| Probe | `_roll(...)`, `_roll_many(...)` (후보 harness를 실제로 실행) |
| Composer ("Combine & Finalize") | 코드에서는 **`aggregate`** (`dim="AGG"`) 또는 `compose_round` |
| Parallel / Sequential | 모드 토큰 `"agg"` / `"seq"` |
| 선택기 (agentic selector) | `run_selection(...)` |
| Reflector | `reflect_adoption(...)` → `_distil(...)` |
| Improvement harness (library) | `Library` 클래스 (`INDEX.md` + `EXPERIENCE.md`) |
| budget `k` | `--k` 옵션, 함수 인자 `k` |

---

## 2. Harness: 파일 묶음

논문에서 harness는 8개 component(system prompt, guardrails, memory, …). 코드에서는 이게 **폴더 안의 각 파일**이다.

`tree.py` 에서 harness 정의됨.

```python
Tree = dict[str, str]   # {"파일 경로": "파일 내용"}
```

OpenCode 실행기 기준으로 항상 켜져 있는(always-on) 파일은 이 네 개입니다 (`substrate/opencode.py`).

```python
always_on=(
    "systemprompt.md",                    # C1 System prompt
    "guardrails.md",                      # C2 Guardrails
    "LongTermMEMORY.md",                  # C3 Memory
    "tool_descriptions/tool_guidance.md", # C4 Tool guidance
),
always_on_max=24_000,   # 합쳐서 24,000자 상한
skill_dir="skills",     # C6 Skills  -> skills/<이름>/SKILL.md
plugin_dir="plugin",    # C8 Plugin  -> plugin/<이름>.ts
```

나머지는 이름 규칙으로 정해집니다 (`tree.py` 의 정규식).

- Subagent: `sub_agents/<이름>/AGENT.md`
- Script: `scripts/<이름>.py`

Editor(LLM)가 고칠 수 있는 범위가 "이 파일들뿐"이라는 뜻. 이 범위 밖의 파일을 만들면 `rejected` 로 걸러지고 다시 고치라는 피드백이 보내짐 (`recursion.py` 의 `_run_stage`).

또 하나, `tree.py` 상단 주석에 "**omitted-is-inherited**(빠뜨린 것은 물려받는다)"라고 적혀 있습니다. Editor는 **바꾼 파일만** 내면 되고, 나머지는 원래 harness 그대로 이어집니다.

---

## 3. 한 task가 처리되는 전체 흐름

`schedule.py` 의 `run_task(...)` 가 총괄. 독스트링이 흐름을 요약.

```python
"""k shared reference executions -> every mode -> blind selection per mode -> summary.json."""
```

풀어 쓰면:

```
1) base 실행 k번        현재(기본) harness로 task를 k번 돌림 (reference execution)
2) 모드별 recursion     parallel 또는 sequential로 개선 harness들을 만들고 실행
3) 블라인드 선택        완성된 후보들 중 하나를 익명으로 비교해 고름
4) 반성 (reflect)       선택된 harness가 왜 좋았는지 경험(lesson) 추출
5) library 저장         경험이 근거 있을 때만 저장 → 다음 task가 참고
```

핵심 코드:

```python
# schedule.py : run_task
base_tree = harness_tree.read_tree(surface, adapter.base_harness())   # 항상 "기본 harness"에서 시작

labels = [f"base{i}" for i in range(1, k + 1)]
...
base = [rolled[label] for label in labels]       # base 실행 결과 k개

for mode in modes:                               # "agg"(parallel), "seq"(sequential)
    _run_one_mode(mode, task_id, k, base, ..., base_tree=base_tree, ...)
```

**여기서 눈여겨볼 점:** `base_tree` 는 매 task마다 `adapter.base_harness()` 에서 새로 읽음. 즉 **이전 task가 만든 harness를 물려받지 않음.** 논문 슬라이드에서 말한 "다음 task는 항상 같은 출발점 H₀에서 시작"이 코드로 확인됨. 대신 library 폴더만 Editor에게 참고용으로 넘김 (`lib_dir = mode_lib.context_dir()`).

---

## 4. Propose: Editor INV와 DOM

Propose 단계에서는 Editor(LLM)가 **두 가지 관점** 중 하나를 맡아 harness를 수정함. `prompts.py` 에 각 관점의 지시문이 있음

### INV — "agent가 *어떻게 일하는가*" (도메인과 무관)

```text
# YOUR DIMENSION: INV -- how the agent WORKS

You own procedure, tool use and completion -- not subject matter. ...
- TOOL ERROR: ...
- MECHANICAL REPETITION: use `scripts/<name>.py` for repeated deterministic extraction ...
- TRIGGERED WORKFLOW: use an on-demand skill for a narrow multi-step procedure ...
...
Define "enough evidence," reserve room for every artifact, and reopen or mechanically check the
{deliverable}; a successful write call does not establish usability.
...
Do not add professional rules, required domain sections or matter facts. A parallel candidate
owns them; stay focused on how the agent works.
```

→ 논문의 **invariant candidate**. "산출물을 쓴 뒤 다시 열어서 확인하라" 같은 일반적인 작업 습관을 다룸

### DOM — "그 분야 전문가는 *무엇을 아는가*"

```text
# YOUR DIMENSION: DOM -- what a PRACTITIONER knows

You own the practitioner model the agent lacks: the {deliverable}, audience and decision,
controlling sources, required structure, consistency relationships, and expert omissions.
...
- Never invent an authority, identifier, standard or citation.
- State knowledge the agent can APPLY and CHECK, not background reading.
...
Do not diagnose commands, retries, reading order, output paths, budgeting, scripts or hooks. A
parallel candidate owns procedure; stay on practitioner knowledge.
```

→ 논문의 **domain-specific candidate**. 그 분야의 규칙·구조

**두 Editor는 서로의 영역을 건드리지 못하게** 프롬프트에 적혀 있음. 
---

## 5. Probe: 고친 harness를 실제로 돌려 본다

```python
def _roll(adapter, ledger, task_id, label, tree, run_id_of, work_dir, *, record=True) -> RunView:
    """Materialise a harness and roll it once. A dead rollout is recorded, never raised."""
    hdir = harness_tree.write_tree(adapter.substrate.surface(), tree, work_dir / "harnesses" / label)
    run_id = run_id_of(label)
    try:
        rd = adapter.execute(task_id, hdir, run_id)       # ← 실제 agent 실행
        rv = RunView(label=label, run_id=run_id, run_dir=rd, ok=exists, delivered=..., ...)
    except Exception as exc:
        rv = RunView(..., ok=False, error=f"{type(exc).__name__}: {exc}")   # 죽어도 예외 안 던지고 기록
    return rv
```



## 요약: 한 task의 데이터 흐름

```
 기본 harness H0 (매 task 동일)           library (같은 도메인의 지난 경험, 읽기 전용 참고)
        │                                        │
        ▼                                        ▼
   base 실행 ×k  ──증거──▶  Editor(INV) ─┐   (Editor가 참고)
 (trajectory,                Editor(DOM) ─┤
  deliverable)                            ▼
                              후보 harness들 ──Probe(실행)──▶ 후보별 증거
                                          │
                                          ▼
                            Compose/Aggregate Editor ──▶ 최종 후보(finals)
                                          │
                                          ▼
                    블라인드 선택 (익명 산출물 비교) ──▶ 채택 harness
                                          │
                                          ▼
                    Reflect: edit별 verdict + 교훈 (근거 없으면 NO_ENTRY)
                                          │
                                          ▼
                       library에 저장 (cue·lesson·evidence 모두 있을 때만)
```
