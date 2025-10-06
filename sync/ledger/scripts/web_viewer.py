# web_viewer.py
from flask import Flask, render_template_string, request, send_from_directory, abort, redirect, url_for
from pathlib import Path
import os
import datetime

app = Flask(__name__)

# 继承 ledger.py 中的一些常量
from ledger import REPORT_DIR, DATA_DIR

# HTML 模板，用于渲染目录页和报告页
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>账单报告目录</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 800px; margin: auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #0056b3; margin-bottom: 30px; }
        ul { list-style: none; padding: 0; }
        li { background: #e9ecef; margin-bottom: 10px; padding: 15px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }
        li a { text-decoration: none; color: #007bff; font-weight: bold; font-size: 1.1em; }
        li a:hover { text-decoration: underline; color: #0056b3; }
        .no-reports { text-align: center; color: #666; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧾 账单报告目录</h1>
        {% if reports %}
        <ul>
            {% for report in reports %}
            <li><a href="{{ url_for('view_report', month_or_year=report.strip('.md')) }}">{{ report.replace('_annual', ' 年度').replace('.md', '') }}</a></li>
            {% endfor %}
        </ul>
        {% else %}
        <p class="no-reports">暂无报告可查看。</p>
        {% endif %}
    </div>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>请输入密码</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; margin: 20px; background-color: #f4f4f4; color: #333; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .login-container { background: #fff; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; max-width: 400px; width: 100%; }
        h2 { color: #0056b3; margin-bottom: 25px; }
        .error { color: red; margin-bottom: 15px; }
        label { display: block; text-align: left; margin-bottom: 8px; font-weight: bold; }
        .password-wrapper { position: relative; }
        input[type="password"], input[type="text"] { width: calc(100% - 22px); padding: 10px; margin-bottom: 20px; border: 1px solid #ccc; border-radius: 4px; font-size: 1em; }
        .toggle-password { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); cursor: pointer; width: 22px; height: 22px; fill: #666; }
        button { background-color: #007bff; color: white; padding: 12px 25px; border: none; border-radius: 4px; cursor: pointer; font-size: 1.1em; transition: background-color 0.3s ease; }
        button:hover { background-color: #0056b3; }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>🔒 请输入密码以查看 {{ month_or_year }} 的报告</h2>
        {% if error %}
        <p class="error">{{ error }}</p>
        {% endif %}
        <form method="POST" action="{{ url_for('view_report', month_or_year=month_or_year) }}">
            <label for="password">密码:</label>
            <div class="password-wrapper">
                <input type="password" id="password" name="password" required>
                <svg class="toggle-password" onclick="togglePassword()" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path id="eye-icon" d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zm0 
                    12.5c-2.76 0-5-2.24-5-5s2.24-5 5-5 
                    5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 
                    0-3 1.34-3 3s1.34 3 3 3 
                    3-1.34 3-3-1.34-3-3-3z"/>
                </svg>
            </div>
            <button type="submit">提交</button>
        </form>
    </div>
    <script>
        function togglePassword() {
            var pwd = document.getElementById("password");
            var eye = document.getElementById("eye-icon");
            if (pwd.type === "password") {
                pwd.type = "text";
                // 闭眼图标
                eye.setAttribute("d", "M12 4.5C7 4.5 2.73 7.61 1 12c.71 1.81 1.93 3.36 3.5 4.54L2.21 18.83l1.41 1.41 18-18-1.41-1.41-2.3 2.3C16.36 5.02 14.25 4.5 12 4.5zm0 12.5c-2.76 0-5-2.24-5-5 0-.83.21-1.61.58-2.29l1.49 1.49C9 11.45 9 11.72 9 12c0 1.66 1.34 3 3 3 .28 0 .55 0 .8-.08l1.49 1.49c-.68.37-1.46.59-2.29.59z");
            } else {
                pwd.type = "password";
                // 开眼图标
                eye.setAttribute("d", "M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zm0 12.5c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z");
            }
        }
    </script>
</body>
</html>
"""


REPORT_VIEW_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ month_or_year }} 账单报告</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 900px; margin: auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1, h2, h3, h4 { color: #0056b3; margin-top: 1.5em; margin-bottom: 0.8em; }
        h1 { text-align: center; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 1.5em; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        img { max-width: 100%; height: auto; display: block; margin: 1.5em auto; border: 1px solid #eee; box-shadow: 0 1px 5px rgba(0,0,0,0.05); }
        hr { border: 0; height: 1px; background: #eee; margin: 2em 0; }
        pre { background: #f8f8f8; padding: 15px; border-radius: 5px; overflow-x: auto; font-family: monospace; }
        .download-buttons { text-align: center; margin-top: 30px; }
        .download-buttons a { display: inline-block; background-color: #28a745; color: white; padding: 12px 25px; border-radius: 5px; text-decoration: none; margin: 0 10px; transition: background-color 0.3s ease; }
        .download-buttons a:hover { background-color: #218838; }
        .back-link { display: block; text-align: center; margin-top: 30px; }
        .back-link a { color: #007bff; text-decoration: none; font-weight: bold; }
        .back-link a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        {{ report_content | safe }}

        <div class="download-buttons">
            <a href="{{ url_for('download_file', type='md', month_or_year=month_or_year) }}">下载 Markdown 报告</a>
            <a href="{{ url_for('download_file', type='csv', month_or_year=month_or_year) }}">下载 CSV 数据</a>
        </div>
        <div class="back-link">
            <a href="{{ url_for('index') }}">返回目录</a>
        </div>
    </div>
</body>
</html>
"""

import markdown # 添加这一行

# ...

def render_markdown_to_html(md_content, base_image_url="/reports_static/"):
    """
    将 Markdown 内容转换为 HTML，并处理图片路径。
    """
    # 替换 Markdown 图片语法为 Flask 静态文件可访问的路径
    import re
    def replace_image_path(match):
        alt_text = match.group(1)
        image_name = match.group(2)
        return f'![{alt_text}]({base_image_url}{image_name})' # 暂时转换，让markdown库处理

    md_content_with_fixed_images = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_image_path, md_content)
    
    # 使用 markdown 库进行渲染
    html_content = markdown.markdown(md_content_with_fixed_images, extensions=['tables', 'fenced_code'])
    
    return html_content

@app.route('/ledger_md/')
def index():
    """显示所有可用的报告链接"""
    reports = []
    for f in REPORT_DIR.iterdir():
        if f.suffix == ".md" and not f.name.startswith('.'): # 排除隐藏文件
            reports.append(f.name)
    
    # 对报告进行排序，例如按年份月份
    reports.sort(key=lambda x: (x.split('_')[0] if 'annual' in x else x.split('.')[0]), reverse=True) # 年度报告优先或按年月倒序

    return render_template_string(INDEX_TEMPLATE, reports=reports)

@app.route('/ledger_md/report/<month_or_year>', methods=['GET', 'POST'])
def view_report(month_or_year):
    """
    显示指定月份或年度的报告。
    通过密码验证。
    """
    md_file = REPORT_DIR / f"{month_or_year}.md"
    csv_file = DATA_DIR / f"{month_or_year}.csv" # 尝试查找对应的CSV文件，对于年度报告需要特殊处理

    if not md_file.exists():
        abort(404, description="报告不存在。")

    # 生成密码
    if '_annual' in month_or_year: # 年度报告
        password_suffix = month_or_year.split('_')[0][2:] # 获取年份后两位，例如 2025_annual -> 25
    else: # 月度报告
        password_suffix = month_or_year.split('-')[1] # 获取月份，例如 2025-09 -> 09
        
    correct_password = f"iaukiaow{password_suffix}"

    error = None
    if request.method == 'POST':
        user_password = request.form.get('password')
        if user_password == correct_password:
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # Flask 可以直接服务静态文件，但对于报告中的图片路径，需要特别处理
            # 报告中的图片路径是相对路径，例如 ![](<month>_pie.png)
            # 我们需要将这些相对路径转换为 /reports_static/<image_name>
            html_content = render_markdown_to_html(md_content, base_image_url=url_for('reports_static', filename=''))
            
            return render_template_string(REPORT_VIEW_TEMPLATE, 
                                          month_or_year=month_or_year, 
                                          report_content=html_content)
        else:
            error = "密码错误，请重试。"
    
    return render_template_string(LOGIN_TEMPLATE, month_or_year=month_or_year, error=error)

@app.route('/ledger_md/download/<type>/<month_or_year>')
def download_file(type, month_or_year):
    """
    下载对应的 Markdown 报告或 CSV 数据。
    注意：这里假设用户已经通过了密码验证，或者直接点击下载按钮时无需再次验证。
    为了简化，我们不对下载操作进行密码验证，但实际生产环境中可能需要。
    """
    if type == 'md':
        file_path = REPORT_DIR / f"{month_or_year}.md"
        if not file_path.exists():
            abort(404, description="Markdown 报告文件不存在。")
        return send_from_directory(REPORT_DIR, f"{month_or_year}.md", as_attachment=True)
    elif type == 'csv':
        # 对于多月或年度报告，CSV文件可能不止一个，这里需要更复杂的逻辑
        # 简单处理：如果是年度报告，则没有直接的同名csv
        if '_annual' in month_or_year:
            # 可以考虑打包所有相关月份的CSV
            abort(404, description="年度报告没有单一的CSV文件，请在目录中选择月份下载。")

        file_path = DATA_DIR / f"{month_or_year}.csv"
        if not file_path.exists():
            abort(404, description="CSV 数据文件不存在。")
        return send_from_directory(DATA_DIR, f"{month_or_year}.csv", as_attachment=True)
    else:
        abort(400, description="无效的下载类型。")

# 服务 REPORT_DIR 下的图片和其他静态文件
@app.route('/ledger_md/reports_static/<path:filename>')
def reports_static(filename):
    return send_from_directory(REPORT_DIR, filename)

if __name__ == '__main__':
    # 确保报告和数据目录存在
    REPORT_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=8001)
