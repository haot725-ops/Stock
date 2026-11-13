# VN Stock Analyst (All-in-one)

Frontend + Backend gộp **một cổng**, chỉ cần chạy một lệnh.

## Chạy

\`\`\`bash
cd vn-stock-api
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
\`\`\`

Mở trình duyệt: **http://localhost:8000**

- Giao diện app: \`/\`
- API docs: \`/docs\`
- API health: \`/api/health\`
- Bảng giá: \`/api/stock/VNM/board\`

## Tính năng

- Bảng giá realtime (VPS): khớp, trần/sàn, dư mua/bán, khối ngoại
- OHLCV lịch sử (DNSE), quote (CafeF/VPS)
- Phân tích BCTC mẫu: sức khỏe DN, ratios, DuPont, định giá, peer…

## Mã có phân tích đầy đủ
VNM · FPT · HPG · VCB · MWG

Bảng giá hỗ trợ hầu hết mã HOSE/HNX.

Không phải khuyến nghị đầu tư.
