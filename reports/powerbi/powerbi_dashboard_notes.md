# Power BI 仪表盘搭建说明

本项目已输出 `reports/powerbi/powerbi_dashboard_dataset.xlsx`，可直接导入 Power BI Desktop。

数据来源为 Hugging Face `millat/e-commerce-orders`，许可证为 MIT。该数据集覆盖 2024-04-20 至 2025-04-19，包含品类、渠道、设备、支付方式、客户分层和地址字段。数据集说明中标注其为 synthetic dataset，适合作为电商分析、机器学习和教学项目数据。

数据来源：https://huggingface.co/datasets/millat/e-commerce-orders

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
