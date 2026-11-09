# Claude Code 메모리 요약

> 출처: https://code.claude.com/docs/ko/memory
> 매 세션은 새 컨텍스트로 시작하며, 세션 간 지식은 **CLAUDE.md**와 **자동 메모리** 두 가지로 전달된다. 둘 다 "강제 설정"이 아니라 **컨텍스트**로 취급된다. (강제하려면 훅/설정 사용)

## 1. CLAUDE.md vs 자동 메모리

| | CLAUDE.md | 자동 메모리 |
|---|---|---|
| 작성자 | 사용자 | Claude |
| 내용 | 지침·규칙 | 학습·패턴 |
| 범위 | 프로젝트/사용자/조직 | 저장소당 (워크트리 공유) |
| 로드 | 매 세션 | 매 세션 (`MEMORY.md` 처음 200줄 또는 25KB) |
| 용도 | 코딩 표준, 워크플로, 아키텍처 | 선호도, 수정 사항, 코드로 파악 불가한 컨텍스트 |

## 2. CLAUDE.md 위치 (넓은 범위 → 좁은 범위 순으로 로드)

| 범위 | 위치 |
|---|---|
| 관리형 정책 | macOS `/Library/Application Support/ClaudeCode/CLAUDE.md`, Linux/WSL `/etc/claude-code/CLAUDE.md`, Windows `C:\Program Files\ClaudeCode\CLAUDE.md` |
| 사용자 | `~/.claude/CLAUDE.md` |
| 프로젝트 | `./CLAUDE.md` 또는 `./.claude/CLAUDE.md` (팀 공유) |
| 로컬 | `./CLAUDE.local.md` (개인용, `.gitignore`에 추가) |

- 작업 디렉터리와 **상위** 디렉터리의 파일은 시작 시 로드, **하위** 디렉터리 파일은 해당 파일을 읽을 때 로드
- 파일끼리 서로 덮어쓰지 않고 이어 붙음 (루트 → 작업 디렉터리 순, 각 디렉터리에서 `CLAUDE.local.md`가 마지막)
- 로드 확인: `/context` → **Memory files**
- 블록 수준 HTML 주석 `<!-- ... -->`은 컨텍스트에서 제거됨 (유지보수자 메모용)
- `/init`: 코드베이스를 분석해 시작용 CLAUDE.md 생성 (이미 있으면 개선안 제안). `CLAUDE_CODE_NEW_INIT=1`이면 대화형 다단계 흐름

## 3. 효과적인 지침 작성

- **구체적으로**: "2칸 들여쓰기 사용", "커밋 전 `npm test` 실행", "API 핸들러는 `src/api/handlers/`에 위치"
- **짧게**: 파일당 **200줄 이하** 권장 (길수록 준수율 하락, 4 MiB 초과 파일은 건너뜀)
- **구조화**: 마크다운 헤더 + 글머리 기호
- **일관성**: 모순되는 지침은 Claude가 임의로 선택 → 주기적으로 정리
- `/doctor prompt-audit`: 오래되거나 충돌하는 지침 점검 (v2.1.283+, 수정은 요청해야 적용)
- 추가 시점: 같은 실수 반복, 코드 리뷰에서 지적된 사항, 매번 같은 설명을 다시 입력할 때
- 다단계 절차·일부 코드에만 해당하는 내용은 **스킬** 또는 **경로 범위 규칙**으로

## 4. 파일 가져오기 (`@`)

```markdown
See @README for overview and @package.json for npm commands.
- git workflow @docs/git-instructions.md
- @~/.claude/my-project-instructions.md   # 여러 worktree에서 개인 지침 공유
```

- 상대 경로는 **가져오는 파일 기준**, 최대 **4홉** 재귀
- 공백 포함 경로는 `\ `로 이스케이프 (따옴표 불가)
- 코드 스팬/코드 블록 안의 `@`는 무시 → 경로만 언급하려면 백틱으로 감싸기
- 가져온 파일도 **시작 시 로드**되므로 컨텍스트 절감 효과는 없음
- 작업 디렉터리 밖 **외부 가져오기**는 최초 1회 승인 대화 상자 (거부 시 비활성)

## 5. `.claude/rules/` 규칙

```
.claude/
├── CLAUDE.md
└── rules/
    ├── code-style.md
    ├── testing.md
    └── security.md
```

