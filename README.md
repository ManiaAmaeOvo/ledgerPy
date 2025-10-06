[中文说明 (Chinese README)](./README_zh.md)

# Ledger Fusion Pro - A Personal Ledger Dashboard

A modern, personal accounting web application built with FastAPI, Pandas, and Matplotlib. It brings the power of a command-line ledger tool (`ledger.py`) to your browser through a clean web interface and a REST API.

> ⚠️ **Important Note**: This project is designed for **personal, single-user** use, deployed on a private server or local network. It **does not have a multi-user account system or data isolation**. All data added via the web interface or API is written to the same set of CSV files. Do not deploy this as a public service to avoid unauthorized access or data tampering.

## ✨ Key Features

- **Web-Based Operations**: Add ledger entries and generate monthly or annual reports directly from your browser, no command line needed.
- **Dynamic Report Viewer**: View all generated Markdown reports in a beautiful, responsive web format.
- **Data Visualization**: Automatically generates charts for your reports, including category pie charts, expense trend lines, and more.
- **IP-Based Authorization**: Only devices (IP addresses) that have successfully authenticated with a password can access data modification and report generation features, preventing data pollution on public-facing servers.
- **REST API**: Provides endpoints protected by an API Key, allowing for easy integration with automation tools like iOS Shortcuts.
- **Simple Deployment**: Built on FastAPI for quick and easy deployment.

## 📂 Project Structure

```
ledger_project/
├── .gitignore
├── data/                  # CSV data files (ignored by git)
├── reports/               # Markdown reports and charts (ignored by git)
├── scripts/               # Core ledger logic
│   ├── __init__.py
│   ├── ledger.py
│   └── ledger_pro.py
├── static/                # Static files like CSS
│   └── style.css
├── templates/             # HTML template files
├── main.py                # The main FastAPI application file
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── README_zh.md           # The Chinese README
```

## 🚀 Quick Start

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/ManiaAmaeOvo/ledgerPy.git
    cd ledger_project
    ```

2.  **Create and Activate a Virtual Environment** (Recommended)
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate   # Windows
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration

1.  **API Key**: Open `main.py` and modify the `API_KEY = "apikeytemp"` variable to your own secret key.
2.  **Report Password**: The password logic is hardcoded in the `route_process_report_login` function in `main.py`. The format is `"pwdtemp" + suffix`, where the suffix is the month for monthly reports (e.g., `09` for September) or the last two digits of the year for annual reports (e.g., `25` for 2025).

## 🛠️ How to Use

First, start the application server from the project's root directory:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```
- **Web Interface**: Open your browser and navigate to `http://[YOUR_SERVER_IP]:8001`.
- **API Docs**: Navigate to `http://[YOUR_SERVER_IP]:8001/docs` to view and test the API.

### Adding Records & Exporting Reports

There are three primary ways to interact with the application:

#### 1. Via the Web UI (Recommended)

This is the most user-friendly method.
1.  **Authorize Your Device**: To begin, you must first authorize your device's IP address. Do this by clicking on any report on the homepage and entering the correct password (e.g., `pwdtemp09` for a September report). Upon success, your IP is temporarily whitelisted.
2.  **Access the Manage Page**: Return to the homepage and click the large "✨ Manage Ledger (Add/Export)" button at the top.
3.  **Add a Record**: Fill out the "Add New Record" form with the date, category, amount, and other details. Clicking "Add Record" will save the entry and automatically update that month's report.
4.  **Export a Report**: In the "Export/Update Report" form, enter a specific month (`YYYY-MM`) or year (`YYYY`) and click "Generate/Update Report" to create or refresh the corresponding report file.

#### 2. Via the Command Line

You can directly use the `ledger.py` script for local operations.
-   **Add a lunch record for today**:
    ```bash
    python scripts/ledger.py add 1 Dining 25.50 "Lunch with colleagues"
    ```
-   **Export a monthly report**:
    ```bash
    python scripts/ledger.py export 2025-10
    ```
-   **Export an annual report**:
    ```bash
    python scripts/ledger.py export --year 2025
    ```

#### 3. Via cURL (API)

For automation scripts or advanced users, you can call the API directly.
-   **Add a new record** (Remember to replace `YOUR_SERVER_IP` and `YOUR_API_KEY`):
    ```bash
    curl -X 'POST' \
      'http://YOUR_SERVER_IP:8001/api/add' \
      -H 'accept: application/json' \
      -H 'X-API-Key: YOUR_API_KEY' \
      -H 'Content-Type: application/json' \
      -d '{
        "date": "2025-10-06",
        "category": "Transportation",
        "amount": 18.0,
        "type": "expense",
        "note": "Subway"
      }'
    ```
-   **Export a monthly report**:
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