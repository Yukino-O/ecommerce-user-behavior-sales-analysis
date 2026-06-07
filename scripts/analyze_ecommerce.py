from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports"
FIG_DIR = REPORT_DIR / "figures"
POWERBI_DIR = REPORT_DIR / "powerbi"


plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def parse_dates(series: pd.Series) -> pd.Series:
    normalized = (
        series.astype("string")
        .str.replace("年", "-", regex=False)
        .str.replace("月", "-", regex=False)
        .str.replace("日", "", regex=False)
        .str.replace(".", "-", regex=False)
        .str.replace("/", "-", regex=False)
    )
    return pd.to_datetime(normalized, errors="coerce")


def load_and_clean() -> tuple[pd.DataFrame, dict[str, int]]:
    raw_path = RAW_DIR / "ecommerce_orders_raw.csv"
    df = pd.read_csv(raw_path, encoding="utf-8-sig")
    quality = {"raw_rows": len(df)}

    df["order_date"] = parse_dates(df["order_date"])
    df = df.dropna(subset=["order_id", "user_id", "order_date", "product_id", "quantity", "unit_price"])
    quality["rows_after_required_drop"] = len(df)

    df["channel"] = df["channel"].fillna("未知渠道")
    df["region"] = df["region"].fillna("未知地区")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype(int)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df = df[df["quantity"] > 0]
    df = df[df["unit_price"] > 0]

    before_dedup = len(df)
    df = df.drop_duplicates(subset=["order_id", "user_id", "order_date", "product_id", "quantity", "unit_price"])
    quality["duplicate_orders_removed"] = before_dedup - len(df)
    quality["clean_rows"] = len(df)

    df["order_amount"] = (df["quantity"] * df["unit_price"]).round(2)
    paid = df[df["payment_status"].eq("已支付")].copy()
    quality["paid_clean_rows"] = len(paid)
    paid["month"] = paid["order_date"].dt.to_period("M").astype(str)
    paid["order_day"] = paid["order_date"].dt.date.astype(str)
    paid["is_repeat_order"] = paid.sort_values("order_date").groupby("user_id").cumcount().gt(0)
    paid["user_order_no"] = paid.sort_values("order_date").groupby("user_id").cumcount() + 1
    return paid, quality


