# CV Evaluator AI

Hệ thống đánh giá CV tự động sử dụng AI với Vintern OCR và LangGraph workflow.

## Tính năng chính

- 🤖 **OCR tự động**: Sử dụng Vintern API để trích xuất thông tin từ CV (PDF/ảnh)
- 🧠 **Đánh giá AI**: Sử dụng GPT-3.5-turbo để đánh giá độ phù hợp với JD
- 📊 **Workflow tự động**: LangGraph quản lý luồng xử lý từ upload đến kết quả
- 💾 **Lưu trữ lịch sử**: SQLite database lưu trữ sessions và kết quả
- 🌐 **Giao diện web**: Streamlit app thân thiện và dễ sử dụng
- 📈 **Báo cáo chi tiết**: Thống kê và phân tích kết quả đánh giá

## Cài đặt

### 1. Clone repository

```bash
git clone https://github.com/nguyentuongbachhy/ResumAI.git
cd cv-evaluator-ai
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 3. Cấu hình môi trường

Tạo file `.env` và cấu hình các biến môi trường:

```env
# API Keys
OPENAI_API_KEY=your_openai_api_key_here

# Vintern API URL (optional, defaults to provided URL)
VINTERN_API_URL=https://8000-01jzb2dp011mzm092e3nns9k0m.cloudspaces.litng.ai

# App Settings
CV_UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
TEMP_DIR=./temp

# Scoring Settings
MIN_SCORE=0
MAX_SCORE=10
```

### 4. Kiểm tra kết nối API

Đảm bảo Vintern API đang chạy và có thể truy cập được:

```bash
curl https://8000-01jzb2dp011mzm092e3nns9k0m.cloudspaces.litng.ai/health
```

## Sử dụng

### Chạy ứng dụng

```bash
streamlit run app.py
```

### Workflow sử dụng

1. **Tạo Session mới**

   - Click "➕ Tạo Session mới" trong sidebar
   - Nhập Job Description (JD)
   - Đặt số lượng ứng viên cần tuyển

2. **Upload CV**

   - Chọn nhiều file CV (PDF hoặc ảnh)
   - Hệ thống sẽ validate và hiển thị thông tin file

3. **Đánh giá tự động**

   - Click "🚀 Bắt đầu đánh giá"
   - Theo dõi tiến trình xử lý
   - Xem kết quả chi tiết

4. **Xem kết quả**

   - Danh sách ứng viên xuất sắc
   - Điểm số và phân tích chi tiết
   - Thống kê tổng quan

5. **Quản lý Session**
   - Xem lịch sử các sessions
   - Quay lại kết quả cũ
   - Tạo session mới

## Cấu trúc thư mục

```
├── app.py                 # Streamlit app chính
├── vintern_api.py         # Vintern API client
├── workflow.py           # LangGraph workflow
├── database.py           # SQLite database manager
├── utils.py              # Utility functions
├── requirements.txt      # Dependencies
├── .env                  # Environment variables
├── uploads/              # Thư mục upload CV
├── outputs/              # Thư mục output
└── temp/                 # Thư mục tạm
```

## Workflow chi tiết

### 1. Process Files

- Chuyển đổi PDF thành ảnh
- Validate file types
- Lưu vào database

### 2. Extract CV Info

- Sử dụng Vintern OCR
- Trích xuất thông tin chi tiết
- Lưu kết quả vào database

### 3. Evaluate CVs

- Gọi GPT-3.5-turbo API
- So sánh với Job Description
- Tính điểm và đánh giá

### 4. Finalize Results

- Sắp xếp theo điểm số
- Tạo báo cáo thống kê
- Lưu kết quả cuối cùng

## API và Database

### SQLite Tables

- **sessions**: Lưu thông tin session
- **cvs**: Lưu thông tin CV và extracted data
- **evaluations**: Lưu kết quả đánh giá

### LangGraph States

- **CVEvaluationState**: Quản lý trạng thái workflow
- **Nodes**: process_files, extract_cv_info, evaluate_cvs, finalize_results

## Tùy chỉnh

### Thay đổi Vintern API URL

Chỉnh sửa trong `vintern_api.py` hoặc sử dụng environment variable:

```python
# In vintern_api.py
vintern_processor = VinternProcessor(
    api_url="your-vintern-api-url"
)

# Hoặc set environment variable
export VINTERN_API_URL="your-vintern-api-url"
```

### Tùy chỉnh prompt đánh giá

Chỉnh sửa prompt trong `workflow.py`, method `_evaluate_cvs()`.

### Thêm tính năng mới

- Extend database schema
- Add new workflow nodes
- Update Streamlit interface

## Lưu ý

- Cần kết nối internet để sử dụng Vintern API
- Cần OpenAI API key để đánh giá
- File PDF lớn có thể mất thời gian xử lý
- Kết quả đánh giá phụ thuộc vào chất lượng JD
- Vintern API cần đang chạy và có thể truy cập được

## Troubleshooting

### Lỗi "No image file provided"

```bash
# Kiểm tra file format và content type
python test_api.py

# Debug file upload
python debug_quick.py
```

### Lỗi OpenAI API "no longer supported"

```bash
# Cập nhật OpenAI package
pip install openai>=1.0.0

# Kiểm tra API key
python test_connection.py
```

### Lỗi kết nối Vintern API

```bash
# Kiểm tra API health
curl https://8000-01jzb2dp011mzm092e3nns9k0m.cloudspaces.litng.ai/health

# Kiểm tra network connectivity
ping 8000-01jzb2dp011mzm092e3nns9k0m.cloudspaces.litng.ai
```

### Lỗi batch processing

- Batch processing có thể fail với một số format file
- Hệ thống sẽ tự động fallback sang individual processing
- Kiểm tra logs để xem chi tiết lỗi

### Lỗi database

```bash
# Xóa và tạo lại database
rm cv_evaluator.db
python -c "from database import db_manager; print('Database recreated')"
```

### Enable debug logging

Uncomment các dòng này trong `app.py`:

```python
logging.getLogger("vintern_api").setLevel(logging.DEBUG)
logging.getLogger("workflow").setLevel(logging.DEBUG)
```

## Đóng góp

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

MIT License - xem file LICENSE để biết chi tiết.
