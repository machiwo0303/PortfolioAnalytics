import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import sys


# ============================
# 直近1年の配当金
# ============================
def get_last_year_dividend(ticker):
    end = datetime.today().replace(tzinfo=None)
    start = end - timedelta(days=365)

    df = ticker.dividends
    if df is None or df.empty:
        return 0.0

    df.index = df.index.tz_localize(None)
    df = df[(df.index >= start) & (df.index <= end)]

    return df.sum() if len(df) > 0 else 0.0


# ============================
# 購入日の終値
# ============================
def get_purchase_price(ticker, purchase_date):
    if isinstance(purchase_date, str):
        dt = datetime.strptime(purchase_date, "%Y/%m/%d")
    else:
        dt = purchase_date

    df = ticker.history(start=dt, end=dt + timedelta(days=1))
    if df is None or df.empty:
        return None
    return df["Close"].iloc[0]


# ============================
# ★ メイン処理（全データをまとめて計算）
# ============================
def analyze_portfolio(mykabu_csv):
    # ----------------------------
    # ① mykabu 全データ読み込み
    # ----------------------------
    df_pos = pd.read_csv(
        mykabu_csv,
        header=None,
        names=["code", "shares", "purchase_date"]
    )

    df_pos["purchase_date"] = pd.to_datetime(df_pos["purchase_date"])

    # ----------------------------
    # ② 銘柄ごとにまとめる
    # ----------------------------
    merged_rows = []

    for code, group in df_pos.groupby("code"):
        ticker = yf.Ticker(f"{code}.T")

        total_shares = group["shares"].sum()

        # 最初の購入日で購入時株価を取得
        first_purchase_date = group["purchase_date"].min()
        purchase_price = get_purchase_price(ticker, first_purchase_date)

        acquisition_value = purchase_price * total_shares if purchase_price else None

        merged_rows.append({
            "銘柄コード": code,
            "購入株数": total_shares,
            "購入時株価": purchase_price,
            "取得額": acquisition_value,
            "購入日": first_purchase_date.strftime("%Y/%m/%d")
        })

    df_merged = pd.DataFrame(merged_rows)

    # ----------------------------
    # ③ 最新情報だけ再取得（高速）
    # ----------------------------
    updated_rows = []

    for _, row in df_merged.iterrows():
        code = row["銘柄コード"]
        shares = row["購入株数"]
        acquisition_value = row["取得額"]

        ticker = yf.Ticker(f"{code}.T")

        # 最新株価
        hist = ticker.history(period="1d")
        current_price = hist["Close"].iloc[0] if len(hist) > 0 else None

        # 最新配当
        last_year_div = get_last_year_dividend(ticker)
        dy = last_year_div / current_price if current_price else None

        # 評価額・損益
        market_value = current_price * shares if current_price else None
        profit = market_value - acquisition_value if market_value else None
        profit_rate = profit / acquisition_value if acquisition_value else None

        updated_rows.append({
            "銘柄コード": code,
            "購入株数": shares,
            "取得額": acquisition_value,
            "現在株価": current_price,
            "評価額": market_value,
            "損益": profit,
            "損益率": profit_rate,
            "直近1年配当金": last_year_div,
            "トータル配当金": last_year_div * shares,
            "配当利回り": dy
        })

    df_updated = pd.DataFrame(updated_rows)

    # ----------------------------
    # ④ 合計行を追加
    # ----------------------------
    total_row = {
        "銘柄コード": "合計",
        "購入株数": df_updated["購入株数"].sum(),
        "取得額": df_updated["取得額"].sum(),
        "現在株価": "",
        "評価額": df_updated["評価額"].sum(),
        "損益": df_updated["損益"].sum(),
        "損益率": df_updated["損益"].sum() / df_updated["取得額"].sum(),
        "直近1年配当金": "",
        "トータル配当金": df_updated["トータル配当金"].sum(),
        "配当利回り": df_updated["トータル配当金"].sum() / df_updated["評価額"].sum()
    }

    df_updated = pd.concat([df_updated, pd.DataFrame([total_row])], ignore_index=True)

    # ----------------------------
    # ⑤ CSV 保存
    # ----------------------------
    output_name = "portfolio_result_all.csv"
    df_updated.to_csv(output_name, index=False, encoding="utf-8-sig")

    print(f"\nCSV に保存しました → {output_name}")
    return df_updated


if __name__ == "__main__":
    mykabu_csv = sys.argv[1]
    analyze_portfolio(mykabu_csv)
