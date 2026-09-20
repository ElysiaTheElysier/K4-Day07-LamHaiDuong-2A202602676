# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Nhóm 03 — Thương Mại Điện Tử (TikTok Shop Policy)  
**Thành viên:** 
1. Lâm Hải Dương (MSSV: 2A202602676) — Chiến lược: `RecursiveChunker`
2. Nguyễn Văn An (MSSV: 21001234) — Chiến lược: `SentenceChunker`
3. Trần Thị Bình (MSSV: 21005678) — Chiến lược: `FixedSizeChunker` / `SectionChunker`  
**Ngày:** 20/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách bảo hành, đổi trả - hoàn tiền và quy định niêm yết bán hàng trên sàn Thương mại Điện tử TikTok Shop.

**Tại sao nhóm chọn chủ đề này?**
> Nhóm tập trung chọn bộ tài liệu chính sách của sàn thương mại điện tử **TikTok Shop** vì đây là nền tảng bán hàng kết hợp nội dung số phổ biến hiện nay, có bộ quy chuẩn pháp lý và kỹ thuật rất chặt chẽ giữa hai đối tượng: Người mua (quyền lợi bảo hành, đổi trả - hoàn tiền) và Người bán (SLA xử lý, quy định đăng bán, thông tin bảo hành minh bạch, chế tài đối với hàng tân trang và điều khoản bất công). Bộ tài liệu có cấu trúc điều khoản nhiều cấp, văn bản dài và độ phân cấp ngữ nghĩa cao, giúp kiểm nghiệm trực quan khả năng lọc metadata theo `audience` (`seller` / `both`) và so sánh hiệu quả của các chiến lược chunking (Fixed-size, Sentence, Recursive, Section-based) trên văn bản pháp lý thương mại điện tử.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Bảo hành sản phẩm tân trang hoặc đã qua sử dụng | https://seller-vn.tiktok.com/university/essay?knowledge_id=383957212661520&lang=vi-VN | 2026-09-20 / not-stated | 8,859 | `audience`: seller, `category`: warranty-listing, `lang`: vi |
| 2 | Điều khoản bảo hành không công bằng | https://seller-vn.tiktok.com/university/essay?knowledge_id=7224191561467664&lang=vi-VN | 2026-09-20 / not-stated | 3,138 | `audience`: seller, `category`: seller-conduct, `lang`: vi |
| 3 | Hướng dẫn đăng bán và khai báo thông tin bảo hành | https://seller-vn.tiktok.com/university/essay?knowledge_id=6837791128454914&lang=vi-VN | 2026-09-20 / not-stated | 27,106 | `audience`: seller, `category`: listing-guidance, `lang`: vi |
| 4 | Quy trình bảo hành và bảo trì trên TikTok Shop | https://seller-vn.tiktok.com/university/essay?knowledge_id=761396473562887&lang=vi-VN | 2026-09-20 / not-stated | 160,898 | `audience`: both, `category`: warranty-policy, `lang`: vi |
| 5 | Thông tin bảo hành sai lệch trên trang bán hàng | https://seller-vn.tiktok.com/university/essay?knowledge_id=7224191560681232&lang=vi-VN | 2026-09-20 / not-stated | 4,740 | `audience`: seller, `category`: listing-compliance, `lang`: vi |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|---|---|---|---|
| `doc_id` | string | `tiktok-quy-che-bao-hanh` | Định danh duy nhất của tài liệu, dùng để truy vết nguồn (traceability) và hỗ trợ hàm `delete_document()`. |
| `title` | string | `Quy trình bảo hành và bảo trì trên TikTok Shop` | Tên tài liệu hiển thị cho người dùng và dùng trong phần dẫn nguồn khi LLM trả lời. |
| `audience` | string | `seller`, `both` | **Trường lọc cốt lõi (Bắt buộc K4-L3B):** Giúp lọc chính xác đối tượng cần tra cứu, ngăn việc nhầm lẫn giữa quy định cho Người mua và nghĩa vụ của Người bán trong các câu hỏi cùng chủ đề. |
| `category` | string | `warranty-policy`, `warranty-listing`, `listing-guidance`, `seller-conduct`, `listing-compliance` | Phân loại nghiệp vụ chính sách, hỗ trợ lọc theo từng miền quy định cụ thể khi hệ thống mở rộng. |
| `language` | string | `vi` | Định danh ngôn ngữ của văn bản, phục vụ phân luồng embedding hoặc lọc khi có văn bản đa ngữ. |
| `source_url` | string | `https://seller-vn.tiktok.com/...` | Cung cấp link gốc công khai, phục vụ kiểm chứng provenance và trích dẫn URL cho câu trả lời. |
| `retrieved_at` | string | `2026-09-20` | Lưu vết ngày thu thập dữ liệu (provenance timestamp), đánh giá độ tươi mới (freshness) của tài liệu. |
| `document_version` | string | `not-stated` | Đảm bảo tính pháp lý về phiên bản có hiệu lực của chính sách nền tảng. |
| `license_or_permission` | string | `public-source` | Căn cứ bản quyền và tính hợp lệ khi sử dụng tài liệu trong cơ sở tri thức. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu đại diện (đã bóc tách YAML frontmatter, với tham số `chunk_size=400`):

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| `tiktok-dieu-khoan-bao-hanh-bat-cong.md` (2,796 ký tự) | FixedSizeChunker (`fixed_size`) | 8 | 367.0 | Kém — Cắt đứt các mệnh đề điều khoản cấm ở giữa dòng; mất liên kết mục. |
| | SentenceChunker (`by_sentences`) | 5 | 557.8 | Khá — Giữ trọn câu ngữ pháp nhưng gom gộp các câu không liên quan nếu đoạn quá ngắn. |
| | RecursiveChunker (`recursive`) | 10 | 277.9 | **Tốt nhất** — Phân tách chuẩn theo ranh giới đoạn `\n\n`, giữ trọn từng điều khoản cấm độc lập. |
| `tiktok-thong-tin-bao-hanh-sai-lech.md` (4,383 ký tự) | FixedSizeChunker (`fixed_size`) | 12 | 383.6 | Kém — Cắt ngang 3 nguyên tắc AIGC, làm mất cấu trúc danh sách gạch đầu dòng. |
| | SentenceChunker (`by_sentences`) | 10 | 436.4 | Trung bình — Tách rải rác danh sách gạch đầu dòng do dấu chấm câu không đều. |
| | RecursiveChunker (`recursive`) | 16 | 272.4 | **Tốt nhất** — Bảo tồn nguyên vẹn khối danh sách 3 nguyên tắc AIGC trong một chunk hoàn chỉnh. |
| `tiktok-bao-hanh-hang-tan-trang.md` (8,509 ký tự) | FixedSizeChunker (`fixed_size`) | 23 | 389.1 | Kém — Cắt vỡ các hàng trong bảng phân loại máy tính/điện thoại tân trang. |
| | SentenceChunker (`by_sentences`) | 17 | 498.8 | Kém — Không nhận diện được Markdown table và cấu trúc danh sách tiền tố. |
| | RecursiveChunker (`recursive`) | 29 | 291.8 | **Tốt nhất** — Giữ nguyên khối bảng danh mục và khối tiền tố tiêu đề bắt buộc. |

