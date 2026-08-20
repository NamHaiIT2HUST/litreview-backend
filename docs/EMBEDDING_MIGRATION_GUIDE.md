# Hướng dẫn migrate sau khi pull `develop` (fix embedding provider)

`develop` vừa merge 4 thay đổi liên quan tới retrieval (vector search). Một
trong số đó (`fix/openai-embedding-provider`) đổi cách hệ thống tạo vector —
**nếu máy bạn đã có dữ liệu Chroma cũ, bạn cần làm theo hướng dẫn này trước
khi chạy app**, nếu không app sẽ crash khi search/chat.

## Tại sao phải làm việc này

Trước đây, nếu `.env` không đặt đúng `EMBEDDING_PROVIDER=openai` (hoặc thiếu
`OPENAI_API_KEY`), hệ thống âm thầm rơi vào `LightweightHashEmbeddings` — một
embedding giả (hash từ, không hiểu ngữ nghĩa) chỉ dùng cho demo/test, không
phải model thật. Nó tạo vector **128 chiều**.

Bản fix mới dùng embedding thật (OpenAI/OpenRouter `text-embedding-3-small`),
tạo vector **1536 chiều**.

Chroma (vector database) **khóa cứng số chiều theo lần insert đầu tiên của
collection**. Một collection đã có vector 128 chiều sẽ **từ chối** nhận thêm
vector 1536 chiều — bạn sẽ gặp lỗi:

```
Collection expecting embedding with dimension of 128, got 1536
```

Đây không phải bug của bản fix mới — mà là hệ quả tất yếu của việc đổi từ
embedding giả sang embedding thật. Nói cách khác: **dữ liệu vector cũ của
bạn (nếu có) đã luôn vô dụng cho semantic search thật** — hash embedding
không hiểu nghĩa, chỉ khớp từ vựng thô — nên không có gì đáng tiếc khi phải
xóa và tạo lại.

## Bạn có cần làm việc này không?

Kiểm tra nhanh:

```bash
grep EMBEDDING_PROVIDER .env
```

- Nếu ra `EMBEDDING_PROVIDER=local` (hoặc không có dòng này) **và bạn chưa
  đổi** → bạn KHÔNG cần làm gì, app vẫn chạy bằng hash embedding cũ như
  trước (không có gì thay đổi hành vi). Tuy nhiên bạn cũng sẽ không có
  retrieval chất lượng tốt — nên cân nhắc chuyển sang bước dưới.
- Nếu bạn **định chuyển** sang `EMBEDDING_PROVIDER=openai` (khuyến nghị,
  đây là fix chính) → làm theo các bước dưới đây.

## Các bước thực hiện

### Bước 1 — Cập nhật `.env`

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=<key của bạn>
```

Nếu dùng OpenRouter thay vì OpenAI trực tiếp: dùng key có prefix `sk-or-v1-`
và đặt `EMBEDDING_MODEL=openai/text-embedding-3-small` (có prefix
`openai/`) — hệ thống tự nhận diện key OpenRouter và route đúng endpoint
(xem `src/config.py`, hàm `get_api_base`).

### Bước 2 — Xóa collection Chroma cũ

Vì lý do đã giải thích ở trên (khóa cứng dimension), phải xóa collection cũ
trước khi tạo vector mới:

```bash
python -c "
import chromadb
client = chromadb.PersistentClient(path='./data/chroma')
client.delete_collection('litreview_papers_v2')
print('deleted')
"
```

Nếu bạn không chắc tên collection, kiểm tra trước bằng:

```bash
python -c "
import chromadb
client = chromadb.PersistentClient(path='./data/chroma')
print([c.name for c in client.list_collections()])
"
```

**Lưu ý**: đây là bước xóa dữ liệu — chỉ xóa **vector**, không đụng gì tới
Postgres (nơi giữ `chunk_text` gốc). Vector mất đi ở bước này hoàn toàn có
thể tạo lại được từ Postgres ở bước 3, không mất dữ liệu thật sự.

### Bước 3 — Re-embed lại toàn bộ paper đã ingest

```bash
python scripts/reembed_openai_migration.py --dry-run
```

Xem trước số paper/chunk sẽ bị ảnh hưởng, không tốn phí API. Nếu ổn, chạy
thật:

```bash
python scripts/reembed_openai_migration.py
```

Script này đọc lại toàn bộ `chunk_text` từ Postgres (theo `active_ingestion_id`
của mỗi paper), gọi API embedding thật, rồi ghi vào collection Chroma mới —
tự tạo lại collection với đúng dimension 1536.

Script **an toàn khi bị gián đoạn giữa chừng**: với mỗi paper, nó luôn thêm
vector mới trước, xóa vector cũ sau — nên nếu script crash giữa chừng, dữ
liệu cũ (nếu còn) vẫn nguyên vẹn, không có khoảng trống mất dữ liệu.

### Bước 4 — Xác nhận đã đúng

```bash
python -c "
import asyncio
from src.services.vector_store import VectorStoreService

async def main():
    svc = VectorStoreService()
    docs = await svc.search_similar_documents('<một câu hỏi liên quan tới paper của bạn>', top_k=3)
    for d in docs:
        print(d.metadata.get('paper_id'), d.metadata.get('page'))
        print(d.page_content[:150])

asyncio.run(main())
"
```

Nếu kết quả trả về đúng ngữ nghĩa câu hỏi (không chỉ khớp từ khóa trùng),
retrieval đã hoạt động đúng.

## Nếu bạn thấy dữ liệu Chroma có nhiều hơn số paper trong Postgres

Nếu `client.list_collections()` cho thấy 1 collection có số vector nhiều bất
thường so với số paper thật trong DB của bạn — **dừng lại, đừng xóa ngay**.
Kiểm tra trước bằng:

```bash
python -c "
import chromadb
client = chromadb.PersistentClient(path='./data/chroma')
coll = client.get_collection('litreview_papers_v2')
print('vector count:', coll.count())
"
```

So với:

```bash
python -c "
import asyncio
from sqlalchemy import select, func
from src.database import AsyncSessionLocal
from src.models.db_models import PDFChunk

async def main():
    async with AsyncSessionLocal() as session:
        total = (await session.execute(select(func.count(PDFChunk.id)))).scalar()
        print('total PDFChunk rows in Postgres:', total)

asyncio.run(main())
"
```

Nếu số vector trong Chroma **lớn hơn hẳn** số chunk trong Postgres, có nghĩa
là có vector "mồ côi" (paper_id không còn tồn tại trong DB hiện tại — có thể
do DB từng bị reset nhưng Chroma không bị dọn theo). Những vector đó vẫn giữ
nguyên `chunk_text` gốc (Chroma lưu cả document text, không chỉ vector), nên
**không thể phục hồi lại bằng script `reembed_openai_migration.py`** (script
chỉ đọc từ Postgres). Nếu gặp trường hợp này, hỏi người quản lý dữ liệu của
nhóm trước khi xóa — đừng tự ý xóa như hướng dẫn ở Bước 2.

## Tóm tắt

| Bước | Lệnh | Mục đích |
|---|---|---|
| 1 | Sửa `.env` | Bật embedding thật |
| 2 | `client.delete_collection(...)` | Dọn vector cũ (bị khóa dimension) |
| 3 | `python scripts/reembed_openai_migration.py` | Tạo lại vector đúng từ Postgres |
| 4 | Test search thử | Xác nhận retrieval hoạt động đúng ngữ nghĩa |
