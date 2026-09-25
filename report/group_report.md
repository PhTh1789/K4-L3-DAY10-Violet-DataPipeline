# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin       | Nội dung                        |
| --------------- | ------------------------------- |
| Khóa/Lớp        | K4-L3A                          |
| Tên nhóm        | Violet                          |
| Repository      | K4-L3-DAY10-Violet-DataPipeline |
| Ngày hoàn thành | 2026-09-25                      |

### Thành viên và phân công

| STT | Họ và tên            | MSSV        | Vai trò chính                   | Module/deliverable sở hữu                                       |
| --: | -------------------- | ----------- | ------------------------------- | --------------------------------------------------------------- |
|   1 | Nguyễn Phát Thịnh    | 2A202602645 | Pipeline Lead & Data Foundation | `crossref.py`, `cleaning.py`, `phase1.py`, `corruption_flow.py` |
|   2 | Lê Nguyễn Thái Dương | 2A202602383 | RAG Specialist & Vector DB      | `index.py`, `embeddings.py`, ChromaDB                           |
|   3 | Nguyễn Minh Lương    | 2A202602618 | Observability & Eval Lead       | `quality.py` (GX 1.x), `testset.py`, reporting                  |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**
Nhóm Violet đã hoàn thành 100% yêu cầu xây dựng Data Pipeline với cơ chế Observability. Baseline pipeline đã kéo, làm sạch và nạp thành công 24 records vào ChromaDB, tạo ra các artifacts đầy đủ trong `data/raw/`, `data/clean/`, `data/chroma/`, và `data/results/`.
Trong 6 kịch bản Corruption, việc xóa nội dung summary và tiêm nhiễu làm hệ thống agent suy giảm nghiêm trọng nhất (Hit Rate rớt từ 100% xuống 0%, Judge Score từ 4.2 xuống 1.8). Tuy nhiên, trạm kiểm dịch Great Expectations đã phát hiện và chặn lại kịp thời (báo FAIL).
Cơ chế Idempotent Repair sau đó đã khôi phục hoàn hảo 100% các chỉ số nhờ vào việc tái thiết lập dữ liệu từ raw snapshot. Blocker lớn nhất trong quá trình làm là tốc độ load mô hình local ban đầu hơi chậm và nguy cơ conflict nhị phân trên Git.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records (Offline Fallback)
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption (Tiêm 6 lỗi)
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối              | Input          | Xử lý chính                  | Output/artifact           | Owner |
| ----------------- | -------------- | ---------------------------- | ------------------------- | ----- |
| Ingestion         | Crossref API   | Fetch, retry, parse          | `data/raw/`               | Thịnh |
| Cleaning          | `raw_records`  | Clean XML tags, nối text     | `data/clean/`             | Thịnh |
| Embedding/index   | `papers_clean` | MiniLM embedding, Chroma     | `data/chroma/`            | Dương |
| Evaluation        | Chroma + LLM   | Test set QA, Hit Rate/F1     | `data/results/`           | Lương |
| Observability     | `papers_clean` | GX 1.x & Freshness checks    | `data/quality/`           | Lương |
| Corruption/repair | `papers_clean` | Tiêm 6 lỗi & Repair từ Raw   | `data/results/*_log.json` | Thịnh |
| Orchestration     | Toàn hệ thống  | Điều phối `phase1`, `phase2` | `data/reports/`           | Thịnh |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng  |
| ------------------------- | ---------------- |
| `LLM_PROVIDER`            | gemini           |
| `LLM_MODEL`               | gemini-2.5-flash |
| Embedding model           | all-MiniLM-L6-v2 |
| Số lượng Crossref records | 24               |
| Retrieval `top_k`         | 3                |
| Freshness threshold       | 180 days         |
| Random seed, nếu có       | 42               |

### Lệnh cài đặt

