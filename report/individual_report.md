# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Nguyễn Minh Lương |
| MSSV | 2A202602618 |
| Khóa/Lớp | K4-L3 |
| Tên nhóm | Violet |
| Vai trò chính | Observability & Evaluation Lead |
| Repository | https://github.com/PhTh1789/K4-L3-DAY10-Violet-DataPipeline |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Data Quality Gate | `src/observability/quality.py`: `run_data_quality_checks()` | Cleaned DataFrame và `Settings` | JSON validation report, trạng thái PASS/FAIL | Hoàn thành |
| Freshness monitoring | `src/observability/quality.py`: `build_freshness_report()` | `published`, `age_days`, ngưỡng 180 ngày | `data/quality/freshness_report.json` | Hoàn thành |
| Benchmark evaluation set | `src/evaluation/testset.py`: `build_test_set()` | Cleaned DataFrame 24 bài báo | `data/eval/test_set.json` gồm 10 câu hỏi cố định | Hoàn thành |
| Báo cáo baseline | `src/observability/reporting.py`: `generate_phase1_report()` | Source summary, metrics, quality và freshness | `data/reports/phase1_report.md` | Hoàn thành |
| Báo cáo đối chiếu ba trạng thái | `src/observability/reporting.py`: `generate_corruption_report()` | Metrics và quality/freshness của corrupted, repaired | `data/reports/corruption_report.md` | Đã hoàn thành code; artifact cuối chờ corruption flow chạy đủ |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Kiểm tra interface contract với pipeline tích hợp | Thịnh — `phase1.py`, `corruption_flow.py` | Ba module của tôi tương thích với các lời gọi thực tế trong pipeline |
| Kiểm tra ChromaDB smoke test theo API hiện tại | Dương — `retrieval/index.py` | Xác định đúng API `LocalEmbeddingIndex.build()` và `search()` thay cho lệnh cũ |
| Kiểm tra baseline end-to-end bằng mock LLM | Cả nhóm | Pipeline sinh đủ test set, metrics, GX report, freshness report và phase-1 report |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Dựng GX Quality Gate theo API 1.x | `src/observability/quality.py` | 6 expectations được thực thi; baseline PASS 6/6 | `data/quality/baseline_quality_report.json` |
| Đo Freshness SLA | `build_freshness_report()` | 1/24 record stale, tỷ lệ 4.17%, trạng thái Fresh | `data/quality/freshness_report.json` |
| Tạo benchmark cố định | `src/evaluation/testset.py` | 10 câu thuộc 4 loại: summary, authors, date, categories | `data/eval/test_set.json` |
| Sinh báo cáo baseline | `generate_phase1_report()` | Tổng hợp source, RAG metrics, GX và freshness trong Markdown | `data/reports/phase1_report.md` |
| Chuẩn bị báo cáo corruption/repair | `generate_corruption_report()` | Code tạo bảng ba trạng thái đã hoàn thành | Chờ `corrupted_metrics.json` và `repaired_metrics.json` được pipeline sinh ra |

Output cụ thể đã được xác minh là `data/quality/baseline_quality_report.json`: Great Expectations đánh giá 6 expectations, cả 6 đều thành công trên 24 records. Ngoài ra, `data/results/baseline_metrics.json` ghi nhận 10 mẫu đánh giá với retrieval hit rate 1.0, mean token F1 1.0, judge accuracy 1.0 và mean judge score 5.0 trong cấu hình mock LLM.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

RAG có thể tiếp tục trả lời dù dữ liệu thiếu, trùng hoặc lỗi thời. Phần việc của tôi tạo một lớp kiểm soát trước khi dữ liệu được dùng để đánh giá/serving, đồng thời tạo benchmark cố định để so sánh công bằng baseline, corrupted và repaired.

### Cách triển khai

Quality Gate sử dụng `gx.get_context(mode="ephemeral")`, tạo Pandas data source, dataframe asset, whole-dataframe batch definition và expectation suite theo API Great Expectations 1.x. Suite kiểm tra số dòng từ 5 đến 5000; các cột `paper_id`, `title`, `text_for_embedding` không null; `paper_id` duy nhất; và độ dài `summary` tối thiểu 30 ký tự. Kết quả validation được chuyển thành JSON để pipeline và báo cáo có thể đọc lại.

Freshness monitoring sử dụng `age_days > 180` để xác định record stale. Dataset bị cảnh báo khi tỷ lệ stale vượt 25%. Báo cáo lưu thêm ngày xuất bản mới nhất/cũ nhất, số record stale, tổng số record và tỷ lệ stale.

