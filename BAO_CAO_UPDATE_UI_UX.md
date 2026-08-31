# BÁO CÁO CHI TIẾT CÁC THAY ĐỔI & NÂNG CẤP HỆ THỐNG
**Dự án**: VinUni AI - TEAM 165 (LitReview Agent)  
**Nhánh nguồn cơ sở**: `fix/test`  
**Nhánh cập nhật mới**: `nvhung-fix-test`  
**Ngày cập nhật**: 29/08/2026  

---

## I. TỔNG QUAN PHẠM VI NÂNG CẤP

Đợt cập nhật này tập trung vào việc **tái cấu trúc toàn diện trải nghiệm người dùng (UI/UX)**, tối ưu luồng thao tác nghiên cứu học thuật, đồng bộ hóa nhận diện thương hiệu và hoàn thiện hệ thống hướng dẫn người dùng mới, đồng thời **bảo toàn nguyên vẹn 100% logic xử lý của Backend (FastAPI)**.

### Các trọng tâm chính:
1. **Đồng bộ hóa Trình chuyển đổi Đề tài (Project Switcher)**: Gộp nút quay lại và danh sách sổ ghi chú thành menu dropdown thống nhất, đồng bộ thuật ngữ "Đề tài / Notebook".
2. **Cố định Header (Sticky Header) & Tối ưu Responsive**: Đảm bảo Header luôn cố định khi cuộn trang ở tất cả các tab và loại bỏ khoảng trắng dư thừa hai bên màn hình.
3. **Tái cấu trúc Chức năng Export (In-Context Export)**: Xóa tab Export độc lập; tích hợp tính năng tải dữ liệu đa định dạng (BibTeX, CSV, Markdown, JSON) trực tiếp tại ngữ cảnh của từng màn hình.
4. **Hệ thống Điều hướng Phẳng 5 Tab (5 Flat Tabs Navigation)**: Đưa các phân hệ chuyên sâu (*Setup, Search, Chat với nguồn, Tổng quan tài liệu, Phân tích dữ liệu*) lên trực tiếp thanh Header chính.
5. **Dọn dẹp Subtab trùng lặp trong Workspace**: Loại bỏ thanh 3 nút con bị lặp lại trong khung nội dung, thay bằng tiêu đề ngữ cảnh trực quan và nút dọn dẹp hội thoại.
6. **Xây dựng Onboarding Tour Tương tác 6 Bước**: Hướng dẫn người dùng từng bước khi đăng nhập lần đầu, khi tạo đề tài mới, và cho phép xem lại bất kỳ lúc nào từ menu người dùng.
7. **Chuẩn hóa Nhận diện Thương hiệu (Origami Logo & Favicon Bundle)**: Thiết kế component `BrandLogo` dùng chung SVG chuẩn, bổ sung trọn bộ Favicon cho trình duyệt.
8. **Dọn dẹp Tài nguyên thừa**: Xóa 13 file asset/logo nháp không sử dụng trong `frontend/src/assets`.

---

## II. CHI TIẾT CÁC TÍNH NĂNG ĐÃ ĐƯỢC CHỈNH SỬA & NÂNG CẤP

### 1. Đồng bộ hóa Sổ ghi chú & Nút Quay lại (Project Switcher Hub)
- **Vấn đề cũ**: Trên giao diện xuất hiện đồng thời nút "Tất cả sổ ghi chú" và một dropdown chuyển đề tài riêng biệt; thuật ngữ giữa "Sổ ghi chú", "Đề tài", "Notebook" chưa đồng bộ.
- **Giải pháp thực hiện**:
  - Gộp chung thành một component Dropdown duy nhất trên Header góc trên bên trái: `[ 🗂️ Tên Đề tài Hiện tại ▾ ]`.
  - Bên trong dropdown tích hợp:
    - Nút `← Quay lại Tất cả Đề tài` (chuyển về màn hình Tổng quan Overview).
    - Nút `+ Khởi tạo Đề tài Mới`.
    - Nút `📥 Xuất Gói Đề tài (.json)`.
    - Danh sách các đề tài hiện có kèm dấu tích đánh dấu đề tài đang chọn.
  - Đồng bộ thuật ngữ tiếng Việt sang **"Đề tài"** và tiếng Anh sang **"Project / Notebook"**.