```bash
uv sync
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh              | Trạng thái | Bằng chứng               |
| ----------------- | ---------- | ------------------------ |
| Baseline pipeline | Thành công | `baseline_metrics.json`  |
| Corruption flow   | Thành công | `corrupted_metrics.json` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính           | Giá trị                                 |
| -------------------- | --------------------------------------- |
| Source               | Crossref API (Fallback Offline)         |
| Query/filter         | query=AI, filter=has-abstract:true      |
| Số record nhận được  | 24                                      |
| Cơ chế retry/backoff | Đọc từ file snapshot local nếu HTTP lỗi |

### Raw và clean schema

| Trường             | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa           | Xử lý khi thiếu/sai    |
| ------------------ | ------------ | --------- | ----------------- | ---------------------- |
| paper_id           | str          | Có        | ID bài báo        | Loại bỏ record         |
| title              | str          | Có        | Tiêu đề           | Báo lỗi Expectation    |
| summary            | str          | Có        | Tóm tắt           | Lọc độ dài > 30        |
| text_for_embedding | str          | Có        | Hợp nhất ngữ cảnh | Tạo mới trong pipeline |

### Quy tắc cleaning

| Quy tắc                      | Quality dimension liên quan | Số record bị tác động | Cách xác minh              |
| ---------------------------- | --------------------------- | --------------------: | -------------------------- |
| Gỡ bỏ thẻ XML `<jats:p>`     | Validity                    | Toàn bộ record có XML | Check `papers_clean.csv`   |
| Nối mảng authors thành chuỗi | Consistency                 |        Toàn bộ record | Check cột `authors_joined` |

**Cách tạo `text_for_embedding`:**
Nhóm kết hợp 5 trường: `Title`, `Authors`, `Published Date`, `Categories`, và `Summary` thành một đoạn văn bản thô duy nhất. `age_days` được tính từ ngày xuất bản đến thời điểm hiện tại.

## 6. Evaluation setup

| Thành phần                            | Cấu hình thực tế                   |
| ------------------------------------- | ---------------------------------- |
| Số câu hỏi                            | 10                                 |
| Các `question_type`                   | summary, authors, date, categories |
| Ground-truth document ID              | Từ cột `paper_id` gốc              |
| Embedding model                       | all-MiniLM-L6-v2                   |
| Vector store/collection               | ChromaDB (3 collections riêng)     |
| Retrieval `top_k`                     | 3                                  |
| LLM provider/model                    | gemini / gemini-2.5-flash          |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`          |

**Giải thích:** Test set được giữ nguyên qua 3 trạng thái để tạo môi trường đối chứng (controlled experiment) nhằm đánh giá tác động thuần túy của Data Quality lên RAG.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                           | Trạng thái | Ghi chú            |
| ------------------------ | ------------------------------------------- | ---------- | ------------------ |
| Raw response/records     | `data/raw/`                                 | Có         | 24 records         |
| Cleaned dataset          | `data/clean/`                               | Có         | `papers_clean.csv` |
| Embedding manifest/index | `data/chroma/`                              | Có         | 3 UUID folders     |
| Evaluation set           | `data/eval/test_set.json`                   | Có         | 10 câu QA          |
| Baseline metrics         | `data/results/baseline_metrics.json`        | Có         | Hit rate 100%      |
| Quality/freshness        | `data/quality/baseline_quality_report.json` | Có         | Pass hết           |
| Baseline report          | `data/reports/phase1_report.md`             | Có         | Tổng kết Pha 1     |

### Baseline metrics

| Metric               | Giá trị | Diễn giải                                   |
| -------------------- | ------: | ------------------------------------------- |
| `retrieval_hit_rate` |   1.000 | 100% trả về đúng tài liệu chứa ground truth |
| `mean_token_f1`      |   0.817 | Độ trùng khớp từ vựng cao (81.7%)           |
| `judge_accuracy`     |   0.800 | LLM Judge đánh giá trả lời đúng 80%         |
| `mean_judge_score`   |   4.200 | Điểm chất lượng câu trả lời cao (4.2/5)     |

## 8. Data quality và freshness

### Quality checks

