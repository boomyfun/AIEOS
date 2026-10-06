# CR-001 — Bản đính chính cho AIEOS-concept.md v0.5

> Trạng thái: chủ dự án đã duyệt ngày 2026-10-07: "kết quả: có; đính chính: có" (session 02bd7476, transcript :1927), trả lời câu hỏi "Bản đính chính cho ý tưởng ban đầu gồm 8 chỗ sửa nhỏ đã ghi sẵn trong bảng quyết định của dự án, và 2 chỗ để mở cho bước sau. Ý tưởng gốc giữ nguyên; bản đính chính là một tài liệu riêng sẽ đưa lên GitHub (công khai, ở lại vĩnh viễn). Bạn duyệt không?". E4 và E10 vẫn để mở. Ý tưởng ban đầu (concept v0.5) giữ nguyên từng byte (DM A22); mọi sửa đổi chỉ nằm trong tài liệu đính chính này. Nguồn nội dung: DM B13 và B18. Tên một dự án không liên quan, có trong văn bản gốc, được thay bằng "[dự án khác]" và không được chép lại.
> Cách diễn đạt các đính chính là của Claude; nội dung lấy từ các dòng nguồn ghi ở cột cuối.

## 1. Các mục đính chính

| # | Vị trí trong concept | Văn bản gốc | Đính chính đề xuất | Nguồn |
|---|---|---|---|---|
| E1 | §8.5 (dòng 628–656) | Dòng 630: "Adapter không chỉ khai báo *"hỗ trợ MCP"* mà khai báo **mức enforcement thật**:", tiếp theo là các ví dụ YAML ở dòng 632–643 | Mức đảm bảo của một adapter **không được tự khai báo**. Nó chỉ có giá trị khi đã được đo, cho từng tổ hợp runtime × nền tảng × phiên bản × cấu hình; chưa đo thì là `advisory`. | B13; DM quy tắc "unmeasured → advisory" |
| E2 | §16 (dòng 946) | "Adapter **Codex (T1/T2)** — để chứng minh core trung lập ngay từ đầu" | Bỏ khỏi v0.1. Adapter Codex chuyển sang bản sau. v0.1 chỉ có adapter Claude Code. | B13 |
| E3 | §13.3 (dòng 851–859) | (không có ngoại lệ cho giai đoạn khởi tạo) | Thêm: các bản ghi được viết **trong giai đoạn khởi tạo** (trước khi AIEOS tự quản lý việc xây chính nó) (diễn giải của Claude) ghi rõ ai đã ghi, và **không có giá trị chính thức**. | B13 |
| E4 | — | (B13 chỉ ghi "layout") | Không đề xuất văn bản: B13 không nêu cụ thể "layout" là gì. Để mở. | B13 |
| E5 | §16 (dòng 962) | "Dogfooding: dùng AIEOS để build AIEOS — và dùng trên [dự án khác] như project thật đầu tiên." | "Dogfooding: dùng AIEOS để build AIEOS; dự án đo của v0.1 là chính việc AIEOS tự xây nó." | B13; A43 (người dùng đầu tiên là chủ dự án) |
| E6 | §17 câu 4 (dòng 971) | "Ngôn ngữ đầu tiên cho constitution checker (TS? Python?) — quyết định theo [dự án khác]." | "Ngôn ngữ đầu tiên cho constitution checker: quyết định bằng một ADR về công nghệ (stack ADR), sau benchmark (DM A8, A10)." | B13 |
| E7 | §11 (dòng 789, 793, 806) | 793: "task tự sinh · risk: low · V0+V1 · auto-accept · 1 dòng log. Xong."; 806: "thời gian human trên mỗi task risk thấp ≈ 0" | Auto-accept chỉ áp dụng ở mức tự chủ L2 trở lên. Ở L1 (mức khởi đầu), task risk thấp dừng ở NEEDS_REVIEW và được duyệt theo lô một lần bấm. Dòng 806 là **mục tiêu** đo theo §12, không phải bất biến ngay từ đầu. | B18 (1); A35 |
| E8 | §5.3 (dòng 300) và §7.4 (dòng 524–527) | 300: "NEEDS_REVIEW — Đủ evidence tự động nhưng risk/policy yêu cầu human duyệt" | Dòng 300 thành: "Đủ evidence profile (kể cả evidence do người tạo) nhưng risk hoặc policy yêu cầu người duyệt". §7.4: task thiếu loại evidence mà **chỉ người mới tạo được** đi sang IN_REVIEW, không sang REWORK. | B18 (2); A36 |
| E9 | §8.2 (dòng 574) | "…adapter thực sự enforce được gì (8.4)…" | Tham chiếu "(8.4)" sửa thành "(8.5)". | B18 (3); A37 |
| E10 | §9.2 (dòng 703) | `ai_review (cross-model)` trong profile mặc định cho task risk cao | **Mở, quyết ở bước 6.** Không đề xuất văn bản. | B18 (4); DEF-0008 |

## 2. Không thuộc CR-001 này

- Các điểm tự mâu thuẫn khác trong concept mà Claude từng ghi nhận (DEF-0007), và "17 nghĩa vụ ngầm": ngoài phạm vi.
- Mọi thay đổi chỉ có hiệu lực khi chủ dự án duyệt CR-001 (DM A22).
