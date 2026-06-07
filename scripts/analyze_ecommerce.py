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

DATASET_XLSX = RAW_DIR / "online_retail_uci" / "Online Retail.xlsx"
DATASET_URL = "https://archive.ics.uci.edu/dataset/352/online+retail"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def classify_category(description: str) -> str:
    text = str(description).upper()
    rules = [
        ("家居装饰", ["HEART", "CANDLE", "LIGHT", "LANTERN", "FRAME", "CLOCK", "MIRROR", "WREATH", "DECORATION"]),
        ("厨房餐具", ["CUP", "MUG", "PLATE", "BOWL", "TEA", "CAKE", "NAPKIN", "KITCHEN", "CUTLERY", "DOILEY"]),
        ("礼品套装", ["GIFT", "SET", "BOX", "BAG", "WRAP", "RIBBON", "TAG", "CARD"]),
        ("收纳用品", ["BASKET", "STORAGE", "DRAWER", "CABINET", "HOLDER", "TIDY", "RACK"]),
        ("儿童用品", ["CHILD", "BABY", "DOLL", "TOY", "GAME", "LUNCH BOX", "JIGSAW"]),
        ("服饰配件", ["SCARF", "BAG", "PURSE", "NECKLACE", "BRACELET", "CHARM", "HAIR"]),
        ("节日季节", ["CHRISTMAS", "EASTER", "HALLOWEEN", "VALENTINE", "PARTY", "BIRTHDAY"]),
    ]
    for category, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return category
    return "其他商品"


