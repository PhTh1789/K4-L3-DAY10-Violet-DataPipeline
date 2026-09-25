# Member Role Report - Day 10: Data Pipeline & Data Observability

## 1. Thông Tin Cá Nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | **Lê Nguyễn Thái Dương** |
| MSSV | **2A202602383** |
| Khóa/Lớp | K4-L3 |
| Tên nhóm | Violet |
| Vai trò chính | RAG Specialist |
| Repository | https://github.com/PhTh1789/K4-L3-DAY10-Violet-DataPipeline.git |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai Trò Và Phạm Vi Công Việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Vector Store ChromaDB | `src/retrieval/index.py`, `LocalEmbeddingIndex.build`, `semantic_search` | `data/clean/papers_clean.json`, `text_for_embedding` | Collection `papers-baseline`, manifest `data/embeddings/papers_embeddings.json` | Hoàn thành |
| Embedding model | `src/retrieval/embeddings.py`, `MiniLMEmbeddings` | Nội dung paper đã làm sạch | Vector embedding bằng `sentence-transformers/all-MiniLM-L6-v2` | Hoàn thành |
| QA retrieval flow | `src/retrieval/qa.py`, `answer_question` | Câu hỏi benchmark và Chroma index | Câu trả lời, retrieved doc IDs, retrieved contexts | Hoàn thành |
| Retrieval smoke test | `LocalEmbeddingIndex(...).build_from_clean()`, `semantic_search()` | Query `"machine learning"` | Trả về 2 tài liệu liên quan | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra tích hợp Phase 1 | Pipeline, evaluation, observability | `script/run_phase1.py` chạy thành công, tạo đủ clean data, ChromaDB, test set, metrics và report |
| Kiểm tra Phase 2 corruption/repair | Corruption flow | Metrics chứng minh silent failure và phục hồi sau repair |

## 3. Kết Quả Theo Vai Trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Build vector index từ dữ liệu sạch | `src/retrieval/index.py`, `data/chroma/` | Chroma collection `papers-baseline` chứa 24 paper | Smoke test semantic search trả về 2 documents |
| Cấu hình embedding | `src/retrieval/embeddings.py` | Dùng `sentence-transformers/all-MiniLM-L6-v2`, có fallback local khi model không tải được | `data/embeddings/papers_embeddings.json` ghi đúng model |
| Tích hợp QA agent đơn giản | `src/retrieval/qa.py` | Trả lời được câu hỏi authors/date/category/summary dựa trên metadata và context retrieved | `data/results/baseline_answers.json` |
| Đánh giá retrieval | `data/results/baseline_metrics.json` | `retrieval_hit_rate = 1.0` trên dữ liệu sạch | `python -B script/run_phase1.py` |

Output cụ thể của phần RAG là vector store tại `data/chroma/`, manifest embedding tại `data/embeddings/papers_embeddings.json`, và các metrics đánh giá RAG trong `data/results/`.

## 4. Giải Thích Phần Kỹ Thuật Đã Thực Hiện

### Vấn đề cần giải quyết

Vai trò RAG Specialist tập trung vào đoạn từ dữ liệu sạch đến truy vấn tri thức: chuyển mỗi paper thành embedding, lưu vào ChromaDB, truy xuất tài liệu liên quan theo câu hỏi, rồi cung cấp context để đánh giá chất lượng trả lời.

### Cách triển khai

Mỗi record sạch được biến thành document gồm `record_id`, `paper_id`, `title`, `content` và `metadata`. Trường `content` chính là `text_for_embedding`, kết hợp title, authors, ngày xuất bản, category và summary để embedding có đủ ngữ cảnh. ChromaDB dùng collection `papers-baseline`, metric cosine, và model embedding `sentence-transformers/all-MiniLM-L6-v2`.

Trong QA flow, hệ thống ưu tiên exact lookup theo title nếu câu hỏi chứa tiêu đề trong dấu nháy. Sau đó kết quả exact được trộn với semantic search để giữ document đúng ở đầu danh sách. Điều này giúp các câu hỏi benchmark có ground-truth doc ID ổn định hơn, đồng thời vẫn kiểm tra được khả năng retrieval.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `data/clean/papers_clean.json` gồm `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `text_for_embedding` |
| Output | `data/chroma/`, `data/embeddings/papers_embeddings.json`, danh sách `SearchResult` |
| Module phụ thuộc | `ingestion.cleaning`, `core.config`, `core.utils` |
| Module sử dụng output | `evaluation.metrics`, `retrieval.qa`, `pipelines.phase1`, `pipelines.corruption_flow` |
| Điều kiện lỗi cần xử lý | Collection chưa tồn tại, model embedding không tải được, dữ liệu clean thiếu `text_for_embedding` |

### Cách xác minh

```bash
python -B -c "from core.config import load_settings; from retrieval.index import LocalEmbeddingIndex; s=load_settings(); idx=LocalEmbeddingIndex(s, collection_name='papers-baseline'); idx.build_from_clean(); res=idx.semantic_search('machine learning', top_k=2); print(len(res))"
```

- **Kết quả mong đợi:** In ra `2`.
- **Kết quả thực tế:** Retrieval smoke test trả về 2 tài liệu liên quan.
- **Artifact/log:** `data/chroma/`, `data/embeddings/papers_embeddings.json`.

## 5. Một Quyết Định Kỹ Thuật Quan Trọng

- **Bối cảnh:** Vector index cần chạy được cả trong môi trường có mạng và môi trường lab bị giới hạn mạng.
- **Các phương án đã cân nhắc:** Chỉ dùng SentenceTransformer trực tiếp; hoặc thêm fallback embedding deterministic khi model không tải được.
- **Phương án đã chọn:** Giữ model chính `sentence-transformers/all-MiniLM-L6-v2`, đồng thời bổ sung fallback vector dựa trên token hashing.
- **Lý do:** Đúng yêu cầu bài lab khi môi trường đầy đủ, nhưng vẫn có khả năng chạy smoke test và pipeline khi việc tải model bị lỗi.
- **Bằng chứng:** Retrieval smoke test trả về 2 documents; Phase 1 tạo được `data/chroma/` và baseline metrics.

## 6. Một Lỗi Hoặc Blocker Đã Xử Lý

- **Triệu chứng/lỗi nguyên văn:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'`.
- **Lệnh hoặc bước tái hiện:** Chạy `python -B script/run_corruption_flow.py` trên Windows PowerShell.
- **Nguyên nhân gốc:** Console Windows dùng encoding `cp1252`, không in được ký tự mũi tên Unicode trong log pipeline.
- **Cách xử lý:** Đổi các banner/log trong `src/pipelines/corruption_flow.py` sang ASCII, ví dụ `Corruption -> Evaluate -> Repair`.
- **Cách xác minh sau khi sửa:** `python -B script/run_corruption_flow.py` chạy thành công và sinh `data/reports/corruption_report.md`.
- **Điều học được:** Log pipeline nên ưu tiên ASCII hoặc cấu hình encoding rõ ràng để tái hiện ổn định trên Windows.

