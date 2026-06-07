---
license: mit
language:
- en
pretty_name: E-commerce Customer Order Behavior Dataset
size_categories:
- 10K<n<100K
---
# E-commerce Customer Order Behavior Dataset

A synthetic e-commerce dataset containing 10,000 orders with realistic customer behavior patterns, suitable for e-commerce analytics and machine learning tasks.

## Dataset Card for E-commerce Orders

### Dataset Summary

This dataset simulates customer order behavior in an e-commerce platform, containing detailed information about orders, customers, products, and delivery patterns. The data is synthetically generated with realistic distributions and patterns.

### Supported Tasks

- `regression`: Predict order quantities or prices
- `classification`: Predict delivery status or customer segments
- `clustering`: Identify customer behavior patterns
- `time-series-forecasting`: Analyze order patterns over time

### Languages

Not applicable (tabular data)

### Dataset Structure

#### Data Instances

Each instance represents a single e-commerce order with the following fields:

```python
{
    'order_id': '5ea92c47-c5b2-4bdd-8a50-d77efd77ec89',
    'customer_id': 2350,
    'product_id': 995,
    'category': 'Electronics',
    'price': 403.17,
    'quantity': 3,
    'order_date': '2024-04-20 14:59:58.897063',
    'shipping_date': '2024-04-22 14:59:58.897063',
    'delivery_status': 'Delivered',
    'payment_method': 'PayPal',
    'device_type': 'Mobile',
    'channel': 'Paid Search',
    'shipping_address': '72166 Cunningham Crescent East Nicholasside Mississippi 85568',
    'billing_address': '38199 Edwin Plain Johnborough Maine 81826',
    'customer_segment': 'Returning'
}
```

#### Data Fields

| Field Name | Type | Description | Value Range |
|------------|------|-------------|-------------|
| order_id | string | Unique order identifier (UUID4) | - |
| customer_id | int | Customer identifier | 1-3,000 |
| product_id | int | Product identifier | 1-1,000 |
| category | string | Product category | Electronics, Clothing, Home, Books, Beauty, Toys |
| price | float | Product price | $5.00-$500.00 |
| quantity | int | Order quantity | 1-10 |
| order_date | datetime | Order placement timestamp | Last 12 months |
| shipping_date | datetime | Shipping timestamp | 1-7 days after order_date |
| delivery_status | string | Delivery status | Pending, Shipped, Delivered, Returned |
| payment_method | string | Payment method used | Credit Card, PayPal, Debit Card, Apple Pay, Google Pay |
| device_type | string | Ordering device | Desktop, Mobile, Tablet |
| channel | string | Marketing channel | Organic, Paid Search, Email, Social |
| shipping_address | string | Delivery address | Street, City, State, ZIP |
| billing_address | string | Billing address | Street, City, State, ZIP |
| customer_segment | string | Customer type | New, Returning, VIP |

#### Data Splits

This dataset is provided as a single CSV file without splits.

### Dataset Creation

#### Source Data

This is a synthetic dataset generated using Python with pandas, numpy, and Faker libraries. The data generation process ensures:

- Realistic customer behavior patterns
- Proper data distributions
- Valid relationships between fields
- Realistic address formatting

#### Annotations

No manual annotations (synthetic data)

### Considerations for Using the Data

#### Social Impact of Dataset

This dataset is designed for:
- Development of e-commerce analytics systems
- Testing of order processing systems
- Training of machine learning models for e-commerce
- Educational purposes in data science

#### Discussion of Biases

As a synthetic dataset, care has been taken to:
- Use realistic distributions for order patterns
- Maintain proper relationships between dates
- Create realistic customer segments
- Avoid demographic biases in address generation

However, users should note that:
- The data patterns are simplified compared to real e-commerce data
- The customer behavior patterns are based on general assumptions
- Geographic distribution might not reflect real-world patterns

### Dataset Statistics

Total Records: 10,000

Distribution Statistics:
- Delivery Status:
  - Delivered: 70%
  - Shipped: 20%
  - Pending: 5%
  - Returned: 5%

- Customer Segments:
  - VIP: ~15%
  - Returning: ~35%
  - New: ~50%

### Loading and Usage

Using Huggingface Datasets:

```python
from datasets import load_dataset

dataset = load_dataset("path/to/e-commerce-orders")

# Example: Load as pandas DataFrame
df = dataset['train'].to_pandas()

# Example: Access specific columns
orders = dataset['train']['order_id']
prices = dataset['train']['price']
```

### Data Quality

The dataset has been validated to ensure:
- No missing values
- Proper value ranges
- Valid categorical values
- Proper date relationships
- Unique order IDs
- Valid address formats

### Licensing Information

This dataset is released under the MIT License.

### Citation Information

If you use this dataset in your research, please cite:

```
@dataset{ecommerce_orders_2024,
  author = {MD MILLAT HOSEN},
  title = {E-commerce Customer Order Behavior Dataset},
  year = {2024},
  publisher = {Hugging Face},
  journal = {Hugging Face Data Repository},
  howpublished = {\url{https://huggingface.co/datasets/millat/e-commerce-orders}}
}
```

### Contributions

Thanks to all the contributors who helped create and maintain this dataset.