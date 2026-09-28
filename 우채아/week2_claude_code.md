# Claude Code의 `.claude` 디렉토리

## 기본 구조
- Claude Code는 두 군데를 읽음: **프로젝트 루트의 `.claude/`** (팀과 git 공유), **홈 디렉토리의 `~/.claude/`** (개인 전역 설정, 모든 프로젝트에 적용)
- 대부분의 사용자는 `CLAUDE.md`와 `settings.json` 정도만 건드리면 충분. 나머지는 필요할 때만 추가

## 프로젝트 루트 파일 (`your-project/`)

- **`CLAUDE.md`** — 매 세션 시작 시 로드되는 프로젝트 지침
  - 200줄 이내 권장 (더 길어도 로드는 되지만 지침 준수율 저하)
  - 빌드/테스트/린트 명령어, 스택, 코드 컨벤션 등을 적어두면 좋음
  - 세션 중 `/memory` 명령으로 바로 열고 편집 가능
  - `.claude/CLAUDE.md`에 둬도 동일하게 동작 (루트를 깔끔하게 유지하고 싶을 때)

- **`.mcp.json`** — 팀이 공유하는 프로젝트 범위 MCP 서버 설정
  - 토큰 등 비밀값은 `${NOTION_TOKEN}` 같은 환경변수 참조로 넣기 (파일에 값이 직접 남지 않음)
  - 나만 쓰는 서버는 `claude mcp add --scope user`로 등록 → `~/.claude.json`에 저장됨

- **`.worktreeinclude`** — git worktree 생성 시 함께 복사할 gitignored 파일 목록 (`.env` 등). `.gitignore` 문법 사용

## `.claude/` 하위 (프로젝트 범위)

- **`settings.json`** (committed) — 권한(permissions), hooks, statusLine, 기본 모델, 환경변수 등 **실제로 강제되는 설정**
  - `permissions.allow` / `deny`에 와일드카드 가능 (예: `Bash(npm test *)`)
  - CLAUDE.md는 "가이드"일 뿐이지만, settings.json은 Claude가 따르든 안 따르든 강제됨

- **`settings.local.json`** (gitignored) — 개인 전용 오버라이드. 팀 설정 위에 나만의 권한 추가할 때

- **`rules/`** — 주제별로 나눈 지침 파일들
  - `paths:` frontmatter 없으면 세션 시작 시 항상 로드
  - `paths:` glob 지정하면 해당 파일 작업할 때만 로드 (예: `**/*.test.ts`일 때만 테스트 규칙 로드)
  - CLAUDE.md가 200줄 넘어가면 여기로 쪼개기 시작

- **`skills/<name>/SKILL.md`** — `/이름`으로 호출하거나 Claude가 자동으로 매칭해서 쓰는 재사용 프롬프트
  - 폴더 형태라 참고 문서, 템플릿, 스크립트 등 함께 번들 가능
  - `disable-model-invocation: true` → 사용자만 호출 가능 (Claude 자동 호출 안 함)
  - `$ARGUMENTS`, `$0`, `$1`로 인자 받기 가능

- **`commands/`** — 단일 파일짜리 프롬프트 (skills와 동일 메커니즘, 신규는 skills 권장)

- **`agents/`** — 서브에이전트 정의 (각자 독립된 컨텍스트 창에서 실행)
  - `tools:` frontmatter로 도구 접근 제한 가능 (예: 리뷰용 에이전트는 Read/Grep/Glob만)
  - `@`로 자동완성에서 직접 호출 가능

- **`workflows/*.js`** — 여러 서브에이전트를 조율하는 동적 워크플로우 스크립트. `/workflows`에서 저장해서 만듦

- **`agent-memory/`** — `memory: project` 옵션 쓰는 서브에이전트의 영구 메모리 (팀 공유용)

## `~/.claude/` (전역, macOS 홈 디렉토리)

- **`~/.claude.json`** — 앱 상태 (테마, OAuth, 프로젝트별 신뢰 여부, 개인 MCP 서버). 보통 `/config`로 관리
- **`~/.claude/CLAUDE.md`** — 모든 프로젝트에 적용되는 개인 지침 (응답 스타일, 커밋 포맷 등). 프로젝트 CLAUDE.md와 충돌 시 프로젝트가 우선
- **`~/.claude/settings.json`** — 전역 기본 설정, 프로젝트 settings.json이 겹치는 키를 덮어씀
- **`~/.claude/projects/`** — **자동 메모리(auto memory)**: Claude가 세션 간 스스로 기록·업데이트하는 노트 (빌드 명령, 아키텍처, 디버깅 팁 등). 기본 켜짐, `/memory`로 토글
- **`~/.claude/rules/`, `skills/`, `agents/`, `workflows/`** — 위 프로젝트 버전과 동일한 개념이나 모든 프로젝트에서 사용 가능

## 알아두면 좋은 것
- 설정 파일이 안 먹히면 `설정 디버그` 관련 문서 참고 (`/docs/debug-your-config`)
- `~/.claude/`에는 트랜스크립트, 프롬프트 기록 등도 쌓이는데, 기본 30일 지나면 자동 정리됨 (`cleanupPeriodDays` 설정으로 조절)
- **로컬 데이터 정리**: `claude project purge <경로>`로 특정 프로젝트의 Claude Code 저장 데이터 삭제 가능 (v2.1.124+). `--dry-run`으로 미리보기 가능
- `~/.claude.json`, `~/.claude/settings.json`, `~/.claude/plugins/`는 절대 삭제 금지 (인증/설정/플러그인 정보 보관)
