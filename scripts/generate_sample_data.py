from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"


def main() -> None:
    rng = np.random.default_rng(20260607)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    users = [f"U{idx:05d}" for idx in range(1, 1401)]
    products = pd.DataFrame(
        [
            ("P001", "无线蓝牙耳机", "数码配件", 189),
            ("P002", "机械键盘", "数码配件", 299),
            ("P003", "智能手表", "数码配件", 529),
            ("P004", "补水面膜套装", "美妆个护", 89),
            ("P005", "氨基酸洗面奶", "美妆个护", 69),
            ("P006", "精华液礼盒", "美妆个护", 269),
            ("P007", "轻薄羽绒服", "服饰鞋包", 399),
            ("P008", "通勤帆布包", "服饰鞋包", 159),
            ("P009", "跑步运动鞋", "服饰鞋包", 349),
            ("P010", "即食燕麦组合", "食品饮料", 59),
            ("P011", "精品挂耳咖啡", "食品饮料", 79),
            ("P012", "坚果礼盒", "食品饮料", 129),
            ("P013", "人体工学椅", "家居生活", 899),
            ("P014", "香薰加湿器", "家居生活", 199),
            ("P015", "收纳箱套装", "家居生活", 99),
        ],
        columns=["product_id", "product_name", "category", "base_price"],
    )

    channels = ["自然搜索", "信息流广告", "直播间", "会员短信", "社群团购"]
    channel_prob = np.array([0.28, 0.24, 0.20, 0.16, 0.12])
    regions = ["华东", "华南", "华北", "华中", "西南", "西北", "东北"]
    region_prob = np.array([0.26, 0.21, 0.18, 0.12, 0.10, 0.06, 0.07])

    dates = pd.date_range("2025-01-01", "2025-12-31", freq="D")
    month_weight = {
        1: 0.90,
        2: 0.78,
        3: 0.96,
        4: 1.02,
        5: 1.10,
        6: 1.28,
        7: 1.05,
        8: 1.08,
        9: 1.18,
        10: 1.12,
        11: 1.85,
        12: 1.45,
    }
    weights = np.array([month_weight[d.month] for d in dates], dtype=float)
    weights /= weights.sum()

    rows = []
    for idx in range(1, 3601):
        order_date = pd.Timestamp(rng.choice(dates, p=weights))
        product = products.sample(1, random_state=int(rng.integers(1, 1_000_000))).iloc[0]
        user_id = rng.choice(users)
        channel = rng.choice(channels, p=channel_prob)
        region = rng.choice(regions, p=region_prob)

        quantity = int(rng.choice([1, 1, 1, 2, 2, 3, 4], p=[0.32, 0.20, 0.16, 0.16, 0.08, 0.06, 0.02]))
        price_noise = rng.normal(1, 0.08)
        if order_date.month in [6, 11, 12]:
            discount = rng.choice([0.72, 0.80, 0.88, 0.95], p=[0.20, 0.34, 0.30, 0.16])
        else:
            discount = rng.choice([0.85, 0.92, 1.00], p=[0.18, 0.26, 0.56])

        unit_price = max(9, round(product["base_price"] * price_noise * discount, 2))
        payment_status = rng.choice(["已支付", "已取消", "退款"], p=[0.91, 0.06, 0.03])

        rows.append(
            {
                "order_id": f"O{idx:06d}",
                "user_id": user_id,
                "order_date": order_date,
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "category": product["category"],
                "quantity": quantity,
                "unit_price": unit_price,
                "channel": channel,
                "region": region,
                "payment_status": payment_status,
            }
        )

    df = pd.DataFrame(rows)

    # Inject realistic data-quality issues for the cleaning pipeline.
    duplicate_rows = df.sample(45, random_state=9).copy()
    df = pd.concat([df, duplicate_rows], ignore_index=True)

    for col, rate in {"channel": 0.018, "region": 0.012, "unit_price": 0.01, "order_date": 0.006}.items():
        mask = rng.random(len(df)) < rate
        df.loc[mask, col] = np.nan

    mixed_dates = []
    for value in df["order_date"]:
        if pd.isna(value):
            mixed_dates.append(value)
            continue
        fmt = rng.choice(["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日"])
        mixed_dates.append(pd.Timestamp(value).strftime(fmt))
    df["order_date"] = mixed_dates

    df.to_csv(RAW_DIR / "ecommerce_orders_raw.csv", index=False, encoding="utf-8-sig")
    products.to_csv(RAW_DIR / "product_catalog.csv", index=False, encoding="utf-8-sig")
    print(f"raw rows: {len(df)}")
    print(f"raw file: {RAW_DIR / 'ecommerce_orders_raw.csv'}")


if __name__ == "__main__":
    main()
