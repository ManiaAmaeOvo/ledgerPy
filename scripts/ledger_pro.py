# ledger_pro.py

import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib import rcParams
import datetime

# 继承 ledger.py 中的一些常量和函数
from .ledger import DATA_DIR, REPORT_DIR, get_csv_path, ensure_csv

# 设置中文字体为系统字体
rcParams['font.sans-serif'] = ['Songti SC']
rcParams['axes.unicode_minus'] = False

def get_monthly_data(month: str):
    """获取指定月份的DataFrame，如果不存在则返回空的DataFrame"""
    path = get_csv_path(month)
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=["date", "category", "amount", "type", "note"])

def calculate_monthly_summary(df_month: pd.DataFrame):
    """计算单个月份的收入、支出和净额"""
    income = df_month[df_month["type"] == "income"]["amount"].sum()
    expense = df_month[df_month["type"] == "expense"]["amount"].sum()
    net = income - expense
    return income, expense, net
# ledger_pro.py

def generate_multi_month_report(months: list):
    """生成多个月份的汇总报告"""
    print("\n📊 多月/年度 收入/支出汇总:")
    total_income_all_months = 0
    total_expense_all_months = 0
    
    all_income_categories = pd.Series(dtype=float) # 用于汇总所有月份的收入类别
    all_expense_categories = pd.Series(dtype=float) # 用于汇总所有月份的支出类别

    monthly_summary_data = [] # 存储每月汇总数据

    for month in sorted(months):
        df_month = get_monthly_data(month)
        if df_month.empty:
            print(f"⚠️ {month} 月没有记录")
            continue
        
        df_month["date"] = pd.to_datetime(df_month["date"])
        df_month = df_month.sort_values(by="date", ascending=True)
        income, expense, net = calculate_monthly_summary(df_month)
        total_income_all_months += income
        total_expense_all_months += expense
        
        monthly_summary_data.append({
            "month": month,
            "income": income,
            "expense": expense,
            "net": net
        })

        print(f"\n--- {month} ---")
        print(f"  收入: {income:.2f} 元")
        print(f"  支出: {expense:.2f} 元")
        print(f"  净额: {net:.2f} 元")
        
        # 月度支出类别汇总
        expense_summary = df_month[df_month["type"] == "expense"].groupby("category")["amount"].sum().sort_values(ascending=False)
        if not expense_summary.empty:
            print("  各类别支出汇总:")
            print(expense_summary.to_string(header=False))
            all_expense_categories = all_expense_categories.add(expense_summary, fill_value=0) # 累加到总计
        
        # 月度收入类别汇总 (新增)
        income_summary = df_month[df_month["type"] == "income"].groupby("category")["amount"].sum().sort_values(ascending=False)
        if not income_summary.empty:
            print("  各类别收入汇总:")
            print(income_summary.to_string(header=False))
            all_income_categories = all_income_categories.add(income_summary, fill_value=0) # 累加到总计

    print("\n--- 总计 ---")
    print(f"总收入: {total_income_all_months:.2f} 元")
    print(f"总支出: {total_expense_all_months:.2f} 元")
    print(f"总净额: {(total_income_all_months - total_expense_all_months):.2f} 元")

    # 总计收入类别汇总 (新增)
    if not all_income_categories.empty:
        print("\n所有月份收入类别总计:")
        print(all_income_categories.sort_values(ascending=False).to_string(header=False))

    # 总计支出类别汇总
    if not all_expense_categories.empty:
        print("\n所有月份支出类别总计:")
        print(all_expense_categories.sort_values(ascending=False).to_string(header=False))


    return monthly_summary_data # 返回月度汇总数据供后续图表使用