def load_and_clean() -> tuple[pd.DataFrame, dict[str, int | str]]:
    if not DATASET_XLSX.exists():
        raise FileNotFoundError(
            f"未找到真实数据文件：{DATASET_XLSX}。请先下载 UCI Online Retail 数据集。"
        )

    raw = pd.read_excel(DATASET_XLSX)
    quality: dict[str, int | str] = {
        "dataset": "UCI Online Retail",
        "dataset_url": DATASET_URL,
        "raw_rows": len(raw),
    }

    df = raw.rename(
        columns={
            "InvoiceNo": "order_id",
            "StockCode": "product_id",
            "Description": "product_name",
            "Quantity": "quantity",
            "InvoiceDate": "order_datetime",
            "UnitPrice": "unit_price",
            "CustomerID": "user_id",
            "Country": "country",
        }
    )

    df["order_id"] = df["order_id"].astype("string")
    df["product_id"] = df["product_id"].astype("string")
    df["product_name"] = df["product_name"].astype("string").str.strip()
    df["country"] = df["country"].astype("string").str.strip()
    df["order_datetime"] = pd.to_datetime(df["order_datetime"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")

    df["is_cancellation"] = df["order_id"].str.upper().str.startswith("C", na=False)
    quality["cancel_rows"] = int(df["is_cancellation"].sum())
    quality["missing_customer_rows"] = int(df["user_id"].isna().sum())
    quality["negative_or_zero_quantity_rows"] = int((df["quantity"] <= 0).sum())
    quality["non_positive_price_rows"] = int((df["unit_price"] <= 0).sum())

    before_required = len(df)
    df = df.dropna(subset=["order_id", "product_id", "product_name", "order_datetime", "quantity", "unit_price", "user_id", "country"])
    quality["rows_after_required_drop"] = len(df)
    quality["required_rows_removed"] = before_required - len(df)

    before_dedup = len(df)
    df = df.drop_duplicates()
    quality["duplicate_rows_removed"] = before_dedup - len(df)

    df["user_id"] = df["user_id"].astype(int).astype(str)
    df["order_status"] = np.where(df["is_cancellation"] | (df["quantity"] < 0), "取消/退货", "有效购买")
    clean_all = df.copy()
    quality["clean_rows_before_business_filter"] = len(clean_all)

    paid = clean_all[
        (clean_all["order_status"].eq("有效购买"))
        & (clean_all["quantity"] > 0)
        & (clean_all["unit_price"] > 0)
    ].copy()
    paid["order_amount"] = (paid["quantity"] * paid["unit_price"]).round(2)
    paid["month"] = paid["order_datetime"].dt.to_period("M").astype(str)
    paid["order_date"] = paid["order_datetime"].dt.date.astype(str)
    paid["category"] = paid["product_name"].map(classify_category)
    paid = paid.sort_values(["user_id", "order_datetime", "order_id"])
    paid["is_repeat_order"] = paid.groupby("user_id").cumcount().gt(0)
    paid["user_order_no"] = paid.groupby("user_id").cumcount() + 1
    quality["valid_purchase_rows"] = len(paid)
    quality["valid_orders"] = int(paid["order_id"].nunique())
    quality["valid_users"] = int(paid["user_id"].nunique())
    quality["date_min"] = str(paid["order_datetime"].min())
    quality["date_max"] = str(paid["order_datetime"].max())
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
        .head(15)
    )
    top_products["sales"] = top_products["sales"].round(2)

    first_order = df.groupby("user_id")["order_datetime"].min().rename("first_order_datetime")
    user_enriched = df.merge(first_order, on="user_id", how="left")
    user_enriched["user_type"] = np.where(
        user_enriched["order_datetime"].dt.to_period("M").eq(user_enriched["first_order_datetime"].dt.to_period("M")),
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

    analysis_date = df["order_datetime"].max() + pd.Timedelta(days=1)
    rfm = (
        df.groupby("user_id")
        .agg(
            recency=("order_datetime", lambda x: (analysis_date - x.max()).days),
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

    country = (
        df.groupby("country", as_index=False)
        .agg(sales=("order_amount", "sum"), orders=("order_id", "nunique"), users=("user_id", "nunique"))
        .sort_values("sales", ascending=False)
    )
    country["avg_order_value"] = (country["sales"] / country["orders"]).round(2)
    country["sales"] = country["sales"].round(2)

    country_gap = country.copy()
    country_gap["sales_share"] = (country_gap["sales"] / country_gap["sales"].sum()).round(4)
    country_gap["orders_share"] = (country_gap["orders"] / country_gap["orders"].sum()).round(4)
    country_gap["aov_index"] = (country_gap["avg_order_value"] / (df["order_amount"].sum() / df["order_id"].nunique())).round(2)

    high_value_users = rfm[rfm["segment"].eq("高价值用户")].merge(
        df.groupby("user_id").agg(main_country=("country", lambda x: x.mode().iat[0]), favorite_category=("category", lambda x: x.mode().iat[0])),
        on="user_id",
        how="left",
    )
    high_value_profile = pd.concat(
        [
            high_value_users["main_country"].value_counts(normalize=True).rename_axis("dimension_value").reset_index(name="share").assign(dimension="国家/地区"),
            high_value_users["favorite_category"].value_counts(normalize=True).rename_axis("dimension_value").reset_index(name="share").assign(dimension="偏好品类"),
        ],
        ignore_index=True,
    )
    high_value_profile["share"] = high_value_profile["share"].round(4)

    channel_limitation = pd.DataFrame(
        [
            {
                "item": "渠道分析限制",
                "description": "UCI Online Retail 原始数据不包含广告渠道、流量来源或转化漏斗字段，因此本项目不伪造渠道分析，改用真实国家/地区字段做区域表现分析。",
            }
        ]
    )

    return {
        "clean_orders": df,
        "monthly_sales": monthly,
        "category_sales": category,
        "top_products": top_products,
        "user_type": user_type,
        "repeat_rate": repeat_rate,
        "rfm_detail": rfm,
        "rfm_summary": rfm_summary,
        "country_metrics": country,
        "country_gap": country_gap,
        "high_value_profile": high_value_profile,
        "channel_limitation": channel_limitation,
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
            "country_metrics",
            "country_gap",
            "high_value_profile",
            "channel_limitation",
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
    ax.set_title("衍生品类销售贡献")
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

    country = tables["country_metrics"].head(10).sort_values("sales")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(country["country"], country["sales"], color="#1d4ed8")
    ax.set_title("TOP10 国家/地区销售额")
    ax.set_xlabel("销售额")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "country_sales.png", dpi=180)
    plt.close(fig)

    country_gap = tables["country_gap"].head(10).sort_values("aov_index")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(country_gap["country"], country_gap["aov_index"], color="#ea580c")
    ax.axvline(1, color="#334155", linewidth=1)
    ax.set_title("TOP10 国家/地区客单价指数")
    ax.set_xlabel("客单价指数：整体均值=1")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "country_aov_index.png", dpi=180)
    plt.close(fig)


def write_powerbi_notes() -> None:
    notes = """# Power BI 仪表盘搭建说明

本项目已输出 `reports/powerbi/powerbi_dashboard_dataset.xlsx`，可直接导入 Power BI Desktop。

数据来源为 UCI Machine Learning Repository 的 Online Retail 真实交易数据。原始字段包含订单号、商品编码、商品描述、数量、订单时间、单价、客户 ID 和国家/地区，不包含广告渠道或流量来源字段，因此不要在 Power BI 中伪造渠道页。

建议建立 4 个页面：

1. 经营总览：卡片展示销售额、订单量、用户数、客单价；折线图展示 `monthly_sales` 的销售额和客单价趋势。
2. 商品与品类：条形图展示 `category_sales` 衍生品类贡献；TOP N 条形图展示 `top_products`。
3. 用户分析：堆积柱形图展示 `user_type` 新老用户；矩阵或条形图展示 `rfm_summary`。
4. 国家/地区分析：条形图展示 `country_metrics` 的销售额和订单量；用 `country_gap` 展示销售占比、订单占比和客单价指数。

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
    country = tables["country_metrics"]
    country_gap = tables["country_gap"]

    total_sales = monthly["sales"].sum()
    total_orders = int(monthly["orders"].sum())
    total_users = int(repeat_rate.loc[repeat_rate["metric"].eq("用户数"), "value"].iloc[0])
    avg_order_value = total_sales / total_orders
    best_month = monthly.loc[monthly["sales"].idxmax()]
    best_category = category.iloc[0]
    best_product = top_products.iloc[0]
    best_country = country.iloc[0]
    weak_country = country[country["orders"] >= 10].iloc[-1]
    high_aov_country = country_gap[country_gap["orders"] >= 10].sort_values("aov_index", ascending=False).iloc[0]
    repurchase = float(repeat_rate.loc[repeat_rate["metric"].eq("复购率"), "value"].iloc[0])
    high_value = rfm[rfm["segment"].eq("高价值用户")]
    high_value_text = "暂无明显高价值用户分组"
    if not high_value.empty:
        high_value_text = (
            f"高价值用户共 {int(high_value['users'].iloc[0])} 人，"
            f"平均消费 {high_value['avg_monetary'].iloc[0]:.2f} 英镑，"
            f"平均购买 {high_value['avg_frequency'].iloc[0]:.2f} 次。"
        )

    report = f"""# 电商用户行为与销售数据分析报告

## 一、数据来源

本项目已替换为公开真实数据集：UCI Machine Learning Repository 的 **Online Retail** 数据集。该数据集记录了英国一家无实体店电商在 2010-12-01 至 2011-12-09 之间的真实交易流水，原始文件约 54.19 万行，字段包括订单号、商品编码、商品描述、数量、订单时间、单价、客户 ID 和国家/地区。

数据来源：{DATASET_URL}

需要说明的是，原始数据不包含广告渠道、流量来源或转化漏斗字段。因此本报告不伪造渠道结论，渠道部分改为说明数据限制，并重点完成真实的国家/地区表现分析。

## 二、数据清洗

原始数据共有 {quality['raw_rows']} 行记录。清洗过程中完成了以下处理：

- 统一订单时间字段为标准日期时间，并派生月份字段。
- 删除客户 ID、商品、日期、数量、单价等关键字段缺失的记录，保留 {quality['rows_after_required_drop']} 行。
- 识别取消订单和退货记录：取消/退货相关行数为 {quality['cancel_rows']} 行。
- 删除重复明细行 {quality['duplicate_rows_removed']} 行。
- 过滤数量小于等于 0、单价小于等于 0 的记录，仅保留有效购买明细。
- 计算订单金额 `order_amount = quantity * unit_price`。
- 根据客户历史购买顺序计算复购标记 `is_repeat_order`。
- 基于商品描述关键词派生中文品类字段，用于品类贡献分析。

清洗后有效购买明细为 {quality['valid_purchase_rows']} 行，覆盖 {quality['valid_orders']} 个订单和 {quality['valid_users']} 位客户。

## 三、核心经营指标

- 总销售额：{total_sales:,.2f} 英镑
- 总订单量：{total_orders:,} 单
- 有效用户数：{total_users:,} 人
- 客单价：{avg_order_value:,.2f} 英镑
- 复购率：{repurchase:.2%}
- 销售峰值月份：{best_month['month']}，销售额 {best_month['sales']:,.2f} 英镑

销售峰值集中在 2011 年 11 月，符合礼品电商在圣诞季前备货和采购集中的业务规律。客单价与销售额并不完全同步，说明增长既受订单量影响，也受批发客户的大额采购影响。

## 四、销售分析

### 1. 每月销售额趋势

2011 年下半年销售额明显走高，11 月达到峰值。12 月数据只覆盖到 12 月 9 日，不能直接与完整月份比较。

![每月销售额与客单价趋势](figures/monthly_sales_aov.png)

### 2. 不同品类销售贡献

由于 UCI 原始数据没有标准品类字段，本项目根据商品描述派生了中文品类。销售贡献最高的衍生品类是 **{best_category['category']}**，销售额为 {best_category['sales']:,.2f} 英镑，占比 {best_category['sales_share']:.2%}。

![衍生品类销售贡献](figures/category_sales.png)

### 3. TOP 商品分析

销售额最高的商品是 **{best_product['product_name']}**，销售额为 {best_product['sales']:,.2f} 英镑，销量 {int(best_product['quantity'])} 件。TOP 商品往往体现平台主力商品池，应重点关注库存、补货和组合销售。

![TOP 商品分析](figures/top_products.png)

## 五、用户分析

### 1. 新老用户占比

新用户在早期月份占比较高，后续老用户贡献逐步上升，说明该电商存在较强复购和批发客户沉淀。

![新老用户占比](figures/new_old_users.png)

### 2. 用户复购率

当前复购率为 **{repurchase:.2%}**。对于礼品类和批发型电商，复购用户是稳定销售的重要来源。后续运营应重点维护高频和高消费客户。

### 3. RFM 用户分层

{high_value_text}

![RFM 用户分层](figures/rfm_segments.png)

高价值用户的特征是近期购买、购买频次高、累计消费高。建议为该群体配置提前补货提醒、批量采购折扣和重点客户服务。

## 六、国家/地区分析

### 1. 不同国家/地区销售额和订单量

销售额最高的国家/地区是 **{best_country['country']}**，销售额为 {best_country['sales']:,.2f} 英镑；在订单量不少于 10 单的地区中，销售额较低的地区之一是 **{weak_country['country']}**，销售额为 {weak_country['sales']:,.2f} 英镑。

![国家/地区销售额](figures/country_sales.png)

### 2. 表现差异较大的地区

客单价指数最高的国家/地区是 **{high_aov_country['country']}**，指数为 {high_aov_country['aov_index']:.2f}。这说明部分地区虽然订单量不一定最大，但单笔订单价值更高，适合用更精细的客户维护和高价值商品推荐。

![国家/地区客单价指数](figures/country_aov_index.png)

### 3. 渠道分析限制

该真实数据集没有渠道字段，因此不能真实回答“不同渠道转化效果”。如果业务方提供广告渠道、访问来源、点击、加购、支付等漏斗字段，可以继续补充渠道转化率、渠道 ROI、渠道客单价和渠道复购率分析。

## 七、业务建议

1. 重点备货和维护 TOP 商品，尤其在 9-11 月提前做库存计划，避免旺季缺货。
2. 对高价值客户建立 RFM 运营名单，配置批量采购折扣、提前购提醒和专属客服。
3. 对高客单价国家/地区优先推荐礼盒、套装和高毛利商品，提高单客价值。
4. 对低销售地区先排查物流成本、配送时效和本地需求，再决定是否扩大投放。
5. 品类字段目前为规则派生，后续若有真实商品类目，应替换规则分类以提高分析精度。
6. 渠道分析必须依赖真实渠道字段，不建议用随机渠道或人为分配渠道替代。

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
    print(f"valid purchase rows: {len(clean_orders)}")
    print(f"report: {REPORT_DIR / 'analysis_report.md'}")


if __name__ == "__main__":
    main()
