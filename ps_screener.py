import os
import smtplib
import time
import requests
import yfinance as yf
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TOP_N = 20
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
}


def fetch_vgt_tickers() -> list[str]:
    """Fetch all VGT holdings from Vanguard's official portfolio API (~323 stocks)."""
    url = "https://investor.vanguard.com/investment-products/etfs/profile/api/VGT/portfolio-holding/stock"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    holdings = data["fund"]["entity"]
    return [h["ticker"] for h in holdings if h.get("ticker")]


SAAS_INDUSTRIES = {"Software - Application", "Software - Infrastructure"}


def get_ticker_ps(ticker: str) -> tuple[str, float] | None:
    for attempt in range(3):
        try:
            info = yf.Ticker(ticker).info
            if info.get("industry") not in SAAS_INDUSTRIES:
                return None
            ratio = info.get("priceToSalesTrailing12Months")
            if ratio and ratio > 0:
                return (info.get("shortName", ticker), ratio)
            return None
        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)
    return None


def build_html(rows: list[tuple[str, str, float]]) -> str:
    today = date.today().strftime("%B %d, %Y")
    row_html = ""
    for rank, (ticker, name, ps) in enumerate(rows, 1):
        bg = "#f9f9ff" if rank % 2 == 0 else "#ffffff"
        row_html += (
            f"<tr style='background:{bg};'>"
            f"<td style='padding:9px 14px;border-bottom:1px solid #eee;text-align:center;color:#888;'>{rank}</td>"
            f"<td style='padding:9px 14px;border-bottom:1px solid #eee;font-weight:700;'>{ticker}</td>"
            f"<td style='padding:9px 14px;border-bottom:1px solid #eee;'>{name}</td>"
            f"<td style='padding:9px 14px;border-bottom:1px solid #eee;text-align:right;font-variant-numeric:tabular-nums;'>{ps:.2f}x</td>"
            f"</tr>"
        )
    return f"""<html><body style="font-family:Arial,sans-serif;color:#222;max-width:660px;margin:32px auto;">
<h2 style="color:#1a73e8;margin-bottom:4px;">20 Lowest P/S Ratio Stocks &mdash; {today}</h2>
<p style="color:#666;font-size:13px;margin-top:0;">
  Universe: Vanguard Information Technology ETF (VGT)<br>
  Sorted ascending by trailing-twelve-month Price / Sales ratio.
</p>
<table style="border-collapse:collapse;width:100%;font-size:14px;">
  <thead>
    <tr style="background:#e8eeff;">
      <th style="padding:9px 14px;text-align:center;color:#555;">#</th>
      <th style="padding:9px 14px;text-align:left;color:#555;">Ticker</th>
      <th style="padding:9px 14px;text-align:left;color:#555;">Company</th>
      <th style="padding:9px 14px;text-align:right;color:#555;">P/S (TTM)</th>
    </tr>
  </thead>
  <tbody>
    {row_html}
  </tbody>
</table>
<p style="color:#bbb;font-size:11px;margin-top:18px;">
  Data via Yahoo Finance &middot; Holdings via Vanguard
</p>
</body></html>"""


def send_email(html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Top 20 Lowest P/S Stocks — {date.today()}"
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())


def main() -> None:
    print("Fetching VGT holdings (Vanguard API)…")
    universe = fetch_vgt_tickers()
    print(f"  {len(universe)} tickers from VGT")

    results: list[tuple[str, str, float]] = []
    for i, ticker in enumerate(universe):
        if i and i % 50 == 0:
            time.sleep(1)
        data = get_ticker_ps(ticker)
        if data:
            name, ps = data
            results.append((ticker, name, ps))
        if i % 25 == 0:
            print(f"  {i}/{len(universe)} processed, {len(results)} with P/S data so far")

    results.sort(key=lambda x: x[2])
    top20 = results[:TOP_N]

    print(f"\nTop {TOP_N} lowest P/S:")
    for rank, (ticker, name, ps) in enumerate(top20, 1):
        print(f"  {rank:>2}. {ticker:<6} {name:<35} {ps:.2f}x")

    send_email(build_html(top20))
    print("\nEmail sent.")


if __name__ == "__main__":
    main()