---

### 2. Cố định Header (Sticky Header) & Tối ưu Hiển thị Toàn màn hình (Responsive)
- **Vấn đề cũ**: Header bị trôi mất khi người dùng cuộn trang ở màn hình Setup và Workspace; khoảng trống hai bên lề quá lớn trên màn hình độ phân giải cao.
- **Giải pháp thực hiện**:
  - Cập nhật Header với class `sticky top-0 z-50 w-full backdrop-blur-md bg-white/95 dark:bg-slate-900/95` đảm bảo Header luôn cố định khi cuộn ở bất kỳ màn hình nào.
  - Mở rộng giới hạn container từ `max-w-5xl` thành `max-w-7xl 2xl:max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8`, giúp giao diện co giãn linh hoạt và tận dụng tối đa diện tích hiển thị.

---

### 3. Chuẩn hóa Nút & Modal Tạo Đề tài Mới (New Project Modal)
- **Vấn đề cũ**: Nút "Tạo đề tài mới" bị hiển thị 2 dấu cộng `++` trùng lặp; giao diện modal tạo đề tài còn đơn điệu.
- **Giải pháp thực hiện**:
  - Xóa bỏ icon `Plus` thừa, chỉ giữ lại một icon duy nhất kèm nhãn rõ ràng.
  - Bổ sung 6 chủ đề gợi ý nhanh chuẩn học thuật (Y sinh, AI & LLM, Robotics, Khoa học môi trường, Khoa học dữ liệu, Kinh tế tài chính) giúp người dùng điền nhanh đề tài mẫu với 1 cú nhấp chuột.

---

### 4. Tái cấu trúc Chức năng Export (In-Context Export)
- **Vấn đề cũ**: Tab Export nằm riêng biệt làm đứt gãy luồng làm việc của nhà nghiên cứu; người dùng phải chuyển tab mới tải được kết quả.
- **Giải pháp thực hiện**:
  - **Xóa bỏ hoàn toàn tab Export độc lập** khỏi hệ thống điều hướng.
  - Xây dựng module tiện ích [`exportUtils.js`](frontend/src/utils/exportUtils.js) hỗ trợ xuất dữ liệu tức thì ở phía Client:
    - `downloadClientBibTeX`: Xuất mã trích dẫn `.bib` chuẩn LaTeX/Overleaf.
    - `downloadClientCSV`: Xuất bảng ma trận bài báo `.csv` mở bằng Excel.
    - `downloadClientMarkdown`: Xuất báo cáo tổng quan `.md`.
    - `downloadClientJSON`: Xuất toàn bộ dữ liệu cấu trúc `.json`.
    - `downloadSetupFrameworkMarkdown`: Xuất khung PICO & tiêu chí PRISMA `.md`.
  - **Tích hợp vị trí xuất dữ liệu theo ngữ cảnh**:
    - **Tại Tab Setup**: Nút `📥 Xuất Khung Đề tài (.md)` tại Bước 3 (PICO & Từ khóa).
    - **Tại Tab Search**: Menu Dropdown `📥 Xuất Dữ liệu` (BibTeX, CSV, Markdown, JSON) ngay trên thanh tác vụ nổi kèm nút CTA `Đưa vào Tổng quan`.
    - **Tại Tab Synthesis**: Thanh công cụ xuất báo cáo trực tiếp với các nút `Sao chép APA`, `Tải .md`, `Tải .bib`, `Xuất CSV`, `Xuất JSON`.
    - **Tại Header Dropdown**: Nút `📥 Xuất Gói Đề tài (.json)` tải về toàn bộ dữ liệu đề tài (PICO, danh sách bài báo, lịch sử chat).

