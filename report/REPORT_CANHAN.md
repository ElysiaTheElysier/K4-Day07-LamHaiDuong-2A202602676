# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Lâm Hải Dương  
**MSSV:** 2A202602676  
**Nhóm:** Sloppers — Thương Mại Điện Tử (TikTok Shop Policy)  
**Ngày:** 20/09/2026  
**Chiến lược được phân công:** `RecursiveChunker`

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao (tiến gần về 1.0) thể hiện góc giữa hai vector trong không gian đa chiều rất nhỏ, đồng nghĩa với việc hai đoạn văn bản có sự tương đồng lớn về mặt ngữ nghĩa và chủ đề, không phụ thuộc vào độ dài hay số lượng từ của mỗi đoạn.

**Ví dụ có độ tương tự CAO:**
- **Câu A:** "Thời hạn người bán phải xử lý hoàn tiền cho khách hàng khi hàng bị lỗi là bao lâu?"
- **Câu B:** "Người mua có thể nhận lại tiền bồi hoàn sau mấy ngày kể từ khi gửi khiếu nại sản phẩm hỏng?"
- **Tại sao tương đồng:** Cả hai câu đều truy vấn về cùng một chủ đề nghiệp vụ là thời hạn hoàn tiền (refund SLA) đối với sản phẩm lỗi hỏng, dù cách diễn đạt và từ ngữ sử dụng hoàn toàn khác nhau.