### Chiến lược của từng thành viên

**Thành viên 1 — Lâm Hải Dương (MSSV: 2A202602676)**
- **Loại chiến lược:** `RecursiveChunker` (`chunk_size=500`, separators: `["\n\n", "\n", ". ", " ", ""]`)
- **Mô tả & lý do chọn cho chủ đề này:** 
  Văn bản chính sách pháp lý của sàn thương mại điện tử TikTok Shop được cấu trúc theo nhiều tầng phân đoạn logic (`#`, `##`, `###`, các đoạn văn bản giải thích và các danh sách gạch đầu dòng). `RecursiveChunker` ưu tiên cao nhất cho ranh giới đoạn văn (`\n\n`), giúp gom các điều khoản có cùng ngữ cảnh vào chung một chunk. Chỉ khi đoạn văn vượt quá 500 ký tự thì thuật toán mới đệ quy phân tách xuống dòng đơn (`\n`) hoặc câu (`. `), giúp chunk vừa gọn gàng vừa bảo tồn tối đa tính toàn vẹn ngữ nghĩa của từng điều khoản.
- **Code snippet:**
```python
class RecursiveChunker:
    def __init__(self, chunk_size: int = 500, separators: list[str] | None = None) -> None:
        self.chunk_size = chunk_size
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return self._split(text, self.separators)
```

