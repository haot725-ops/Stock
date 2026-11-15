"""
VN Stock Analyst API
FastAPI backend — dữ liệu giá từ nguồn công khai (DNSE chart, CafeF).
 BCTC/ratios: lấy và chuẩn hóa từ endpoint CafeF theo mã, không fallback sang dữ liệu mẫu.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(
    title="VN Stock Analyst",
    description="App phân tích chứng khoán VN — frontend + API gộp một cổng",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}

# ---------------------------------------------------------------------------
# Sample fundamental data (chất lượng cao) — dùng khi chưa có key nguồn BCTC
# ---------------------------------------------------------------------------
SAMPLE_DB: dict[str, dict[str, Any]] = {
    "VNM": {
        "name": "CTCP Sữa Việt Nam",
        "sector": "Thực phẩm & Đồ uống",
        "exchange": "HOSE",
        "shares": 2085,
        "health": {"total": 82, "liq": 88, "prof": 85, "lev": 78, "eff": 80},
        "quality": 84,
        "ratios": {
            "roe": 28.4, "roa": 16.2, "npm": 14.8, "gpm": 36.0, "opm": 17.5,
            "cr": 2.15, "qr": 1.65, "cashR": 0.85, "de": 0.32, "interestCov": 28.5,
            "debtToAsset": 0.24, "assetTurn": 1.76, "invTurn": 6.2, "recvTurn": 9.1,
            "pe": 15.2, "pb": 4.1, "ps": 1.95, "evebitda": 9.8, "peg": 1.35,
            "divYield": 4.2, "fcfYield": 6.5, "revGrowth": 3.7, "npGrowth": 5.6, "epsGrowth": 5.2,
        },
        "sectorAvg": {"pe": 16.5, "pb": 3.2, "evebitda": 10.5, "roe": 18.0, "npm": 10.5, "de": 0.45},
        "years": [2023, 2024, 2025],
        "revenue": [59800, 61200, 64500],
        "netProfit": [8900, 9200, 9800],
        "margins": {"gpm": [35.2, 35.8, 36.0], "opm": [16.8, 17.1, 17.5], "npm": [14.9, 15.0, 15.2]},
        "bs": {
            "Tiền & tương đương tiền": [5200, 5800, 6400],
            "Tài sản ngắn hạn": [18500, 19200, 20500],
            "Tài sản dài hạn": [15200, 15800, 16200],
            "Tổng tài sản": [33700, 35000, 36700],
            "Nợ ngắn hạn": [6200, 6500, 6800],
            "Nợ phải trả": [8200, 8500, 8900],
            "Vốn chủ sở hữu": [25500, 26500, 27800],
        },
        "is": {
            "Doanh thu thuần": [59800, 61200, 64500],
            "Giá vốn hàng bán": [38750, 39300, 41280],
            "Lợi nhuận gộp": [21050, 21900, 23220],
            "Chi phí bán hàng & QLDN": [11000, 11400, 11900],
            "LN từ HĐKD": [10050, 10500, 11320],
            "LN trước thuế": [10200, 10800, 11600],
            "LN sau thuế": [8900, 9200, 9800],
        },
        "fcf": 7800,
        "ebitda": 12500,
        "peers": [
            {"ticker": "VNM", "pe": 15.2, "pb": 4.1, "roe": 28.4, "de": 0.32, "npm": 14.8, "health": 82},
            {"ticker": "MSN", "pe": 22.0, "pb": 2.8, "roe": 12.5, "de": 0.95, "npm": 6.2, "health": 65},
            {"ticker": "SAB", "pe": 18.5, "pb": 3.5, "roe": 20.1, "de": 0.28, "npm": 16.5, "health": 80},
            {"ticker": "MCH", "pe": 12.0, "pb": 1.9, "roe": 15.8, "de": 0.55, "npm": 9.5, "health": 72},
        ],
        "strengths": [
            "ROE cao ổn định (>25%)",
            "Dòng tiền tự do mạnh & đều",
            "Cấu trúc vốn rất lành mạnh (D/E thấp)",
            "Thương hiệu dẫn đầu thị phần",
            "Biên lợi nhuận ổn định qua các năm",
        ],
        "risks": [
            "Tăng trưởng doanh thu chậm lại",
            "Áp lực cạnh tranh từ sữa nhập khẩu",
            "Phụ thuộc nguyên liệu sữa bột nhập khẩu",
            "Định giá không còn rẻ so với lịch sử",
        ],
        "note": "VNM là doanh nghiệp chất lượng cao với lợi thế thương hiệu và phân phối mạnh. ROE và biên lợi nhuận thuộc top ngành.",
    },
    "FPT": {
        "name": "CTCP FPT",
        "sector": "Công nghệ thông tin",
        "exchange": "HOSE",
        "shares": 1487,
        "health": {"total": 88, "liq": 82, "prof": 92, "lev": 85, "eff": 90},
        "quality": 90,
        "ratios": {
            "roe": 32.1, "roa": 14.8, "npm": 12.5, "gpm": 30.8, "opm": 15.2,
            "cr": 1.85, "qr": 1.55, "cashR": 0.72, "de": 0.45, "interestCov": 22.0,
            "debtToAsset": 0.35, "assetTurn": 1.45, "invTurn": 12.5, "recvTurn": 5.8,
            "pe": 22.5, "pb": 6.8, "ps": 2.6, "evebitda": 14.2, "peg": 1.15,
            "divYield": 2.1, "fcfYield": 3.3, "revGrowth": 16.9, "npGrowth": 16.2, "epsGrowth": 15.5,
        },
        "sectorAvg": {"pe": 25.0, "pb": 5.5, "evebitda": 16.0, "roe": 22.0, "npm": 10.0, "de": 0.50},
        "years": [2023, 2024, 2025],
        "revenue": [52800, 61200, 71500],
        "netProfit": [6800, 7800, 9200],
        "margins": {"gpm": [29.5, 30.2, 30.8], "opm": [14.5, 14.9, 15.2], "npm": [12.9, 12.7, 12.9]},
        "bs": {
            "Tiền & tương đương tiền": [8500, 10200, 12500],
            "Tài sản ngắn hạn": [28500, 32100, 36800],
            "Tài sản dài hạn": [9800, 11200, 12500],
            "Tổng tài sản": [38300, 43300, 49300],
            "Nợ ngắn hạn": [12500, 13800, 15200],
            "Nợ phải trả": [15200, 16800, 18500],
            "Vốn chủ sở hữu": [23100, 26500, 30800],
        },
        "is": {
            "Doanh thu thuần": [52800, 61200, 71500],
            "Giá vốn hàng bán": [37200, 42700, 49500],
            "Lợi nhuận gộp": [15600, 18500, 22000],
            "Chi phí bán hàng & QLDN": [8000, 9200, 10800],
            "LN từ HĐKD": [7600, 9300, 11200],
            "LN trước thuế": [7900, 9400, 11200],
            "LN sau thuế": [6800, 7800, 9200],
        },
        "fcf": 6200,
        "ebitda": 11200,
        "peers": [
            {"ticker": "FPT", "pe": 22.5, "pb": 6.8, "roe": 32.1, "de": 0.45, "npm": 12.5, "health": 88},
            {"ticker": "CMG", "pe": 18.0, "pb": 3.2, "roe": 18.5, "de": 0.60, "npm": 8.5, "health": 70},
            {"ticker": "ELC", "pe": 15.5, "pb": 2.1, "roe": 14.0, "de": 0.40, "npm": 7.2, "health": 68},
        ],
        "strengths": ["Tăng trưởng doanh thu & LN ổn định cao", "ROE vượt trội ngành (>30%)", "Mảng xuất khẩu phần mềm tăng mạnh"],
        "risks": ["Định giá premium (P/E, P/B cao)", "Phụ thuộc nhân sự chất lượng cao"],
        "note": "FPT là cổ phiếu tăng trưởng chất lượng hàng đầu thị trường Việt Nam.",
    },
    "HPG": {
        "name": "CTCP Tập đoàn Hòa Phát",
        "sector": "Thép & Sản phẩm thép",
        "exchange": "HOSE",
        "shares": 5850,
        "health": {"total": 71, "liq": 68, "prof": 65, "lev": 62, "eff": 78},
        "quality": 68,
        "ratios": {
            "roe": 12.8, "roa": 6.5, "npm": 8.2, "gpm": 16.5, "opm": 10.8,
            "cr": 1.42, "qr": 0.85, "cashR": 0.35, "de": 0.85, "interestCov": 6.5,
            "debtToAsset": 0.47, "assetTurn": 0.76, "invTurn": 3.8, "recvTurn": 8.5,
            "pe": 11.5, "pb": 1.35, "ps": 1.14, "evebitda": 7.8, "peg": 0.75,
            "divYield": 1.5, "fcfYield": 6.1, "revGrowth": 10.2, "npGrowth": 21.3, "epsGrowth": 20.0,
        },
        "sectorAvg": {"pe": 12.0, "pb": 1.2, "evebitda": 8.5, "roe": 10.5, "npm": 6.5, "de": 0.90},
        "years": [2023, 2024, 2025],
        "revenue": [118500, 125200, 138000],
        "netProfit": [8500, 10200, 12500],
        "margins": {"gpm": [14.8, 15.5, 16.5], "opm": [9.2, 9.8, 10.8], "npm": [7.2, 8.1, 9.1]},
        "bs": {
            "Tiền & tương đương tiền": [8500, 9200, 10500],
            "Tài sản ngắn hạn": [68500, 72100, 78500],
            "Tài sản dài hạn": [95200, 98500, 102000],
            "Tổng tài sản": [163700, 170600, 180500],
            "Nợ ngắn hạn": [42000, 44500, 46800],
            "Nợ phải trả": [78500, 81200, 84500],
            "Vốn chủ sở hữu": [85200, 89400, 96000],
        },
        "is": {
            "Doanh thu thuần": [118500, 125200, 138000],
            "Giá vốn hàng bán": [101000, 105800, 115230],
            "Lợi nhuận gộp": [17500, 19400, 22770],
            "Chi phí bán hàng & QLDN": [6500, 7000, 7800],
            "LN từ HĐKD": [11000, 12400, 14970],
            "LN trước thuế": [9800, 12100, 15200],
            "LN sau thuế": [8500, 10200, 12500],
        },
        "fcf": 9500,
        "ebitda": 18500,
        "peers": [
            {"ticker": "HPG", "pe": 11.5, "pb": 1.35, "roe": 12.8, "de": 0.85, "npm": 8.2, "health": 71},
            {"ticker": "HSG", "pe": 9.5, "pb": 0.95, "roe": 9.5, "de": 1.10, "npm": 4.5, "health": 58},
        ],
        "strengths": ["Quy mô lớn nhất ngành thép VN", "Định giá hấp dẫn (P/E thấp, PEG <1)"],
        "risks": ["Đòn bẩy tài chính khá cao", "Biên lợi nhuận phụ thuộc giá nguyên liệu"],
        "note": "HPG là cổ phiếu chu kỳ điển hình. Hiện đang trong pha phục hồi với định giá hấp dẫn.",
    },
    "VCB": {
        "name": "Ngân hàng TMCP Ngoại thương Việt Nam",
        "sector": "Ngân hàng",
        "exchange": "HOSE",
        "shares": 5570,
        "health": {"total": 86, "liq": 90, "prof": 88, "lev": 75, "eff": 85},
        "quality": 92,
        "ratios": {
            "roe": 21.5, "roa": 1.85, "npm": 42.0, "gpm": None, "opm": None,
            "cr": 1.12, "qr": None, "cashR": None, "de": 8.5, "interestCov": None,
            "debtToAsset": 0.90, "assetTurn": 0.036, "invTurn": None, "recvTurn": None,
            "pe": 14.8, "pb": 2.95, "ps": None, "evebitda": None, "peg": 1.05,
            "divYield": 1.2, "fcfYield": None, "revGrowth": 10.5, "npGrowth": 13.5, "epsGrowth": 12.8,
        },
        "sectorAvg": {"pe": 13.5, "pb": 1.8, "evebitda": None, "roe": 16.0, "npm": 35.0, "de": 9.5},
        "years": [2023, 2024, 2025],
        "revenue": [68500, 75200, 82500],
        "netProfit": [28500, 32200, 36500],
        "margins": {"gpm": [None, None, None], "opm": [None, None, None], "npm": [41.6, 42.8, 44.2]},
        "bs": {
            "Tổng tài sản": [1850000, 2050000, 2280000],
            "Nợ phải trả": [1680000, 1850000, 2050000],
            "Vốn chủ sở hữu": [170000, 200000, 230000],
        },
        "is": {
            "Doanh thu thuần": [68500, 75200, 82500],
            "LN từ HĐKD": [35200, 39800, 45200],
            "LN trước thuế": [34800, 39200, 44500],
            "LN sau thuế": [28500, 32200, 36500],
        },
        "fcf": None,
        "ebitda": None,
        "peers": [
            {"ticker": "VCB", "pe": 14.8, "pb": 2.95, "roe": 21.5, "de": 8.5, "npm": 42.0, "health": 86},
            {"ticker": "TCB", "pe": 9.5, "pb": 1.35, "roe": 18.5, "de": 7.8, "npm": 38.0, "health": 80},
            {"ticker": "MBB", "pe": 8.2, "pb": 1.25, "roe": 20.0, "de": 8.2, "npm": 36.5, "health": 78},
        ],
        "strengths": ["Chất lượng tài sản tốt nhất ngành", "ROE & ROA vượt trội"],
        "risks": ["Định giá premium so với peer ngân hàng"],
        "note": "VCB là ngân hàng chất lượng số 1 Việt Nam.",
    },
    "MWG": {
        "name": "CTCP Đầu tư Thế Giới Di Động",
        "sector": "Bán lẻ",
        "exchange": "HOSE",
        "shares": 1460,
        "health": {"total": 68, "liq": 72, "prof": 55, "lev": 65, "eff": 75},
        "quality": 62,
        "ratios": {
            "roe": 15.2, "roa": 5.8, "npm": 2.8, "gpm": 14.5, "opm": 4.2,
            "cr": 1.35, "qr": 0.65, "cashR": 0.28, "de": 1.15, "interestCov": 4.2,
            "debtToAsset": 0.60, "assetTurn": 2.02, "invTurn": 4.5, "recvTurn": 25.0,
            "pe": 18.5, "pb": 2.6, "ps": 0.64, "evebitda": 9.2, "peg": 1.45,
            "divYield": 0.8, "fcfYield": 3.5, "revGrowth": -2.8, "npGrowth": 25.0, "epsGrowth": 22.0,
        },
        "sectorAvg": {"pe": 16.0, "pb": 2.2, "evebitda": 8.5, "roe": 12.0, "npm": 2.5, "de": 1.0},
        "years": [2023, 2024, 2025],
        "revenue": [132500, 128800, 142000],
        "netProfit": [2800, 3500, 4800],
        "margins": {"gpm": [13.8, 14.0, 14.5], "opm": [3.2, 3.6, 4.2], "npm": [2.1, 2.7, 3.4]},
        "bs": {
            "Tiền & tương đương tiền": [3200, 3800, 4500],
            "Tài sản ngắn hạn": [48500, 45200, 49800],
            "Tài sản dài hạn": [18500, 19200, 20500],
            "Tổng tài sản": [67000, 64400, 70300],
            "Nợ ngắn hạn": [35000, 32000, 34500],
            "Nợ phải trả": [42500, 39800, 42200],
            "Vốn chủ sở hữu": [24500, 24600, 28100],
        },
        "is": {
            "Doanh thu thuần": [132500, 128800, 142000],
            "Giá vốn hàng bán": [114200, 110800, 121410],
            "Lợi nhuận gộp": [18300, 18000, 20590],
            "Chi phí bán hàng & QLDN": [14200, 13500, 14800],
            "LN từ HĐKD": [4100, 4500, 5790],
            "LN trước thuế": [3800, 4600, 6200],
            "LN sau thuế": [2800, 3500, 4800],
        },
        "fcf": 3200,
        "ebitda": 6800,
        "peers": [
            {"ticker": "MWG", "pe": 18.5, "pb": 2.6, "roe": 15.2, "de": 1.15, "npm": 2.8, "health": 68},
            {"ticker": "FRT", "pe": 22.0, "pb": 3.5, "roe": 12.0, "de": 1.40, "npm": 2.2, "health": 60},
            {"ticker": "PNJ", "pe": 14.5, "pb": 2.8, "roe": 18.5, "de": 0.55, "npm": 6.5, "health": 78},
        ],
        "strengths": ["Thị phần bán lẻ ICT & điện máy lớn", "Biên lợi nhuận đang phục hồi"],
        "risks": ["Biên LN mỏng", "Hàng tồn kho lớn", "Đòn bẩy khá cao"],
        "note": "MWG đang trong giai đoạn phục hồi sau khó khăn của mảng điện máy.",
    },
}


# ---------------------------------------------------------------------------
# Live price helpers (free public endpoints)
# ---------------------------------------------------------------------------

async def fetch_dnse_ohlcv(symbol: str, days: int = 90) -> list[dict]:
    """Lấy OHLCV từ DNSE chart API (không cần key)."""
    to_ts = int(time.time())
    from_ts = to_ts - days * 86400
    url = (
        "https://api.dnse.com.vn/chart-api/v2/ohlcs/stock"
        f"?symbol={symbol.upper()}&resolution=1D&from={from_ts}&to={to_ts}"
    )
    async with httpx.AsyncClient(timeout=15.0, headers=HEADERS) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()

    times = data.get("t") or []
    opens = data.get("o") or []
    highs = data.get("h") or []
    lows = data.get("l") or []
    closes = data.get("c") or []
    vols = data.get("v") or []

    rows = []
    for i in range(len(times)):
        rows.append({
            "date": datetime.utcfromtimestamp(times[i]).strftime("%Y-%m-%d"),
            "open": opens[i] if i < len(opens) else None,
            "high": highs[i] if i < len(highs) else None,
            "low": lows[i] if i < len(lows) else None,
            "close": closes[i] if i < len(closes) else None,
            "volume": vols[i] if i < len(vols) else None,
        })
    return rows


async def fetch_cafef_latest(symbol: str) -> Optional[dict]:
    """Lấy giá gần nhất từ CafeF."""
    end = datetime.now()
    start = end - timedelta(days=14)
    url = (
        "https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/PriceHistory.ashx"
        f"?Symbol={symbol.upper()}"
        f"&StartDate={start.strftime('%d/%m/%Y')}"
        f"&EndDate={end.strftime('%d/%m/%Y')}"
        "&PageIndex=1&PageSize=10"
    )
    async with httpx.AsyncClient(timeout=15.0, headers=HEADERS) as client:
        r = await client.get(url)
        r.raise_for_status()
        payload = r.json()

    items = (payload.get("Data") or {}).get("Data") or []
    if not items:
        return None

    # CafeF trả giá theo nghìn đồng (vd 54.5 = 54.500đ)
    latest = items[0]
    close = latest.get("GiaDongCua") or latest.get("GiaDieuChinh")
    prev = None
    if len(items) > 1:
        prev = items[1].get("GiaDongCua") or items[1].get("GiaDieuChinh")

    price = float(close) * 1000 if close is not None else None
    change_pct = None
    if price and prev:
        prev_p = float(prev) * 1000
        if prev_p:
            change_pct = round((price - prev_p) / prev_p * 100, 2)

    return {
        "symbol": symbol.upper(),
        "date": latest.get("Ngay"),
        "price": price,
        "changePercent": change_pct,
        "volume": latest.get("KhoiLuongKhopLenh"),
        "source": "cafef",
    }


def _parse_level(raw: Optional[str]) -> Optional[dict]:
    """Parse 'price|volume|flag' từ VPS (giá thường là nghìn đồng)."""
    if not raw or not isinstance(raw, str):
        return None
    parts = raw.split("|")
    if len(parts) < 2:
        return None
    try:
        price = float(parts[0])
        vol = float(parts[1])
    except ValueError:
        return None
    if price <= 0 and vol <= 0:
        return None
    # Chuẩn về đồng nếu giá < 1000 (nghìn đồng)
    if 0 < price < 1000:
        price = round(price * 1000, 2)
    return {"price": price, "volume": int(vol)}


def _to_vnd(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        x = float(val)
    except (TypeError, ValueError):
        return None
    if 0 < x < 1000:
        return round(x * 1000, 2)
    return x


async def fetch_vps_board(symbols: list[str]) -> list[dict]:
    """Bảng giá từ VPS datafeed (không cần key). Hỗ trợ nhiều mã."""
    syms = ",".join(s.upper().strip() for s in symbols if s.strip())
    if not syms:
        return []
    url = f"https://bgapidatafeed.vps.com.vn/getliststockdata/{syms}"
    async with httpx.AsyncClient(timeout=12.0, headers=HEADERS) as client:
        r = await client.get(url)
        r.raise_for_status()
        raw_list = r.json()

    if not isinstance(raw_list, list):
        return []

    result = []
    for item in raw_list:
        sym = item.get("sym") or item.get("hashValue")
        if not sym:
            continue

        bid = []
        ask = []
        # g1..g3 thường là bên mua (bid), g4..g6 bên bán (ask) — theo snapshot thực tế VPS
        for key in ("g1", "g2", "g3"):
            lv = _parse_level(item.get(key))
            if lv:
                bid.append(lv)
        for key in ("g4", "g5", "g6"):
            lv = _parse_level(item.get(key))
            if lv:
                ask.append(lv)

        # Sắp xếp bid giảm dần, ask tăng dần cho đúng bảng giá
        bid = sorted(bid, key=lambda x: x["price"], reverse=True)
        ask = sorted(ask, key=lambda x: x["price"])

        last = _to_vnd(item.get("lastPrice"))
        # closePrice đôi khi đã là đồng (54500)
        close_raw = item.get("closePrice")
        try:
            close_p = float(close_raw) if close_raw not in (None, "") else None
        except (TypeError, ValueError):
            close_p = None
        if close_p is not None and close_p < 1000:
            close_p = close_p * 1000

        result.append({
            "symbol": sym,
            "lastPrice": last,
            "open": _to_vnd(item.get("openPrice")),
            "high": _to_vnd(item.get("highPrice")),
            "low": _to_vnd(item.get("lowPrice")),
            "reference": _to_vnd(item.get("r")),
            "ceiling": _to_vnd(item.get("c")),
            "floor": _to_vnd(item.get("f")),
            "average": _to_vnd(item.get("avePrice")),
            "change": _to_vnd(item.get("ot")),
            "changePercent": float(item["changePc"]) if item.get("changePc") not in (None, "") else None,
            "totalVolume": int(float(item["lot"])) if item.get("lot") not in (None, "") else None,
            "lastVolume": int(float(item["lastVolume"])) if item.get("lastVolume") not in (None, "") else None,
            "bid": bid,
            "ask": ask,
            "foreignBuyVolume": int(float(item["fBVol"])) if item.get("fBVol") not in (None, "") else None,
            "foreignSellVolume": int(float(item["fSVolume"])) if item.get("fSVolume") not in (None, "") else None,
            "foreignRoom": float(item["fRoom"]) if item.get("fRoom") not in (None, "") else None,
            "side": item.get("side"),
            "closePrice": close_p,
            "source": "vps",
        })
    return result


# ---------------------------------------------------------------------------
# CafeF financial statements (the same JSON endpoints used by CafeF's page)
# ---------------------------------------------------------------------------

CAFEEF_BCTC_URL = "https://apiweb.cafef.vn/api/v1/BCTC/GetReportSummary"
CAFEEF_INDICATORS_URL = "https://apiweb.cafef.vn/api/v2/BCTC/FinancialIndicators"


async def _cafef_json(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0, headers={**HEADERS, "Referer": "https://cafef.vn/"}) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict) or payload.get("isSuccess") is False:
        raise ValueError("CafeF trả phản hồi không hợp lệ")
    return payload


async def fetch_cafef_report(symbol: str, report_type: str, type_time: str = "NAM") -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Fetch all available annual/quarterly periods and preserve CafeF labels."""
    symbol = symbol.upper().strip()
    rows: list[dict[str, Any]] = []
    labels: dict[str, str] = {}
    for page in range(1, 12):
        url = (
            f"{CAFEEF_BCTC_URL}?symbol={symbol}&pageIndex={page}&pageSize=4"
            f"&reportType={report_type}&TypeTime={type_time}"
        )
        payload = await _cafef_json(url)
        value = payload.get("value") or {}
        for template in value.get("templace") or []:
            for item in template.get("data") or []:
                if item.get("code") and item.get("name"):
                    labels[item["code"]] = item["name"]
        page_rows = []
        for group in value.get("data") or []:
            page_rows.extend(group.get("data") or [])
        if not page_rows:
            break
        rows.extend(page_rows)
        if len(rows) >= int(value.get("count") or 0):
            break
    # Never accept a response whose company identity does not match the request.
    if rows and any(str(row.get("symbol", "")).upper() != symbol for row in rows):
        raise ValueError(f"CafeF trả sai mã cho yêu cầu {symbol}")
    return rows, labels


