# Fitness Assistant

운동 정보를 검색하고, 검색된 내용을 바탕으로 답변하는 RAG API 실습 프로젝트입니다.
[DataTalks.Club LLM Zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp/tree/main/07-project-example)
ㅇㅇ의 프로젝트 예제를 바탕으로 작성했습니다.

## 동작 흐름

```text
질문 -> minsearch 키워드 검색 -> 상위 10개 운동 정보
    -> OpenAI 답변 생성 → LLM 판사의 관련성 평가
    -> PostgreSQL에 질문·답변·평가·사용량 저장 -> JSON 응답

사용자 피드백 -> 대화 ID로 연결 -> PostgreSQL 저장
Grafana -> PostgreSQL 조회 -> 대시보드 표시
```

질문 한 건당 LLM을 두 번 호출합니다. 검색과 피드백 저장에는 LLM을 호출하지 않습니다.
각 질문은 독립적으로 처리하며, 이전 대화를 프롬프트에 누적하지 않습니다.

## 준비

- Docker 및 Docker Compose
- uv와 Python 3.14 (`.python-version`에 지정)
- OpenAI API 키

아래 명령은 모두 프로젝트 루트에서 실행합니다.

```bash
uv sync
```

Flask와 PostgreSQL 드라이버도 의존성에 등록되어 있으므로 별도로 `uv add`할 필요가 없습니다.

`.env`가 없을 때만 예시 파일을 복사하고, 본인의 키로 변경합니다.
기존 `.env`가 있다면 그대로 사용하세요.

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=your-openai-api-key
```

`.env`와 로컬 가상환경은 Git 및 Docker 이미지에서 제외합니다.
앱 시작 시 기존 `data/data.csv`를 읽어 메모리에 검색 인덱스를 만듭니다.
CSV가 있다면 데이터를 다시 생성할 필요가 없습니다.

## 처음 실행하기

### 1. 컨테이너 시작

```bash
docker compose up -d --build
```

| 서비스 | 주소 / 접속 정보 |
| --- | --- |
| Flask API | `http://localhost:5001` |
| PostgreSQL | `localhost:5432`, DB `fitness_assistant`, 사용자 `user`, 비밀번호 `password` |
| Grafana | `http://localhost:3000`, 아이디 `admin`, 비밀번호 `admin` |

API는 웹 채팅 화면이 아니라 아래의 POST 엔드포인트로 사용합니다.
현재 Flask 실행 설정은 로컬 개발용 debug 모드입니다.

### 2. DB 초기화 — 최초 한 번

PostgreSQL이 연결을 받을 준비가 되었는지 확인합니다.
아직 준비되지 않았다면 잠시 후 다시 확인하세요.

```bash
docker compose exec postgres pg_isready -U user -d fitness_assistant
```

처음 사용할 때 대화·피드백 테이블을 생성합니다.

```bash
docker compose exec app python -c \
  "from fitness_assistant.db import init_db; init_db()"
```

**현재 `init_db()`는 기존 테이블을 삭제하고 다시 만듭니다.**
기존 대화·피드백을 유지하려면 재시작할 때 이 명령을 실행하지 마세요.

### 3. Grafana 대시보드 자동 등록

```bash
uv run grafana/init.py
```

PostgreSQL 데이터소스와 대시보드를 Grafana API로 등록합니다.
다시 실행하면 같은 대시보드를 갱신하며, DB 데이터는 변경하지 않습니다.