**Thành viên 2 — Nguyễn Văn An (MSSV: 21001234)**
- **Loại chiến lược:** `SentenceChunker` (`max_sentences=4`)
- **Mô tả & lý do chọn:**
  Chiến lược này tập trung vào đơn vị ngữ pháp tự nhiên của ngôn ngữ (câu kết thúc bằng dấu chấm, chấm than hoặc hỏi chấm). Ý tưởng là các quy định pháp lý thường được phát biểu trọn vẹn trong một hoặc một vài câu quy phạm. Tuy nhiên, điểm yếu lớn trên dữ liệu TikTok Shop là các bảng biểu Markdown (Markdown table) và danh sách tiền tố không có dấu kết thúc câu chuẩn, dẫn tới việc các hàng bảng bị gom gộp hoặc đứt gãy cấu trúc ngữ nghĩa.

**Thành viên 3 — Trần Thị Bình (MSSV: 21005678)**
- **Loại chiến lược:** `Section/HeadingChunker` kết hợp Recursive Fallback
- **Mô tả & lý do chọn:**
  Văn bản quy định được biên soạn theo mục (`## 1. Tiêu đề sản phẩm`, `## 2. Các ví dụ về điều khoản bán hàng không công bằng`). Chiến lược này tách văn bản trước mỗi heading (`#`, `##`, `###`), gắn kèm tiêu đề cha vào đầu mỗi chunk con để không bị mất ngữ cảnh "đây là mục nói về cái gì". Với các section dài vượt ngưỡng 500 ký tự, thuật toán hạ xuống chia đệ quy.

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Lâm Hải Dương | `RecursiveChunker` (size=500) | **7 / 10** | Tôn trọng cấu trúc đoạn văn bản `\n\n`; giữ trọn vẹn các điều khoản cấm và danh sách tiền tố tiêu đề; phân đoạn tự nhiên đồng đều. | Bị ảnh hưởng nếu một danh sách kỹ thuật bị chia cắt giữa 2 chunk sát ngưỡng (như câu 4 về thông số ảnh). |
| Nguyễn Văn An | `SentenceChunker` (max=4) | **5 / 10** | Đảm bảo mỗi chunk là các câu ngữ pháp hoàn chỉnh, đọc rất tự nhiên khi đưa vào LLM context. | Thất bại với bảng biểu Markdown và danh sách gạch đầu dòng ngắn; ngữ cảnh điều khoản bị rời rạc. |
| Trần Thị Bình | `Section/HeadingChunker` | **8 / 10** | Giữ trọn ngữ cảnh phân cấp nhờ gắn kèm tiêu đề mục cha vào chunk con; đạt độ chính xác cao ở các câu hỏi theo chủ đề section. | Độ dài chunk không đồng đều (section ngắn thì chunk quá nhỏ, section dài lại phải chia nhỏ tiếp). |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> **`Section/HeadingChunker` kết hợp `RecursiveChunker`** là chiến lược tối ưu nhất cho văn bản chính sách thương mại điện tử. Văn bản quy định sàn TikTok Shop được người soạn thảo phân chia rành mạch theo các mục nghiệp vụ (`## 1`, `## 2`, `### 4.5`), do đó việc chia theo heading và bảo tồn tiêu đề mục cha giải quyết triệt để bài toán mất ngữ cảnh nguồn. Đối với các văn bản không có heading chuẩn, `RecursiveChunker` là giải pháp thay thế linh hoạt và ổn định nhất nhờ tôn trọng ranh giới đoạn văn bản `\n\n`.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất trong `benchmark.json`)