async def fetch_cafef_indicators(symbol: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    symbol = symbol.upper().strip()
    payload = await _cafef_json(f"{CAFEEF_INDICATORS_URL}?symbol={symbol}&pageIndex=1&pageSize=100")
    value = payload.get("value") or {}
    rows = value.get("data") or []
    if rows and any(str(row.get("symbol", "")).upper() != symbol for row in rows):
        raise ValueError(f"CafeF trả sai mã chỉ số cho yêu cầu {symbol}")
    labels = {x.get("code"): x.get("name") for x in value.get("templace") or [] if x.get("code")}
    return rows, labels


def _cafef_value(row: dict[str, Any], code: str) -> Optional[float]:
    for item in row.get("data") or []:
        if item.get("code") == code:
            value = item.get("value")
            try:
                return None if value in (None, "") else float(value)
            except (TypeError, ValueError):
                return None
    return None


def _code_by_name(labels: dict[str, str], *terms: str) -> Optional[str]:
    for code, name in labels.items():
        text = str(name).lower()
        if all(term.lower() in text for term in terms):
            return code
    return None


def _series(rows: list[dict[str, Any]], labels: dict[str, str], *terms: str) -> list[Optional[float]]:
    code = _code_by_name(labels, *terms)
    return [None if code is None else (_cafef_value(row, code) / 1_000_000_000 if _cafef_value(row, code) is not None else None) for row in rows]


def _latest_indicator(rows: list[dict[str, Any]], code: str) -> Optional[float]:
    if not rows:
        return None
    return _cafef_value(rows[0], code)


async def build_cafef_fundamentals(symbol: str) -> dict[str, Any]:
    """Normalize CafeF's verified symbol-specific data to the frontend contract."""
    symbol = symbol.upper().strip()
    income, income_labels = await fetch_cafef_report(symbol, "KQKD", "NAM")
    balance, balance_labels = await fetch_cafef_report(symbol, "CDKT", "NAM")
    indicators, _ = await fetch_cafef_indicators(symbol)
    if not income or not balance:
        raise ValueError(f"CafeF chưa có đủ BCTC cho {symbol}")

    income = sorted(income, key=lambda row: int(row.get("year") or 0))[-3:]
    balance = sorted(balance, key=lambda row: int(row.get("year") or 0))[-3:]
    years = [int(row.get("year")) for row in income]
    revenue = _series(income, income_labels, "doanh thu thuần")
    if all(value is None for value in revenue):
        # Banks do not report a manufacturing-style net revenue line.
        revenue = _series(income, income_labels, "thu nhập lãi thuần")
    if all(value is None for value in revenue):
        revenue = _series(income, income_labels, "tổng thu nhập hoạt động")
    cogs = _series(income, income_labels, "giá vốn hàng bán")
    gross = _series(income, income_labels, "lợi nhuận gộp")
    operating = _series(income, income_labels, "lợi nhuận thuần từ hoạt động kinh doanh")
    pretax = _series(income, income_labels, "tổng lợi nhuận kế toán trước thuế")
    net = _series(income, income_labels, "lợi nhuận sau thuế")

    bs = {
        "Tiền": _series(balance, balance_labels, "tiền và các khoản tương đương tiền"),
        "TS ngắn hạn": _series(balance, balance_labels, "tài sản ngắn hạn"),
        "TS dài hạn": _series(balance, balance_labels, "tài sản dài hạn"),
        "Tổng TS": _series(balance, balance_labels, "tổng cộng tài sản"),
        "Nợ NH": _series(balance, balance_labels, "nợ ngắn hạn"),
        "Nợ phải trả": _series(balance, balance_labels, "tổng cộng nợ phải trả"),
        "VCSH": _series(balance, balance_labels, "vốn chủ sở hữu"),
    }
    is_data = {
        "DT thuần": revenue, "GVHB": cogs, "LN gộp": gross,
        "LN HĐKD": operating, "LNTT": pretax, "LNST": net,
    }
    latest = indicators[0] if indicators else {}
    raw = {code: _latest_indicator(indicators, code) for code in ("EPS", "PE", "PB", "GOS", "ROS", "ROE", "ROA", "TSTTHH", "KNTTLV", "DAR")}
    clean = lambda value: None if value in (None, 0) else value
    total_assets = bs["Tổng TS"][-1] if bs["Tổng TS"] else None
    liabilities = bs["Nợ phải trả"][-1] if bs["Nợ phải trả"] else None
    equity = bs["VCSH"][-1] if bs["VCSH"] else None
    current_assets = bs["TS ngắn hạn"][-1] if bs["TS ngắn hạn"] else None
    current_liabilities = bs["Nợ NH"][-1] if bs["Nợ NH"] else None
    de = liabilities / equity if liabilities is not None and equity else None
    da = liabilities / total_assets if liabilities is not None and total_assets else None
    cr = current_assets / current_liabilities if current_assets is not None and current_liabilities else None
    ratios = {
        "roe": clean(raw["ROE"]), "roa": clean(raw["ROA"]), "npm": clean(raw["ROS"]),
        "gpm": clean(raw["GOS"]), "opm": None, "cr": cr, "qr": None, "cash": None,
        "de": de, "ic": clean(raw["KNTTLV"]), "da": da, "at": None, "it": None, "rt": None,
        "pe": clean(raw["PE"]), "pb": clean(raw["PB"]), "ps": None, "ev": None, "peg": None,
        "dy": None, "fy": None, "rg": None, "ng": None, "eg": None,
    }
    if len(revenue) >= 2 and revenue[-2] not in (None, 0) and revenue[-1] is not None:
        ratios["rg"] = (revenue[-1] / revenue[-2] - 1) * 100
    if len(net) >= 2 and net[-2] not in (None, 0) and net[-1] is not None:
        ratios["ng"] = (net[-1] / net[-2] - 1) * 100
    for key in ("gpm", "npm"):
        if ratios[key] is None:
            source = gross if key == "gpm" else net
            if source[-1] is not None and revenue[-1]: ratios[key] = source[-1] / revenue[-1] * 100
    for key in ("roe", "roa"):
        if ratios[key] is None:
            ratios[key] = None
    roe_score = ratios["roe"]
    health_total = round(max(0, min(100, 50 + (roe_score or 0) * 1.2 - (de or 0) * 8)))
    health = {"total": health_total, "liq": 50 if cr is None else round(max(0, min(100, cr * 40))), "prof": round(max(0, min(100, 50 + (ratios["npm"] or 0) * 1.5))), "lev": round(max(0, min(100, 100 - (de or 0) * 25))), "eff": 50}
    return {
        "symbol": symbol, "name": f"Mã {symbol}", "sector": "Chưa xác định", "exchange": "",
        "shares": None, "years": years, "revenue": revenue, "netProfit": net,
        "margins": {"gpm": [None if revenue[i] in (None, 0) or gross[i] is None else gross[i] / revenue[i] * 100 for i in range(len(revenue))], "opm": [None] * len(revenue), "npm": [None if revenue[i] in (None, 0) or net[i] is None else net[i] / revenue[i] * 100 for i in range(len(revenue))]},
        "balanceSheet": bs, "incomeStatement": is_data, "fcf": None, "ebitda": None,
        "ratios": ratios, "sectorAvg": {"pe": None, "pb": None, "ev": None, "roe": None, "npm": None, "de": None},
        "health": health, "quality": health_total, "peers": [], "strengths": [], "risks": [],
        "note": "Phân tích dùng BCTC và chỉ số do CafeF cung cấp; các chỉ tiêu CafeF không trả về được giữ là chưa có dữ liệu.",
        "hasFundamentals": True, "source": "cafef", "sourceUrl": "https://cafef.vn/du-lieu/hose/" + symbol.lower() + "-tai-chinh.chn",
        "retrievedAt": datetime.now().isoformat(), "currency": "VND", "unit": "tỷ đồng",
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api")
async def api_info():
    return {
        "name": "VN Stock Analyst API",
        "version": "1.2.0",
        "docs": "/docs",
        "endpoints": [
            "GET /api/health",
            "GET /api/symbols",
            "GET /api/board?symbols=VNM,FPT,HPG",
            "GET /api/stock/{symbol}",
            "GET /api/stock/{symbol}/board",
            "GET /api/stock/{symbol}/ohlcv?days=90",
            "GET /api/stock/{symbol}/quote",
            "GET /api/stock/{symbol}/financials",
            "GET /api/stock/{symbol}/ratios",
        ],
    }


@app.get("/")
async def spa_index():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Frontend chưa có. Xem /api hoặc /docs"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.get("/api/symbols")
async def list_symbols():
    return {
        "symbols": sorted(SAMPLE_DB.keys()),
        "note": "Danh sách mã phân tích lấy theo CafeF; giá realtime hỗ trợ hầu hết mã HOSE/HNX qua DNSE/CafeF/VPS.",
    }


@app.get("/api/board")
async def price_board(symbols: str = Query(..., description="Danh sách mã, cách nhau bởi dấu phẩy. VD: VNM,FPT,HPG")):
    """Bảng giá nhiều mã: giá khớp, trần/sàn/tham chiếu, dư mua/dư bán 3 mức, khối ngoại."""
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not sym_list:
        raise HTTPException(status_code=400, detail="Thiếu danh sách mã")
    if len(sym_list) > 50:
        raise HTTPException(status_code=400, detail="Tối đa 50 mã mỗi lần gọi")
    try:
        rows = await fetch_vps_board(sym_list)
        return {"count": len(rows), "data": rows, "source": "vps"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Không lấy được bảng giá: {e}")


@app.get("/api/stock/{symbol}/board")
async def stock_board(symbol: str):
    """Bảng giá 1 mã (giá, trần/sàn, 3 mức dư mua / dư bán, khối ngoại)."""
    symbol = symbol.upper().strip()
    try:
        rows = await fetch_vps_board([symbol])
        if not rows:
            raise HTTPException(status_code=404, detail=f"Không có bảng giá cho {symbol}")
        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Không lấy được bảng giá: {e}")


@app.get("/api/stock/{symbol}/quote")
async def stock_quote(symbol: str):
    symbol = symbol.upper().strip()

    # Ưu tiên bảng giá VPS (đầy đủ hơn)
    try:
        rows = await fetch_vps_board([symbol])
        if rows:
            b = rows[0]
            if b.get("lastPrice"):
                return {
                    "symbol": symbol,
                    "price": b["lastPrice"],
                    "changePercent": b.get("changePercent"),
                    "volume": b.get("totalVolume"),
                    "open": b.get("open"),
                    "high": b.get("high"),
                    "low": b.get("low"),
                    "reference": b.get("reference"),
                    "ceiling": b.get("ceiling"),
                    "floor": b.get("floor"),
                    "source": "vps",
                }
    except Exception:
        pass

    try:
        live = await fetch_cafef_latest(symbol)
        if live and live.get("price"):
            return live
    except Exception:
        pass

    # fallback: last close from DNSE
    try:
        rows = await fetch_dnse_ohlcv(symbol, days=10)
        if rows:
            last = rows[-1]
            prev = rows[-2] if len(rows) > 1 else None
            chg = None
            if prev and prev.get("close") and last.get("close"):
                chg = round((last["close"] - prev["close"]) / prev["close"] * 100, 2)
            # DNSE thường trả giá theo nghìn đồng
            price = last["close"]
            if price and price < 1000:
                price = price * 1000
            return {
                "symbol": symbol,
                "date": last["date"],
                "price": price,
                "changePercent": chg,
                "volume": last.get("volume"),
                "source": "dnse",
            }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Không lấy được giá: {e}")

    raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu giá cho {symbol}")


@app.get("/api/stock/{symbol}/ohlcv")
async def stock_ohlcv(symbol: str, days: int = Query(90, ge=5, le=730)):
    symbol = symbol.upper().strip()
    try:
        rows = await fetch_dnse_ohlcv(symbol, days=days)
        # chuẩn hoá giá về đồng nếu đang là nghìn đồng
        for r in rows:
            for k in ("open", "high", "low", "close"):
                if r.get(k) is not None and r[k] < 1000:
                    r[k] = round(r[k] * 1000, 2)
        return {"symbol": symbol, "count": len(rows), "data": rows, "source": "dnse"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Lỗi OHLCV: {e}")


@app.get("/api/stock/{symbol}/financials")
async def stock_financials(symbol: str):
    symbol = symbol.upper().strip()
    try:
        data = await build_cafef_fundamentals(symbol)
        return {"symbol": symbol, "years": data["years"], "balanceSheet": data["balanceSheet"], "incomeStatement": data["incomeStatement"], "revenue": data["revenue"], "netProfit": data["netProfit"], "margins": data["margins"], "fcf": data["fcf"], "ebitda": data["ebitda"], "source": data["source"], "sourceUrl": data["sourceUrl"], "retrievedAt": data["retrievedAt"], "unit": data["unit"]}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Không lấy được BCTC CafeF cho {symbol}: {exc}")


@app.get("/api/stock/{symbol}/ratios")
async def stock_ratios(symbol: str):
    symbol = symbol.upper().strip()
    try:
        data = await build_cafef_fundamentals(symbol)
        return {"symbol": symbol, "ratios": data["ratios"], "sectorAvg": data["sectorAvg"], "health": data["health"], "quality": data["quality"], "source": data["source"], "sourceUrl": data["sourceUrl"], "retrievedAt": data["retrievedAt"]}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Không lấy được chỉ số CafeF cho {symbol}: {exc}")


@app.get("/api/stock/{symbol}")
async def stock_full(symbol: str):
    """Payload đầy đủ cho frontend phân tích."""
    symbol = symbol.upper().strip()
    try:
        fund = await build_cafef_fundamentals(symbol)
    except Exception:
        fund = None

    quote = None
    try:
        quote = await stock_quote(symbol)
    except HTTPException:
        quote = None
    except Exception:
        quote = None

    if not fund and not quote:
        raise HTTPException(status_code=404, detail=f"Không có dữ liệu cho {symbol}")

    if not fund:
        return {
            "symbol": symbol,
            "quote": quote,
            "hasFundamentals": False,
            "message": "Chỉ có dữ liệu giá. Chưa lấy được BCTC CafeF đã xác minh cho mã này.",
        }

    price = (quote or {}).get("price")
    change = (quote or {}).get("changePercent")

    ratios = dict(fund["ratios"])

    return {
        "symbol": symbol,
        "name": fund["name"],
        "sector": fund["sector"],
        "exchange": fund["exchange"],
        "shares": fund["shares"],
        "quote": quote,
        "price": price,
        "changePercent": change,
        "health": fund["health"],
        "quality": fund["quality"],
        "ratios": ratios,
        "sectorAvg": fund["sectorAvg"],
        "years": fund["years"],
        "revenue": fund["revenue"],
        "netProfit": fund["netProfit"],
        "margins": fund["margins"],
        "balanceSheet": fund["balanceSheet"],
        "incomeStatement": fund["incomeStatement"],
        "fcf": fund.get("fcf"),
        "ebitda": fund.get("ebitda"),
        "peers": fund.get("peers", []),
        "strengths": fund.get("strengths", []),
        "risks": fund.get("risks", []),
        "note": fund.get("note", ""),
        "hasFundamentals": True,
        "sources": {
            "price": (quote or {}).get("source"),
            "fundamentals": fund.get("source"),
        },
        "source": fund.get("source"),
        "sourceUrl": fund.get("sourceUrl"),
        "retrievedAt": fund.get("retrievedAt"),
        "currency": fund.get("currency"),
        "unit": fund.get("unit"),
    }


@app.get("/manifest.json")
async def manifest():
    f = STATIC_DIR / "manifest.json"
    if f.exists():
        return FileResponse(f, media_type="application/manifest+json")
    raise HTTPException(404)


@app.get("/sw.js")
async def service_worker():
    f = STATIC_DIR / "sw.js"
    if f.exists():
        return FileResponse(f, media_type="application/javascript")
    raise HTTPException(404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