---

### 5. Tái cấu trúc Hệ thống Điều hướng 5 Tab Phẳng (5 Flat Tabs Architecture)
- **Vấn đề cũ**: Tab "Analysis" chứa 3 subtab con lồng nhau (*Chat with sources, Literature review, Data Analysis*) gây khó tìm kiếm và tốn diện tích giao diện.
- **Giải pháp thực hiện**:
  - Đưa cả 3 phân hệ lên Header chính thành **5 Tab Độc lập, Liền mạch**:
    1. ⚙️ **Khung đề tài** (*Setup*)
    2. 🔍 **Tìm kiếm** (*Search*)
    3. 💬 **Chat với nguồn** (*Chat with Sources*)
    4. 📄 **Tổng quan tài liệu** (*Literature Review / Synthesis*)
    5. 📊 **Phân tích dữ liệu** (*Data Analysis*)
  - Cập nhật [`App.jsx`](frontend/src/App.jsx) và [`HorizontalNavbar.jsx`](frontend/src/components/navigation/HorizontalNavbar.jsx) để chuyển tab trực tiếp mà không cần backend thay đổi cấu trúc dữ liệu.

---

### 6. Xóa bỏ Subtab Trùng Lặp trong Không gian làm việc (Workspace Cleanup)
- **Vấn đề cũ**: Sau khi đưa 3 tab lên Header, bên trong khung làm việc của `WorkspaceTab.jsx` vẫn còn một thanh 3 nút con tương ứng làm lặp lại giao diện.
- **Giải pháp thực hiện**:
  - Gỡ bỏ thanh 3 nút pill bên trong `WorkspaceTab.jsx`.
  - Thay thế bằng thanh tiêu đề ngữ cảnh thông minh hiển thị rõ trạng thái:
    - Chế độ Chat: Tiêu đề `Chat & Hỏi đáp Tài liệu` + badge nguồn + nút `🗑️ Xóa Lịch sử`.
    - Chế độ Synthesis: Tiêu đề `Tổng quan Tài liệu Học thuật (SLR)` + Evidence AI Engine.
    - Chế độ Data: Tiêu đề `Phân tích Dữ liệu & Ma trận Bằng chứng` + badge Dataset.

---

### 7. Thiết Kế Hệ Thống Onboarding Tour 6 Bước Tương Tác (Interactive Tour)
- **Giải pháp thực hiện**:
  - Nâng cấp component [`OnboardingTour.jsx`](frontend/src/components/onboarding/OnboardingTour.jsx) với hiệu ứng Spotlight SVG Cutout và viền phát sáng (Glowing Frame).
  - Lộ trình 6 bước bám sát 5 tab học thuật:
    - **Bước 1 (Setup)**: Hướng dẫn thiết lập câu hỏi, tiêu chí PRISMA và phân rã PICO.
    - **Bước 2 (Search)**: Hướng dẫn tìm kiếm học thuật, đối chiếu Scopus và xem Gap Map.
    - **Bước 3 (Chat)**: Hướng dẫn hỏi đáp RAG có trích dẫn số trang PDF gốc.
    - **Bước 4 (Synthesis)**: Hướng dẫn tổng hợp báo cáo Literature Review tự động.
    - **Bước 5 (Data)**: Hướng dẫn phân tích ma trận dữ liệu và vẽ biểu đồ.
    - **Bước 6 (Project & Export)**: Hướng dẫn quản lý đề tài và xuất dữ liệu.
  - **Cơ chế kích hoạt linh hoạt**:
    - Tự động mở khi người dùng mới đăng nhập lần đầu.
    - Tự động mở khi tạo xong một đề tài mới và mở đề tài đó.
    - Nút **`[ ✨ Hướng dẫn sử dụng (Tour) ]`** được đặt trong menu người dùng (ngay phía trên nút Đăng xuất) để xem lại bất cứ lúc nào.

---