Benchmark test set lấy mẫu xác định bằng `random_state=42`. Mỗi mẫu chứa `id`, `question_type`, `question`, `ground_truth` và `ground_truth_doc_ids`. Việc cố định mẫu và document ID giúp dùng cùng một bài kiểm tra cho cả ba trạng thái dữ liệu.

Module reporting chỉ tổng hợp số liệu đã được pipeline sinh ra; không tự tạo hoặc thay đổi metrics. Điều này giúp báo cáo có thể truy vết về artifact JSON tương ứng.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | DataFrame có `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`, `text_for_embedding` |
| Output | Quality JSON, freshness JSON, test-set JSON và báo cáo Markdown |
| Module phụ thuộc | `ingestion/cleaning.py`, `core/config.py`, `core/utils.py` |
| Module sử dụng output | `pipelines/phase1.py`, `pipelines/corruption_flow.py`, `evaluation/metrics.py` |
| Điều kiện lỗi cần xử lý | Thiếu cột bắt buộc, dưới 5 documents, null/duplicate ID, summary quá ngắn, tỷ lệ stale vượt SLA |

### Cách xác minh

```powershell
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'baseline'); print(res['success'])"

python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(len(ts))"

$env:LLM_PROVIDER='mock'
$env:PYTHONIOENCODING='utf-8'
python script/run_phase1.py
```

- **Kết quả mong đợi:** Quality Gate trả `True`, test set có 10 câu, baseline pipeline sinh đủ metrics và report.
- **Kết quả thực tế:** Quality Gate PASS 6/6; test set có 10 câu; baseline pipeline hoàn tất với 24 records.
- **Artifact/log:** `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json`, `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần tạo benchmark dùng chung cho ba trạng thái mà không bị thay đổi ngẫu nhiên sau mỗi lần chạy.
- **Các phương án đã cân nhắc:** Lấy mẫu ngẫu nhiên mới ở mỗi lần chạy; hoặc dùng seed cố định và tái sử dụng cùng file test set.
- **Phương án đã chọn:** Dùng `random_state=42`, tạo 10 câu hỏi và giữ nguyên `test_set.json` cho baseline, corrupted và repaired.
- **Lý do:** Nếu test set thay đổi, chênh lệch metrics có thể do câu hỏi khác chứ không phải do corruption/repair. Test cố định giúp kiểm soát biến và tái lập kết quả.
- **Bằng chứng quyết định phù hợp:** `data/eval/test_set.json` có 10 ID cố định và mỗi câu liên kết tới `ground_truth_doc_ids`; baseline đạt retrieval hit rate 1.0 trên bộ này.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ImportError: cannot import name 'load_or_create_test_set' from 'evaluation.testset'` và `TypeError: LocalEmbeddingIndex.__init__() missing 2 required positional arguments` khi chạy các lệnh hướng dẫn cũ.
- **Lệnh hoặc bước tái hiện:** Chạy smoke-test dùng `load_or_create_test_set()`, `build_from_clean()` và `semantic_search()`.
- **Nguyên nhân gốc:** Lệnh tham khảo thuộc một phiên bản interface cũ, trong khi code hiện tại dùng `build_test_set()`, `LocalEmbeddingIndex.build()` và `search()`; khi copy từ Markdown còn xuất hiện ký tự escape `\_`.
- **Cách xử lý:** Đối chiếu trực tiếp chữ ký hàm trong source và sử dụng API hiện tại, đồng thời bỏ các dấu escape khỏi lệnh PowerShell.
- **Cách xác minh sau khi sửa:** `build_test_set()` sinh 10 câu; `LocalEmbeddingIndex.build(...).search(..., top_k=2)` trả về 2 tài liệu.
- **Điều học được:** Lệnh kiểm thử phải bám theo contract của revision đang chạy, không nên giả định tài liệu và code luôn cùng phiên bản.

Blocker còn lại của CP5 là lần chạy corruption flow chưa sinh được `corrupted_metrics.json`, `repaired_metrics.json` và `corruption_report.md`. Lần chạy gần nhất dừng ở bước tải/kiểm tra model Hugging Face do môi trường chặn socket. Vì vậy tôi không ghi nhận CP5 là đã chạy thành công.

## 7. Hiểu biết về luồng end-to-end

