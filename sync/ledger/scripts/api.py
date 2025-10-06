#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api.py - 记账 REST API (基于 FastAPI)
运行：
  uvicorn scripts.api:app --reload
测试：
  http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# --------------------
# 路径配置
# --------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
DATA_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

# --------------------
# FastAPI 初始化
# --------------------
app = FastAPI(title="Ledger API", description="简易记账系统接口", version="1.0.0")

# --------------------
# API Key 配置
# --------------------
API_KEY = "2686771314"

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True

# --------------------
# 中间件：拦截异常路径 & 限速
# --------------------
BLOCKED_PATHS = ["/cgi-bin", "/.env", "/admin", "/phpmyadmin", "/PRI"]
MAX_REQUESTS = 10
WINDOW_SECONDS = 60
access_log = defaultdict(list)  # {ip: [datetime,...]}

@app.middleware("http")
async def block_malicious_requests(request: Request, call_next):
    ip = request.client.host
    path = request.url.path

    # 异常路径拦截
    for blocked in BLOCKED_PATHS:
        if blocked in path:
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    # 限速
    now = datetime.now()
    access_log[ip] = [t for t in access_log[ip] if t > now - timedelta(seconds=WINDOW_SECONDS)]
    if len(access_log[ip]) >= MAX_REQUESTS:
        return JSONResponse(status_code=429, content={"detail": "Too many requests"})

    access_log[ip].append(now)

    response = await call_next(request)
    return response

# --------------------
# CSV 相关
# --------------------
def get_csv_path(month: str):
    return DATA_DIR / f"{month}.csv"

def ensure_csv(month: str):
    path = get_csv_path(month)
    if not path.exists():
        df = pd.DataFrame(columns=["date", "category", "amount", "type", "note"])
        df.to_csv(path, index=False)
    return path

# --------------------
# 数据模型
# --------------------
class Record(BaseModel):
    date: str
    category: str
    amount: float
    type: str = "expense"  # expense / income
    note: str = ""

# --------------------
# 公共接口
# --------------------
@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.get("/files")
def list_files():
    files = [f.name for f in DATA_DIR.glob("*.csv")]
    return {"files": files}

# --------------------
# 敏感接口（需 API Key）
# --------------------
@app.post("/add")
def add_record(record: Record, authorized: bool = Depends(verify_api_key)):
    month = record.date[:7]
    path = ensure_csv(month)
    df = pd.read_csv(path)
    new_record = pd.DataFrame([[record.date, record.category, record.amount, record.type, record.note]],
                              columns=df.columns)
    df = pd.concat([df, new_record], ignore_index=True)
    df.to_csv(path, index=False)
    return {"status": "success", "data": record.dict()}

@app.get("/report/{month}")
def generate_report(month: str, authorized: bool = Depends(verify_api_key)):
    path = ensure_csv(month)
    df = pd.read_csv(path)
    if df.empty:
        return {"month": month, "income": 0, "expense": 0, "net": 0, "summary": {}}

    income = df[df["type"]=="income"]["amount"].sum()
    expense = df[df["type"]=="expense"]["amount"].sum()
    net = income - expense
    summary = df[df["type"]=="expense"].groupby("category")["amount"].sum().to_dict()
    return {"month": month, "income": income, "expense": expense, "net": net, "summary": summary}

@app.get("/export/{month}")
def export_md(month: str, authorized: bool = Depends(verify_api_key)):
    path = ensure_csv(month)
    df = pd.read_csv(path)
    md = f"# {month} 月账单\n\n| 日期 | 类别 | 金额 | 类型 | 备注 |\n|------|------|------|------|------|\n"
    for _, row in df.iterrows():
        md += f"| {row['date']} | {row['category']} | {row['amount']} | {row['type']} | {row['note']} |\n"
    md += f"\n## 本月小结\n- 收入: {df[df['type']=='income']['amount'].sum()} 元\n"
    md += f"- 支出: {df[df['type']=='expense']['amount'].sum()} 元\n"
    md += f"- 净额: {df[df['type']=='income']['amount'].sum() - df[df['type']=='expense']['amount'].sum()} 元\n"

    md_path = REPORT_DIR / f"{month}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    return {"status": "success", "report_path": str(md_path)}