### 8. Đồng bộ Hóa Nhận diện Thương hiệu (Origami Brand Logo & Favicon Bundle)
- Tạo component chuẩn [`BrandLogo.jsx`](frontend/src/components/common/BrandLogo.jsx) hỗ trợ các kích cỡ từ `xs` đến `2xl`, dark mode, hiệu ứng hover xoay nhẹ và back-glow.
- Thay thế toàn bộ biểu tượng logo chữ "LR" tạm thời bằng logo Origami xanh ngọc chính thức trên toàn hệ thống (Navbar, Sidebar, Landing Page, Dashboard, Auth Modal).
- Cung cấp trọn bộ Favicon trong `frontend/public/` (`favicon.ico`, `favicon.svg`, `favicon-16.png`, `favicon-32.png`, `favicon-64.png`, `favicon-128.png`, `apple-touch-icon.png`).

---

### 9. Dọn dẹp Tài nguyên Thừa trong Thư mục `src/assets`
- Đã xóa bỏ 13 file asset/logo nháp không còn dùng đến:
  `AI.png`, `favicon.png`, `hero.png`, `logo-icon.svg`, `logo-vertical.svg`, `logo.png`, `logo_full.svg`, `logo_raw.jpg`, `logo_raw_user.svg`, `user_exact_logo.svg`, `user_svg_latest.svg`, `react.svg`, `vite.svg`.
- Giữ lại các file chuẩn: `logo.svg`, `member1.jpeg`, `member2.jpg`, `member3.JPG`, `member4.jpg`.

---

## III. BẢNG CHI TIẾT TẤT CẢ CÁC FILE ĐÃ ĐƯỢC CHỈNH SỬA / THÊM MỚI / XÓA

Tổng cộng có **40 files** thay đổi (2.910 dòng thêm mới, 1.967 dòng chỉnh sửa/xóa):

