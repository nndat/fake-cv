# Fake CV Generator

Ứng dụng tạo CV tự động sử dụng Flask và Gemini AI. Ứng dụng cho phép người dùng nhập thông tin cơ bản và sử dụng AI để tạo một CV chuyên nghiệp, sau đó có thể tải xuống dưới dạng PDF.

## Tính năng

- Tạo CV tự động với AI (Gemini)
- Hỗ trợ tiếng Việt
- Tải xuống CV dưới dạng PDF
- Giao diện thân thiện với người dùng
- Hỗ trợ chỉnh sửa CV
- Deploy trên AWS Lambda thông qua Zappa

## Yêu cầu

- Python 3.9+
- AWS Account
- Google Cloud Account (để lấy API key cho Gemini)

## Cài đặt

1. Clone repository:
```bash
git clone <repository-url>
cd fake-cv
```

2. Tạo và kích hoạt môi trường ảo:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
.\venv\Scripts\activate  # Windows
```

3. Cài đặt các dependencies:
```bash
pip install -r requirements.txt
```

4. Tạo file `.env` và thêm các biến môi trường:
```
GOOGLE_API_KEY=your_api_key_here
AI_MODEL=gemini-2.0-flash  # Có thể thay đổi model AI tại đây
```

## Cấu trúc thư mục

```
fake-cv/
├── app.py              # File chính của ứng dụng
├── requirements.txt    # Danh sách dependencies
├── zappa_settings.json # Cấu hình Zappa
├── templates/          # Thư mục chứa templates
│   ├── index.html     # Trang chủ
│   └── cv.html        # Trang hiển thị và chỉnh sửa CV
├── static/            # Thư mục chứa static files
└── fonts/            # Thư mục chứa fonts
    └── TimesNewRoman.ttf
```

## Chạy locally

1. Kích hoạt môi trường ảo:
```bash
source venv/bin/activate  # Linux/Mac
# hoặc
.\venv\Scripts\activate  # Windows
```

2. Chạy ứng dụng:
```bash
python app.py
```

3. Truy cập ứng dụng tại `http://localhost:5000`

## Deploy lên AWS

1. Cấu hình AWS credentials:
```bash
aws configure
```

2. Cập nhật `zappa_settings.json`:
```json
{
    "dev": {
        "app_function": "app.app",
        "aws_region": "ap-northeast-1",
        "profile_name": "default",
        "project_name": "fake-cv",
        "runtime": "python3.9",
        "s3_bucket": "zappa-fake-cv",
        "keep_warm": true,
        "binary_support": true,
        "use_precompiled_packages": true,
        "include": [
            "templates/*",
            "static/*",
            "fonts/*"
        ],
        "exclude": [
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".git/*",
            ".gitignore",
            ".env",
            "venv/*",
            "__pycache__/*"
        ],
        "lambda_package": "lambda_package.zip",
        "lambda_description": "Fake CV Generator",
        "lambda_timeout_seconds": 30,
        "lambda_memory_size": 512,
        "aws_environment_variables": {
            "GOOGLE_API_KEY": "your_api_key_here",
            "AI_MODEL": "gemini-2.0-flash"
        },
        "manage_roles": false,
        "role_name": "ZappaDeploymentRole"
    }
}
```

3. Deploy ứng dụng:
```bash
zappa deploy dev
```

4. Để cập nhật sau khi thay đổi code:
```bash
zappa update dev
```

5. Để xem logs:
```bash
zappa tail
```

## Cấu hình Custom Domain (tùy chọn)

1. Trong AWS Console:
   - Vào Route 53 và tạo domain mới hoặc sử dụng domain hiện có
   - Tạo A record alias trỏ đến API Gateway

2. Trong API Gateway:
   - Vào Custom Domain Names
   - Tạo custom domain mới
   - Cấu hình SSL certificate (có thể dùng ACM)
   - Map domain với API và stage

3. Cập nhật `zappa_settings.json`:
```json
{
    "dev": {
        ...
        "domain": "your-domain.com",
        "base_path": "",
        "certificate_arn": "arn:aws:acm:region:account:certificate/xxx"
    }
}
```

4. Deploy lại:
```bash
zappa update dev
```

## Xử lý sự cố

1. Lỗi 403 khi download PDF:
   - Kiểm tra API Gateway configuration
   - Đảm bảo binary support được bật
   - Kiểm tra CORS settings

2. Lỗi font:
   - Kiểm tra font file trong thư mục `fonts/`
   - Đảm bảo font được include trong `zappa_settings.json`

3. Lỗi API key:
   - Kiểm tra `GOOGLE_API_KEY` trong environment variables
   - Đảm bảo API key có quyền truy cập Gemini API

## Đóng góp

Mọi đóng góp đều được hoan nghênh! Vui lòng tạo issue hoặc pull request.
