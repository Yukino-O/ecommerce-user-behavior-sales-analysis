# 电商用户行为与销售数据分析项目

这是一个基于公开真实电商交易数据的中文数据分析项目，覆盖数据清洗、指标计算、销售分析、用户分析、国家/地区分析、matplotlib 可视化、Power BI 仪表盘数据准备和中文分析报告。

## 数据来源

项目使用 UCI Machine Learning Repository 的 Online Retail 数据集：

<https://archive.ics.uci.edu/dataset/352/online+retail>

该数据集记录了一家英国无实体店电商在 2010-12-01 至 2011-12-09 期间的真实交易流水，字段包括订单号、商品编码、商品描述、数量、订单时间、单价、客户 ID 和国家/地区。

原始数据不包含广告渠道、流量来源或转化漏斗字段，因此本项目不伪造渠道结论。渠道相关需求在报告中作为数据限制说明，分析重点改为真实的国家/地区表现差异。

## 项目亮点

- 使用公开真实交易数据，不再使用模拟数据作为主分析来源。
- 清洗缺失客户、取消订单、退货/负数量、非正单价和重复明细行。
- 计算订单金额、客单价、复购标记、复购率和 RFM 用户分层。
- 分析月度销售趋势、衍生品类贡献、TOP 商品、客单价变化、新老用户占比、国家/地区表现差异。
- 使用 matplotlib 输出中文图表。
- 输出 Power BI 可直接导入的数据集和仪表盘搭建说明。

## 目录结构

```text
.
├── data
│   ├── raw                         # UCI 原始真实数据
│   └── processed                   # 清洗后数据与指标结果
├── reports
│   ├── figures                     # matplotlib 图表
│   ├── powerbi                     # Power BI 导入数据集和说明
│   └── analysis_report.md          # 中文分析报告
├── scripts
│   └── analyze_ecommerce.py        # 清洗、指标、可视化、报告
└── requirements.txt
```

## 快速运行

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\analyze_ecommerce.py
```

如果本地没有原始文件，可先下载：

```powershell
Invoke-WebRequest -Uri "https://archive.ics.uci.edu/static/public/352/online+retail.zip" -OutFile "data\raw\online_retail_uci.zip"
Expand-Archive -Path "data\raw\online_retail_uci.zip" -DestinationPath "data\raw\online_retail_uci" -Force
```

## 关键产出

- 中文分析报告：[reports/analysis_report.md](reports/analysis_report.md)
- Power BI 数据集：[reports/powerbi/powerbi_dashboard_dataset.xlsx](reports/powerbi/powerbi_dashboard_dataset.xlsx)
- Power BI 搭建说明：[reports/powerbi/powerbi_dashboard_notes.md](reports/powerbi/powerbi_dashboard_notes.md)
- 清洗后订单数据：[data/processed/clean_orders.csv](data/processed/clean_orders.csv)

## 分析口径

- 仅统计有效购买明细：数量大于 0、单价大于 0，且不是取消/退货订单。
- 订单金额 = 商品数量 × 商品单价。
- 客单价 = 销售额 ÷ 订单量。
- 复购用户 = 至少有 2 笔有效购买订单的用户。
- RFM 分层基于最近一次购买间隔、购买频次和累计消费金额。
- 品类字段由商品描述关键词规则派生，真实业务中应优先使用标准商品类目。

## Power BI 仪表盘建议

Power BI Desktop 中导入 `reports/powerbi/powerbi_dashboard_dataset.xlsx`，建议建立以下页面：

1. 经营总览：销售额、订单量、用户数、客单价、月度销售趋势。
2. 商品与品类：衍生品类销售贡献、TOP 商品排行。
3. 用户分析：新老用户占比、复购率、RFM 分层。
4. 国家/地区分析：国家/地区销售额、订单量、客单价指数。

## 业务结论摘要

真实数据呈现出明显的季节性，2011 年 11 月销售额达到峰值，符合礼品电商在圣诞季前备货和采购集中的业务规律。高价值用户具备近期购买、高频购买和高消费特征，应优先用于重点客户运营。国家/地区之间存在明显销售额和客单价差异，后续应结合物流成本、配送时效和本地需求制定差异化策略。
