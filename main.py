import markdown
import re
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException, Header, Form, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import pandas as pd # 引入 pandas 以处理空 CSV 异常
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# --- 1. 导入你的核心逻辑 ---
from scripts import ledger, ledger_pro

# --- 2. 配置与初始化 ---
BASE_DIR = ledger.BASE_DIR
DATA_DIR = ledger.DATA_DIR
REPORT_DIR = ledger.REPORT_DIR

class IPAuthorizationError(Exception):
    pass

# 已授权的ip
AUTHORIZED_IPS = set()

app = FastAPI(title="Ledger Fusion Pro")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/reports_static", StaticFiles(directory=REPORT_DIR), name="reports_static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals['now'] = datetime.now

@app.exception_handler(IPAuthorizationError)
async def ip_authorization_exception_handler(request: Request, exc: IPAuthorizationError):
    """
    当 verify_ip_authorization 抛出 IPAuthorizationError 时，
    这个处理器会被激活，并返回一个重定向响应。
    """
    message = "❌ 访问被拒绝！请先通过查看任一报告的密码来授权您的设备。"
    return RedirectResponse(
        url=f"/?message={message}", 
        status_code=status.HTTP_303_SEE_OTHER
    )

# --- 3. Pydantic 数据模型 ---
class Record(BaseModel):
    date: str = datetime.now().strftime("%Y-%m-%d")
    category: str
    amount: float
    type: str = "expense"
    note: str = ""

# --- 4. 辅助函数 ---
def render_markdown_to_html(md_content: str) -> str:
    def replace_image_path(match):
        alt_text, image_name = match.groups()
        return f'<img src="/reports_static/{image_name}" alt="{alt_text}" class="report-image">'
    md_content_with_fixed_images = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_image_path, md_content)
    return markdown.markdown(md_content_with_fixed_images, extensions=['tables', 'fenced_code'])

def get_all_categories() -> list:
    """重写 ledger.list_categories() 以返回列表而不是打印"""
    categories = set()
    for csv_file in DATA_DIR.glob("*.csv"):
        try:
            df = pd.read_csv(csv_file)
            if "category" in df.columns:
                categories.update(df["category"].dropna().unique())
        except (pd.errors.EmptyDataError, FileNotFoundError):
            continue
    return sorted(list(categories))

# 🆕 2. 修改依赖项，使其在验证失败时抛出异常
async def verify_ip_authorization(request: Request):
    """
    检查 IP 是否已授权。如果未授权，则抛出 IPAuthorizationError 异常。
    """
    if request.client.host not in AUTHORIZED_IPS:
        raise IPAuthorizationError()

# --- 5. Web 界面路由 ---

