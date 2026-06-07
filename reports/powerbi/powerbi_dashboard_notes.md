# Power BI 仪表盘搭建说明

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
