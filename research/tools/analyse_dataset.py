#!/usr/bin/env python3
"""Concentration analysis over the 2019 Shopify App Store dataset.

    python3 analyse_dataset.py

Reports leader share, top-3 share, median vs mean, and tail health per category.
Median is printed beside mean deliberately: the gap between them is the finding.
"""
import statistics as st, sys
import pandas as pd

D = "research/data"
apps = pd.read_csv(f"{D}/shopify_apps_2019.csv", engine="python", on_bad_lines="skip")
cats = pd.read_csv(f"{D}/shopify_categories_2019.csv")
apps["reviews_count"] = pd.to_numeric(apps["reviews_count"], errors="coerce").fillna(0)
df = cats.merge(apps, left_on="app_url", right_on="url", how="inner")

def verdict(s):
    if s["lead_pct"] >= 40: return "CLOSED - one app owns it"
    if s["top3"] >= 65:     return "CLOSED - top 3 own it"
    if s["tail"] < 50:      return "WINNER-TAKE-ALL - tail starving"
    if s["lead_pct"] < 20 and s["tail"] > 200: return "OPEN? - but see scale warning"
    return "CONTESTED"

rows = []
for cat, g in df.groupby("category"):
    r = sorted(g.reviews_count.tolist(), reverse=True)
    tot = sum(r) or 1
    tail = r[4:15] or r[-1:]
    rows.append(dict(cat=cat, n=len(r), lead_pct=round(r[0]/tot*100,1),
                     top3=round(sum(r[:3])/tot*100,1), med=int(st.median(r)),
                     mean=int(st.mean(r)), tail=int(st.median(tail)),
                     zero=round(sum(1 for x in r if x==0)/len(r)*100,1),
                     leader=g.loc[g.reviews_count.idxmax(), "title"][:30]))
rows.sort(key=lambda x: x["lead_pct"])

print("="*112)
print(f"{'CATEGORY':<24}{'APPS':>6}{'LEAD%':>7}{'TOP3%':>7}{'MEDIAN':>8}{'MEAN':>7}{'TAIL':>7}{'ZERO%':>7}  VERDICT")
print("="*112)
for s in rows:
    print(f"{s['cat'][:23]:<24}{s['n']:>6}{s['lead_pct']:>7}{s['top3']:>7}"
          f"{s['med']:>8}{s['mean']:>7}{s['tail']:>7}{s['zero']:>7}  {verdict(s)}")
print("="*112)
print(f"WHOLE STORE            {len(df):>6}{'':>14}{int(df.reviews_count.median()):>8}"
      f"{int(df.reviews_count.mean()):>7}")
print("\nMEAN is ~16x MEDIAN. Any 'average reviews per app' baseline is measuring")
print("the winners, not the market. Never compare a category against a mean.")
print("\nSCALE WARNING: these categories are broad (Store design = 1,025 apps).")
print("Leader share dilutes as the bucket widens, so 'OPEN' here may be an artifact.")
print("Measure at the level buyers actually shop at, not the top-level nav.")