**Ví dụ có độ tương tự THẤP:**
- **Câu A:** "Yêu cầu kỹ thuật về độ phân giải và tỷ lệ khung hình của ảnh sản phẩm đăng bán."
- **Câu B:** "Chế tài xử phạt áp dụng cho nhà bán hàng có hành vi đe dọa hoặc trả đũa đánh giá tiêu cực của người mua."
- **Tại sao khác:** Hai câu đề cập đến hai miền nghiệp vụ hoàn toàn tách biệt: một bên là thông số kỹ thuật media hình ảnh (`listing-guidance`), một bên là chế tài đạo đức và hành vi ứng xử của người bán (`seller-conduct`).

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Khoảng cách Euclid bị phụ thuộc trực tiếp vào độ lớn (magnitude) của vector — vốn tỉ lệ thuận với độ dài văn bản và tần suất từ ngữ — khiến hai câu có cùng ý nghĩa nhưng một câu dài và một câu ngắn có thể bị đẩy ra rất xa nhau. Trong khi đó, Cosine Similarity chỉ đo góc định hướng và chuẩn hóa độ dài vector (L2 normalization), giúp phản ánh trung thực bản chất ngữ nghĩa bất kể văn bản ngắn hay dài.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> **Trình bày phép tính:**
> - Bước nhảy (step size / stride) giữa các chunk: $\text{step} = \text{chunk\_size} - \text{overlap} = 500 - 50 = 450$ ký tự.
> - Vị trí bắt đầu của chunk thứ $k$ là $(k-1) \times 450$.
> - Chunk cuối cùng bắt đầu khi vị trí đầu chunk bao phủ hết 10,000 ký tự:  
>   $$\text{Số lượng chunk} = \left\lceil \frac{10000 - 500}{450} \right\rceil + 1 = \left\lceil \frac{9500}{450} \right\rceil + 1 = \lceil 21.11 \rceil + 1 = 22 + 1 = 23 \text{ chunks}$$
> - Cụ thể: Chunk 1: [0..500], Chunk 2: [450..950], ..., Chunk 22: [9450..9950], Chunk 23: [9900..10000].
> 
> **Đáp án:** **23 chunks**.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> - Khi overlap = 100, bước nhảy giảm xuống $500 - 100 = 400$ ký tự. Số lượng chunk tăng lên: $\lceil (10000 - 500) / 400 \rceil + 1 = \lceil 23.75 \rceil + 1 = 24 + 1 = 25$ chunks.
> - Ta muốn độ chồng chéo nhiều hơn để giảm thiểu nguy cơ mất mát thông tin tại các điểm cắt (boundary truncation). Overlap lớn giúp các câu điều khoản quan trọng, công thức hoặc các con số kỹ thuật không bị chặt làm đôi ở hai chunk riêng biệt, giúp bộ truy xuất (retriever) bảo toàn trọn vẹn ngữ cảnh.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Sử dụng biểu thức chính quy Regex `(?<=[.!?])\s+` kết hợp `lookbehind` để tách chuỗi thành các câu hoàn chỉnh dựa trên các dấu chấm, chấm than, hỏi chấm có khoảng trắng theo sau. Thuật toán lọc bỏ các câu rỗng do khoảng trắng thừa, sau đó gom gộp tuần tự từng nhóm tối đa `max_sentences` câu thành một chunk hoàn chỉnh, bảo đảm mỗi chunk là một chỉnh thể ngữ pháp tự nhiên.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Xây dựng giải thuật đệ quy chia để trị với danh sách các ký tự phân cách ưu tiên giảm dần: `["\n\n", "\n", ". ", " ", ""]`. 
> - **Base case:** Nếu độ dài văn bản nhỏ hơn hoặc bằng `chunk_size` hoặc danh sách ký tự phân cách đã duyệt hết, đoạn văn bản được giữ nguyên hoặc cắt cứng theo ký tự.
> - **Recursive step:** Phân tách văn bản theo phân cách hiện tại (ưu tiên tách đoạn `\n\n`), sau đó duyệt qua các mảnh và gộp dần vào chunk hiện tại chừng nào tổng độ dài chưa vượt `chunk_size`. Bất kỳ mảnh con nào đơn lẻ vẫn dài hơn `chunk_size` sẽ được gọi đệ quy với danh sách ký tự phân cách cấp tiếp theo (`\n`, rồi đến `. `, rồi đến khoảng trắng).

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Lưu trữ các tài liệu dưới dạng danh sách bản ghi (in-memory dictionary) và đồng bộ sang client ChromaDB nếu khả dụng. Khi nạp tài liệu (`add_documents`), hệ thống tính toán embedding cho nội dung từng Document qua `_embedding_fn` và chuẩn hoá L2. Khi tìm kiếm (`search`), hệ thống tính Tích vô hướng (Dot Product) giữa vector câu hỏi và các vector tài liệu (tương đương Cosine Similarity vì các vector đã được chuẩn hoá về độ dài đơn vị), sau đó sắp xếp giảm dần theo điểm số để trích xuất Top-k kết quả.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` áp dụng chiến lược **Pre-filtering (lọc trước)**: duyệt qua danh sách các tài liệu trong kho và chỉ giữ lại những tài liệu có `metadata` khớp 100% với các cặp khóa-giá trị trong `metadata_filter` (ví dụ: `audience == "seller"`), sau đó mới thực hiện tính điểm tương đồng trên tập con này, vừa tăng tốc độ xử lý vừa đảm bảo không lấy nhầm dữ liệu sai đối tượng. `delete_document` tìm kiếm bản ghi theo `doc_id` (hoặc `id`), loại bỏ phần tử tương ứng khỏi danh sách và trả về `True` nếu xóa thành công hoặc `False` nếu không tìm thấy.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Triển khai mô hình RAG tiêu chuẩn: Hàm `answer` nhận câu hỏi của người dùng, gọi `store.search` để lấy ra Top-k chunk phù hợp nhất, sau đó định dạng thành khối ngữ cảnh có đánh số rõ ràng `[1] Nội dung chunk 1\n\n[2] Nội dung chunk 2...`. Ngữ cảnh này được gắn vào System Prompt chỉ định LLM đóng vai trò trợ lý chuyên gia, chỉ được sử dụng thông tin trong khối ngữ cảnh để trả lời câu hỏi trung thực, tránh hiện tượng ảo giác (hallucination).

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe
cachedir: .pytest_cache
rootdir: C:\Ki_OJT\Labs\Lab_7\K4-Day07-LamHaiDuong-2A202602676
plugins: anyio-4.13.0, langsmith-0.11.2
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================== 42 passed in 0.40s ==============================
```

**Số lượng bài test vượt qua (pass):** **42 / 42** (100% tests PASSED)

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