## 7. Hiểu Biết Về Luồng End-To-End

1. Dữ liệu đi từ Crossref snapshot/API vào raw records, sau đó được cleaning để tạo `text_for_embedding`. RAG module embed trường này bằng MiniLM và lưu vào ChromaDB.
2. Evaluation set chứa câu hỏi, đáp án chuẩn và `ground_truth_doc_ids`. Retrieval được tính hit nếu tài liệu truy xuất có chứa doc ID chuẩn.
3. Quality checks kiểm tra schema, null, unique và độ dài summary; freshness monitoring kiểm tra tuổi dữ liệu qua `age_days` và tỷ lệ stale.
4. Phải dùng cùng test set cho baseline, corrupted và repaired để so sánh công bằng; nếu test set thay đổi thì không biết metric thay đổi do dữ liệu hay do câu hỏi.
5. Repair thành công khi dữ liệu được rebuild từ raw source, quality/freshness quay lại PASS/Fresh và metrics phục hồi về baseline.

## 8. Phân Tích Kết Quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.0000 | 1.0000 | Dữ liệu bẩn làm retrieval mất hoàn toàn ground-truth docs; repair phục hồi đầy đủ |
| `mean_token_f1` | 0.8174 | 0.2000 | 0.8174 | Chất lượng answer giảm mạnh khi context sai hoặc thiếu |
| `judge_accuracy` | 0.8000 | 0.2000 | 0.8000 | Judge phản ánh rõ silent failure |
| `mean_judge_score` | 4.2000 | 1.8000 | 4.2000 | Điểm trung bình giảm sâu rồi phục hồi |
| Quality checks | PASS | FAIL | PASS | Duplicate paper IDs và summary rỗng làm quality gate fail |
| Freshness status | Fresh | Stale | Fresh | Stale date đẩy tỷ lệ stale lên 29.17%, vượt ngưỡng 25% |

### Kết luận từ số liệu

1. Drop latest records, blank summary, duplicate rows và stale date -> quality/freshness chuyển sang FAIL/Stale -> `retrieval_hit_rate` giảm từ `1.0` xuống `0.0`.
2. Repair bằng cách đọc lại raw records và rebuild clean/index -> quality/freshness quay lại PASS/Fresh -> `retrieval_hit_rate` phục hồi từ `0.0` lên `1.0`.

Corruption ảnh hưởng rõ nhất là nhóm **drop latest records + duplicate rows** vì test set dùng các paper mới làm ground truth. Khi các paper mới bị bỏ khỏi corpus và một số record bị nhân đôi, retriever không còn tìm được doc ID đúng, dù hệ thống vẫn chạy không báo lỗi runtime. Đây là đúng bản chất silent failure.

Kết quả khác kỳ vọng ban đầu là chất lượng corrupted giảm rất mạnh, đặc biệt hit rate về `0.0`. Điều này cho thấy chỉ cần corruption có chủ đích vào các tài liệu trong benchmark thì RAG có thể trả lời tự tin nhưng dựa trên context sai.

## 9. Điều Học Được Và Hướng Cải Thiện

### Ba điều quan trọng nhất

1. Vector store không chỉ phụ thuộc model embedding, mà phụ thuộc rất mạnh vào chất lượng `text_for_embedding` và độ đầy đủ của dữ liệu nguồn.
2. Data quality gate cần chạy trước khi build index; nếu duplicate hoặc summary rỗng đã vào ChromaDB thì RAG có thể sai mà không crash.
3. So sánh baseline, corrupted và repaired bằng cùng test set giúp chứng minh tác động nhân quả của dữ liệu bẩn lên RAG agent.

### Nếu có thêm thời gian

Tôi sẽ bổ sung retrieval diagnostics theo từng query: lưu top-k score, retrieved titles và lý do miss ground-truth doc ID. Cải thiện này giúp phân biệt lỗi do embedding yếu, do dữ liệu bị drop, do duplicate, hay do câu hỏi benchmark chưa đủ rõ.

## 10. Cam Kết Của Thành Viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lê Nguyễn Thái Dương
**Ngày xác nhận:** 2026-09-25
