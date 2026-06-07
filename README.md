# 电商用户行为与销售数据分析项目

这是一个完整的中文电商数据分析项目，覆盖数据清洗、指标计算、销售分析、用户分析、渠道与地区分析、matplotlib 可视化、Power BI 仪表盘数据准备和中文分析报告。

## 项目亮点

- 清洗缺失值、重复订单和混合日期格式。
- 计算订单金额、客单价、复购标记、复购率和 RFM 用户分层。
- 分析月度销售趋势、品类贡献、TOP 商品、客单价变化、新老用户占比、渠道效率和地区表现。
- 使用 matplotlib 输出中文图表。
- 输出 Power BI 可直接导入的数据集和仪表盘搭建说明。
- 输出一份可直接展示的中文业务分析报告。

## 目录结构

```text
.
├── data
│   ├── raw                         # 原始模拟订单数据
│   └── processed                   # 清洗后数据与指标结果
├── reports
│   ├── figures                     # matplotlib 图表
│   ├── powerbi                     # Power BI 导入数据集和说明
│   └── analysis_report.md          # 中文分析报告
├── scripts
│   ├── generate_sample_data.py     # 生成示例电商订单数据
│   └── analyze_ecommerce.py        # 清洗、指标、可视化、报告
└── requirements.txt
```

## 快速运行

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\generate_sample_data.py
.\.venv\Scripts\python.exe scripts\analyze_ecommerce.py
```

## 关键产出

- 中文分析报告：[reports/analysis_report.md](reports/analysis_report.md)
- Power BI 数据集：[reports/powerbi/powerbi_dashboard_dataset.xlsx](reports/powerbi/powerbi_dashboard_dataset.xlsx)
- Power BI 搭建说明：[reports/powerbi/powerbi_dashboard_notes.md](reports/powerbi/powerbi_dashboard_notes.md)
- 清洗后订单数据：[data/processed/clean_orders.csv](data/processed/clean_orders.csv)

## 分析口径

- 仅统计 `payment_status = 已支付` 的有效订单。
- 订单金额 = 商品数量 × 商品单价。
- 客单价 = 销售额 ÷ 订单量。
- 复购用户 = 至少有 2 笔有效支付订单的用户。
- RFM 分层基于最近一次购买间隔、购买频次和累计消费金额。

## Power BI 仪表盘建议

Power BI Desktop 中导入 `reports/powerbi/powerbi_dashboard_dataset.xlsx`，建议建立以下页面：

1. 经营总览：销售额、订单量、用户数、客单价、月度销售趋势。
2. 商品与品类：品类销售贡献、TOP 商品排行。
3. 用户分析：新老用户占比、复购率、RFM 分层。
4. 渠道与地区：渠道转化效果、地区销售额和订单量。

## 业务结论摘要

项目数据显示，促销月份对销售额有明显拉动，但客单价受折扣影响不一定同步提升。高价值用户具备近期购买、高频购买和高消费特征，应优先用于会员运营和新品触达。渠道评估不能只看销售额，还要结合人均订单数和客单价判断真实转化效率。地区差异建议从物流、品类偏好和投放覆盖三个方向继续拆解。
