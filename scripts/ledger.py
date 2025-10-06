#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ledger.py - 简易记账命令行工具
用法示例：
  python ledger.py add 2025-09-01 餐饮 25 午饭
  python ledger.py add 2025-09-01 薪水 5000 --type income
  python ledger.py report 2025-09
  python ledger.py export 2025-09
  python ledger.py report --months 2025-01 2025-03 2025-05
  python ledger.py report --range 2025-01 2025-03
  python ledger.py report --year 2025
  python ledger.py export --range 2025-01 2025-03
  python ledger.py export --year 2025
  python ledger.py category
"""

import argparse
import argcomplete
import pandas as pd
from pathlib import Path
import datetime
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 导入 ledger_pro.py (假设此文件存在并包含多月/年度处理逻辑)
try:
    from . import ledger_pro
except ImportError:
    print("⚠️ 警告: 未找到 ledger_pro.py 文件。多月/年度报告和导出功能将无法使用。")
    class MockLedgerPro:
        def get_months_in_range(self, start, end):
            raise NotImplementedError("ledger_pro.py is missing.")
        def get_months_in_year(self, year):
            raise NotImplementedError("ledger_pro.py is missing.")
        def generate_multi_month_report(self, months):
            print("❌ 无法生成多月报告，因为 ledger_pro.py 不可用。")
        def export_multi_month_md(self, months, year=None):
            print("❌ 无法导出多月/年度报告，因为 ledger_pro.py 不可用。")
    ledger_pro = MockLedgerPro()


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
DATA_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

# 设置中文字体为系统字体（Mac 上一般是 "Songti SC" 或 "Heiti SC"）
# 这应该在导入 matplotlib 后尽早设置
rcParams['font.sans-serif'] = ['Songti SC', 'Arial Unicode MS'] # 增加备用字体
rcParams['axes.unicode_minus'] = False                       # 正确显示负号

def get_csv_path(month: str):
    return DATA_DIR / f"{month}.csv"

def ensure_csv(month: str):
    path = get_csv_path(month)
    if not path.exists():
        df = pd.DataFrame(columns=["date", "category", "amount", "type", "note"])
        df.to_csv(path, index=False)
    return path

def add_record(date, category, amount, record_type="expense", note=""):
    """新增记录，可为收入或支出"""
    month = date[:7]
    path = ensure_csv(month)
    df = pd.read_csv(path)
    new_record = pd.DataFrame([[date, category, float(amount), record_type, note]],
                              columns=df.columns)
    df = pd.concat([df, new_record], ignore_index=True)
    df.to_csv(path, index=False)
    print("✅ 已添加:", new_record.to_dict(orient="records")[0])

def generate_report(month):
    """生成月度汇总（收入/支出/净额）"""
    path = ensure_csv(month)
    df = pd.read_csv(path)
    if df.empty:
        print(f"⚠️ {month} 本月没有记录")
        return

    income = df[df["type"]=="income"]["amount"].sum()
    expense = df[df["type"]=="expense"]["amount"].sum()
    net = income - expense

    print(f"\n📊 {month} 收入/支出汇总:")
    print("收入:", income, "元")
    print("支出:", expense, "元")
    print("净额:", net, "元")
    print("\n各类别支出汇总:")
    summary = df[df["type"]=="expense"].groupby("category")["amount"].sum().sort_values(ascending=False)
    if summary.empty:
        print("无支出记录。")
    else:
        print(summary.to_string()) # 使用to_string避免截断

def export_md(month):
    """导出 Markdown 报告，并生成饼图 & 累计支出折线图 & 每日支出折线图 & 每周汇总"""
    
    path = ensure_csv(month)
    df = pd.read_csv(path)

    if df.empty:
        print(f"⚠️ {month} 本月没有记录，无法生成报告。")
        return

    # 确保日期列是 datetime 类型
    df["date"] = pd.to_datetime(df["date"])

    pie_path = None
    line_path = None
    daily_line_path = None
    weekly_pie_paths = []
    weekly_expense_md = ""

    # ========= 每周汇总功能开始 =========
    # 确保只有在处理单个月份时才生成每周汇总，否则多月报告的周数会混乱
    # 这里的判断是检查 df 中是否存在多个月份，但对于单月报告，我们知道它只有一个月份
    # 因此，这个条件 `len(df["date"].dt.month.unique()) > 1` 应该在多月导出时阻止每周汇总
    # 现修改为：只要是调用 export_md(month) 就生成，因为这个函数是为单个月份设计的。
    
    if not df.empty:
        # 获取该月的第一天和最后一天
        start_of_month = df["date"].min().replace(day=1)
        end_of_month = df["date"].max().replace(day=1) + pd.DateOffset(months=1) - pd.DateOffset(days=1)
        # 确保 end_of_month 不超过实际数据中的最大日期（如果数据不完整月）
        end_of_month = min(end_of_month, df["date"].max())


        # 循环生成每周汇总
        week_num = 1
        current_week_start = start_of_month
        
        while current_week_start <= end_of_month:
            current_week_end = current_week_start + pd.DateOffset(days=6) # 一周是7天，从current_week_start算起6天后是这周的最后一天
            # 确保周结束日期不超过月末
            if current_week_end > end_of_month:
                current_week_end = end_of_month

            weekly_df = df[(df["date"] >= current_week_start) & (df["date"] <= current_week_end) & (df["type"] == "expense")]
            weekly_expense_summary = weekly_df.groupby("category")["amount"].sum().sort_values(ascending=False)

            if not weekly_expense_summary.empty:
                weekly_expense_md += f"\n### 第 {week_num} 周支出汇总 ({current_week_start.strftime('%Y-%m-%d')} 至 {current_week_end.strftime('%Y-%m-%d')})\n\n"
                weekly_expense_md += f"| 类别 | 金额 |\n|------|------|\n"
                for category, amount in weekly_expense_summary.items():
                    weekly_expense_md += f"| {category} | {amount:.2f} |\n"
                weekly_expense_md += f"**本周总支出:** {weekly_expense_summary.sum():.2f} 元\n\n"

                # 生成每周饼图
                plt.figure(figsize=(6,6))
                plt.pie(weekly_expense_summary, labels=weekly_expense_summary.index, autopct="%1.1f%%", startangle=140)
                plt.title(f"{month} 第 {week_num} 周各类别支出占比")
                weekly_pie_path = REPORT_DIR / f"{month}_week{week_num}_pie.png"
                plt.savefig(weekly_pie_path, bbox_inches="tight")
                plt.close()
                weekly_pie_paths.append(weekly_pie_path)
                weekly_expense_md += f"![第 {week_num} 周支出分类饼图]({weekly_pie_path.name})\n\n"
            
            # 移动到下一周的开始
            current_week_start = current_week_end + pd.DateOffset(days=1)
            week_num += 1
    # ========= 每周汇总功能结束 =========

    # 生成饼图（支出分类占比）
    expense_summary = df[df["type"]=="expense"].groupby("category")["amount"].sum()
    if not expense_summary.empty:
        plt.figure(figsize=(6,6))
        plt.pie(expense_summary, labels=expense_summary.index, autopct="%1.1f%%", startangle=140)
        plt.title(f"{month} 各类别支出占比")
        pie_path = REPORT_DIR / f"{month}_pie.png"
        plt.savefig(pie_path, bbox_inches="tight")
        plt.close()
    
    # 生成累计支出折线图
    # 将日期转换为日期对象以便正确排序和分组
    df_expense = df[df["type"]=="expense"].copy()
    if not df_expense.empty:
        df_expense["date"] = df_expense["date"].dt.date
        daily_expense = df_expense.groupby("date")["amount"].sum().sort_index()
        
        if not daily_expense.empty:
            plt.figure(figsize=(10,5))
            plt.plot(daily_expense.index, daily_expense.cumsum(), marker="o")
            plt.title(f"{month} 累计支出走势")
            plt.xlabel("日期")
            plt.ylabel("累计金额")
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            line_path = REPORT_DIR / f"{month}_line.png"
            plt.savefig(line_path, bbox_inches="tight")
            plt.close()

            # 生成每日支出折线图
            plt.figure(figsize=(10,5))
            plt.plot(daily_expense.index, daily_expense, marker="s", linestyle="-", color="orange")
            plt.title(f"{month} 每日支出走势")
            plt.xlabel("日期")
            plt.ylabel("每日支出金额")
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            daily_line_path = REPORT_DIR / f"{month}_daily_line.png"
            plt.savefig(daily_line_path, bbox_inches="tight")
            plt.close()

    # 构造 Markdown 内容
    md = f"# {month} 月账单\n\n"
    
    # 插入每周汇总内容
    md += weekly_expense_md

    md += f"# 月总账单\n\n"

    md += f"| 日期 | 类别 | 金额 | 类型 | 备注 |\n|------|------|------|------|------|\n"
    for _, row in df.iterrows():
        # 注意：这里row['date']已经是datetime对象，需要格式化
        md += f"| {row['date'].strftime('%Y-%m-%d')} | {row['category']} | {row['amount']:.2f} | {row['type']} | {row['note']} |\n"

    income_total = df[df['type']=='income']['amount'].sum()
    expense_total = df[df['type']=='expense']['amount'].sum()
    net_total = income_total - expense_total

    md += f'\n## 各类支出汇总： \n'
    md += f"| 类别 | 金额 |\n|------|------|\n"
    for category, amount in expense_summary.items():
        md += f"|{category}|{amount:.2f}|\n"

    md += f"\n## 本月小结\n- 收入: {income_total:.2f} 元\n"
    md += f"- 支出: {expense_total:.2f} 元\n"
    md += f"- 净额: {net_total:.2f} 元\n"

    # 插入图表
    if pie_path:
        md += f"\n## 支出分类饼图\n![]({pie_path.name})\n"
    if line_path:
        md += f"\n## 累计支出曲线\n![]({line_path.name})\n"
    if daily_line_path:
        md += f"\n## 每日支出曲线\n![]({daily_line_path.name})\n"
    
    # 保存 Markdown
    md_path = REPORT_DIR / f"{month}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"✅ 已导出 Markdown 报告 → {md_path}")
    if pie_path:
        print(f"📊 饼图 → {pie_path}")
    if line_path:
        print(f"📈 累计支出折线图 → {line_path}")
    if daily_line_path:
        print(f"📈 每日支出折线图 → {daily_line_path}")
    for weekly_pie in weekly_pie_paths:
        print(f"📊 每周饼图 → {weekly_pie}")

# ========= 在 main() 函数中 subparsers 之前添加 =========
def list_categories():
    """遍历所有CSV，汇总已使用过的类别"""
    categories = set()
    for csv_file in DATA_DIR.glob("*.csv"):
        try:
            df = pd.read_csv(csv_file)
            if "category" in df.columns:
                categories.update(df["category"].dropna().unique())
        except pd.errors.EmptyDataError:
            # 如果CSV文件是空的，跳过
            continue
        except Exception as e:
            print(f"❌ 读取文件 {csv_file} 时出错: {e}")
            continue

    if categories:
        print("📂 已使用的类别列表：")
        for c in sorted(categories):
            print("-", c)
    else:
        print("⚠️ 没有找到任何类别记录。")


def main():
    parser = argparse.ArgumentParser(
        description="简易记账工具（收入/支出），支持新增记录、查看汇总、导出报告"
    )
    subparsers = parser.add_subparsers(dest="command")

    # ---------------- add ----------------
    parser_add = subparsers.add_parser(
        "add",
        help="新增一条记录，日期可省略，支持 1(今天)、-1(昨天)、-2(前天)、-3(大前天)"
    )
    parser_add.add_argument(
        "date",
        nargs="?",
        default="1",
        help="日期 (YYYY-MM-DD)，输入1表示今天，-1/-2/-3 表示前几天，缺省则为今天"
    )
    parser_add.add_argument("category", help="类别，如餐饮、交通")
    parser_add.add_argument("amount", type=float, help="金额")
    parser_add.add_argument(
        "--type",
        choices=["expense", "income"],
        default="expense",
        help="类型：支出(expense)或收入(income)，默认为支出"
    )
    parser_add.add_argument(
        "note",
        nargs="?",
        default="",
        help="备注信息，可选"
    )

    # ---------------- category ----------------
    parser_category = subparsers.add_parser(
        "category",
        help="查看所有已使用过的类别，避免输入不一致"
    )

    # ---------------- report ----------------
    parser_report = subparsers.add_parser(
        "report",
        help="查看月度汇总，默认当月。或通过 --months, --range, --year 查看多月/年度汇总"
    )
    parser_report.add_argument(
        "month",
        nargs="?",
        default=None,
        help="月份 (YYYY-MM)，默认当月，输入-1表示上个月。此参数与 --months, --range, --year 互斥"
    )
    parser_report.add_argument(
        "--months",
        nargs="+",
        help="指定多个月份 (YYYY-MM YYYY-MM ...)，例如: 2025-01 2025-03"
    )
    parser_report.add_argument(
        "--range",
        nargs=2,
        metavar=("START_MONTH", "END_MONTH"),
        help="指定月份区间 (YYYY-MM YYYY-MM)，例如: 2025-01 2025-03"
    )
    parser_report.add_argument(
        "--year",
        help="指定年份 (YYYY)，例如: 2025"
    )

    # ---------------- export ----------------
    parser_export = subparsers.add_parser(
        "export",
        help="导出 Markdown 报告，默认当月。或通过 --months, --range, --year 导出多月/年度报告"
    )
    parser_export.add_argument(
        "month",
        nargs="?",
        default=None,
        help="月份 (YYYY-MM)，默认当月，输入-1表示上个月。此参数与 --months, --range, --year 互斥"
    )
    parser_export.add_argument(
        "--months",
        nargs="+",
        help="指定多个月份 (YYYY-MM YYYY-MM ...)，例如: 2025-01 2025-03"
    )
    parser_export.add_argument(
        "--range",
        nargs=2,
        metavar=("START_MONTH", "END_MONTH"),
        help="指定月份区间 (YYYY-MM YYYY-MM)，例如: 2025-01 2025-03"
    )
    parser_export.add_argument(
        "--year",
        help="指定年份 (YYYY)，例如: 2025"
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # -------- 处理 add 命令 --------
    if args.command == "add":
        today = datetime.date.today()
        date_str = args.date

        if date_str == "1":
            date_str = today.strftime("%Y-%m-%d")
        elif date_str in ["-1", "-2", "-3"]:
            delta = int(date_str)
            date_str = (today + datetime.timedelta(days=delta)).strftime("%Y-%m-%d")
        else:
            try:
                datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                print(f"❌ 日期格式错误: {date_str}，应为 YYYY-MM-DD 或 1/-1/-2/-3")
                return

        add_record(date_str, args.category, args.amount, args.type, args.note)

    # -------- 处理 report 命令 --------
    elif args.command == "report":
        months_to_process = []
        
        if args.months:
            months_to_process = sorted(args.months)
        elif args.range:
            try:
                months_to_process = ledger_pro.get_months_in_range(args.range[0], args.range[1])
            except NotImplementedError:
                print("❌ ledger_pro.py 不可用，无法处理月份区间报告。")
                return
            except ValueError:
                print("❌ 月份区间格式错误，应为 YYYY-MM YYYY-MM")
                return
        elif args.year:
            try:
                months_to_process = ledger_pro.get_months_in_year(args.year)
            except NotImplementedError:
                print("❌ ledger_pro.py 不可用，无法处理年度报告。")
                return
        elif args.month: # 单月报告
            month = args.month
            if month == "-1":
                first_day_this_month = datetime.date.today().replace(day=1)
                last_month = first_day_this_month - datetime.timedelta(days=1)
                month = last_month.strftime("%Y-%m")
            months_to_process.append(month)
        else: # 默认当月报告
            months_to_process.append(datetime.date.today().strftime("%Y-%m"))
        
        if len(months_to_process) == 1 and not (args.months or args.range or args.year):
            # 兼容原有的单月报告逻辑
            generate_report(months_to_process[0])
        elif months_to_process:
            try:
                ledger_pro.generate_multi_month_report(months_to_process)
            except NotImplementedError:
                print("❌ ledger_pro.py 不可用，无法生成多月报告。")
        else:
            print("⚠️ 未指定月份或月份区间进行报告生成。")


    # -------- 处理 export 命令 --------
    elif args.command == "export":
        months_to_process = []
        year_to_process = None # 标记是否为年度导出

        if args.months:
            months_to_process = sorted(args.months)
        elif args.range:
            try:
                months_to_process = ledger_pro.get_months_in_range(args.range[0], args.range[1])
            except NotImplementedError:
                print("❌ ledger_pro.py 不可用，无法处理月份区间导出。")
                return
            except ValueError:
                print("❌ 月份区间格式错误，应为 YYYY-MM YYYY-MM")
                return
        elif args.year:
            year_to_process = args.year
            try:
                months_to_process = ledger_pro.get_months_in_year(args.year)
            except NotImplementedError:
                print("❌ ledger_pro.py 不可用，无法处理年度导出。")
                return
        elif args.month: # 单月导出
            month = args.month
            if month == "-1":
                first_day_this_month = datetime.date.today().replace(day=1)
                last_month = first_day_this_month - datetime.timedelta(days=1)
                month = last_month.strftime("%Y-%m")
            months_to_process.append(month)
        else: # 默认当月导出
            months_to_process.append(datetime.date.today().strftime("%Y-%m"))

        if len(months_to_process) == 1 and not (args.months or args.range or args.year):
            # 兼容原有的单月导出逻辑
            export_md(months_to_process[0])
        elif months_to_process:
            try:
                ledger_pro.export_multi_month_md(months_to_process, year=year_to_process)
            except NotImplementedError:
                print("❌ ledger_pro.py 不可用，无法导出多月/年度报告。")
        else:
            print("⚠️ 未指定月份或月份区间进行导出。")

    # -------- 处理 category 命令 --------
    elif args.command == "category":
        list_categories()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
