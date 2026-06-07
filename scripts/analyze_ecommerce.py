from __future__ import annotations

import re
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

DATASET_CSV = RAW_DIR / "ecommerce_orders_2024_2025.csv"
DATASET_CARD = RAW_DIR / "ecommerce_orders_2024_2025_README.md"
DATASET_URL = "https://huggingface.co/datasets/millat/e-commerce-orders"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


CATEGORY_CN = {
    "Electronics": "电子产品",
    "Clothing": "服饰",
    "Home": "家居",
    "Books": "图书",
    "Beauty": "美妆",
    "Toys": "玩具",
}

CHANNEL_CN = {
    "Organic": "自然流量",
    "Paid Search": "付费搜索",
    "Email": "邮件营销",
    "Social": "社交媒体",
}

SEGMENT_CN = {
    "New": "新客",
    "Returning": "回访客",
    "VIP": "VIP",
}


def extract_state(address: str) -> str:
    match = re.search(r",\s*([^,]+)\s+\d{5}(?:-\d{4})?\s*$", str(address))
    if match:
        return match.group(1).strip()
    parts = str(address).split(",")
    if len(parts) >= 2:
        return parts[-1].strip().rsplit(" ", 1)[0]
    return "未知地区"


def load_and_clean() -> tuple[pd.DataFrame, dict[str, int | str]]:
    if not DATASET_CSV.exists():
        raise FileNotFoundError(f"未找到数据文件：{DATASET_CSV}")

    raw = pd.read_csv(DATASET_CSV)
    quality: dict[str, int | str] = {
        "dataset": "Hugging Face millat/e-commerce-orders",
        "dataset_url": DATASET_URL,
        "license": "MIT",
        "raw_rows": len(raw),
    }

    df = raw.copy()
    required = [
        "order_id",
        "customer_id",
        "product_id",
        "category",
        "price",
        "quantity",
        "order_date",
        "shipping_date",
        "delivery_status",
        "payment_method",
        "device_type",
        "channel",
        "shipping_address",
        "customer_segment",
    ]
    missing_cols = [col for col in required if col not in df.columns]
    if missing_cols:
        raise ValueError(f"数据缺少必要字段：{missing_cols}")

    for col in ["order_id", "category", "delivery_status", "payment_method", "device_type", "channel", "customer_segment"]:
        df[col] = df[col].astype("string").str.strip()
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["shipping_date"] = pd.to_datetime(df["shipping_date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce")
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")

    quality["missing_required_rows"] = int(df[required].isna().any(axis=1).sum())
    before_drop = len(df)
    df = df.dropna(subset=required)
    quality["rows_after_required_drop"] = len(df)
    quality["required_rows_removed"] = before_drop - len(df)

    before_dedup = len(df)
    df = df.drop_duplicates(subset=["order_id"])
    quality["duplicate_orders_removed"] = before_dedup - len(df)
    quality["non_positive_price_rows"] = int((df["price"] <= 0).sum())
    quality["non_positive_quantity_rows"] = int((df["quantity"] <= 0).sum())
    df = df[(df["price"] > 0) & (df["quantity"] > 0)].copy()

    df["customer_id"] = df["customer_id"].astype(int).astype(str)
    df["product_id"] = df["product_id"].astype(int).astype(str)
    df["order_amount"] = (df["price"] * df["quantity"]).round(2)
    df["month"] = df["order_date"].dt.to_period("M").astype(str)
    df["order_day"] = df["order_date"].dt.date.astype(str)
    df["shipping_days"] = (df["shipping_date"] - df["order_date"]).dt.days
    df["category_cn"] = df["category"].map(CATEGORY_CN).fillna(df["category"])
    df["channel_cn"] = df["channel"].map(CHANNEL_CN).fillna(df["channel"])
    df["customer_segment_cn"] = df["customer_segment"].map(SEGMENT_CN).fillna(df["customer_segment"])
    df["region"] = df["shipping_address"].map(extract_state)

    df = df.sort_values(["customer_id", "order_date", "order_id"])
    df["is_repeat_order"] = df.groupby("customer_id").cumcount().gt(0)
    df["user_order_no"] = df.groupby("customer_id").cumcount() + 1

    quality["clean_rows"] = len(df)
    quality["valid_orders"] = int(df["order_id"].nunique())
    quality["valid_users"] = int(df["customer_id"].nunique())
    quality["date_min"] = str(df["order_date"].min())
    quality["date_max"] = str(df["order_date"].max())
    return df, quality


def build_metrics(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    monthly = (
        df.groupby("month", as_index=False)
        .agg(sales=("order_amount", "sum"), orders=("order_id", "nunique"), users=("customer_id", "nunique"))
        .sort_values("month")
    )
    monthly["avg_order_value"] = (monthly["sales"] / monthly["orders"]).round(2)
    monthly["sales"] = monthly["sales"].round(2)

    category = (
        df.groupby(["category", "category_cn"], as_index=False)
        .agg(sales=("order_amount", "sum"), orders=("order_id", "nunique"), users=("customer_id", "nunique"))
        .sort_values("sales", ascending=False)
    )
    category["sales_share"] = (category["sales"] / category["sales"].sum()).round(4)
    category["sales"] = category["sales"].round(2)

    top_products = (
        df.groupby(["product_id", "category_cn"], as_index=False)
        .agg(sales=("order_amount", "sum"), quantity=("quantity", "sum"), orders=("order_id", "nunique"), avg_price=("price", "mean"))
        .sort_values("sales", ascending=False)
        .head(15)
    )
    top_products["product_name"] = "商品ID-" + top_products["product_id"].astype(str)
    top_products["sales"] = top_products["sales"].round(2)
    top_products["avg_price"] = top_products["avg_price"].round(2)

    first_order = df.groupby("customer_id")["order_date"].min().rename("first_order_date")
    user_enriched = df.merge(first_order, on="customer_id", how="left")
    user_enriched["user_type"] = np.where(
        user_enriched["order_date"].dt.to_period("M").eq(user_enriched["first_order_date"].dt.to_period("M")),
        "新用户",
        "老用户",
    )
    user_type = (
        user_enriched.groupby(["month", "user_type"], as_index=False)
        .agg(users=("customer_id", "nunique"), sales=("order_amount", "sum"))
        .sort_values(["month", "user_type"])
    )
    user_type["sales"] = user_type["sales"].round(2)

    user_orders = df.groupby("customer_id", as_index=False).agg(orders=("order_id", "nunique"), sales=("order_amount", "sum"))
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
        df.groupby("customer_id")
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
        .agg(users=("customer_id", "nunique"), avg_recency=("recency", "mean"), avg_frequency=("frequency", "mean"), avg_monetary=("monetary", "mean"))
        .sort_values("avg_monetary", ascending=False)
    )
    for col in ["avg_recency", "avg_frequency", "avg_monetary"]:
        rfm_summary[col] = rfm_summary[col].round(2)

    channel = (
        df.groupby(["channel", "channel_cn"], as_index=False)
        .agg(sales=("order_amount", "sum"), orders=("order_id", "nunique"), users=("customer_id", "nunique"))
        .sort_values("sales", ascending=False)
    )
    channel["avg_order_value"] = (channel["sales"] / channel["orders"]).round(2)
    channel["order_per_user"] = (channel["orders"] / channel["users"]).round(2)
    channel["sales_share"] = (channel["sales"] / channel["sales"].sum()).round(4)
    channel["sales"] = channel["sales"].round(2)

    region = (
        df.groupby("region", as_index=False)
        .agg(sales=("order_amount", "sum"), orders=("order_id", "nunique"), users=("customer_id", "nunique"))
        .sort_values("sales", ascending=False)
    )
    region["avg_order_value"] = (region["sales"] / region["orders"]).round(2)
    region["sales_share"] = (region["sales"] / region["sales"].sum()).round(4)
    region["sales"] = region["sales"].round(2)

    segment_metrics = (
        df.groupby(["customer_segment", "customer_segment_cn"], as_index=False)
        .agg(sales=("order_amount", "sum"), orders=("order_id", "nunique"), users=("customer_id", "nunique"), avg_shipping_days=("shipping_days", "mean"))
        .sort_values("sales", ascending=False)
    )
    segment_metrics["avg_order_value"] = (segment_metrics["sales"] / segment_metrics["orders"]).round(2)
    segment_metrics["avg_shipping_days"] = segment_metrics["avg_shipping_days"].round(2)
    segment_metrics["sales"] = segment_metrics["sales"].round(2)

    high_value_users = rfm[rfm["segment"].eq("高价值用户")].merge(
        df.groupby("customer_id").agg(main_region=("region", lambda x: x.mode().iat[0]), main_channel=("channel_cn", lambda x: x.mode().iat[0]), main_category=("category_cn", lambda x: x.mode().iat[0])),
        on="customer_id",
        how="left",
    )
    high_value_profile = pd.concat(
        [
            high_value_users["main_region"].value_counts(normalize=True).rename_axis("dimension_value").reset_index(name="share").assign(dimension="地区"),
            high_value_users["main_channel"].value_counts(normalize=True).rename_axis("dimension_value").reset_index(name="share").assign(dimension="渠道"),
            high_value_users["main_category"].value_counts(normalize=True).rename_axis("dimension_value").reset_index(name="share").assign(dimension="偏好品类"),
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
        "segment_metrics": segment_metrics,
        "high_value_profile": high_value_profile,
    }


def save_tables(tables: dict[str, pd.DataFrame], quality: dict[str, int | str]) -> None:
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
            "segment_metrics",
            "high_value_profile",
        ]:
            tables[name].to_excel(writer, sheet_name=name[:31], index=False)
        pd.DataFrame([quality]).to_excel(writer, sheet_name="data_quality", index=False)


def plot_figures(tables: dict[str, pd.DataFrame]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for filename in ["country_sales.png", "country_aov_index.png"]:
        path = FIG_DIR / filename
        if path.exists():
            path.unlink()

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
    ax.barh(category["category_cn"], category["sales"], color="#0f766e")
    ax.set_title("不同品类销售贡献")
    ax.set_xlabel("销售额")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "category_sales.png", dpi=180)
    plt.close(fig)

    top_products = tables["top_products"].head(10).sort_values("sales")
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
    ax.bar(channel["channel_cn"], channel["order_per_user"], color="#ea580c")
    ax.set_title("不同渠道转化效果：人均订单数")
    ax.set_xlabel("渠道")
    ax.set_ylabel("人均订单数")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "channel_conversion.png", dpi=180)
    plt.close(fig)

    region = tables["region_metrics"].head(12).sort_values("sales")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(region["region"], region["sales"], color="#1d4ed8")
    ax.set_title("TOP12 地区销售额")
    ax.set_xlabel("销售额")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "region_sales.png", dpi=180)
    plt.close(fig)


