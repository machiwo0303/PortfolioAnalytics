import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import sys


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
def get_purchase_price(ticker, purchase_date):
    # ★ purchase_date が Timestamp ならそのまま、str なら変換
    if isinstance(purchase_date, str):
        dt = datetime.strptime(purchase_date, "%Y/%m/%d")
    else:
        dt = purchase_date  # Timestamp のまま使う

    df = ticker.history(start=dt, end=dt + timedelta(days=1))
    if len(df) == 0:
        return None
    return df["Close"].iloc[0]



# ============================
# メイン処理（改修版）
# ============================
def analyze_portfolio(mykabu_csv, target_yyyymm):
    # ----------------------------
    # ① mykabu の対象年月だけ抽出
    # ----------------------------
    df_pos = pd.read_csv(
        mykabu_csv,
        header=None,
        names=["code", "shares", "purchase_date"]
    )

    # ★ 日付を datetime に変換（1桁月/日でも確実に処理）
    df_pos["purchase_date"] = pd.to_datetime(df_pos["purchase_date"])

    # ★ yyyymm を安全に生成
    df_pos["yyyymm"] = df_pos["purchase_date"].dt.strftime("%Y%m")

    # ★ 指定年月だけ抽出
    df_pos_target = df_pos[df_pos["yyyymm"] == target_yyyymm]

    if df_pos_target.empty:
        print(f"{target_yyyymm} の購入データがありません。")
        return


    # ----------------------------
    # ② 既存 portfolio_result を読み込み
    # ----------------------------
    #df_existing = pd.read_csv(portfolio_csv)

    # 合計行を除外
    #df_existing = df_existing[df_existing["銘柄コード"] != "合計"]

    # ----------------------------
    # ③ 対象年月の銘柄だけ再計算
    # ----------------------------
    results = []
    today_str = datetime.today().strftime("%Y/%m/%d")

    for _, row in df_pos_target.iterrows():
        code = row["code"]
        shares = row["shares"]
        purchase_date = row["purchase_date"]

        symbol = f"{code}.T"
        ticker = yf.Ticker(symbol)

        info = ticker.info
        company = info.get("longName", "")
        sector = info.get("sector", "")

        purchase_price = get_purchase_price(ticker, purchase_date)

        hist = ticker.history(period="1d")
        current_price = hist["Close"].iloc[0] if len(hist) > 0 else None

        last_year_div = get_last_year_dividend(ticker)
        total_dividend = last_year_div * shares
        total_yield = last_year_div / current_price if current_price else None
        purchase_yield = last_year_div / purchase_price if purchase_price else None

        acquisition_value = purchase_price * shares if purchase_price else None
        market_value = current_price * shares if current_price else None
        profit = market_value - acquisition_value if (market_value and acquisition_value) else None
        profit_rate = profit / acquisition_value if (profit and acquisition_value) else None

        results.append({
            "銘柄コード": code,
            "会社名": company,
            "購入株数": shares,
            "購入日": purchase_date,
            "購入時株価": purchase_price,
            "購入時配当利回り": purchase_yield,
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

    df_new = pd.DataFrame(results)

    # ----------------------------
    # ④ 既存データと結合
    # ----------------------------
    # df_all = pd.concat([df_existing, df_new], ignore_index=True)

    # ----------------------------
    # ⑤ 合計行を再計算
    # ----------------------------
    total_dividend_sum = df_new["トータル配当金"].sum()
    total_market_value = df_new["評価額"].sum()
    total_acquisition_value = df_new["取得額"].sum()

    summary_row = {
        "銘柄コード": "合計",
        "会社名": "",
        "業種": "",
        "購入株数": df_new["購入株数"].sum(),
        "購入日": "",
        "購入時株価": "",
        "購入時配当利回り": total_dividend_sum / total_acquisition_value if total_acquisition_value else None,
        "現在日": "",
        "現在株価": "",
        "直近1年配当金": "",
        "トータル配当金": total_dividend_sum,
        "配当利回り": total_dividend_sum / total_market_value if total_market_value else None,
        "取得額": total_acquisition_value,
        "評価額": total_market_value,
        "損益": df_new["損益"].sum(),
        "損益率": df_new["損益"].sum() / total_acquisition_value if total_acquisition_value else None
    }

    df_new = pd.concat([df_new, pd.DataFrame([summary_row])], ignore_index=True)

    # ----------------------------
    # ⑥ CSV 保存
    # ----------------------------
    output_name = f"portfolio_result_{target_yyyymm}.csv"
    df_new.to_csv(output_name, index=False, encoding="utf-8-sig")

    print(f"\nCSV に保存しました → {output_name}")
    return df_new


if __name__ == "__main__":
    mykabu_csv = sys.argv[1]
    #portfolio_csv = sys.argv[2]
    target_yyyymm = sys.argv[2]
    analyze_portfolio(mykabu_csv, target_yyyymm)