| STT | Đường dẫn File | Trạng thái | Nội dung Thay đổi Cụ thể |
| :---: | :--- | :---: | :--- |
| **1** | `frontend/src/components/navigation/HorizontalNavbar.jsx` | **Chỉnh sửa** | Nâng cấp 5 flat tabs; tích hợp Project Switcher Hub; thêm nút Export gói đề tài; thêm nút Tour trong menu tài khoản. |
| **2** | `frontend/src/components/workspace/WorkspaceTab.jsx` | **Chỉnh sửa** | Nhận `activeTab` từ Header; gỡ bỏ thanh 3-pill subtab bị lặp; bổ sung tiêu đề ngữ cảnh và gán ID cho Tour. |
| **3** | `frontend/src/components/workspace/SynthesisPanel.jsx` | **Chỉnh sửa** | Thêm tính năng xuất JSON; hoàn thiện bộ nút xuất Markdown, BibTeX, CSV và sao chép APA. |
| **4** | `frontend/src/components/search/SearchTab.jsx` | **Chỉnh sửa** | Tích hợp dock menu xuất BibTeX/CSV/MD/JSON; cập nhật nút CTA `Đưa vào Tổng quan`; thêm ID target cho Tour. |
| **5** | `frontend/src/components/setup/ResearchSetupTab.jsx` | **Chỉnh sửa** | Mở rộng layout responsive (Full-Width); thêm nút `Xuất Khung Đề tài (.md)`; thêm ID stepper cho Tour. |
| **6** | `frontend/src/components/onboarding/OnboardingTour.jsx` | **Chỉnh sửa** | Viết lại lộ trình 6 bước bám sát 5 tab và Project Hub; tối ưu SVG Spotlight Mask và điều khiển bàn phím. |
| **7** | `frontend/src/components/projects/NewProjectModal.jsx` | **Chỉnh sửa** | Sửa lỗi 2 dấu cộng `++`; thêm 6 chủ đề gợi ý nhanh; kích hoạt Tour khi tạo xong đề tài. |
| **8** | `frontend/src/components/dashboard/PersonalizedDashboard.jsx` | **Chỉnh sửa** | Cập nhật nhận diện thương hiệu `BrandLogo`; tối ưu responsive; thêm nút xem Tour trong menu tài khoản. |
| **9** | `frontend/src/components/landing/PublicLandingPage.jsx` | **Chỉnh sửa** | Cập nhật logo Origami thống nhất trên Header, Hero và Footer của trang giới thiệu. |
| **10** | `frontend/src/components/auth/AuthModal.jsx` | **Chỉnh sửa** | Tích hợp `BrandLogo` chuẩn vào modal đăng nhập/đăng ký. |
| **11** | `frontend/src/components/common/BrandLogo.jsx` | **Tạo mới** | Component hiển thị Logo Origami chuẩn hóa cho toàn bộ dự án. |
| **12** | `frontend/src/utils/exportUtils.js` | **Chỉnh sửa** | Bổ sung đầy đủ các hàm xuất dữ liệu Client-side: BibTeX, CSV, Markdown, JSON, Framework Setup. |
| **13** | `frontend/src/App.jsx` | **Chỉnh sửa** | Quản lý điều hướng 5 tab phẳng; quản lý state `isTourOpen`; liên kết sự kiện kích hoạt Tour tự động. |
| **14** | `frontend/src/index.css` | **Chỉnh sửa** | Bổ sung class `.logo-origami` và hiệu ứng tương tác hover back-glow. |
| **15** | `frontend/src/locales/vi.json` | **Chỉnh sửa** | Thêm & cập nhật toàn bộ từ khóa bản dịch tiếng Việt cho Tour 6 bước, Export và 5 tab. |
| **16** | `frontend/src/locales/en.json` | **Chỉnh sửa** | Thêm & cập nhật toàn bộ từ khóa bản dịch tiếng Anh cho Tour 6 bước, Export và 5 tab. |
| **17** | `frontend/src/components/Navbar.jsx` | **Chỉnh sửa** | Cập nhật logo và menu tài khoản. |
| **18** | `frontend/src/components/Sidebar.jsx` | **Chỉnh sửa** | Cập nhật logo Origami và điều hướng đồng bộ. |
| **19** | `frontend/src/contexts/AuthContext.jsx` | **Chỉnh sửa** | Tinh gọn xử lý đăng xuất và phiên đăng nhập. |
| **20** | `frontend/index.html` | **Chỉnh sửa** | Cập nhật thẻ `<title>` và liên kết trọn bộ icon/favicon mới. |
| **21** | `frontend/src/assets/logo.svg` | **Tạo mới** | File SVG vector chính thức của Logo Origami thương hiệu. |
| **22**-**26** | `frontend/src/assets/` (`AI.png`, `hero.png`, `react.svg`, `vite.svg`, ...) | **Đã xóa** | Dọn dẹp 13 file logo và asset mẫu không sử dụng. |
| **27**-**40** | `frontend/public/` (`favicon.*`, `logo.*`, `apple-touch-icon.png`, ...) | **Tạo mới / Cập nhật** | Trọn bộ biểu tượng ứng dụng và favicon phục vụ trình duyệt web. |

---

## IV. KẾT QUẢ KIỂM THỬ VÀ ĐẢM BẢO TƯƠNG THÍCH

- **Kiểm thử Biên dịch (Build Test)**: Chạy lệnh `npm run build` thành công trong **1.54 giây**, tạo ra gói phân phối production với **0 lỗi, 0 cảnh báo cú pháp**.
- **Tính toàn vẹn Logic Backend**: Toàn bộ API endpoints (`/search`, `/synthesis`, `/chat`, `/projects`, `/analyze`, `/auth`) được giữ nguyên 100%, không bị ảnh hưởng bởi việc tái cấu trúc giao diện.
- **Quản lý Mã nguồn Git**: Mã nguồn đã được commit an toàn với commit `feat: update ui ux` và đẩy lên nhánh `nvhung-fix-test` trên GitHub.
