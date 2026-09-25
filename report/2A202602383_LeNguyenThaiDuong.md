# Báo Cáo Cá Nhân - Bài Lab Day 10

- **Họ và tên:** Lê Nguyễn Thái Dương
- **MSSV:** 2A202602383
- **Vai trò:** RAG Specialist & Vector DB Manager
- **Tên Nhóm:** Violet

---

## 1. Khối Lượng Công Việc Đã Hoàn Thành (Thực tế)

Trong bài lab Day 10, vai trò của tôi tập trung vào thành phần cốt lõi của ứng dụng AI: Hệ thống Retrieval (Truy xuất) và sinh câu trả lời bằng LLM. Tôi đảm nhiệm việc biến dữ liệu sạch của Data Pipeline thành tri thức mà Agent có thể truy cập được.

1. **Quản lý Embedding & Vector Store (`src/retrieval/`):**
   - Rà soát và cấu hình mô hình `sentence-transformers/all-MiniLM-L6-v2` để nhúng khối văn bản `text_for_embedding` thành các vector đa chiều.
   - Quản lý kiến trúc ChromaDB cục bộ. Đảm bảo 3 trạng thái dữ liệu (Baseline, Corrupted, Repaired) được lưu vào 3 Collections độc lập hoàn toàn để không xảy ra hiện tượng chồng chéo dữ liệu khi đánh giá.
2. **Khởi tạo QA Agent:**
   - Kiểm thử cơ chế Router kết nối đến các nhà cung cấp LLM khác nhau.
   - Tối ưu hóa prompt template để LLM có thể dễ dàng trích xuất thông tin như Summary, Authors, hay Categories từ tài liệu được cung cấp.
3. **Thực thi và Giám sát Pipeline:**
   - Trực tiếp cấu hình môi trường, kích hoạt tiến trình tạo index trên ChromaDB (một bước đòi hỏi cài đặt môi trường chuẩn do tính chất nặng của thư viện).
   - Kiểm tra log chạy của Vector DB, đảm bảo mọi record hợp lệ đều được load đúng metadata. Phối hợp cùng Pipeline Lead chạy tổng hợp Phase 2 tạo dữ liệu cuối cùng (`data/results/`, `data/chroma/`).

---

## 2. Thách Thức Kỹ Thuật Gặp Phải & Cách Giải Quyết

- **Thách thức:** Trong quá trình chạy Phase 2, tôi phải đối mặt với nguy cơ Vector Database bị rác hoặc trùng lặp nếu chạy lại nhiều lần (gây hiện tượng Ghost Vectors).
  - *Giải quyết:* Quán triệt nguyên tắc "Tách biệt môi trường". Các bộ dữ liệu được index vào các collection tên khác nhau hoàn toàn (`papers-baseline`, `papers-corrupted`, `papers-repaired`) và reset trước mỗi lần run. Điều này đảm bảo Hit Rate không bị làm ảo bởi các id cũ.

---

## 3. Bài Học Rút Ra Về RAG & Data Observability

- **Sự nhạy cảm của Vector DB với Dữ Liệu Bẩn:** Ban đầu, tôi từng nghĩ RAG có thể bao dung các lỗi văn bản nhỏ. Tuy nhiên, sau khi Phase 2 chạy hàm Corruption (tiêm noise, xóa summary), Hit Rate tìm kiếm của ChromaDB đã giảm sốc (tụt xuống 80%). Điều này cho thấy nếu không có Great Expectations đứng canh cửa, mô hình Embedding sẽ bị "đui mù" trước các văn bản rác.
- Tầm quan trọng của MLOps và tự động hóa: Có một Pipeline làm sẵn giúp công việc của một RAG Engineer nhàn hơn rất nhiều. Thay vì phải chắp vá script tay, toàn bộ luồng đánh giá giờ đây chỉ tốn một dòng lệnh `run_corruption_flow.py`.
