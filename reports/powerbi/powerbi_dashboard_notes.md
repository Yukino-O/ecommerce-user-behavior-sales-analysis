# Power BI 仪表盘搭建说明

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