def export_multi_month_md(months: list, year: str = None):
    """
    导出多月或年度的 Markdown 报告，包括每月图表和总计图表。
    当year不为None时，表示是年度导出。
    """
    if year:
        output_filename_prefix = f"{year}_annual"
    elif len(months) > 1:
        output_filename_prefix = f"{months[0]}_to_{months[-1]}"
    else: # 只有单个月份，这种情况在ledger.py中已经处理，这里是为了保险
        output_filename_prefix = months[0]
        
    md = f"# {output_filename_prefix} 账单报告\n\n"
    all_dfs = []
    
    monthly_summary_data = [] # 用于绘制月级收入支出折线图

    # 用于汇总所有月份的类别数据
    total_income_categories = pd.Series(dtype=float)
    total_expense_categories = pd.Series(dtype=float)

    for month in sorted(months):
        df_month = get_monthly_data(month)
        if df_month.empty:
            continue

        all_dfs.append(df_month)
        
        income, expense, net = calculate_monthly_summary(df_month)
        monthly_summary_data.append({
            "month": month,
            "income": income,
            "expense": expense
        })

        md += f"## {month} 月账单\n\n"
        md += f"| 日期 | 类别 | 金额 | 类型 | 备注 |\n|------|------|------|------|------|\n"
        for _, row in df_month.iterrows():
            md += f"| {row['date']} | {row['category']} | {row['amount']} | {row['type']} | {row['note']} |\n"

        md += f"\n### {month} 月小结\n- 收入: {income:.2f} 元\n"
        md += f"- 支出: {expense:.2f} 元\n"
        md += f"- 净额: {net:.2f} 元\n"

        # 月度支出类别汇总表格 (新增)
        expense_summary = df_month[df_month["type"] == "expense"].groupby("category")["amount"].sum().sort_values(ascending=False)
        if not expense_summary.empty:
            md += f"\n#### {month} 月各类别支出汇总\n\n| 类别 | 金额 |\n|------|------|\n"
            for category, amount in expense_summary.items():
                md += f"| {category} | {amount:.2f} |\n"
            total_expense_categories = total_expense_categories.add(expense_summary, fill_value=0) # 累加到总计

        # 月度收入类别汇总表格 (新增)
        income_summary = df_month[df_month["type"] == "income"].groupby("category")["amount"].sum().sort_values(ascending=False)
        if not income_summary.empty:
            md += f"\n#### {month} 月各类别收入汇总\n\n| 类别 | 金额 |\n|------|------|\n"
            for category, amount in income_summary.items():
                md += f"| {category} | {amount:.2f} |\n"
            total_income_categories = total_income_categories.add(income_summary, fill_value=0) # 累加到总计


        # 生成每月饼图
        if not expense_summary.empty:
            plt.figure(figsize=(6, 6))
            plt.pie(expense_summary, labels=expense_summary.index, autopct="%1.1f%%", startangle=140)
            plt.title(f"{month} 各类别支出占比")
            pie_path = REPORT_DIR / f"{month}_{output_filename_prefix}_pie.png"
            plt.savefig(pie_path, bbox_inches="tight")
            plt.close()
            md += f"\n#### 支出分类饼图\n![]({pie_path.name})\n"
            print(f"📊 {month} 饼图 → {pie_path}")

        # 生成每月累计支出折线图
        df_month["date"] = pd.to_datetime(df_month["date"])
        df_month_expense = df_month[df_month["type"] == "expense"].sort_values("date")
        daily_expense = df_month_expense.groupby(df_month_expense["date"].dt.date)["amount"].sum()

        if not daily_expense.empty:
            plt.figure(figsize=(10, 5))
            plt.plot(daily_expense.index, daily_expense.cumsum(), marker="o")
            plt.title(f"{month} 累计支出走势")
            plt.xlabel("日期")
            plt.ylabel("累计金额")
            plt.grid(True)
            line_path = REPORT_DIR / f"{month}_{output_filename_prefix}_line.png"
            plt.savefig(line_path, bbox_inches="tight")
            plt.close()
            md += f"\n#### 累计支出曲线\n![]({line_path.name})\n"
            print(f"📈 {month} 折线图 → {line_path}")

        md += "\n---\n\n" # 分隔线

    if not all_dfs:
        print("⚠️ 没有可用的数据进行汇总和导出。")
        return

    # 合并所有数据
    df_all = pd.concat(all_dfs, ignore_index=True)

    md += "## 所有月份汇总\n\n"

    # 总计收入类别汇总表格 (新增)
    if not total_income_categories.empty:
        md += f"### 所有月份收入类别总计\n\n| 类别 | 金额 |\n|------|------|\n"
        for category, amount in total_income_categories.sort_values(ascending=False).items():
            md += f"| {category} | {amount:.2f} |\n"
        md += "\n"

    # 总计支出类别汇总表格 (新增)
    if not total_expense_categories.empty:
        md += f"### 所有月份支出类别总计\n\n| 类别 | 金额 |\n|------|------|\n"
        for category, amount in total_expense_categories.sort_values(ascending=False).items():
            md += f"| {category} | {amount:.2f} |\n"
        md += "\n"

    # 总计饼图 (所有月)
    total_expense_summary = df_all[df_all["type"] == "expense"].groupby("category")["amount"].sum()
    if not total_expense_summary.empty:
        plt.figure(figsize=(8, 8))
        plt.pie(total_expense_summary, labels=total_expense_summary.index, autopct="%1.1f%%", startangle=140)
        plt.title(f"{output_filename_prefix} 所有类别支出占比")
        total_pie_path = REPORT_DIR / f"{output_filename_prefix}_total_pie.png"
        plt.savefig(total_pie_path, bbox_inches="tight")
        plt.close()
        md += f"\n### 所有月份支出分类饼图\n![]({total_pie_path.name})\n"
        print(f"📊 总计饼图 → {total_pie_path}")

    
    # 总计收入饼图 (所有月)
    total_income_summary = df_all[df_all["type"] == "income"].groupby("category")["amount"].sum()
    if not total_income_summary.empty:
        plt.figure(figsize=(8, 8))
        plt.pie(total_income_summary, labels=total_income_summary.index, autopct="%1.1f%%", startangle=140)
        plt.title(f"{output_filename_prefix} 所有类别收入占比")
        total_pie_path = REPORT_DIR / f"{output_filename_prefix}_total_income_pie.png"
        plt.savefig(total_pie_path, bbox_inches="tight")
        plt.close()
        md += f"\n### 所有月份收入分类饼图\n![]({total_pie_path.name})\n"
        print(f"📊 总计饼图 → {total_pie_path}")

    # 总计日级支出走势图 (所有月)
    df_all["date"] = pd.to_datetime(df_all["date"])
    df_all_expense = df_all[df_all["type"] == "expense"].sort_values("date")
    daily_total_expense = df_all_expense.groupby(df_all_expense["date"].dt.date)["amount"].sum()

    if not daily_total_expense.empty:
        plt.figure(figsize=(12, 6))
        plt.plot(daily_total_expense.index, daily_total_expense.cumsum(), marker="o", linestyle="-")
        plt.title(f"{output_filename_prefix} 累计支出走势 (所有月份)")
        plt.xlabel("日期")
        plt.ylabel("累计金额")
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        total_line_path = REPORT_DIR / f"{output_filename_prefix}_total_line.png"
        plt.savefig(total_line_path, bbox_inches="tight")
        plt.close()
        md += f"\n### 所有月份累计支出曲线\n![]({total_line_path.name})\n"
        print(f"📈 总计日级支出折线图 → {total_line_path}")
    
    # 月级收入和支出折线图 (所有月)
    if monthly_summary_data:
        df_monthly_summary = pd.DataFrame(monthly_summary_data)
        df_monthly_summary["month_dt"] = pd.to_datetime(df_monthly_summary["month"])
        df_monthly_summary = df_monthly_summary.sort_values("month_dt")

        plt.figure(figsize=(12, 6))
        plt.plot(df_monthly_summary["month"], df_monthly_summary["income"], marker="o", label="月收入")
        plt.plot(df_monthly_summary["month"], df_monthly_summary["expense"], marker="x", label="月支出")
        plt.title(f"{output_filename_prefix} 月度收入与支出走势")
        plt.xlabel("月份")
        plt.ylabel("金额")
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        monthly_income_expense_path = REPORT_DIR / f"{output_filename_prefix}_monthly_income_expense.png"
        plt.savefig(monthly_income_expense_path, bbox_inches="tight")
        plt.close()
        md += f"\n### 月度收入与支出折线图\n![]({monthly_income_expense_path.name})\n"
        print(f"📊 月度收入/支出折线图 → {monthly_income_expense_path}")

    md_path = REPORT_DIR / f"{output_filename_prefix}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"✅ 已导出 Markdown 报告 → {md_path}")

def get_months_in_range(start_month_str, end_month_str):
    """获取一个月份区间内的所有月份字符串 (YYYY-MM)"""
    start_year, start_month = map(int, start_month_str.split('-'))
    end_year, end_month = map(int, end_month_str.split('-'))

    months = []
    current_date = datetime.date(start_year, start_month, 1)
    while current_date <= datetime.date(end_year, end_month, 1):
        months.append(current_date.strftime("%Y-%m"))
        # 移动到下个月
        if current_date.month == 12:
            current_date = datetime.date(current_date.year + 1, 1, 1)
        else:
            current_date = datetime.date(current_date.year, current_date.month + 1, 1)
    return months

def get_months_in_year(year_str):
    """获取一年中的所有月份字符串 (YYYY-MM)"""
    months = []
    for month_num in range(1, 13):
        months.append(f"{year_str}-{month_num:02d}")
    return months