| Check       | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng                     |
| ----------- | ----------------- | -------------- | ---------------- | ------------------------------ |
| Row count   | Completeness      | 5 - 5000       | Pass (24 rows)   | `baseline_quality_report.json` |
| Not Null ID | Completeness      | Bắt buộc có    | Pass (0% thiếu)  | `baseline_quality_report.json` |
| Unique ID   | Uniqueness        | 100%           | Pass (0% trùng)  | `baseline_quality_report.json` |
| Summary len | Validity          | > 30 chars     | Pass             | `baseline_quality_report.json` |

### Freshness

| Thuộc tính            | Giá trị                        |
| --------------------- | ------------------------------ |
| Freshness được đo tại | Cột `age_days` trong DataFrame |
| Timestamp mới nhất    | 2026-07-22                     |
| Ngưỡng freshness      | 180 ngày (stale ratio < 25%)   |
| Trạng thái baseline   | Fresh                          |
| Lý do                 | Chỉ có 1/24 dòng cũ (4% < 25%) |

## 9. Corruption scenarios và repair

| Corruption     | Cách tạo        | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế      | Cách repair |
| -------------- | --------------- | -----------------: | ---------------------- | --------------------- | ----------- |
| Blank summary  | Xóa cột summary |            Toàn bộ | Length check FAIL      | Hit rate tụt xuống 0% | Idempotent  |
| Inject noise   | Chèn ký tự rác  |         Ngẫu nhiên | Token F1 suy giảm      | F1 giảm còn 0.200     | Idempotent  |
| Duplicate rows | Nhân bản dòng   |           Vài dòng | Unique check FAIL      | RAG lấy trùng lặp     | Idempotent  |

**Cách repair:** Chạy lại hàm `build_clean_dataframe()` trực tiếp từ snapshot thô (`raw_records`) thay vì lặp qua từng dòng lỗi để sửa thủ công. Cách này (Idempotent) đảm bảo tính nhất quán tuyệt đối của dữ liệu đầu ra.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét                  |
| ------------------------ | -------: | --------: | -------: | ---------------------: | -----------: | ------------------------- |
| `retrieval_hit_rate`     |      1.0 |       0.0 |      1.0 |                   -1.0 |          1.0 | Rớt 100% do thiếu Summary |
| `mean_token_f1`          |    0.817 |     0.200 |    0.817 |                 -0.617 |        0.617 | Độ chính xác tụt dốc      |
| `judge_accuracy`         |      0.8 |       0.2 |      0.8 |                   -0.6 |          0.6 | AI Hallucinate nhiều hơn  |
| `mean_judge_score`       |      4.2 |       1.8 |      4.2 |                   -2.4 |          2.4 | Điểm đánh giá cực thấp    |
| Quality checks pass/fail |     PASS |      FAIL |     PASS |            Cảnh báo đỏ |   Trở lại bt | GX hoạt động xuất sắc     |

**Hai kết luận nhân quả:**

1. **[Blank Summary & Noise]** → **[GX Length Check FAIL]** → **[Hit Rate giảm từ 1.0 xuống 0.0]**.
2. **[Idempotent Repair từ Raw Data]** → **[GX PASS 100%]** → **[Metrics phục hồi hoàn toàn về trạng thái Baseline]**.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Pipeline bị lỗi `ModuleNotFoundError: No module named 'core'` hoặc `'ingestion'`.
- **Nguyên nhân:** Môi trường Python không nhận diện thư mục `src` là một package gốc do tính phân cấp thư mục.
- **Cách xử lý:** Chạy lệnh `python -m pip install -e .` để cài đặt project ở dạng editable.
- **Cách xác minh:** Chạy thành công lệnh `python script/run_phase1.py` không còn văng lỗi.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại         | Ảnh hưởng                     | Hướng cải thiện có thể kiểm chứng           |
| ------------------------- | ----------------------------- | ------------------------------------------- |
| Tốc độ tải mô hình MiniLM | Lần chạy đầu tiên bị treo lâu | Dùng API Embedding (OpenAI/Gemini) thay thế |
| GX 1.x Ephemeral context  | Chỉ lưu log JSON, khó trace   | Liên kết với GX Cloud hoặc Postgres SQL DB  |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