def build_metrics(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    monthly = (
        df.groupby("month", as_index=False)
        .agg(sales=("order_amount", "sum"), orders=("order_id", "nunique"), users=("user_id", "nunique"))
        .sort_values("month")
    )
    monthly["avg_order_value"] = (monthly["sales"] / monthly["orders"]).round(2)
    monthly["sales"] = monthly["sales"].round(2)

    category = (
        df.groupby("category", as_index=False)
        .agg(sales=("order_amount", "sum"), orders=("order_id", "nunique"), users=("user_id", "nunique"))
        .sort_values("sales", ascending=False)
    )
    category["sales_share"] = (category["sales"] / category["sales"].sum()).round(4)
    category["sales"] = category["sales"].round(2)

    top_products = (
        df.groupby(["product_id", "product_name", "category"], as_index=False)
        .agg(sales=("order_amount", "sum"), quantity=("quantity", "sum"), orders=("order_id", "nunique"))
        .sort_values("sales", ascending=False)
        .head(10)
    )
    top_products["sales"] = top_products["sales"].round(2)

    first_order = df.groupby("user_id")["order_date"].min().rename("first_order_date")
    user_enriched = df.merge(first_order, on="user_id", how="left")
    user_enriched["user_type"] = np.where(
        user_enriched["order_date"].dt.to_period("M").eq(user_enriched["first_order_date"].dt.to_period("M")),
        "新用户",
        "老用户",
    )
    user_type = (
        user_enriched.groupby(["month", "user_type"], as_index=False)
        .agg(users=("user_id", "nunique"), sales=("order_amount", "sum"))
        .sort_values(["month", "user_type"])
    )
    user_type["sales"] = user_type["sales"].round(2)

    user_orders = df.groupby("user_id", as_index=False).agg(orders=("order_id", "nunique"), sales=("order_amount", "sum"))
    repeat_rate = pd.DataFrame(
        {
            "metric": ["用户数", "复购用户数", "复购率"],
            "value": [
                len(user_orders),
                int((user_orders["orders"] >= 2).sum()),
                round(float((user_orders["orders"] >= 2).mean()), 4),
            ],
        }
    )

    analysis_date = df["order_date"].max() + pd.Timedelta(days=1)
    rfm = (
        df.groupby("user_id")
        .agg(
            recency=("order_date", lambda x: (analysis_date - x.max()).days),
            frequency=("order_id", "nunique"),
            monetary=("order_amount", "sum"),
        )
        .reset_index()
    )
    rfm["r_score"] = pd.qcut(rfm["recency"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    def segment(row: pd.Series) -> str:
        if row["r_score"] >= 4 and row["f_score"] >= 4 and row["m_score"] >= 4:
            return "高价值用户"
        if row["r_score"] >= 4 and row["f_score"] <= 2:
            return "新客培育"
        if row["r_score"] <= 2 and row["f_score"] >= 4:
            return "沉睡高频用户"
        if row["m_score"] >= 4:
            return "高消费潜力"
        if row["r_score"] <= 2:
            return "流失风险"
        return "一般用户"

    rfm["segment"] = rfm.apply(segment, axis=1)
    rfm["monetary"] = rfm["monetary"].round(2)
    rfm_summary = (
        rfm.groupby("segment", as_index=False)
        .agg(users=("user_id", "nunique"), avg_recency=("recency", "mean"), avg_frequency=("frequency", "mean"), avg_monetary=("monetary", "mean"))
        .sort_values("avg_monetary", ascending=False)
    )
    for col in ["avg_recency", "avg_frequency", "avg_monetary"]:
        rfm_summary[col] = rfm_summary[col].round(2)

    channel = (
        df.groupby("channel", as_index=False)
        .agg(sales=("order_amount", "sum"), orders=("order_id", "nunique"), users=("user_id", "nunique"))
        .sort_values("sales", ascending=False)
    )
    channel["avg_order_value"] = (channel["sales"] / channel["orders"]).round(2)
    channel["order_per_user"] = (channel["orders"] / channel["users"]).round(2)
    channel["sales"] = channel["sales"].round(2)

    region = (
        df.groupby("region", as_index=False)
        .agg(sales=("order_amount", "sum"), orders=("order_id", "nunique"), users=("user_id", "nunique"))
        .sort_values("sales", ascending=False)
    )
    region["avg_order_value"] = (region["sales"] / region["orders"]).round(2)
    region["sales"] = region["sales"].round(2)

    high_value_users = rfm[rfm["segment"].eq("高价值用户")].merge(
        df.groupby("user_id").agg(main_region=("region", lambda x: x.mode().iat[0]), main_channel=("channel", lambda x: x.mode().iat[0])),
        on="user_id",
        how="left",
    )
    high_value_profile = pd.concat(
        [
            high_value_users["main_region"].value_counts(normalize=True).rename_axis("dimension_value").reset_index(name="share").assign(dimension="地区"),
            high_value_users["main_channel"].value_counts(normalize=True).rename_axis("dimension_value").reset_index(name="share").assign(dimension="渠道"),
        ],
        ignore_index=True,
    )
    high_value_profile["share"] = high_value_profile["share"].round(4)

    return {
        "clean_orders": df,
        "monthly_sales": monthly,
        "category_sales": category,
        "top_products": top_products,
        "user_type": user_type,
        "repeat_rate": repeat_rate,
        "rfm_detail": rfm,
        "rfm_summary": rfm_summary,
        "channel_metrics": channel,
        "region_metrics": region,
        "high_value_profile": high_value_profile,
    }


def save_tables(tables: dict[str, pd.DataFrame], quality: dict[str, int]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    POWERBI_DIR.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(PROCESSED_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame([quality]).to_csv(PROCESSED_DIR / "data_quality_summary.csv", index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(POWERBI_DIR / "powerbi_dashboard_dataset.xlsx", engine="openpyxl") as writer:
        for name in [
            "monthly_sales",
            "category_sales",
            "top_products",
            "user_type",
            "repeat_rate",
            "rfm_summary",
            "channel_metrics",
            "region_metrics",
            "high_value_profile",
        ]:
            tables[name].to_excel(writer, sheet_name=name[:31], index=False)
        pd.DataFrame([quality]).to_excel(writer, sheet_name="data_quality", index=False)


def plot_figures(tables: dict[str, pd.DataFrame]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    monthly = tables["monthly_sales"]
    fig, ax1 = plt.subplots(figsize=(11, 6))
    ax1.plot(monthly["month"], monthly["sales"], marker="o", linewidth=2.5, color="#2563eb", label="销售额")
    ax1.set_ylabel("销售额")
    ax1.tick_params(axis="x", rotation=45)
    ax2 = ax1.twinx()
    ax2.plot(monthly["month"], monthly["avg_order_value"], marker="s", linewidth=2, color="#dc2626", label="客单价")
    ax2.set_ylabel("客单价")
    ax1.set_title("每月销售额与客单价趋势")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "monthly_sales_aov.png", dpi=180)
    plt.close(fig)

    category = tables["category_sales"].sort_values("sales")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(category["category"], category["sales"], color="#0f766e")
    ax.set_title("不同品类销售贡献")
    ax.set_xlabel("销售额")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "category_sales.png", dpi=180)
    plt.close(fig)

    top_products = tables["top_products"].sort_values("sales")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(top_products["product_name"], top_products["sales"], color="#7c3aed")
    ax.set_title("TOP10 商品销售额")
    ax.set_xlabel("销售额")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "top_products.png", dpi=180)
    plt.close(fig)

    user_type = tables["user_type"].pivot(index="month", columns="user_type", values="users").fillna(0)
    fig, ax = plt.subplots(figsize=(11, 5.8))
    user_type.plot(kind="bar", stacked=True, ax=ax, color=["#f97316", "#16a34a"])
    ax.set_title("新老用户月度占比")
    ax.set_xlabel("月份")
    ax.set_ylabel("用户数")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "new_old_users.png", dpi=180)
    plt.close(fig)

    rfm_summary = tables["rfm_summary"].sort_values("users")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(rfm_summary["segment"], rfm_summary["users"], color="#0891b2")
    ax.set_title("RFM 用户分层规模")
    ax.set_xlabel("用户数")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "rfm_segments.png", dpi=180)
    plt.close(fig)

    channel = tables["channel_metrics"].sort_values("order_per_user", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.bar(channel["channel"], channel["order_per_user"], color="#ea580c")
    ax.set_title("不同渠道转化效果：人均订单数")
    ax.set_xlabel("渠道")
    ax.set_ylabel("人均订单数")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "channel_conversion.png", dpi=180)
    plt.close(fig)

    region = tables["region_metrics"].sort_values("sales")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(region["region"], region["sales"], color="#1d4ed8")
    ax.set_title("不同地区销售额")
    ax.set_xlabel("销售额")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "region_sales.png", dpi=180)
    plt.close(fig)


def write_powerbi_notes() -> None:
    notes = """# Power BI 仪表盘搭建说明

本项目已输出 `reports/powerbi/powerbi_dashboard_dataset.xlsx`，可直接导入 Power BI Desktop。

建议建立 4 个页面：

1. 经营总览：卡片展示销售额、订单量、用户数、客单价；折线图展示 `monthly_sales` 的销售额和客单价趋势。
2. 商品与品类：条形图展示 `category_sales` 品类贡献；TOP N 条形图展示 `top_products`。
3. 用户分析：堆积柱形图展示 `user_type` 新老用户；矩阵或条形图展示 `rfm_summary`。
4. 渠道与地区：柱形图展示 `channel_metrics` 的人均订单数和销售额；地图或条形图展示 `region_metrics` 的销售额和订单量。

核心度量值建议：

```DAX
销售额 = SUM(monthly_sales[sales])
订单量 = SUM(monthly_sales[orders])
用户数 = SUM(monthly_sales[users])
客单价 = DIVIDE([销售额], [订单量])
复购率 = CALCULATE(MAX(repeat_rate[value]), repeat_rate[metric] = "复购率")
```

配色建议使用蓝色表示销售趋势、绿色表示用户增长、橙色表示渠道效率，避免所有页面使用同一种颜色。
"""
    (POWERBI_DIR / "powerbi_dashboard_notes.md").write_text(notes, encoding="utf-8")


def write_report(tables: dict[str, pd.DataFrame], quality: dict[str, int]) -> None:
    monthly = tables["monthly_sales"]
    category = tables["category_sales"]
    top_products = tables["top_products"]
    repeat_rate = tables["repeat_rate"]
    rfm = tables["rfm_summary"]
    channel = tables["channel_metrics"]
    region = tables["region_metrics"]

    total_sales = monthly["sales"].sum()
    total_orders = monthly["orders"].sum()
    total_users = int(repeat_rate.loc[repeat_rate["metric"].eq("用户数"), "value"].iloc[0])
    avg_order_value = total_sales / total_orders
    best_month = monthly.loc[monthly["sales"].idxmax()]
    best_category = category.iloc[0]
    best_product = top_products.iloc[0]
    best_channel = channel.iloc[0]
    efficient_channel = channel.sort_values("order_per_user", ascending=False).iloc[0]
    best_region = region.iloc[0]
    weak_region = region.iloc[-1]
    repurchase = float(repeat_rate.loc[repeat_rate["metric"].eq("复购率"), "value"].iloc[0])
    high_value = rfm[rfm["segment"].eq("高价值用户")]
    high_value_text = "暂无明显高价值用户分组"
    if not high_value.empty:
        high_value_text = (
            f"高价值用户共 {int(high_value['users'].iloc[0])} 人，"
            f"平均消费 {high_value['avg_monetary'].iloc[0]:.2f} 元，"
            f"平均购买 {high_value['avg_frequency'].iloc[0]:.2f} 次。"
        )

    report = f"""# 电商用户行为与销售数据分析报告

## 一、项目说明

本项目围绕电商订单数据完成了从数据清洗、指标构建、销售分析、用户分析、渠道与地区分析到可视化报告的完整流程。由于当前仓库没有外部原始数据，项目内置了一份可复现的模拟订单数据，模拟了缺失值、重复订单和多种日期格式，便于展示真实业务分析中的处理能力。

## 二、数据清洗

原始数据共有 {quality['raw_rows']} 行记录。清洗过程中完成了以下处理：

- 统一 `YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY.MM.DD`、`YYYY年MM月DD日` 等日期格式。
- 删除关键字段缺失的订单，保留 {quality['rows_after_required_drop']} 行。
- 对渠道和地区缺失值填充为“未知渠道”和“未知地区”，避免渠道/地区分析口径丢失。
- 按订单号、用户、日期、商品、数量和单价识别重复订单，删除 {quality['duplicate_orders_removed']} 行重复记录。
- 计算订单金额 `order_amount = quantity * unit_price`。
- 按用户历史订单顺序计算复购标记 `is_repeat_order`。

清洗后订单为 {quality['clean_rows']} 行，其中有效已支付订单为 {quality['paid_clean_rows']} 行。

## 三、核心经营指标

- 总销售额：{total_sales:,.2f} 元
- 总订单量：{int(total_orders):,} 单
- 有效用户数：{total_users:,} 人
- 月均客单价：{avg_order_value:,.2f} 元
- 复购率：{repurchase:.2%}
- 销售峰值月份：{best_month['month']}，销售额 {best_month['sales']:,.2f} 元

销售峰值集中在促销月份，说明平台销售对大促活动敏感。客单价在大促期未必同步上升，通常代表折扣拉动订单量，但单笔价格受到促销折扣压低。

## 四、销售分析

### 1. 每月销售额趋势

从月度趋势看，11 月和 12 月销售额显著抬升，符合“双11”和年末促销的业务规律。6 月也出现阶段性增长，说明年中促销对需求有明显拉动。

![每月销售额与客单价趋势](figures/monthly_sales_aov.png)

### 2. 不同品类销售贡献

销售贡献最高的品类是 **{best_category['category']}**，销售额为 {best_category['sales']:,.2f} 元，占比 {best_category['sales_share']:.2%}。该品类更适合作为平台主推品类，用于承接大促流量和会员复购。

![不同品类销售贡献](figures/category_sales.png)

### 3. TOP 商品分析

销售额最高的商品是 **{best_product['product_name']}**，销售额为 {best_product['sales']:,.2f} 元，销量 {int(best_product['quantity'])} 件。TOP 商品通常承担拉动 GMV 的作用，后续可围绕这些商品做组合包、加购推荐和会员专享价。

![TOP 商品分析](figures/top_products.png)

## 五、用户分析

### 1. 新老用户占比

新用户在促销期明显增加，说明大促能够带来拉新。但如果大促后老用户占比不能持续提升，说明用户沉淀仍有优化空间。

![新老用户占比](figures/new_old_users.png)

### 2. 用户复购率

当前复购率为 **{repurchase:.2%}**。从电商经营角度看，复购率是判断用户资产质量的核心指标。如果平台主要依赖促销拉新，而复购不足，后续获客成本会持续上升。

### 3. RFM 用户分层

{high_value_text}

![RFM 用户分层](figures/rfm_segments.png)

高价值用户的特征是近期有购买、购买频次高、累计消费高。建议对该群体配置会员权益、专属客服、提前购和高客单新品推荐。

## 六、渠道与地区分析

### 1. 不同渠道转化效果

销售额最高的渠道是 **{best_channel['channel']}**，销售额为 {best_channel['sales']:,.2f} 元；人均订单数最高的渠道是 **{efficient_channel['channel']}**，人均订单数为 {efficient_channel['order_per_user']:.2f}。这说明渠道评估不能只看销售额，也要看用户质量和转化效率。

![渠道转化效果](figures/channel_conversion.png)

### 2. 不同地区销售额和订单量

销售额最高地区是 **{best_region['region']}**，销售额为 {best_region['sales']:,.2f} 元；销售额最低地区是 **{weak_region['region']}**，销售额为 {weak_region['sales']:,.2f} 元。地区差异可能来自用户规模、物流时效、商品偏好和营销覆盖强度。

![地区销售额](figures/region_sales.png)

### 3. 差异较大的地区或渠道

渠道上，销售额第一和转化效率第一不完全等同，说明部分渠道“量大但效率一般”，部分渠道“规模小但用户质量高”。地区上，头部地区贡献明显高于尾部地区，建议分别使用不同经营策略。

## 七、业务建议

1. 对大促月份提前备货 TOP 商品，并为高贡献品类设置组合购和满减门槛，提高连带购买。
2. 对高价值用户做会员分层运营，重点推送新品、复购券和专属权益，提升留存。
3. 对新客培育用户设置首购后 7 天、30 天复购触达，减少促销后流失。
4. 对高转化渠道增加预算测试，对高销售低效率渠道优化投放素材和落地页。
5. 对弱势地区排查物流、价格、品类偏好和渠道覆盖，优先做小规模 A/B 测试。
6. Power BI 仪表盘建议按“经营总览、商品品类、用户分层、渠道地区”四页组织，便于管理层快速定位问题。

## 八、项目产出

- 清洗后数据：`data/processed/clean_orders.csv`
- 指标宽表：`data/processed/*.csv`
- matplotlib 图表：`reports/figures/*.png`
- Power BI 导入数据集：`reports/powerbi/powerbi_dashboard_dataset.xlsx`
- Power BI 搭建说明：`reports/powerbi/powerbi_dashboard_notes.md`
"""
    (REPORT_DIR / "analysis_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    for path in [PROCESSED_DIR, REPORT_DIR, FIG_DIR, POWERBI_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    clean_orders, quality = load_and_clean()
    tables = build_metrics(clean_orders)
    save_tables(tables, quality)
    plot_figures(tables)
    write_powerbi_notes()
    write_report(tables, quality)
    print(f"clean orders: {len(clean_orders)}")
    print(f"report: {REPORT_DIR / 'analysis_report.md'}")


if __name__ == "__main__":
    main()