@app.get("/", response_class=HTMLResponse)
async def route_index(request: Request, message: str = None):
    reports_info = []
    for f in sorted(REPORT_DIR.iterdir(), reverse=True):
        if f.suffix == ".md" and not f.name.startswith('.'):
            reports_info.append({
                "name": f.name.replace('.md', ''),
                "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            })
    return templates.TemplateResponse("index.html", {
        "request": request,
        "reports": reports_info,
        "message": message # 传递消息给模板
    })

@app.get("/manage", response_class=HTMLResponse, dependencies=[Depends(verify_ip_authorization)])
async def route_manage(request: Request, message: str = None):
    """🆕 显示管理页面的路由"""
    return templates.TemplateResponse("manage.html", {
        "request": request,
        "categories": get_all_categories(),
        "today_date": datetime.now().strftime("%Y-%m-%d"),
        "message": message
    })

@app.post("/add-record", dependencies=[Depends(verify_ip_authorization)])
async def route_add_record(
    date: str = Form(...),
    category: str = Form(...),
    amount: float = Form(...),
    type: str = Form(...),
    note: str = Form("")
):
    """🆕 处理添加记录表单提交的路由"""
    try:
        ledger.add_record(date, category, amount, type, note)
        # 自动更新当月报告
        month = date[:7]
        ledger.export_md(month)
        message = f"✅ 添加成功！记录已保存，{month} 的报告已更新。"
    except Exception as e:
        message = f"❌ 添加失败: {e}"
    
    return RedirectResponse(
        url=f"/manage?message={message}", 
        status_code=status.HTTP_303_SEE_OTHER
    )

@app.post("/export-report", dependencies=[Depends(verify_ip_authorization)])
async def route_export_report(month: str = Form(None), year: str = Form(None)):
    """🆕 处理导出报告表单提交的路由"""
    if not month and not year:
        message = "❌ 导出失败: 请至少提供月份或年份。"
        return RedirectResponse(url=f"/manage?message={message}", status_code=status.HTTP_303_SEE_OTHER)
    
    try:
        if year:
            months_in_year = ledger_pro.get_months_in_year(year)
            ledger_pro.export_multi_month_md(months_in_year, year=year)
            message = f"✅ 导出成功！{year} 年的年度报告已生成。"
        else: # month
            ledger.export_md(month)
            message = f"✅ 导出成功！{month} 的月度报告已生成。"
    except Exception as e:
        message = f"❌ 导出失败: {e}"

    return RedirectResponse(url=f"/manage?message={message}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/report/{month_or_year}", response_class=HTMLResponse)
async def route_view_report_login(request: Request, month_or_year: str, error: str = None):
    return templates.TemplateResponse("login.html", {
        "request": request, "month_or_year": month_or_year, "error": error
    })

@app.post("/report/{month_or_year}", response_class=HTMLResponse)
async def route_process_report_login(request: Request, month_or_year: str, password: str = Form(...)):
    md_file = REPORT_DIR / f"{month_or_year}.md"
    if not md_file.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")
    if '_annual' in month_or_year:
        password_suffix = month_or_year.split('_')[0][2:]
    else:
        password_suffix = month_or_year.split('-')[1]
    correct_password = f"pwdtemp{password_suffix}"
    if password != correct_password:
        return templates.TemplateResponse("login.html", {
            "request": request, "month_or_year": month_or_year, "error": "密码错误，请重试。"
        }, status_code=401)
    AUTHORIZED_IPS.add(request.client.host)
    print(f"授权 IP: {request.client.host}。当前授权列表: {AUTHORIZED_IPS}") # 在服务器后台打印日志
    md_content = md_file.read_text(encoding='utf-8')
    html_content = render_markdown_to_html(md_content)
    return templates.TemplateResponse("report_view.html", {
        "request": request, "month_or_year": month_or_year, "report_content": html_content
    })

@app.get("/download/{file_type}/{month_or_year}")
async def route_download_file(file_type: str, month_or_year: str):
    if file_type == 'md':
        file_path = REPORT_DIR / f"{month_or_year}.md"
    elif file_type == 'csv':
        file_path = DATA_DIR / f"{month_or_year.split('_')[0]}.csv"
    else:
        raise HTTPException(status_code=400, detail="无效的文件类型")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file_path, filename=file_path.name)

# --- 6. REST API 路由 (保持不变) ---
# ... (此部分代码省略，与上一版本相同) ...
API_KEY = "apikeytemp"
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="无效的 API Key")

@app.post("/api/add", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_key)])
async def api_add_record(record: Record):
    try:
        ledger.add_record(record.date, record.category, record.amount, record.type, record.note)
        month = record.date[:7]
        ledger.export_md(month)
        return {"status": "success", "data": record.dict(), "message": f"记录已添加，{month} 的报告已更新。"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时发生错误: {e}")

@app.post("/api/export", dependencies=[Depends(verify_api_key)])
async def api_export_report(month: str = Form(None), year: str = Form(None)):
    if not month and not year:
        raise HTTPException(status_code=400, detail="必须提供 'month' 或 'year' 参数。")
    try:
        if year:
            months_in_year = ledger_pro.get_months_in_year(year)
            ledger_pro.export_multi_month_md(months_in_year, year=year)
            message = f"年度报告 {year}_annual.md 已成功导出。"
        else:
            ledger.export_md(month)
            message = f"月度报告 {month}.md 已成功导出。"
        return {"status": "success", "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出报告时发生错误: {e}")


# --- 7. 启动应用 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)