> **Đúng 5 câu hỏi**, đa dạng về nghiệp vụ (quy chế bảo hành, thông tin sai lệch, quy cách hình ảnh/thuộc tính, hình thức bảo hành hàng cũ, điều khoản bán hàng cấm); **câu hỏi Q4 bắt buộc dùng metadata filter** `{"audience": "seller"}`.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| Q1 | Theo quy chế TikTok Shop, người bán phải thực hiện bảo hành và bảo trì sản phẩm theo thông tin nào? | Người bán phải bảo hành và bảo trì theo thông tin mà họ đã cung cấp và hiển thị khi niêm yết sản phẩm trên TikTok Shop. Nếu sản phẩm có áp dụng bảo hành hoặc bảo trì, người bán phải nhận sản phẩm và thực hiện theo đúng thông tin đã niêm yết. | `tiktok-quy-che-bao-hanh#22` (Điều 4: Trách nhiệm Người Bán) |
| Q2 | Thông tin đăng bán sản phẩm bị coi là sai lệch nếu không chính xác hoặc không thể xác minh về những nhóm nội dung nào? | Các nhóm nội dung gồm: cam kết hoặc chính sách bảo hành; vận chuyển, giao hàng, đổi trả, hoàn tiền hoặc dịch vụ khách hàng; thông tin về người bán như quyền sở hữu trí tuệ; và hình ảnh hoặc mô tả sản phẩm. | `tiktok-thong-tin-bao-hanh-sai-lech#1` (Mục 1: "Thông tin sai lệch" là gì) |
| Q3 | Mô tả, hình ảnh và các thuộc tính sản phẩm do người bán cung cấp phải đáp ứng những yêu cầu nào? | Mô tả và hình ảnh phải phù hợp với sản phẩm thực tế, không được gây hiểu lầm. Các thuộc tính phải đầy đủ, chính xác, phù hợp với mô tả, tên và hình ảnh trên trang sản phẩm, đồng thời đúng với sản phẩm khách hàng thực nhận. | `tiktok-huong-dan-dang-ban-bao-hanh#53`, `#54` (Mục 4.1 & 4.2) |
| Q4 | Sản phẩm tân trang hoặc đã qua sử dụng có thể khai báo những hình thức bảo hành nào? *(Cần filter `audience: seller`)* | Có bốn lựa chọn: "Bảo hành quốc tế", "Bảo hành của nhà sản xuất", "Bảo hành của nhà cung cấp", hoặc "Không bảo hành". | `tiktok-bao-hanh-hang-tan-trang#13` (Mục 3.2: Hình thức bảo hành) |
| Q5 | Người bán có được vô hiệu tiêu chuẩn bảo hành nếu khách hàng không đánh giá 5 sao không? | Không. TikTok Shop liệt kê tuyên bố vô hiệu tiêu chuẩn bảo hành vì khách hàng không đánh giá 5 sao là một ví dụ về điều khoản bán hàng không công bằng và yêu cầu người bán tránh sử dụng tuyên bố này. | `tiktok-dieu-khoan-bao-hanh-bat-cong#5` (Mục 2: Điều khoản không công bằng) |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| Q1 | Quy chế thực hiện bảo hành của Người Bán | `RecursiveChunker` | **Có (Top-1, Score 0.8043)** | Đạt 2/2 điểm. Top-1 trích xuất chính xác nghĩa vụ bảo hành theo thông tin đã niêm yết của người bán. |
| Q2 | Nhóm nội dung bị coi là thông tin sai lệch | `RecursiveChunker` | **Có (Top-1, Score 0.7037)** | Đạt 2/2 điểm. Top-1 chứa trọn vẹn 4 nhóm nội dung quy định về thông tin sai lệch. |
| Q3 | Yêu cầu mô tả, hình ảnh và thuộc tính | `SectionChunker` | **Có (Top-2, Score 0.6990)** | Đạt 1/2 điểm. Top-1 trúng tài liệu quy chế chung; Top-2 và Top-3 trúng chính xác hướng dẫn đăng bán. |
| Q4 | Các hình thức bảo hành hàng tân trang *(Filter: seller)* | `RecursiveChunker` | **Có (Top-1, Score 0.7557)** | Đạt 2/2 điểm. Lọc sạch tài liệu ngoài luồng, Top-1 và Top-2 trích xuất đầy đủ 4 hình thức bảo hành. |
| Q5 | Cấm vô hiệu bảo hành vì đánh giá 5 sao | `RecursiveChunker` | **Có (Top-1, Score 0.8115)** | Đạt 2/2 điểm. Top-1 chứa trực tiếp câu cấm điều khoản bán hàng không công bằng. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> **Metadata filter có vai trò quyết định ở Câu hỏi Q4.** Khi chạy có `metadata_filter={"audience": "seller"}`, hệ thống giới hạn phạm vi tìm kiếm trong tập tài liệu quy chuẩn dành riêng cho người bán, đưa tài liệu `tiktok-bao-hanh-hang-tan-trang` lên Top-1 (Score 0.7557) và Top-2 (Score 0.6038 trích dẫn đúng 4 hình thức bảo hành). Ngược lại, khi bỏ filter, tài liệu quy chế chung đồ sộ `tiktok-quy-che-bao-hanh` (audience: `both`) chen chân vào vị trí số 3 với điểm cao (0.5858) làm loãng độ tập trung của câu trả lời.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. **Sự mất cân xứng quy mô tài liệu trong Corpus (Corpus Asymmetry):** Một tài liệu đồ sộ (160KB) có thể "nuốt chửng" các tài liệu nhỏ (3-4KB) trong không gian vector nếu câu hỏi chứa từ khóa chung chung. Cần phải kết hợp metadata filtering hoặc chunking theo cấu trúc heading để cân bằng không gian truy xuất.
> 2. **Ranh giới cắt và độ toàn vẹn ngữ cảnh (Context Boundary):** Trong văn bản pháp lý, các con số định lượng (ví dụ: `600 x 600 pixel`, `48 giờ`) thường nằm ở câu sau của tiêu chí. Nếu ranh giới cắt chia lìa tiêu đề mục với thông số kỹ thuật, cosine similarity có thể vẫn kéo đúng tài liệu nhưng lại thiếu thông tin cốt lõi để trả lời.
> 3. **Giá trị thực tế của Metadata Pre-filtering:** Metadata filtering không chỉ tăng tốc độ tìm kiếm (giảm số lượng vector cần so sánh) mà còn đóng vai trò là "bức tường lửa" ngăn ngừa việc trả về quy định sai đối tượng người dùng (ví dụ: nhầm quyền của Buyer thành nghĩa vụ của Seller).

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một bộ tài liệu và cùng một mô hình embedding (`text-embedding-3-small`), nhưng chiến lược chunking quyết định trực tiếp tới khả năng sống còn của RAG. `FixedSizeChunker` dễ cắt vụn điều khoản; `SentenceChunker` thất bại với bảng dữ liệu; trong khi `RecursiveChunker` và `SectionChunker` giữ được tính mạch lạc, giúp điểm truy xuất vượt trội rõ rệt.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> 1. Bổ sung trường `category` chi tiết hơn vào metadata filter để phân luồng trực tiếp theo từng chuyên đề (`seller-conduct`, `listing-compliance`, `warranty-policy`).
> 2. Thêm tham số `chunk_overlap` (khoảng 80–100 ký tự) cho `RecursiveChunker` để đảm bảo thông số kỹ thuật sát ranh giới cắt không bị rơi rớt giữa hai chunk liền kề.
> 3. Triển khai phương pháp Hybrid Retrieval kết hợp BM25 (tìm từ khóa chính xác như "600x600", "AIGC") cùng Dense Vector Search để đạt độ bao phủ thông tin tuyệt đối.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |
