# 电商用户行为与销售数据分析项目

这是一个基于 2024 年之后公开电商订单数据的数据分析项目，覆盖数据清洗、指标计算、销售分析、用户分析、渠道分析、地区分析、matplotlib 可视化、Power BI 仪表盘数据准备和中文分析报告。

## 数据来源

项目使用 Hugging Face 的 `millat/e-commerce-orders` 数据集：

<https://huggingface.co/datasets/millat/e-commerce-orders>

数据覆盖 2024-04-20 至 2025-04-19，共 10,000 条订单，字段包括订单号、客户 ID、商品 ID、品类、价格、数量、订单日期、发货日期、配送状态、支付方式、设备类型、营销渠道、收货地址、账单地址和客户分层。许可证为 MIT。

数据集卡片明确说明该数据为 synthetic dataset，即近年公开合成电商订单数据。它不是某家企业公开的真实流水，但字段完整、时间较新，适合展示电商数据分析、机器学习和 BI 项目能力。

## 项目亮点

- 使用 2024-2025 年公开电商订单数据，不再使用 2010-2011 年旧数据集。
- 清洗缺失值、重复订单、异常价格和异常数量。
- 统一订单日期和发货日期格式。
- 计算订单金额、客单价、发货间隔、复购标记、复购率和 RFM 用户分层。
- 分析月度销售趋势、品类贡献、TOP 商品、新老用户占比、高价值用户画像、渠道效果和地区表现。
- 使用 matplotlib 输出中文图表。
- 输出 Power BI 可直接导入的数据集和仪表盘搭建说明。

## 目录结构

```text
.
├── data
│   ├── raw                         # 2024-2025 原始订单数据
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
Invoke-WebRequest -Uri "https://huggingface.co/datasets/millat/e-commerce-orders/resolve/main/ecommerce_orders_clean.csv" -OutFile "data\raw\ecommerce_orders_2024_2025.csv"
Invoke-WebRequest -Uri "https://huggingface.co/datasets/millat/e-commerce-orders/raw/main/README.md" -OutFile "data\raw\ecommerce_orders_2024_2025_README.md"
```

## 关键产出

- 中文分析报告：[reports/analysis_report.md](reports/analysis_report.md)
- Power BI 数据集：[reports/powerbi/powerbi_dashboard_dataset.xlsx](reports/powerbi/powerbi_dashboard_dataset.xlsx)
- Power BI 搭建说明：[reports/powerbi/powerbi_dashboard_notes.md](reports/powerbi/powerbi_dashboard_notes.md)
- 清洗后订单数据：[data/processed/clean_orders.csv](data/processed/clean_orders.csv)

## 分析口径

- 订单金额 = 商品价格 × 购买数量。
- 客单价 = 销售额 ÷ 订单量。
- 复购用户 = 至少有 2 笔订单的客户。
- 发货间隔 = 发货日期 - 下单日期。
- 地区字段从收货地址中提取州/地区。
- RFM 分层基于最近一次购买间隔、购买频次和累计消费金额。

## Power BI 仪表盘建议

Power BI Desktop 中导入 `reports/powerbi/powerbi_dashboard_dataset.xlsx`，建议建立以下页面：

1. 经营总览：销售额、订单量、用户数、客单价、月度销售趋势。
2. 商品与品类：品类销售贡献、TOP 商品排行。
3. 用户分析：新老用户占比、复购率、RFM 分层、高价值用户画像。
4. 渠道与地区：渠道转化效果、地区销售额和订单量。

## 业务结论摘要

项目使用近年订单字段完成从清洗、指标、可视化到业务解释的完整流程。渠道分析同时比较销售额、销售占比、客单价和人均订单数，地区分析用于发现区域差异。高价值用户通过 RFM 识别，可用于会员运营、复购触达和精准推荐。
