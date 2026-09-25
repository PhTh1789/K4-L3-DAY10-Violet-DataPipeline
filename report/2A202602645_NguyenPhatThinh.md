# Báo Cáo Cá Nhân - Bài Lab Day 10

- **Họ và tên:** Nguyễn Phát Thịnh
- **MSSV:** 2A202602645
- **Vai trò:** Trưởng nhóm / Pipeline Lead & Data Foundation Owner
- **Tên Nhóm:** Violet

---

## 1. Khối Lượng Công Việc Đã Hoàn Thành (Thực tế)

Trong buổi lab Day 10, tôi đảm nhận vị trí Trưởng nhóm kiêm kỹ sư xây dựng Data Pipeline. Trọng tâm công việc của tôi là thiết lập phần móng dữ liệu (Data Foundation) và điều phối toàn bộ đường ống xử lý. Cụ thể tôi đã hoàn thành:

1. **Thu thập dữ liệu nguyên bản (Ingestion & Lineage):**
   - Viết module `src/ingestion/crossref.py` giao tiếp với Crossref API.
   - Triển khai cơ chế Offline Fallback đọc từ bản snapshot mẫu (`crossref_response.json`) để hệ thống luôn ổn định khi mất mạng. Lưu giữ an toàn các raw artifacts để đảm bảo truy vết (Data Lineage).
2. **Làm sạch và Chuẩn hóa (Data Cleaning):**
   - Viết hàm làm sạch tại `src/ingestion/cleaning.py`. Loại bỏ các mã XML rác (`<jats:p>`), xử lý khoảng trắng thừa.
   - Hợp nhất các cột thành một đoạn ngữ cảnh duy nhất `text_for_embedding` hỗ trợ mô hình nhúng.
   - Xử lý tuổi đời bài báo (`age_days`) làm tiền đề cho hệ thống Freshness SLA.
3. **Tiêm độc tố dữ liệu (Data Corruption Suite):**
   - Lập trình giả lập 6 kịch bản lỗi trong `src/ingestion/corruption.py` (Drop latest records, Blank summary, Inject noise, Truncate title, Stale date, Duplicate rows) để kiểm chứng hậu quả của Silent Failure lên RAG.
4. **Xây dựng luồng thực thi tổng (End-to-end Pipeline):**
   - Lắp ráp `script/run_phase1.py` để tích hợp toàn bộ luồng sạch từ Data -> ChromaDB -> Evaluation.
   - Xây dựng `script/run_corruption_flow.py` thể hiện rõ cơ chế phục hồi bất biến (Idempotent Repair), tái tạo hoàn hảo dữ liệu từ file thô khi hệ thống bị "nhiễm độc".

---

## 2. Thách Thức Kỹ Thuật Gặp Phải & Cách Giải Quyết

- **Thách thức 1:** Vấn đề import module trong Python (`ModuleNotFoundError`).
  - *Giải quyết:* Cùng team thiết lập môi trường ảo chuẩn và chạy lệnh `pip install -e .` (chế độ editable) để đảm bảo package `src/` được nhận diện.
- **Thách thức 2:** Khi chạy Phase 2, việc sửa lỗi thủ công trên DataFrame rất cồng kềnh.
  - *Giải quyết:* Ứng dụng tư tưởng **Idempotent Repair** - không đi vá lỗi thủ công từng dòng mà lật lại bản lưu thô (`raw snapshot`), làm sạch lại từ đầu. Cách này đảm bảo tính nhất quán (Consistency) và an toàn tuyệt đối.

---

## 3. Bài Học Rút Ra Về RAG & Data Observability

- **Sự nguy hiểm của "Lỗi Câm" (Silent Failure):** Hệ thống RAG phụ thuộc 100% vào ngữ cảnh. Khi dữ liệu đầu vào bị lỗi (VD: thiếu summary, sai ngày tháng), AI không báo lỗi (Exception) mà vẫn tự tin trả lời sai (Hallucination). Bảng kết quả chạy Phase 2 đã chứng minh điều này bằng sự tụt dốc của Hit Rate (từ 100% xuống 80%).
- **Tầm quan trọng của Chất lượng Dữ liệu:** Không có một LLM nào có thể cứu vãn một kho Vector Database chứa đầy "rác". Việc xây dựng Data Quality Gate (Great Expectations) ở cửa ngõ Ingestion là điều kiện sống còn đối với một hệ thống AI ở cấp độ Production.
