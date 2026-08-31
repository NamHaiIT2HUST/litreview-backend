# Hướng dẫn: Pull Request `fix/test` → `main`, đồng bộ 2 repo, cập nhật EC2

Tài liệu này hướng dẫn từng bước để đưa toàn bộ công việc Module 1 (Tri-Layer
Evidence Quantification Engine + tích hợp vào cả pipeline Legacy và fast_v2) từ
nhánh `fix/test` lên `main`, đồng bộ sang repo mirror, rồi cập nhật EC2 đang
chạy (`t165-server`, `13.212.121.28`) sao cho chạy đúng y hệt những gì đã kiểm
chứng trên localhost.

**Trạng thái đã kiểm tra trước khi viết tài liệu này** (2026-08-29):
- `fix/test` chứa toàn bộ `origin/main` (là ancestor của nó) → merge sẽ **không
  có conflict**.
- `origin/main` (repo tổ chức `AI20K-Build-Phase-Cohort-3/P-165`) và
  `mirror/main` (repo cá nhân `NamHaiIT2HUST/litreview-backend`) hiện **giống
  hệt nhau về code** (chỉ khác 2 merge-commit rỗng, không có diff thật) — 2
  repo đang đồng bộ tốt, chỉ cần lặp lại đúng quy trình cũ.
- EC2 (`i-0167474bb9f75ed02`) hiện đang ở nhánh `main`, thư mục `~/P-165`,
  chạy bằng `nohup` (không phải Docker) — dựa trên file `nohup.out` xuất hiện
  trong `git status`.

⚠️ **Trước khi bắt đầu**: remote `origin` trên máy này đang lưu một Personal
Access Token thẳng trong URL (`git remote -v`). Sau khi xong việc hôm nay, thu
hồi token đó trên GitHub và chuyển sang `gh auth login`. Không dán token này
vào đâu khác.

---

## PHẦN A — Tạo Pull Request `fix/test` → `main` (repo `P-165`)