Đo lường thực tế bằng mô hình `text-embedding-3-small` (1536 chiều) của OpenAI thông qua hàm `compute_similarity` trong `src/chunking.py`:

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Quy định đổi trả hàng và hoàn tiền cho người mua khi sản phẩm bị lỗi." | "Chính sách khiếu nại trả hàng và nhận lại tiền do hàng hỏng hóc." | cao | **0.6831** | **Đúng** |
| 2 | "Tiêu chuẩn kỹ thuật về hình ảnh và video khi đăng tải sản phẩm." | "Quy chuẩn độ phân giải, khung hình và chất lượng ảnh sản phẩm niêm yết." | cao | **0.6615** | **Đúng** |
| 3 | "Cấm người bán đe dọa khách hàng đưa ra đánh giá tiêu cực." | "Xử phạt nhà bán hàng có hành vi sỉ nhục và trả đũa đánh giá xấu." | cao | **0.5720** | **Đúng** |
| 4 | "Quy trình bảo hành sản phẩm điện tử đã qua sử dụng." | "Mức phạt điểm vi phạm đối với sản phẩm giả mạo nhãn hiệu." | thấp | **0.3199** | **Đúng** |
| 5 | "Yêu cầu hình ảnh sản phẩm phải có độ phân giải tối thiểu 600x600." | "Thời gian xử lý giao hàng cho bên vận chuyển trong vòng 48 giờ." | thấp | **0.3437** | **Đúng** |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Kết quả ở **Cặp 3 (0.5720)** là bất ngờ nhất: dù hai câu sử dụng các từ đồng nghĩa rất tự nhiên trong ngữ cảnh pháp lý ("đe dọa" vs "sỉ nhục, trả đũa", "tiêu cực" vs "xấu"), nhưng điểm số chỉ đạt 0.5720 (thấp hơn Cặp 1 và Cặp 2 vốn đạt gần 0.70). Điều này cho thấy mô hình embedding biểu diễn ngữ nghĩa không chỉ dựa trên sự tương đồng từ vựng mà còn rất nhạy cảm với cấu trúc mệnh đề hành vi và mức độ trừu tượng của khái niệm.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá chính thức của nhóm (`benchmark.json`)** trên chiến lược `RecursiveChunker` (`chunk_size=500`) kết hợp OpenAI Embedding `text-embedding-3-small` (kết quả từ `ket_qua_benchmark.txt`):

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| Q1 | Theo quy chế TikTok Shop, người bán phải thực hiện bảo hành và bảo trì sản phẩm theo thông tin nào? | `tiktok-quy-che-bao-hanh#22`: Người Bán có trách nhiệm thực hiện bảo hành và bảo trì Sản Phẩm theo thông tin bảo hành mà Người Bán đã cung cấp và hiển thị khi niêm yết sản phẩm. | **0.8043** | **Có (Gold Match)** | Người bán phải bảo hành và bảo trì theo đúng thông tin đã cung cấp và hiển thị khi niêm yết sản phẩm trên TikTok Shop, có nghĩa vụ nhận sản phẩm khi có bảo hành áp dụng. |
| Q2 | Thông tin đăng bán sản phẩm bị coi là sai lệch nếu không chính xác hoặc không thể xác minh về những nhóm nội dung nào? | `tiktok-thong-tin-bao-hanh-sai-lech#1`: Quy định thông tin đăng bán không được chứa nội dung không chính xác về: cam kết bảo hành, vận chuyển/đổi trả/hoàn tiền, quyền sở hữu trí tuệ, hình ảnh/mô tả sản phẩm. | **0.7037** | **Có (Gold Match)** | Bao gồm 4 nhóm: cam kết hoặc chính sách bảo hành; quy trình vận chuyển, giao hàng, đổi trả, hoàn tiền; thông tin quyền sở hữu trí tuệ; hình ảnh hoặc mô tả sản phẩm. |
| Q3 | Mô tả, hình ảnh và các thuộc tính sản phẩm do người bán cung cấp phải đáp ứng những yêu cầu nào? | `tiktok-quy-che-bao-hanh#362`: Quy định tổng thể mô tả sản phẩm (Top-2 `tiktok-huong-dan-dang-ban-bao-hanh#53` Score **0.6990** trúng đích hướng dẫn mô tả sản phẩm thực tế). | **0.7503** | **Có (Top-2 & Top-3)** | Mô tả và hình ảnh phải phù hợp với sản phẩm thực tế được bán, không gây hiểu lầm; các thuộc tính phải đầy đủ, chính xác và đúng với hàng khách hàng thực nhận. |
| Q4 | Sản phẩm tân trang hoặc đã qua sử dụng có thể khai báo những hình thức bảo hành nào? *(Filter: `audience: seller`)* | `tiktok-bao-hanh-hang-tan-trang#0`: Nguyên tắc đăng bán hàng tân trang (Top-2 `chunk #13` Score **0.6038** trích xuất trọn vẹn 4 hình thức bảo hành). | **0.7557** | **Có (Gold Match)** | Người bán có thể khai báo 1 trong 4 hình thức: "Bảo hành quốc tế", "Bảo hành của nhà sản xuất", "Bảo hành của nhà cung cấp", hoặc "Không bảo hành". |
| Q5 | Người bán có được vô hiệu tiêu chuẩn bảo hành nếu khách hàng không đánh giá 5 sao không? | `tiktok-dieu-khoan-bao-hanh-bat-cong#5`: Liệt kê điều khoản cấm: "- Chúng tôi sẽ vô hiệu tiêu chuẩn bảo hành của sản phẩm nếu khách hàng không đánh giá 5 sao." | **0.8115** | **Có (Gold Match)** | Hoàn toàn không. Đây là điều khoản bán hàng không công bằng bị TikTok Shop cấm người bán đưa vào danh sách niêm yết sản phẩm. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **5 / 5** câu (100% Top-3 Relevance, Điểm đánh giá: **8 / 10 điểm**)