def write_powerbi_notes() -> None:
    notes = f"""# Power BI 仪表盘搭建说明

本项目已输出 `reports/powerbi/powerbi_dashboard_dataset.xlsx`，可直接导入 Power BI Desktop。

数据来源为 Hugging Face `millat/e-commerce-orders`，许可证为 MIT。该数据集覆盖 2024-04-20 至 2025-04-19，包含品类、渠道、设备、支付方式、客户分层和地址字段。数据集说明中标注其为 synthetic dataset，适合作为电商分析、机器学习和教学项目数据。

数据来源：{DATASET_URL}

建议建立 4 个页面：

1. 经营总览：卡片展示销售额、订单量、用户数、客单价；折线图展示 `monthly_sales` 的销售额和客单价趋势。
2. 商品与品类：条形图展示 `category_sales` 品类贡献；TOP N 条形图展示 `top_products`。
3. 用户分析：堆积柱形图展示 `user_type` 新老用户；矩阵或条形图展示 `rfm_summary` 和 `segment_metrics`。
4. 渠道与地区：柱形图展示 `channel_metrics` 的人均订单数、销售额占比和客单价；条形图展示 `region_metrics` 的销售额和订单量。

核心度量值建议：

```DAX
销售额 = SUM(monthly_sales[sales])
订单量 = SUM(monthly_sales[orders])
用户数 = SUM(monthly_sales[users])
客单价 = DIVIDE([销售额], [订单量])
复购率 = CALCULATE(MAX(repeat_rate[value]), repeat_rate[metric] = "复购率")
```
"""
    (POWERBI_DIR / "powerbi_dashboard_notes.md").write_text(notes, encoding="utf-8")


