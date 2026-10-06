# Reflection — Lab 19

**Tên:** Phùng Gia Bảo
**Cohort:** A20-K4
**Path đã chạy:** lite

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Trên 50 golden queries, Hybrid có Precision@10 trung bình cao nhất (78,6%),
so với BM25 (77,8%) và Vector (73,2%). Với nhóm `exact`, BM25 và Hybrid cùng
đạt 96,7% vì thuật ngữ kỹ thuật xuất hiện nguyên văn. Ở nhóm `mixed`, Hybrid
thắng rõ với 100% nhờ RRF kết hợp tín hiệu từ khóa chính xác và độ tương đồng
ngữ nghĩa. Riêng `paraphrase`, BM25 đạt 33,3%, Hybrid 32,0% và Vector 24,0%.
Kết quả này trái với kỳ vọng Vector sẽ thắng, nhưng hợp lý vì Lite path dùng
`bge-small-en-v1.5`, một mô hình thiên về tiếng Anh, cho truy vấn diễn đạt lại
bằng tiếng Việt.

Tôi không dùng Hybrid khi truy vấn chứa mã sản phẩm, tên hàm, lỗi hoặc định danh
chính xác: BM25 đơn giản, nhanh và dễ giải thích hơn. Pure Vector phù hợp khi
người dùng hỏi theo ý nghĩa, từ đồng nghĩa hoặc diễn đạt mơ hồ, với điều kiện
mô hình embedding hỗ trợ tốt ngôn ngữ và domain. Hybrid là mặc định an toàn
cho lưu lượng hỗn hợp, nhưng phải trả thêm chi phí embedding và fusion.

---

## Điều ngạc nhiên nhất khi làm lab này

Điều ngạc nhiên nhất là lựa chọn embedding model có thể đảo ngược kết quả mong
đợi: vector search không tự động tốt hơn BM25 chỉ vì nó “hiểu ngữ nghĩa”. Tôi
cũng thấy post-filter có thể âm thầm đưa recall về 0 khi filter chỉ còn 3,8% corpus.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/`)
- [ ] Pair work — thực hiện cá nhân
