"""강의 완성 프로젝트 grafana/init.py를 현재 Compose 환경에 맞춘 초기화 코드."""
import base64
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000").rstrip("/")
GRAFANA_USER = os.getenv("GRAFANA_ADMIN_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")
DATASOURCE_UID = "fitness-postgres"
DATASOURCE_TYPE = "grafana-postgresql-datasource"


def grafana_api(method, path, payload=None):
    credentials = base64.b64encode(
        f"{GRAFANA_USER}:{GRAFANA_PASSWORD}".encode()
    ).decode()
    request = Request(
        GRAFANA_URL + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def create_or_update_datasource():
    # DB 주소는 이 스크립트가 아니라 Grafana 컨테이너를 기준으로 합니다.
    payload = {
        "uid": DATASOURCE_UID,
        "name": "Fitness PostgreSQL",
        "type": DATASOURCE_TYPE,
        "access": "proxy",
        "url": f"{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}",
        "user": os.getenv("POSTGRES_USER", "user"),
        "isDefault": True,
        "jsonData": {
            "database": os.getenv("POSTGRES_DB", "fitness_assistant"),
            "sslmode": "disable",
            "postgresVersion": 1600,
            "timescaledb": False,
        },
        "secureJsonData": {"password": os.getenv("POSTGRES_PASSWORD", "password")},
    }
    path = f"/api/datasources/uid/{DATASOURCE_UID}"
    try:
        grafana_api("GET", path)
    except HTTPError as error:
        if error.code != 404:
            raise
        grafana_api("POST", "/api/datasources", payload)
    else:
        grafana_api("PUT", path, payload)
    print("PostgreSQL 데이터소스 등록 완료")


def set_datasource(value):
    # 패널과 각 쿼리의 데이터소스를 모두 같은 UID로 바꿉니다.
    if isinstance(value, dict):
        datasource = value.get("datasource")
        if isinstance(datasource, dict) and datasource.get("type") in (
            "postgres", DATASOURCE_TYPE
        ):
            value["datasource"] = {"type": DATASOURCE_TYPE, "uid": DATASOURCE_UID}
        for child in value.values():
            set_datasource(child)
    elif isinstance(value, list):
        for child in value:
            set_datasource(child)


def create_dashboard():
    path = Path(__file__).with_name("dashboard.json")
    dashboard = json.loads(path.read_text())
    set_datasource(dashboard)
    result = grafana_api("POST", "/api/dashboards/db", {
        "dashboard": dashboard,
        "overwrite": True,
        "message": "Fitness Assistant dashboard setup",
    })
    print("대시보드 등록 완료:", GRAFANA_URL + result["url"])


def main():
    create_or_update_datasource()
    create_dashboard()


if __name__ == "__main__":
    main()