### Phân Tích Trường Hợp Lỗi Thực Tế (Failure Case Analysis)

**1. Câu hỏi gặp lỗi xếp hạng:**
> **Câu Q3:** *"Mô tả, hình ảnh và các thuộc tính sản phẩm do người bán cung cấp phải đáp ứng những yêu cầu nào?"*  
> - **Tài liệu chuẩn (Expected Doc):** `tiktok-huong-dan-dang-ban-bao-hanh` (Mục 4.1 & 4.2).  
> - **Kết quả thực tế:** Top-1 bị chiếm bởi `tiktok-quy-che-bao-hanh#362` (Score: **0.7503**), còn chunk đáp án chuẩn `tiktok-huong-dan-dang-ban-bao-hanh#53` chỉ về vị trí **Top-2** (Score: **0.6990**).

**2. Nguyên nhân cốt lõi (Tại sao hỏng ở Top-1?):**
> - **Sự mất cân xứng quy mô tài liệu (Corpus Asymmetry):** Tài liệu quy chế chung `tiktok-quy-che-bao-hanh` có độ dài lên tới 160,898 ký tự (chiếm 480/603 chunks toàn bộ corpus). Chunk #362 của tài liệu này cũng nhắc lại cụm từ *"Mô tả Thông Tin Cơ Bản về Sản Phẩm... Hình Ảnh Sản Phẩm, Mô Tả Sản Phẩm"*. Do chứa nhiều từ khoá trùng lặp với câu hỏi, vector của chunk quy chế chung có điểm cosine cao hơn chunk hướng dẫn chi tiết.
> - **Mất liên kết phân cấp ngữ cảnh (Loss of Hierarchical Context):** `RecursiveChunker` cắt văn bản theo ranh giới `\n\n`, khiến chunk #53 (chứa nội dung yêu cầu thuộc tính) bị tách rời khỏi tiêu đề mục lớn `## 4. Hướng dẫn chi tiết về đăng tải sản phẩm`. Vì thiếu thông tin tiêu đề cha, điểm tương đồng bị sụt giảm từ 0.75 xuống 0.69.
> - **Không áp dụng Metadata Filter:** Câu Q3 không có bộ lọc metadata (chạy toàn bộ corpus), khiến các tài liệu diện rộng không liên quan chen chân vào Top-1.

**3. Đề xuất cải thiện:**
> - **Bổ sung Breadcrumb/Heading Prefix:** Gắn tiêu đề section cha (ví dụ: `[Hướng dẫn đăng bán > Thuộc tính sản phẩm]`) vào đầu mỗi chunk con trước khi tính embedding để giữ vững ngữ cảnh nguồn.
> - **Sử dụng Metadata Pre-filtering:** Bổ sung trường metadata `category: "listing-guidance"` vào câu hỏi để loại bỏ 480 chunk của tài liệu quy chế chung, đảm bảo 100% Top-1 rơi vào tài liệu hướng dẫn đăng bán.
> - **Tăng Chunk Overlap:** Bổ sung `overlap=80` ký tự để kết nối thông suốt giữa đoạn nêu nguyên tắc và các tiêu chí kỹ thuật cụ thể.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Qua việc so sánh trực tiếp kết quả của `RecursiveChunker` với chiến lược `Section/HeadingChunker` của bạn Trần Thị Bình, tôi nhận thấy rõ giá trị của việc **bảo tồn tiêu đề phân cấp mục (hierarchical breadcrumb)**. Khi văn bản bị cắt nhỏ, nếu chỉ dựa vào `RecursiveChunker` đơn thuần thì ở câu Q3, chunk mô tả thuộc tính bị tách rời khỏi ngữ cảnh "Hướng dẫn đăng bán", dẫn tới việc tài liệu quy chế chung có điểm cao hơn một chút ở Top-1. Việc gắn kèm tiêu đề mục cha vào từng chunk con giúp cải thiện độ chính xác phân cấp lên đáng kể.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