- 주제별 `.md` 파일, 하위 디렉터리 재귀 탐색
- `paths` 없는 규칙 → 시작 시 무조건 로드
- **경로별 규칙**: 일치하는 파일을 Read/Write/Edit(또는 읽기성 Bash)할 때만 로드

```markdown
---
paths:
  - "src/**/*.{ts,tsx}"
  - "lib/**/*.ts"
---
# API Development Rules
- All API endpoints must include input validation
```

- glob 예: `**/*.ts`, `src/**/*`, `*.md`, `src/components/*.tsx`
- frontmatter에서 Claude가 읽는 필드는 `paths`뿐
- 중괄호 확장은 규칙당 1,000패턴/4 MiB 예산 공유
- **사용자 수준 규칙**: `~/.claude/rules/` (모든 프로젝트 적용, 프로젝트 규칙보다 먼저 로드)
- **심볼릭 링크**로 규칙 공유 가능 (`ln -s ~/shared-claude-rules .claude/rules/shared`). 대상이 작업 디렉터리 밖이면 외부 가져오기로 취급, 네트워크 경로는 로드 안 됨

## 6. 조직/대규모 팀 관리

- **관리형 CLAUDE.md**: 위 관리형 정책 경로에 MDM/Ansible 등으로 배포, 개별 설정으로 제외 불가
- `managed-settings.json`의 `claudeMd` 키로 내용을 직접 삽입 가능 (관리형 설정에서만 유효)
- 역할 분담: **강제**(`permissions.deny`, `sandbox.enabled` 등) → 관리형 설정 / **행동 지침**(코드 스타일, 규정 안내) → 관리형 CLAUDE.md
- **`claudeMdExcludes`**: 모노레포에서 무관한 CLAUDE.md/규칙을 경로·glob으로 제외 (관리형 정책 CLAUDE.md는 제외 불가, 계층 간 배열 병합)

```json
{ "claudeMdExcludes": ["**/monorepo/CLAUDE.md", "/home/user/monorepo/other-team/.claude/rules/**"] }
```

- `--add-dir` 디렉터리의 CLAUDE.md 로드: `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1 claude --add-dir ../shared-config`

## 7. AGENTS.md 지원 (v2.1.277+)

| 저장소 상태 | Claude가 읽는 것 |
|---|---|
| `AGENTS.md`만 있음 | `AGENTS.md` |
| `AGENTS.md` + (작업 디렉터리 또는 상위에) `CLAUDE.md`/`CLAUDE.local.md` | `CLAUDE.md`만 |
| `CLAUDE.md`가 `@AGENTS.md`를 가져옴 | 둘 다 (가져오기 경유) |

- `/config` → **프로젝트 지침** 값
  - `claude-md-or-agents-md` (기본)
  - `claude-md-and-agents-md` (둘 다, 중복 로드 방지)
  - `claude-md` (CLAUDE.md만)
  - `managed-only` (관리형 CLAUDE.md + 자동 메모리만)
- 설정 파일로는 `pluginConfigs`의 `cc-plugin-agents-md@builtin` → `options.instructionFiles`
- 읽지 않는 것: `AGENTS.local.md`, `AGENTS.override.md`, `.agents/`
- 다른 도구와 공유: `CLAUDE.md`에 `@AGENTS.md` 한 줄 + Claude 전용 지침 추가, 또는 `ln -s AGENTS.md CLAUDE.md` (Windows는 가져오기 권장)
- `/init`은 Cursor/Copilot 등 다른 도구 규칙을 흡수, `/import`는 다른 에이전트 설정(지침·MCP·명령·서브에이전트·스킬)을 일회성 복사

## 8. 자동 메모리

**저장하는 4가지 유형** (`type` frontmatter)
- `user`: 역할, 전문 분야, 작업 선호
- `feedback`: 사용자의 수정 사항, 확인된 접근 방식
- `project`: 진행 중 작업, 마감, 결정 (코드/git으로 알 수 없는 것)
- `reference`: 외부 정보 위치 (이슈 트래커, 대시보드 등)

코드에서 도출 가능한 것, 이미 CLAUDE.md에 있는 내용은 저장하지 않음.

**켜기/끄기**
- 로컬 세션은 기본 ON, 자체 호스팅 환경은 기본 OFF
- `/memory` 토글 → `~/.claude/settings.json`의 `autoMemoryEnabled`
- 프로젝트별 끄기: 프로젝트 설정에 `"autoMemoryEnabled": false`
- 환경 변수: `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`
- 백그라운드 세션·다른 Claude Code가 시작한 세션에서는 끌 수만 있고 다시 켤 수 없음

