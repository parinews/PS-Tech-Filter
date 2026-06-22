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
TOP_N = 50
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
        border = "border-bottom:1px solid #ebebeb;"
        row_html += (
            f"<tr>"
            f"<td style='padding:14px 16px;{border}color:#999;font-size:13px;text-align:center;'>{rank}</td>"
            f"<td style='padding:14px 16px;{border}font-weight:700;font-size:14px;letter-spacing:-0.01em;'>{ticker}</td>"
            f"<td style='padding:14px 16px;{border}font-size:14px;color:#333;'>{name}</td>"
            f"<td style='padding:14px 16px;{border}text-align:right;font-size:14px;font-weight:600;font-variant-numeric:tabular-nums;color:#00a86b;'>{ps:.2f}x</td>"
            f"</tr>"
        )
    count = len(rows)
    return f"""<html>
<body style="margin:0;padding:0;background:#f5f5f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="max-width:620px;margin:0 auto;padding:32px 16px 48px;">

    <!-- Header -->
    <div style="background:#000;border-radius:16px;padding:36px 32px 32px;margin-bottom:24px;">
      <div style="font-size:12px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#00a86b;margin-bottom:12px;">VGT &middot; SaaS Filter</div>
      <h1 style="margin:0 0 8px;font-size:28px;font-weight:800;color:#fff;line-height:1.15;letter-spacing:-0.03em;">
        SaaS P/S Screener 📊
      </h1>
      <p style="margin:0;font-size:15px;color:#aaa;line-height:1.5;">
        {count} software companies from VGT with a P/S ratio between 2.0x and 4.0x &mdash; {today}
      </p>
    </div>

    <!-- Table card -->
    <div style="background:#fff;border-radius:16px;overflow:hidden;border:1px solid #ebebeb;">
      <div style="padding:20px 16px 12px;border-bottom:1px solid #ebebeb;">
        <span style="font-size:12px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#999;">Sorted by P/S ratio &uarr;</span>
      </div>
      <table style="border-collapse:collapse;width:100%;">
        <thead>
          <tr style="background:#fafafa;">
            <th style="padding:10px 16px;text-align:center;font-size:11px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#bbb;">#</th>
            <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#bbb;">Ticker</th>
            <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#bbb;">Company</th>
            <th style="padding:10px 16px;text-align:right;font-size:11px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#bbb;">P/S (TTM)</th>
          </tr>
        </thead>
        <tbody>
          {row_html}
        </tbody>
      </table>
    </div>

    <!-- Footer -->
    <p style="margin:24px 0 0;text-align:center;font-size:12px;color:#bbb;line-height:1.6;">
      Data via Yahoo Finance &middot; Holdings via Vanguard (VGT)<br>
      Industry filter: Software &mdash; Application &amp; Infrastructure
    </p>

  </div>
</body>
</html>"""


def send_email(html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"SaaS Stocks with P/S 2.0x–4.0x — {date.today()}"
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

    filtered = sorted(
        [(t, n, ps) for t, n, ps in results if 2.0 <= ps <= 4.0],
        key=lambda x: x[2]
    )

    print(f"\nSaaS stocks with P/S between 2.0x and 4.0x: {len(filtered)}")
    for rank, (ticker, name, ps) in enumerate(filtered, 1):
        print(f"  {rank:>2}. {ticker:<6} {name:<35} {ps:.2f}x")

    send_email(build_html(filtered))
    print("\nEmail sent.")


if __name__ == "__main__":
    main()