`fix/test` đã lên `origin` đầy đủ (`git status` báo "up to date with
'origin/fix/test'"), nên không cần push gì thêm trước bước này.

1. Mở: `https://github.com/AI20K-Build-Phase-Cohort-3/P-165/compare/main...fix/test`
2. Bấm **Create pull request**.
3. Điền:
   - **Title**: `feat(module1): Tri-Layer Evidence Quantification Engine — train, integrate, verify`
   - **Description** (gợi ý, sửa lại theo văn phong bạn muốn):
     ```markdown
     ## Tóm tắt
     Triển khai đầy đủ Module 1 (Tri-Layer Evidence Quantification Engine —
     xem MODULE_1_PLAN.md): tự huấn luyện và so sánh 3 mô hình NLI trên Colab,
     tích hợp Tier 1 (khớp gần-nguyên-văn) + Tier 2 (NLI cục bộ) làm pre-filter
     trước Tier 3 (LLM-as-Judge hiện có) cho CẢ 2 pipeline tổng hợp (Legacy
     `cross_paper_analysis` và fast_v2 `SectionScopedSynthesisPipeline`), thêm
     endpoint/UI đo lường chất lượng trích dẫn thật, và sửa 2 bug hiển thị trên
     UI (citation chỉ gán cho câu đầu mỗi đoạn; batch size 8 khiến model bỏ
     sót nhiều câu có thể trích dẫn được).

     ## Chi tiết theo commit
     - `7cd5fc3` port cải thiện độ chính xác synthesis từ nhánh feat/synthesis-fast-v2-ui
     - `1dbb9c0` fix ragas_eval_service tính điểm RAGAS thật (không còn fallback ngầm)
     - `ce4a380` huấn luyện + chọn model NLI (script sinh dataset, notebook Colab, báo cáo benchmark)
     - `c84cb49` nối Tier 2 (NLI) pre-filter vào cross_paper_analysis (Legacy)
     - `88ced5c` thêm Tier 1 (khớp gần-nguyên-văn) + endpoint đo chất lượng /quality
     - `59000d7` nối Tier 1/2 pre-filter vào citation pipeline fast_v2 thật (nơi UI dùng)
     - `22f1513` sửa citation chỉ gán đúng cho đoạn đầu; card đo lường hiện số liệu thật
     - `8feaf95` hoàn thiện, kiểm tra lại toàn bộ

     ## Kiểm chứng
     - `pytest tests/test_fast_v2/ tests/test_services/` — 680 pass (4 fail +
       3 error còn lại là pre-existing, xác nhận bằng git stash trước khi sửa).
     - Test end-to-end thật (không mock): PDF thật → DocumentProcessor →
       cross_paper_analysis() → NLI model thật → /quality endpoint, đúng số.
     - `npm run lint` + `npm run build` sạch.
     - Migration DB: cột mới `citation_coverage_telemetry` (JSONB, nullable) —
       additive-only qua `ensure_local_schema_compatibility()`, không cần
       downtime, không ảnh hưởng dữ liệu cũ.
     ```
4. **Merge method**: chọn **"Create a merge commit"** (không squash — 8 commit
   đã có message rõ từng phần việc, giữ nguyên để dễ tra cứu sau này).
5. Bấm **Merge pull request** → **Confirm merge**.
6. GitHub sẽ hỏi có xoá nhánh `fix/test` không — xoá hay giữ đều được, không
   ảnh hưởng gì (giữ lại nếu muốn tham chiếu sau).

---

## PHẦN B — Đồng bộ `main` sang repo mirror (`litreview-backend`)

Chạy trên máy này, **sau khi** PR ở Phần A đã merge xong trên GitHub:

```bash
git checkout main
git pull origin main
git push mirror main
```

Nếu lệnh `push` cuối bị từ chối (non-fast-forward — vì `mirror/main` có 2
merge-commit riêng không nằm trong `origin/main`), chạy thêm:

```bash
git pull mirror main --no-edit
git push mirror main
```

Đây là `git pull`/merge bình thường, không phải force-push — an toàn, giữ
nguyên lịch sử.

**Xác nhận đã đồng bộ**: `https://github.com/NamHaiIT2HUST/litreview-backend/commits/main`
phải thấy đúng 8 commit `feat(module1)...` mới nhất ở trên cùng.

---

## PHẦN C — Cập nhật EC2 (`13.212.121.28`, `t165-server`)

### C.0. Vào EC2

Dùng đúng cách bạn đã dùng (EC2 Instance Connect qua AWS Console — "Connect" ở
trang Instances), hoặc SSH bằng key pair nếu có:
```bash
ssh -i /path/to/key.pem ubuntu@13.212.121.28
```

### C.1. Kiểm tra trạng thái hiện tại trước khi đổi gì

Backend chạy qua **systemd service `litreview-backend`** (xem C.7) — không
`kill`/`nohup` thủ công cho các bước dưới đây.

```bash
cd ~/P-165
git status
sudo systemctl status litreview-backend --no-pager   # xem service đang chạy thế nào
ps aux | grep uvicorn          # phải chỉ thấy đúng 1 dòng process
which python3 && python3 --version
ls -la .venv 2>/dev/null || ls -la venv 2>/dev/null   # tìm virtualenv đang dùng
free -h                        # RAM hiện tại — QUAN TRỌNG, xem mục C.4
```

Nếu có `.venv` hoặc `venv`, mọi lệnh `pip`/`python` bên dưới cần chạy sau khi
`source .venv/bin/activate` (hoặc đường dẫn tương ứng tìm được ở bước này).

### C.2. Backup rồi kéo code mới

```bash
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)     # luôn backup .env trước khi đổi
git fetch origin
git status                      # xác nhận không có gì uncommitted bị mất
git pull origin main
```

Nếu `git status` ở trên báo có thay đổi cục bộ ngoài `.env.save`/`nohup.out`
(untracked, đã biết là vô hại), dừng lại và kiểm tra kỹ trước khi `pull` —
đừng để mất việc gì đó đang dở trên EC2 mà local chưa có.

### C.3. Cài dependency mới

Nhánh này thêm 2 gói mới bắt buộc cho model NLI (`sentencepiece` cho tokenizer
của DeBERTa-v3, `accelerate` cho `transformers.Trainer`):

```bash
pip install -r requirements.txt
```

### C.4. RAM — ĐÃ THỬ THẬT trên instance này, kết luận: Tier 2 KHÔNG bật được an toàn

**Kết quả đo thật (2026-08-29), không phải ước lượng**: instance `t165-server`
(`t3.small`, 2GB RAM) có RAM `available` baseline (backend chạy, chưa bật NLI)
chỉ **615MB**. Đã thử cả model C (nhẹ nhất trong 3 model, 279MB trên đĩa):

| Thời điểm đo | RAM `available` |
|---|---|
| Baseline, trước khi bật NLI | 615MB |
| Model C đã load thật vào RAM (xác nhận qua log, không phải đoán) | **140MB** |

140MB dưới hẳn ngưỡng an toàn (150-200MB) — và trên thực tế, **kernel OOM-killer
đã thật sự giết chết tiến trình backend** trong lúc đo (`dmesg`/`journalctl`
xác nhận: `Out of memory: Killed process ... (python)`), gây gián đoạn dịch vụ
thật. Đây không phải suy đoán lý thuyết mà là sự cố đã xảy ra và được xác nhận
bằng log kernel.

**Kết luận cho instance `t3.small` này**: `NLI_EVIDENCE_ENABLED` phải để
**`false`**. Tier 1 (khớp gần-nguyên-văn, không tốn RAM) và Tier 3 (LLM) vẫn
hoạt động đầy đủ như trước — hệ thống không có gì bị lỗi, chỉ là chưa tận dụng
được phần tối ưu chi phí của riêng Tier 2. Muốn bật Tier 2 thật sự an toàn,
cần nâng cấp lên `t3.medium` (4GB) trở lên qua AWS Console (Stop instance →
Actions → Instance settings → Change instance type → Start lại) — khi đó có
thể dùng lại model B (549MB, F1-macro cao hơn, xem `models/nli_evidence_benchmark_report.md`)
thay vì phải giới hạn ở model C. Instance thứ 2 hiện có (`i-0e32d07358d3fd99e`)
cũng nên kiểm tra có đang dùng không, tránh trả tiền cho instance thừa.

### C.5. Copy model NLI lên EC2 (đã làm — model C, sẵn sàng cho khi nâng cấp instance)

Dù mục C.4 kết luận Tier 2 phải tắt trên instance hiện tại, model C (279MB,
nhẹ nhất trong 3 model — xem `models/nli_evidence_benchmark_report.md`) đã
được copy sẵn lên EC2 tại `~/P-165/models/nli_evidence_v1/`, để khi nâng cấp
instance chỉ cần đổi `NLI_EVIDENCE_ENABLED=true` trong `.env` và restart, không
cần copy lại gì.

Model này **không nằm trong git** (bị `.gitignore`, đúng chủ đích — không
commit weight file). Copy trực tiếp từ máy này, đặt tên thư mục đích là
`nli_evidence_v1` (khớp với `.env` mặc định, không cần đổi biến
`NLI_EVIDENCE_MODEL_PATH`):

```bash
# Chạy trên MÁY LOCAL (không phải trên EC2), từ thư mục dự án:
scp -i /path/to/key.pem -r scripts/finetune_nli/candidates/C_xsmall_nli_pretrained \
    ubuntu@13.212.121.28:~/P-165/models/
```

Việc này copy khoảng 279MB vào `~/P-165/models/C_xsmall_nli_pretrained/` —
nhanh hơn model B đáng kể. Trên EC2, đổi tên đúng vào đường dẫn `.env` đang
trỏ tới (xóa thư mục `nli_evidence_v1` cũ trước nếu có, ví dụ từ lần copy hụt
trước đó):

```bash
cd ~/P-165/models
rm -rf nli_evidence_v1
mv C_xsmall_nli_pretrained nli_evidence_v1
ls -la nli_evidence_v1
# phải thấy config.json, model.safetensors (hoặc pytorch_model.bin), tokenizer files
```

Nếu sau này muốn nâng lên model B (độ chính xác cao hơn) khi đã nâng cấp
instance lên t3.medium trở lên, chỉ cần lặp lại bước này với
`models/nli_evidence_v1` (model B) từ máy local, ghi đè thư mục cũ trên EC2 —
không cần đổi gì khác trong code hay `.env`.

### C.6. Cập nhật `.env` trên EC2

Mở `.env` (`nano ~/P-165/.env`) và đảm bảo có đủ các dòng sau (thêm nếu thiếu,
sửa nếu giá trị khác):

```env
# Module 1 — KHÔNG bật trên t3.small (xem mục C.4: đã thử thật, gây OOM kill
# backend). Chỉ đổi thành true sau khi nâng cấp instance lên t3.medium+.
NLI_EVIDENCE_ENABLED=false
NLI_EVIDENCE_MODEL_PATH=./models/nli_evidence_v1

# fast_v2 Writer/Citation model — PHẢI khớp với local (đã xác nhận trên
# localhost bạn dùng gpt-4o-mini cho cả 2, không phải model mặc định khác)
FAST_V2_WRITER_MODEL=gpt-4o-mini
FAST_V2_VERIFIER_MODEL=gpt-4o-mini
```

Không copy nguyên `.env` từ local sang EC2 — `DATABASE_URL`, API key, và các
biến hạ tầng khác trên EC2 khác với local, chỉ thêm/sửa đúng 4 dòng trên.

### C.7. Khởi động lại backend — dùng `systemctl`, KHÔNG dùng `nohup`/`kill` thủ công

**Quan trọng, phát hiện thật trong lúc triển khai**: backend trên EC2 này
được quản lý bởi một **systemd service** có sẵn tên `litreview-backend`
(`Restart=always`, `RestartSec=5`) — không phải chạy tay qua `nohup` (file
`nohup.out` trong thư mục dự án chỉ là tàn dư từ một lần chạy thử cũ, không
phải cách service thật đang chạy). Dùng `kill <PID>` trực tiếp sẽ khiến
systemd **tự động khởi động lại một tiến trình mới ngay sau đó** — nếu đồng
thời có ai đó/script nào khác cũng tự `nohup` một bản riêng, sẽ có **2 tiến
trình backend chạy song song, tranh RAM** (đây chính là một phần nguyên nhân
gây OOM kill thật đã xảy ra trong lúc soạn tài liệu này). Luôn dùng đúng lệnh
`systemctl` để không rơi vào tình huống đó:

```bash
sudo systemctl restart litreview-backend
sleep 5
sudo systemctl status litreview-backend --no-pager
```

`status` phải hiện `Active: active (running)` và đúng 1 PID trong `CGroup`.
Nếu nghi ngờ có tiến trình orphan khác đang chạy song song, kiểm tra và dọn
trước khi restart:

```bash
ps aux | grep '[u]vicorn'    # phải chỉ thấy ĐÚNG 1 dòng process
```

Khi tiến trình khởi động, `create_all_tables()` +
`ensure_local_schema_compatibility()` sẽ **tự động** thêm cột mới
`citation_coverage_telemetry` vào bảng `synthesis_sessions` — không cần chạy
migration thủ công nào cả (đúng cách project này vẫn làm cho các cột trước
đó).

### C.8. Kiểm tra sau khi khởi động lại

```bash
curl -s http://localhost:8000/health
free -h                       # RAM baseline — với NLI_EVIDENCE_ENABLED=false
                               # (C.6), phải thấy available tương đương hoặc
                               # tốt hơn baseline gốc (~615-750MB), KHÔNG cần
                               # đo thêm gì vì Tier 2 không được load.
journalctl -u litreview-backend -n 50 --no-pager   # xem log khởi động qua systemd
```

**Nếu sau này nâng cấp lên t3.medium+ và muốn bật Tier 2**: đổi
`NLI_EVIDENCE_ENABLED=true` trong `.env`, `sudo systemctl restart litreview-backend`,
rồi bắt buộc lặp lại phép đo ở mục C.4 (gọi thử `nli_checker.check(...)` để
buộc model load thật vào RAM, đo `free -h` NGAY lúc đó, không phải suy đoán từ
số đo trước khi model load) trước khi coi là an toàn — lazy-loading khiến số
đo ngay sau khi restart luôn trông "ổn" một cách giả tạo.

Kiểm tra riêng NLI model load được (không lỗi label mismatch):
```bash
cd ~/P-165
python3 -c "
import asyncio
from src.services.nli_checker import nli_checker
v = asyncio.run(nli_checker.check('Test premise.', 'Test claim.'))
print('OK:', v.status, v.confidence)
"
```
Nếu dòng này báo `NLIModelUnavailableError`, xem lại đường dẫn ở C.5/C.6.

### C.9. Kiểm tra thực tế qua trình duyệt

Mở `http://13.212.121.28:8000/health` từ máy khác để xác nhận backend chạy
được từ ngoài (không chỉ localhost trên EC2) — nếu không vào được, kiểm tra
Security Group của EC2 có mở port 8000 (hoặc port bạn expose) cho inbound
traffic chưa (EC2 Console → instance → Security → Security groups → Inbound
rules).

Nếu frontend production của bạn trỏ tới URL backend cũ, cập nhật biến
`VITE_API_BASE` ở nơi build frontend (Vercel, hoặc nơi bạn deploy — xem
`DEPLOY_GUIDE.md` phần 4 nếu dùng Vercel) trỏ đúng về địa chỉ EC2 mới, rồi
build/deploy lại frontend.

---

## Tóm tắt thứ tự thao tác

1. Phần A: Tạo & merge PR `fix/test → main` trên GitHub (web UI).
2. Phần B: 3 lệnh git trên máy local để đồng bộ sang repo mirror.
3. Phần C: SSH vào EC2 → backup `.env` → `git pull` → cài dependency → kiểm
   tra RAM → copy model (550MB qua `scp`) → sửa `.env` → restart → kiểm tra
   log + `/health` + Security Group.
