# Slide thuyết trình

Bộ slide cho đồ án **Edge AI Multi-Agent — Giám sát môi trường thông minh** (CE2206).

| File | Mô tả |
|------|--------|
| [`thuyet-trinh.md`](thuyet-trinh.md) | Nội dung slide (Marp Markdown), ~22 slide, 16:9 |

## Chỉnh sửa trước khi trình bày

Trong `thuyet-trinh.md`, thay các placeholder:

- `*[Họ và tên sinh viên]*`
- `*[MSSV]*`
- `*[Giảng viên hướng dẫn]*`

## Cách xem / xuất slide

### Cách 1 — Cursor / VS Code (khuyến nghị)

1. Cài extension **[Marp for VS Code](https://marketplace.visualstudio.com/items?itemName=marp-team.marp-vscode)**
2. Mở `thuyet-trinh.md`
3. Biểu tượng preview (góc phải) hoặc lệnh **Marp: Open Preview**
4. Xuất PDF/PPTX: **Marp: Export Slide Deck**

### Cách 2 — Marp CLI

```bash
npm install -g @marp-team/marp-cli
cd reports/slides
marp thuyet-trinh.md --pdf -o thuyet-trinh.pdf
marp thuyet-trinh.md --pptx -o thuyet-trinh.pptx
marp thuyet-trinh.md --html -o thuyet-trinh.html
```

### Cách 3 — Copy sang Google Slides / PowerPoint

Xuất PDF hoặc PPTX rồi import, hoặc copy từng slide từ preview Marp.

## Gợi ý thời lượng (~10–12 phút)

| Phần | Slide | Thời gian |
|------|-------|-----------|
| Mở đầu | 1–3 | ~1,5 phút |
| Kiến trúc & agent | 4–9 | ~3 phút |
| AI & fault tolerance | 10–11 | ~2 phút |
| Hiện thực & thí nghiệm | 12–17 | ~3 phút |
| Demo, kết luận, Q&A | 18–22 | ~2,5 phút |

Khi demo live, ưu tiên slide **Dashboard**, **Fault injection** và chạy `docker compose ps` + `inject_fault_analysis.sh`.
