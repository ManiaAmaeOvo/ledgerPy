# Ledger Fusion Pro - 个人账单仪表盘

一个基于 FastAPI、Pandas 和 Matplotlib 构建的现代化个人记账 Web 应用。它通过简洁的 Web 界面和 REST API，将命令行的账单工具 (`ledger.py`) 的强大功能带入浏览器。

> ⚠️ **重要提示**：本项目为**个人使用**设计，部署在个人服务器或本地网络。它**没有内置多用户账户系统或数据隔离**。所有通过 Web 界面或 API 添加的数据都将写入同一组 CSV 文件中。请勿将其作为公共服务部署，以免数据被他人访问或篡改。

## ✨ 主要功能

- **Web 操作界面**：无需命令行，直接在浏览器中添加账单记录、生成月度或年度报告。
- **动态报告查看**：以美观、响应式的网页格式查看所有生成的 Markdown 账单报告。
- **数据可视化**：自动为报告生成分类饼图、支出走势图等多种图表。
- **IP 授权访问**：只有通过密码验证的设备（IP地址）才能访问数据修改和报告生成功能，防止公开访问时的数据污染。
- **REST API**：提供带 API Key 保护的接口，方便与其他自动化工具（如 iOS 快捷指令）集成。
- **简单部署**：基于 FastAPI，部署简单快速。

## 📂 项目结构

```
ledger_project/
├── .gitignore
├── data/                  # CSV 数据文件 (已被忽略)
├── reports/               # Markdown 报告和图表 (已被忽略)
├── scripts/               # 核心记账逻辑
│   ├── __init__.py
│   ├── ledger.py
│   └── ledger_pro.py
├── static/                # CSS 等静态文件
├── templates/             # HTML 模板文件
├── main.py                # FastAPI 应用主文件
└── requirements.txt       # Python 依赖
```

## 🚀 快速开始

1.  **克隆仓库**
    ```bash
    git clone https://github.com/ManiaAmaeOvo/ledgerPy.git
    cd ledger_project
    ```

2.  **创建并激活虚拟环境** (推荐)
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate   # Windows
    ```

3.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ 配置

1.  **API Key**: 打开 `main.py` 文件，找到 `API_KEY = "apikeytemp"` 并修改为你自己的密钥。
2.  **报告密码**: 密码逻辑硬编码在 `main.py` 的 `route_process_report_login` 函数中。格式为 `"pwdtemp" + 后缀`，后缀对月度报告是月份（如`09`），对年度报告是年份的后两位（如`25`）。

## 🛠️ 如何使用

首先，启动服务器。在项目根目录下运行：
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```
- **Web 界面**: 打开浏览器访问 `http://[你的服务器IP]:8001`。
- **API 文档**: 访问 `http://[你的服务器IP]:8001/docs` 查看并测试 API。

### 添加记录与导出报告

有三种方式可以与应用交互：

#### 1. 通过 Web 界面 (推荐)

这是最直观的方式。
1.  **授权设备**：首次使用时，你需要先点击首页任意一个报告，输入正确的密码（例如 `pwdtemp09`）进行查看。成功后，你的设备 IP 将被临时授权。
2.  **访问管理页面**：回到首页，点击顶部的“✨ 管理账单”按钮。
3.  **添加记录**：在“添加新记录”表单中填写日期、类别、金额等信息，然后点击“添加记录”。提交成功后，当月的报告会自动更新。
4.  **导出报告**：在“导出/更新报告”表单中，输入你想要导出的月份（`YYYY-MM`）或年份（`YYYY`），然后点击“生成/更新报告”。

#### 2. 通过命令行

你也可以直接使用项目自带的 `ledger.py` 脚本。
-   **添加一条今天的午餐记录**：
    ```bash
    python scripts/ledger.py add 1 餐饮 25.50 "和同事的午餐"
    ```
-   **导出一个月度报告**：
    ```bash
    python scripts/ledger.py export 2025-10
    ```
-   **导出一个年度报告**：
    ```bash
    python scripts/ledger.py export --year 2025
    ```

#### 3. 通过 cURL (API)

对于自动化脚本或高级用户，可以直接调用 API。
-   **添加一条记录** (记得替换 `YOUR_SERVER_IP` 和 `YOUR_API_KEY`):
    ```bash
    curl -X 'POST' \
      'http://YOUR_SERVER_IP:8001/api/add' \
      -H 'accept: application/json' \
      -H 'X-API-Key: YOUR_API_KEY' \
      -H 'Content-Type: application/json' \
      -d '{
        "date": "2025-10-06",
        "category": "交通",
        "amount": 18.0,
        "type": "expense",
        "note": "地铁"
      }'
    ```
-   **导出一个月度报告**:
    ```bash
    curl -X 'POST' \
      'http://YOUR_SERVER_IP:8001/api/export' \
      -H 'accept: application/json' \
      -H 'X-API-Key: YOUR_API_KEY' \
      -H 'Content-Type: application/x-www-form-urlencoded' \
      -d 'month=2025-10'
    ```

---

## License
This project is licensed under the [MIT License](LICENSE).