**저장 위치**
```
~/.claude/projects/<project>/memory/
├── MEMORY.md            # 인덱스(한 줄당 메모리 1개), 매 세션 로드
├── user_role.md         # 주제별 파일 (필요할 때만 읽음)
└── feedback_testing.md
```
- 같은 git 저장소의 워크트리·하위 디렉터리는 하나의 디렉터리 공유, **머신 로컬**(기기·클라우드 간 공유 안 됨)
- 위치 변경: `settings.json`의 `autoMemoryDirectory` (절대 경로 또는 `~/`)
- `cleanupPeriodDays` 정리 대상 아님 (직접 삭제 전까지 유지)

**동작 방식**
- 시작 시 `MEMORY.md`의 **처음 200줄 / 25KB**만 로드, 초과분은 누락 → Claude가 상세 내용을 주제 파일로 분리해 간결 유지
- 주제 파일은 필요할 때 Claude가 읽음
- 서브에이전트에는 메인 자동 메모리가 로드되지 않음 (포크 제외), 서브에이전트는 `memory` 필드로 별도 메모리 가능
- "Saved N memories" / "Recalled N memories" 메시지로 동작 확인
- 일반 markdown이라 언제든 직접 편집·삭제 가능

## 9. `/memory` 명령

- CLAUDE.md, CLAUDE.local.md, 규칙 등 메모리 파일 목록 → 선택해 편집기에서 열기 (없으면 생성)
- 자동 메모리 토글, 자동 메모리 폴더 열기
- "항상 pnpm 사용해" 같은 요청 → 자동 메모리에 저장 / CLAUDE.md에 넣으려면 "이것을 CLAUDE.md에 추가해"라고 명시

## 10. 문제 해결

**Claude가 CLAUDE.md를 안 따를 때**
- `/context`로 파일이 로드됐는지 확인 (안 보이면 Claude도 못 봄)
- 하위 디렉터리 CLAUDE.md는 해당 디렉터리 파일을 읽어야 로드됨
- 지침을 더 구체적으로, 충돌하는 지침 제거
- Claude Code 내장 지침(커밋/PR)과 충돌하면 `includeGitInstructions`, `attribution` 설정
- 특정 시점에 반드시 실행돼야 하면 **훅** 사용, 시스템 프롬프트 수준은 `--append-system-prompt`
- `InstructionsLoaded` 훅으로 로드된 파일·시점·이유를 로깅

**AGENTS.md가 안 읽힐 때**
1. 작업 디렉터리/상위에 `CLAUDE.md`·`.claude/CLAUDE.md`·`CLAUDE.local.md`가 있는지 (`~/.claude/CLAUDE.md` 제외)
2. `claude --version`이 v2.1.277+ (일부 세션은 v2.1.281+) 인지
3. `/config`의 **프로젝트 지침** 값이 `claude-md`/`managed-only`가 아닌지
- 읽혔는지는 `/memory`에서 확인

**CLAUDE.md가 너무 클 때**
- 200줄 초과 시 경고, 경로별 규칙으로 분리, 코드에서 파생 가능한 내용(디렉터리 구조 등)은 제거
- `@` 분할은 정리에는 좋지만 컨텍스트는 안 줄어듦

**`/compact` 후 지침이 사라진 것 같을 때**
- 프로젝트 루트 CLAUDE.md는 압축 후 디스크에서 다시 주입됨
- 대화 중에만 말한 지침, 아직 재로드 안 된 중첩 CLAUDE.md, 일치 파일을 안 건드린 경로별 규칙은 사라질 수 있음 → CLAUDE.md에 기록

## 핵심 요약

1. 반복해서 설명하는 내용은 **CLAUDE.md**에, 짧고(200줄 이하) 구체적이고 일관되게
2. 일부 파일에만 해당하는 지침은 **`.claude/rules/` + `paths`**로 범위 지정
3. Claude가 스스로 배우는 선호·수정 사항은 **자동 메모리**(`MEMORY.md`, 200줄/25KB 제한)
4. 반드시 강제해야 하는 것은 CLAUDE.md가 아니라 **훅·권한 설정**
5. 확인은 `/context`, `/memory`, `/doctor prompt-audit`
