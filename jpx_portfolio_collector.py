import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ============================
# 直近1年の配当金を取得
# ============================
def get_last_year_dividend(ticker):
    end = datetime.today().replace(tzinfo=None)
    start = end - timedelta(days=365)

    df = ticker.dividends
    df.index = df.index.tz_localize(None)
    df = df[(df.index >= start) & (df.index <= end)]

    return df.sum() if len(df) > 0 else 0.0


# ============================
# 購入日の終値を取得
# ============================
def get_purchase_price(ticker, purchase_date_str):
    dt = datetime.strptime(purchase_date_str, "%Y/%m/%d")
    df = ticker.history(start=dt, end=dt + timedelta(days=1))
    if len(df) == 0:
        return None
    return df["Close"].iloc[0]


# ============================
# メイン処理
# ============================
def analyze_portfolio(csv_file):
    df_pos = pd.read_csv(
        csv_file,
        header=None,
        names=["code", "shares", "purchase_date"]
    )

    results = []
    today_str = datetime.today().strftime("%Y/%m/%d")  # 現在日付
    today_file = datetime.today().strftime("%Y%m%d")   # ファイル名用

    for _, row in df_pos.iterrows():
        code = row["code"]
        shares = row["shares"]
        purchase_date = row["purchase_date"]

        symbol = f"{code}.T"
        ticker = yf.Ticker(symbol)

        info = ticker.info
        company = info.get("longName", "")
        industry = info.get("industry", "")

        purchase_price = get_purchase_price(ticker, purchase_date)

        hist = ticker.history(period="1d")
        current_price = hist["Close"].iloc[0] if len(hist) > 0 else None

        last_year_div = get_last_year_dividend(ticker)
        total_dividend = last_year_div * shares
        total_yield = last_year_div / current_price if current_price else None

        acquisition_value = purchase_price * shares if purchase_price else None
        market_value = current_price * shares if current_price else None
        profit = market_value - acquisition_value if (market_value and acquisition_value) else None
        profit_rate = profit / acquisition_value if (profit and acquisition_value) else None

        results.append({
            "銘柄コード": code,
            "会社名": company,
            "業種": industry,
            "購入株数": shares,
            "購入日": purchase_date,
            "購入時株価": purchase_price,
            "現在日": today_str,
            "現在株価": current_price,
            "直近1年配当金": last_year_div,
            "トータル配当金": total_dividend,
            "配当利回り": total_yield,
            "取得額": acquisition_value,
            "評価額": market_value,
            "損益": profit,
            "損益率": profit_rate
        })

    df = pd.DataFrame(results)

    # ============================
    # ★ サマリー行（全体集計）
    # ============================
    total_dividend_sum = df["トータル配当金"].sum()
    total_market_value = df["評価額"].sum()
    total_yield_all = total_dividend_sum / total_market_value if total_market_value else None

    summary_row = {
        "銘柄コード": "合計",
        "会社名": "",
        "業種": "",
        "購入株数": df["購入株数"].sum(),
        "購入日": "",
        "購入時株価": "",
        "現在日": "",
        "現在株価": "",
        "直近1年配当金": "",
        "トータル配当金": total_dividend_sum,
        "配当利回り": total_yield_all,
        "取得額": df["取得額"].sum(),
        "評価額": total_market_value,
        "損益": df["損益"].sum(),
        "損益率": df["損益"].sum() / df["取得額"].sum()
                 if df["取得額"].sum() else None
    }

    df = pd.concat([df, pd.DataFrame([summary_row])], ignore_index=True)

    # ============================
    # ★ CSV 保存（YYYYMMDD 付き）
    # ============================
    output_name = f"portfolio_result_{today_file}.csv"
    df.to_csv(output_name, index=False, encoding="utf-8-sig")

    return df


if __name__ == "__main__":
    df = analyze_portfolio("sample.csv")
    print(df)
    print("\nCSV に保存しました → portfolio_result_YYYYMMDD.csv")
