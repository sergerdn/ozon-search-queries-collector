# Ozon Search Queries Collector

Ozon Search Queries Collector is a `proof of concept` project designed to collect search query
data from [What to Sell on Ozon](https://data.ozon.ru/app/search-queries). It provides insights into trending products
and related search behavior on the Ozon marketplace.

![What to Sell on Ozon](./docs/images/data_ozon_ru_search_queries.png "What to Sell on Ozon")

## Features

This project collects detailed search query data from Ozon:

### Meta data:

- **`_query_keyword`**: The initial keyword used to generate the data.
- **`_scraped_at`**: Timestamp of when the data was scraped.

### Scraped data:

- **`avgCaRub`**: Average price (in rubles) per query, representing the typical price range for products
  associated with the search query.
- **`avgCountItems`**: The average number of products appearing in search results for the query.
- **`ca`**: The cart conversion rate, showing how frequently users add products related to the query to their shopping
  cart.
- **`count`**: The popularity of the search query, measured by the total number of times it was searched.
- **`itemsViews`**: The average number of product views for items appearing in search results for the query.
- **`query`**: The actual search query string entered by users.
- **`uniqQueriesWCa`**: The number of unique queries where users added products to their cart.
- **`uniqSellers`**: The number of unique sellers offering products related to the query.

## Setup

### Prerequisites

- Python 3.10+.
- Poetry.
- Google Chrome.

### Installation

1. Clone the repository:
   ```bash
   git clone git@github.com:sergerdn/ozon-search-queries-collector.git
   cd ozon-search-queries-collector
   ```
2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Configure your environment variables in `.env.development`:
    - `BROWSER_PROFILE_STORAGE_DIR`: Directory for persistent browser profiles.

### Usage

**NOTE**: If you're running the spider from the command line, make sure the required environment variables are correctly
set. You can set them manually using the following command:

```bash
export BROWSER_PROFILE_STORAGE_DIR="/path/to/directory"
```

This will ensure the necessary environment variables are available for the spider to run correctly.

To run the spider with an initial keyword and output the results to a file, use the following command:

```bash
scrapy crawl ozon_data_query_spider -a initial_query_keyword="дозатор для жидкого мыла" -o items.json
```

To enable **depth parsing** (i.e., parsing multiple queries from the initial search result), use the following command:

```bash
scrapy crawl ozon_data_query_spider -a initial_query_keyword="дозатор для жидкого мыла" \
       -o items.json -a parse_in_depth=True -a query_popularity_threshold=10
```

### First-Time Setup

When running the script for the first time, you need to **log in manually** to the Ozon analytics service to grant the
spider access to the necessary data.

Follow these steps:

1. **Run the script for the first time**:
   ```bash
   scrapy crawl ozon_data_query_spider -a initial_query_keyword="дозатор для жидкого мыла"
   ```
2. **Manual Login**: The browser will open automatically, prompting you to log in to Ozon. Enter your credentials and
   complete the login process.
3. **Save the Session**: After logging in, **close the browser**. This action saves the session data to the persistent
   browser profile, enabling future automated logins.
4. **Re-run the script**:
   ```bash
   scrapy crawl ozon_data_query_spider -a initial_query_keyword="дозатор для жидкого мыла"
   ```

From the second run onward, the script will reuse the saved session to access the Ozon service.

## Output

The output will be in JSON format, containing structured data for the keyword and its related search queries.

Example:

```json
[
  {
    "_query_keyword": "дозатор для жидкого мыла",
    "_scraped_at": "2024-12-16T09:39:08.157158",
    "avgCaRub": 1050.92,
    "avgCountItems": 6592.7656,
    "ca": 0.2962,
    "count": 2907,
    "itemsViews": 60.26694,
    "query": "сенсорный дозатор для жидкого мыла",
    "uniqQueriesWCa": 861,
    "uniqSellers": 35.900585
  },
  {
    "_query_keyword": "дозатор для жидкого мыла",
    "_scraped_at": "2024-12-16T09:39:08.158146",
    "avgCaRub": 436.66,
    "avgCountItems": 21091.857,
    "ca": 0.3251,
    "count": 1261,
    "itemsViews": 43.363205,
    "query": "жидкое мыло для дозатора",
    "uniqQueriesWCa": 410,
    "uniqSellers": 18.18874
  }
]
```

## Project Components

### Spiders

- **`ozon_data_query_spider`**:
    - The main spider used to scrape Ozon search query data.
    - Supports Playwright for handling dynamic pages.

### Templates

- Jinja2 templates are used to inject dynamic JavaScript for data extraction.

### Items

- **`OzonCollectorItem`**:
    - Defines the structure for the scraped data.

## Logs and Execution Time

The spider includes enhanced logging and execution time tracking for debugging and performance monitoring.

```txt
INFO: Execution time for execute_js_in_browser: 5.04 seconds.
INFO: Execution time for execute_js_in_browser: 5.01 seconds.
```

```txt
INFO: Crawled 1 pages (at 1 pages/min), scraped 1058 items (at 1058 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 1209 items (at 151 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 1375 items (at 166 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 1428 items (at 53 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 1547 items (at 119 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 1805 items (at 258 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 1842 items (at 37 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 2961 items (at 1119 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 3084 items (at 123 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 3202 items (at 118 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 3477 items (at 275 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 3558 items (at 81 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 4070 items (at 512 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 4157 items (at 87 items/min)
INFO: Crawled 1 pages (at 0 pages/min), scraped 4502 items (at 345 items/min)
```

---

## Spider Performance

The collection time of the spider depends on factors like the number of accounts used, network speed, and other
variables.

For example, when running the spider with the following settings:

```bash
scrapy crawl ozon_data_query_spider -a initial_query_keyword="дозатор для жидкого мыла" \
       -o items.json -a parse_in_depth=True -a query_popularity_threshold=50
```

The spider worked for approximately **10 minutes**, and around **10,000 items** were collected.

### Example Calculation

If Ozon allows collecting **10,000 queries per account per 24 hours**:

- **With 100 browsers** running, processing **10 million keywords** would take approximately **34.7 days**, and you
  would need **29 accounts**.

- **With 500 browsers** running, processing **40 million keywords** would take approximately **6.94 days**, and you
  would need **116 accounts**.

**Note**: These calculations are estimated based on sample test data and may vary depending on factors like network
speed, server load, and other conditions.

---

## Tips and Tricks

It is very likely that Ozon uses an `anti-bot system to prevent scraping`.

![We've detected suspicious activity](./docs/images/ozon_blocked_24h.png "We've detected suspicious activity")

Here are some things to keep in mind when scraping Ozon:

- **Multiple Browser Profiles**: If you run multiple browsers simultaneously using the same account across all browser
  profiles, Ozon can quickly detect the activity and log the account out of all profiles.
- **Rapid JavaScript Execution**: If JavaScript code execution within the same browser profile collects data too
  quickly, it may trigger Ozon detection system, causing the account to be logged out.
- **Frequent Page Refreshes**: If the page is refreshed too frequently within the same browser profile, it may also
  trigger Ozon anti-bot system, resulting in the account being logged out.
- **High-Volume Scraping**: If a large volume of items is collected within a short time frame per account, Ozon may
  block the account for up to 24 hours.

---
