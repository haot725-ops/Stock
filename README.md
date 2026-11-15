# VN Stock Analyst (All-in-one)

Frontend + Backend gộp **một cổng**, chỉ cần chạy một lệnh.

## Dữ liệu thị trường miễn phí

- **Bảng giá hiện tại:** frontend mặc định tải danh sách toàn bộ mã HOSE, HNX và UPCOM từ WiFeed, sau đó gọi public feed của VPS (`getliststockdata`) theo lô 200 mã mỗi 30 giây trong giờ giao dịch, không cần API key. Nguồn trả về giá khớp, tham chiếu, trần/sàn, khối lượng, dư mua/bán và một số dữ liệu khối ngoại. Giá được hiển thị theo **nghìn đồng/cổ phiếu**.
- **OHLCV lịch sử:** backend gọi chart API công khai của DNSE qua endpoint `/api/stock/{symbol}/ohlcv?days=90`; giá được chuẩn hóa về đồng trong JSON API.
- **Giá dự phòng:** backend thử VPS trước, sau đó CafeF và DNSE qua `/api/stock/{symbol}/quote`.
- **BCTC và chỉ số tài chính:** app lấy dữ liệu thật theo mã từ các endpoint JSON mà trang hồ sơ CafeF đang sử dụng (`apiweb.cafef.vn`), gồm kết quả kinh doanh, cân đối kế toán, lưu chuyển tiền tệ và chỉ số tài chính. LCTT dùng endpoint `GetReportLCTT`, gộp các nhóm hoạt động kinh doanh/đầu tư/tài chính theo cùng kỳ. Dữ liệu được chuẩn hóa về tỷ đồng, giữ kỳ báo cáo và kiểm tra `symbol` trả về phải trùng mã yêu cầu. Khi CafeF không có chỉ tiêu, app để trống và không dùng số liệu mẫu.

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
- Phân tích BCTC CafeF: ratios, DuPont, bảng LCTT, FCF và DCF khi đủ dữ liệu; FCF được tính bằng CFO cộng dòng chi mua sắm/xây dựng TSCĐ (CapEx, thường là số âm). Các điểm sức khỏe là điểm dẫn xuất, còn peer/EBITDA chỉ hiển thị khi có nguồn xác minh.

## Mã có phân tích đầy đủ
Toàn bộ mã có dữ liệu trên CafeF có thể được tra cứu; đã kiểm thử NVL, VNM, FPT, HPG, VCB và MWG.

Bảng giá hỗ trợ hầu hết mã HOSE/HNX.

CafeF ghi rõ dữ liệu có giá trị tham khảo và không chịu trách nhiệm cho rủi ro sử dụng. Không phải khuyến nghị đầu tư.
