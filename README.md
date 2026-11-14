# VN Stock Analyst (All-in-one)

Frontend + Backend gộp **một cổng**, chỉ cần chạy một lệnh.

## Dữ liệu thị trường miễn phí

- **Bảng giá hiện tại:** frontend mặc định gọi public feed của VPS (`getliststockdata`) mỗi 30 giây trong giờ giao dịch, không cần API key. Nguồn trả về giá khớp, tham chiếu, trần/sàn, khối lượng, dư mua/bán và một số dữ liệu khối ngoại. Giá được hiển thị theo **nghìn đồng/cổ phiếu**.
- **OHLCV lịch sử:** backend gọi chart API công khai của DNSE qua endpoint `/api/stock/{symbol}/ohlcv?days=90`; giá được chuẩn hóa về đồng trong JSON API.
- **Giá dự phòng:** backend thử VPS trước, sau đó CafeF và DNSE qua `/api/stock/{symbol}/quote`.
- **BCTC và ratios:** hiện vẫn là **dữ liệu mẫu** cho VNM, FPT, HPG, VCB và MWG; không được xem là số liệu tài chính thực tế.

Các nguồn trên là endpoint công khai, có thể thay đổi hoặc giới hạn truy cập. Ứng dụng hiển thị thời điểm lấy giá và trạng thái kết nối; không coi dữ liệu cũ/mẫu là giá hiện tại.

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

- Bảng giá realtime (VPS public feed): khớp, trần/sàn, dư mua/bán, khối ngoại
- OHLCV lịch sử (DNSE), quote (CafeF/VPS)
- Phân tích BCTC mẫu: sức khỏe DN, ratios, DuPont, định giá, peer…

## Mã có phân tích đầy đủ
VNM · FPT · HPG · VCB · MWG

Bảng giá hỗ trợ hầu hết mã HOSE/HNX.

Không phải khuyến nghị đầu tư.