def write_report(tables: dict[str, pd.DataFrame], quality: dict[str, int | str]) -> None:
    monthly = tables["monthly_sales"]
    category = tables["category_sales"]
    top_products = tables["top_products"]
    repeat_rate = tables["repeat_rate"]
    rfm = tables["rfm_summary"]
    channel = tables["channel_metrics"]
    region = tables["region_metrics"]
    segment_metrics = tables["segment_metrics"]

    total_sales = monthly["sales"].sum()
    total_orders = int(monthly["orders"].sum())
    total_users = int(repeat_rate.loc[repeat_rate["metric"].eq("用户数"), "value"].iloc[0])
    avg_order_value = total_sales / total_orders
    best_month = monthly.loc[monthly["sales"].idxmax()]
    best_category = category.iloc[0]
    best_product = top_products.iloc[0]
    best_channel = channel.iloc[0]
    efficient_channel = channel.sort_values("order_per_user", ascending=False).iloc[0]
    best_region = region.iloc[0]
    weak_region = region[region["orders"] >= 20].iloc[-1]
    best_segment = segment_metrics.iloc[0]
    repurchase = float(repeat_rate.loc[repeat_rate["metric"].eq("复购率"), "value"].iloc[0])
    high_value = rfm[rfm["segment"].eq("高价值用户")]
    high_value_text = "暂无明显高价值用户分组"
    if not high_value.empty:
        high_value_text = (
            f"高价值用户共 {int(high_value['users'].iloc[0])} 人，"
            f"平均消费 {high_value['avg_monetary'].iloc[0]:.2f} 美元，"
            f"平均购买 {high_value['avg_frequency'].iloc[0]:.2f} 次。"
        )

    report = f"""# 电商用户行为与销售数据分析报告

## 一、数据来源

本项目已替换为 2024 年之后的数据集：Hugging Face 的 **millat/e-commerce-orders**。数据覆盖 **2024-04-20 至 2025-04-19**，共 {quality['raw_rows']} 条订单，字段包含订单、客户、商品、品类、价格、数量、订单日期、发货日期、配送状态、支付方式、设备类型、营销渠道、地址和客户分层。

数据来源：{DATASET_URL}

许可证：MIT。

重要说明：该数据集的数据卡明确标注为 synthetic dataset，也就是近年公开合成电商订单数据。它不是某家企业公开的真实流水，但字段完整、时间较新，适合用来展示电商分析作品集能力。

## 二、数据清洗

清洗过程中完成了以下处理：

- 统一订单日期和发货日期为标准日期时间格式。
- 检查订单号、客户 ID、商品 ID、品类、价格、数量、渠道、地址等关键字段缺失情况。
- 删除关键字段缺失记录，清洗后保留 {quality['rows_after_required_drop']} 行。
- 按订单号识别并删除重复订单 {quality['duplicate_orders_removed']} 行。
- 过滤价格小于等于 0、数量小于等于 0 的异常记录。
- 计算订单金额 `order_amount = price * quantity`。
- 计算发货间隔 `shipping_days = shipping_date - order_date`。
- 将英文品类、渠道和客户分层映射为中文展示字段。
- 从收货地址中提取州/地区字段，用于地区销售分析。
- 按客户历史订单顺序计算复购标记 `is_repeat_order`。

清洗后有效订单为 {quality['clean_rows']} 行，覆盖 {quality['valid_users']} 位客户。

## 三、核心经营指标

- 总销售额：{total_sales:,.2f} 美元
- 总订单量：{total_orders:,} 单
- 有效用户数：{total_users:,} 人
- 客单价：{avg_order_value:,.2f} 美元
- 复购率：{repurchase:.2%}
- 销售峰值月份：{best_month['month']}，销售额 {best_month['sales']:,.2f} 美元

从整体看，订单覆盖完整 12 个月，适合做月度趋势和渠道对比。销售峰值月份为 {best_month['month']}，需要结合渠道投放、品类结构和客户分层继续拆解。

## 四、销售分析

### 1. 每月销售额趋势

月度销售额整体波动较平稳，说明样本没有极端大促峰值。若用于真实业务复盘，可以进一步叠加促销日历、广告预算和库存变化解释峰谷。

![每月销售额与客单价趋势](figures/monthly_sales_aov.png)

### 2. 不同品类销售贡献

销售贡献最高的品类是 **{best_category['category_cn']}**，销售额为 {best_category['sales']:,.2f} 美元，占比 {best_category['sales_share']:.2%}。该品类应优先关注毛利、库存周转和渠道投放效率。

![不同品类销售贡献](figures/category_sales.png)

### 3. TOP 商品分析

销售额最高的商品是 **{best_product['product_name']}**，销售额为 {best_product['sales']:,.2f} 美元，销量 {int(best_product['quantity'])} 件。TOP 商品适合做组合推荐、广告素材主推和复购提醒。

![TOP 商品分析](figures/top_products.png)

## 五、用户分析

### 1. 新老用户占比

新老用户结构可以帮助判断增长质量。若新用户占比高但复购不足，说明获客后沉淀弱；若老用户占比高但新客不足，则需要加大拉新渠道测试。

![新老用户占比](figures/new_old_users.png)

### 2. 用户复购率

当前复购率为 **{repurchase:.2%}**。复购率较高说明样本中客户重复下单明显，适合进一步做会员分层、复购券和自动化触达。

### 3. RFM 用户分层

{high_value_text}

![RFM 用户分层](figures/rfm_segments.png)

高价值用户的特征是近期购买、频次高、累计消费高。建议优先配置会员权益、专属折扣、组合推荐和新品提前触达。

### 4. 高价值用户画像

高价值用户画像从地区、渠道和偏好品类三个维度输出在 `high_value_profile.csv` 中，可直接用于 Power BI 的画像页。

客户分层中销售额最高的是 **{best_segment['customer_segment_cn']}**，销售额为 {best_segment['sales']:,.2f} 美元，客单价为 {best_segment['avg_order_value']:.2f} 美元。

## 六、渠道与地区分析

### 1. 不同渠道转化效果

销售额最高的渠道是 **{best_channel['channel_cn']}**，销售额为 {best_channel['sales']:,.2f} 美元，占比 {best_channel['sales_share']:.2%}；人均订单数最高的渠道是 **{efficient_channel['channel_cn']}**，人均订单数为 {efficient_channel['order_per_user']:.2f}。

![渠道转化效果](figures/channel_conversion.png)

### 2. 不同地区销售额和订单量

销售额最高地区是 **{best_region['region']}**，销售额为 {best_region['sales']:,.2f} 美元；在订单量不少于 20 单的地区中，销售额较低的地区之一是 **{weak_region['region']}**，销售额为 {weak_region['sales']:,.2f} 美元。

![地区销售额](figures/region_sales.png)

### 3. 表现差异较大的地区或渠道

渠道上，销售额第一和人均订单数第一可能不同，说明“规模”和“效率”要分开看。地区上，头部地区贡献明显高于尾部地区，后续可以结合物流时效、客户分层和品类偏好继续拆解。

## 七、业务建议

1. 对销售贡献最高的品类提高库存保障，并围绕 TOP 商品设计组合推荐。
2. 对高价值用户建立 RFM 运营名单，配置专属券、新品提前购和复购提醒。
3. 对高销售渠道继续拆解客单价和人均订单数，避免只按销售额分配预算。
4. 对人均订单数高但销售规模较小的渠道做预算小幅放大测试。
5. 对弱势地区先检查配送时效、品类偏好和渠道覆盖，再决定是否扩大投放。
6. Power BI 仪表盘建议按“经营总览、商品品类、用户分层、渠道地区”四页组织。

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