[Fitness Assistant 대시보드 열기](http://localhost:3000/d/fitness-assistant/fitness-assistant)

- 최근 대화 5개
- 사용자 긍정·부정 피드백
- LLM 판사의 답변 관련성
- OpenAI 예상 비용
- 답변·평가 토큰 사용량
- 사용 모델
- 응답 시간 — 검색·답변 생성·판사 평가의 합계

기본 시간 범위는 최근 6시간, 시간대는 한국, 자동 갱신은 30초입니다.
기록이 없으면 먼저 질문을 보내세요. 과거 기록을 보려면 시간 범위를 넓히세요.
비용은 코드에 설정된 토큰 단가로 계산한 추정치이며, 실제 청구액과 일치한다고 보장하지 않습니다.

Grafana 관리자 계정을 바꿨다면 `.env`에 아래 설정을 추가합니다.
이 값은 등록 스크립트의 로그인 설정이며, Grafana 계정 자체를 변경하지는 않습니다.

```env
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your-grafana-password
```

`grafana/dashboard.json`은 패널·SQL·배치 설정이고,
`grafana/init.py`는 해당 설정을 Grafana에 등록하는 스크립트입니다.

## API 사용

### 질문하기

```bash
curl -X POST http://localhost:5001/question \
  -H "Content-Type: application/json" \
  -d '{"question": "What exercises target the chest?"}'
```

응답 형식:

```json
{
  "conversation_id": "생성된 UUID",
  "question": "What exercises target the chest?",
  "answer": "생성된 답변"
}
```

관련성 평가와 사용량은 DB에 저장하며, 현재 API 응답에는 포함하지 않습니다.

### 피드백 보내기

질문 응답에서 받은 실제 `conversation_id`를 사용합니다.
`feedback`은 긍정 `1`, 부정 `-1`입니다.

```bash
curl -X POST http://localhost:5001/feedback \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "실제 대화 ID", "feedback": 1}'
```

피드백 요청마다 새 행을 저장합니다. 중복 제출 방지는 구현하지 않았습니다.

## 다시 실행하기 / 종료하기

컨테이너를 정지하거나 다시 시작합니다. DB 초기화는 반복하지 않습니다.

```bash
docker compose stop
docker compose start
```

코드를 수정한 뒤에는 앱 이미지를 다시 빌드합니다.

```bash
docker compose up -d --build
```

상태와 로그 확인:

```bash
docker compose ps
docker compose logs -f app
```

컨테이너와 네트워크를 삭제하려면:

```bash
docker compose down
```

PostgreSQL 데이터는 이름 있는 볼륨에 유지됩니다.
현재 Grafana에는 별도 저장 볼륨이 없으므로 컨테이너를 삭제·재생성했다면
`uv run grafana/init.py`를 다시 실행해 대시보드를 등록하세요.
단순 정지·재시작은 Grafana 설정을 유지합니다.

## DB 직접 조회

```bash
docker compose exec postgres psql -U user -d fitness_assistant
```

```sql
SELECT id, question, answer, relevance, openai_cost, timestamp
FROM conversations
ORDER BY timestamp DESC
LIMIT 10;

SELECT id, conversation_id, feedback, timestamp
FROM feedback
ORDER BY timestamp DESC
LIMIT 10;
```

## 데이터 생성과 평가

아래 스크립트는 컨테이너가 아닌 로컬 가상환경에서 실행합니다.
`python -m`은 패키지 안의 모듈을 실행하는 옵션입니다.
기존 CSV가 있다면 생성 단계는 건너뛰세요.
생성·평가 스크립트는 같은 이름의 결과 CSV를 덮어씁니다.

| 명령 | 역할 | LLM 호출 |
| --- | --- | --- |
| `uv run python -m scripts.generate_data` | 운동 데이터 생성 → `data/data.csv` | 있음 |
| `uv run python -m scripts.generate_ground_truth` | 운동당 질문 2개 생성 → `data/ground-truth-retrieval.csv` | 운동당 1회 |
| `uv run python -m scripts.evaluate_retrieval` | Hit Rate·MRR 평가 및 랜덤 가중치 탐색 | 없음 |
| `uv run python -m scripts.demo` | 터미널에서 질문 한 건 실행 | 답변·판사 총 2회 |
| `uv run python -m scripts.evaluate_rag` | 질문 20개 답변 생성 및 평가 → `data/rag-eval-gpt-5.4-mini.csv` | 현재 질문당 3회, 총 60회 |

`evaluate_rag.py`는 앞 단계 실습의 별도 판사를 유지하고 있어,
현재는 `rag()` 내부 판사 외에 한 번 더 평가합니다.
실제 API 질문 처리는 답변 생성과 내부 판사의 두 번만 호출합니다.
터미널 실습·평가 스크립트는 API를 거치지 않으므로 대화 DB에 기록되지 않습니다.

운동 데이터를 새로 만들었다면 앱 이미지를 다시 빌드해 CSV를 반영하세요.

## 프로젝트 구조

```text
fitness-assistant/
├── app.py                       # POST /question, POST /feedback
├── fitness_assistant/
│   ├── __init__.py
│   ├── ingest.py                # CSV 읽기·메모리 검색 인덱스
│   ├── rag.py                   # 검색·답변·판사·사용량 계산
│   └── db.py                    # PostgreSQL 연결·초기화·저장
├── scripts/
│   ├── __init__.py
│   ├── generate_data.py
│   ├── generate_ground_truth.py
│   ├── evaluate_retrieval.py
│   ├── evaluate_rag.py
│   └── demo.py
├── grafana/
│   ├── init.py                  # 데이터소스·대시보드 등록
│   └── dashboard.json           # 패널·SQL 설정
├── data/                        # 운동·평가 CSV
├── Dockerfile
├── docker-compose.yaml
├── .dockerignore
├── .env.example
├── .python-version
├── pyproject.toml
└── uv.lock
```

## 참고 자료

- [LLM Zoomcamp 프로젝트 예제](https://github.com/DataTalksClub/llm-zoomcamp/tree/main/07-project-example)
- [완성 프로젝트의 Grafana 자료](https://github.com/alexeygrigorev/fitness-assistant/tree/main/grafana)
