# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Violet`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3-DAY10-Violet-DataPipeline`

---

## 👥 Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Nguyễn Phát Thịnh | 2A202602645 | thinhnp2A202602645@student.vn | Pipeline Lead & Data Foundation Owner (`crossref.py`, `cleaning.py`, `corruption.py`, `phase1.py`, `corruption_flow.py`) | `report/2A202602645_NguyenPhatThinh.md` |
| 2 | Lê Nguyễn Thái Dương | 2A202602383 | duonglnt2A202602383@student.vn | RAG Specialist (`retrieval/index.py`, `embeddings.py`, ChromaDB, metrics) | `report/2A202602383_LeNguyenThaiDuong.md` |
| 3 | Nguyễn Minh Lương | 2A202602618 | luongnm2A202602618@student.vn | Observability & Evaluation Lead (`quality.py` GX 1.x, `testset.py`, reporting) | `report/2A202602618_NguyenMinhLuong.md` |

*(Nhóm có 3 thành viên, đã bao phủ toàn bộ khối lượng công việc theo yêu cầu của bài lab)*.

---

## 📝 Tóm tắt đóng góp cá nhân

### 👤 Nguyễn Phát Thịnh (2A202602645)
- **Vai trò:** Trưởng nhóm & Pipeline Lead.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập API Crossref và cơ chế Fallback Offline trong `src/ingestion/crossref.py`.
  - Làm sạch văn bản, xử lý rác HTML và tạo cột `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Lập trình 6 kịch bản giả lập lỗi (Silent Data Failures) trong `src/ingestion/corruption.py`.
  - Xây dựng 2 file luồng chính: `script/run_phase1.py` và `script/run_corruption_flow.py`. Đảm bảo cơ chế tự phục hồi (Idempotent Repair) hoạt động hoàn hảo.

### 👤 Lê Nguyễn Thái Dương (2A202602383)
- **Vai trò:** Phụ trách RAG, Vector Database & Embedding.
- **Công việc chi tiết đã hoàn thành:**
  - Quản lý và verify mô hình embedding `sentence-transformers/all-MiniLM-L6-v2`.
  - Khởi tạo và thiết lập Collection trên ChromaDB, đảm bảo metadata được lưu chuẩn xác.
  - Phụ trách tích hợp và kiểm thử truy vấn RAG độc lập trên dữ liệu Baseline và Corrupted.
  - Hỗ trợ Pipeline Lead chạy test, fix bug luồng RAG và gom các artifacts (`data/chroma/`, `data/results/`) chuẩn bị cho quá trình Submit.

### 👤 Nguyễn Minh Lương (2A202602618)
- **Vai trò:** Phụ trách Data Observability & Benchmark Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate chuẩn Great Expectations 1.x (mode ephemeral) bắt chính xác lỗi dữ liệu dơ trong `src/observability/quality.py`.
  - Xây dựng thuật toán tạo bộ câu hỏi Benchmark tự động từ DataFrame trong `src/evaluation/testset.py`.
  - Cài đặt hệ thống Freshness SLA, đo lường độ trễ ngày xuất bản.
  - Lập trình tự động sinh file Báo cáo định lượng (Markdown) đối chiếu 3 trạng thái Baseline - Corrupted - Repaired.
