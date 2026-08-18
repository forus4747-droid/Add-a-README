# Data

## `shopify_apps_2019.csv` / `shopify_categories_2019.csv`

2,510 apps, 3,530 category rows, 287,453 reviews. Source:
[markthomas93/Shopify-App-Store-Data-Science](https://github.com/markthomas93/Shopify-App-Store-Data-Science),
originally from Kaggle. Crawler: [usernam3/shopify-app-store-scraper](https://github.com/usernam3/shopify-app-store-scraper).

**Vintage: 2019** (repo last commit 2019-03-04). The store held 2,510 apps then and now holds
**over 16,000**. Do **not** use the category rankings as a current read on where opportunity is.

Use it for what it actually settles — distribution shape:

| | |
|---|---|
| Mean reviews/app | 128 |
| Median reviews/app | **8** |
| Apps with zero reviews | 13.6% |

Analyse with `python3 research/tools/analyse_dataset.py` from the repo root.