1. Crossref API hoặc snapshot offline được parse thành `PaperRecord` và lưu raw để bảo toàn lineage. Cleaning chuẩn hóa nội dung, tính `age_days`, loại DOI trùng và tạo `text_for_embedding`. Quality Gate kiểm tra dữ liệu trước khi MiniLM tạo embedding và ChromaDB lưu vector.
2. Mỗi câu hỏi có đáp án chuẩn và `ground_truth_doc_ids`. Retrieval hit được tính khi danh sách tài liệu truy xuất chứa document ID chuẩn; câu trả lời được so với `ground_truth` bằng token F1 và judge score.
3. Quality checks đo tính hợp lệ, đầy đủ và duy nhất của schema/nội dung. Freshness monitoring riêng biệt đo tuổi dữ liệu và tỷ lệ record vượt ngưỡng 180 ngày.
4. Cùng một test set giúp giữ nguyên biến đánh giá; khi metrics thay đổi, nguyên nhân có thể quy về trạng thái dữ liệu/index thay vì do thay câu hỏi.
5. Repair thành công khi dữ liệu được dựng lại từ raw, GX trở về PASS, freshness trở lại mức baseline và các metrics repaired tiến gần hoặc bằng baseline. Kết luận phải dựa trên `repaired_metrics.json`, quality/freshness artifacts và báo cáo ba trạng thái.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0000 | Chưa sinh artifact | Chưa sinh artifact | Baseline truy xuất đúng ground-truth document cho 10/10 câu |
| `mean_token_f1` | 1.0000 | Chưa sinh artifact | Chưa sinh artifact | Điểm baseline hoàn hảo trong cấu hình mock LLM; chưa đại diện chất lượng LLM thật |
| `judge_accuracy` | 1.0000 | Chưa sinh artifact | Chưa sinh artifact | Judge dùng cấu hình mock/fallback của lần chạy baseline |
| `mean_judge_score` | 5.0000 | Chưa sinh artifact | Chưa sinh artifact | Cần chạy lại với provider thật nếu muốn kết luận về năng lực sinh câu trả lời |
| Quality checks | PASS 6/6 | FAIL trong kiểm tra độc lập; artifact cuối chưa hoàn tất | Chưa kiểm chứng | GX phát hiện summary rỗng và `paper_id` trùng trong DataFrame corrupted |
| Freshness status | Fresh, 1/24 stale (4.17%) | Chưa có artifact CP5 cuối | Chưa có artifact CP5 cuối | Baseline thấp hơn ngưỡng cảnh báo 25% |

### Kết luận từ số liệu

1. Blank summary và duplicate rows trong kiểm tra độc lập → expectation độ dài summary và tính duy nhất của `paper_id` thất bại → GX trả FAIL. Chưa có `corrupted_metrics.json`, nên chưa kết luận mức suy giảm retrieval/answer quality.
2. Repair từ raw → chưa có quality/freshness/metrics repaired cuối → chưa đủ bằng chứng để tuyên bố đã phục hồi. Bước tiếp theo là chạy thành công `python script/run_corruption_flow.py` và đối chiếu artifact với baseline.

Corruption ảnh hưởng rõ nhất ở thời điểm hiện tại là `blank_summary` và `duplicate_rows`, vì chúng tạo tín hiệu FAIL trực tiếp, có thể kiểm tra được trong GX. Chưa thể xác định corruption nào làm giảm agent metrics mạnh nhất khi chưa có corrupted metrics.

Kết quả khác kỳ vọng là baseline đạt toàn bộ metrics 1.0. Nguyên nhân chính là lần chạy sử dụng mock LLM và câu hỏi gắn trực tiếp với tiêu đề/document ID, vì vậy đây là kiểm tra tính đúng của pipeline hơn là benchmark khó cho mô hình sản xuất. Cần chạy với LLM provider thật và giữ nguyên test set để đánh giá thực tế hơn.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw snapshot và pipeline có tính idempotent giúp tái tạo trạng thái sạch thay vì sửa thủ công dữ liệu đã corrupt.
2. Data quality và freshness là hai tín hiệu bổ sung: dữ liệu có thể đúng schema nhưng vẫn quá cũ, hoặc còn mới nhưng thiếu/trùng nội dung.
3. Metrics RAG chỉ có ý nghĩa khi evaluation set được cố định và mọi kết luận đều truy vết được về artifact.

### Nếu có thêm thời gian

Tôi sẽ bổ sung test tự động cho cả DataFrame sạch và sáu corruption scenarios, đồng thời chạy evaluation với một LLM provider thật. Cải thiện được đo bằng việc corruption flow sinh đủ ba bộ metrics, GX baseline/repaired PASS, corrupted FAIL và repaired metrics phục hồi về gần baseline trên cùng `test_set.json`.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Minh Lương

**Ngày xác nhận:** 2026-09-25
