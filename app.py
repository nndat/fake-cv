import os
from dotenv import load_dotenv
import json
import re

# Load biến môi trường từ file .env
load_dotenv()

from flask import Flask, render_template, request, jsonify, send_file
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
import google.generativeai as genai
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import tempfile

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Cấu hình Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("Không tìm thấy GOOGLE_API_KEY trong biến môi trường")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

class CVForm(FlaskForm):
    name = StringField('Họ và tên')
    email = StringField('Email')
    phone = StringField('Số điện thoại')
    education = TextAreaField('Học vấn')
    experience = TextAreaField('Kinh nghiệm')
    skills = TextAreaField('Kỹ năng')
    submit = SubmitField('Tạo CV')

@app.route('/', methods=['GET', 'POST'])
def index():
    form = CVForm()
    if request.method == 'POST':
        # Lấy dữ liệu từ form
        form.name.data = request.form.get('name')
        form.email.data = request.form.get('email')
        form.phone.data = request.form.get('phone')
        form.education.data = request.form.get('education')
        form.experience.data = request.form.get('experience')
        form.skills.data = request.form.get('skills')

        # Tạo prompt cho Gemini
        prompt = f"""
        Dựa trên thông tin sau, tạo một CV chuyên nghiệp dưới dạng JSON với cấu trúc như sau:
        {{
            "personal_info": {{
                "name": "Họ và tên",
                "email": "Email",
                "phone": "Số điện thoại",
                "summary": "Mô tả ngắn gọn về bản thân"
            }},
            "education": [
                {{
                    "degree": "Bằng cấp",
                    "school": "Trường học",
                    "year": "Năm tốt nghiệp",
                    "description": "Mô tả chi tiết"
                }}
            ],
            "experience": [
                {{
                    "position": "Vị trí",
                    "company": "Công ty",
                    "period": "Thời gian",
                    "description": "Mô tả công việc"
                }}
            ],
            "skills": [
                {{
                    "category": "Nhóm kỹ năng",
                    "items": ["Kỹ năng 1", "Kỹ năng 2"]
                }}
            ]
        }}

        Thông tin đầu vào:
        Họ và tên: {form.name.data}
        Email: {form.email.data}
        Số điện thoại: {form.phone.data}
        Học vấn: {form.education.data}
        Kinh nghiệm: {form.experience.data}
        Kỹ năng: {form.skills.data}

        Hãy tạo một CV đầy đủ và chuyên nghiệp, bổ sung thêm các thông tin phù hợp nếu cần.
        Chỉ trả về JSON, không thêm bất kỳ text nào khác.
        """
        
        # Gọi Gemini API
        response = model.generate_content(prompt)
        try:
            # Xử lý response để loại bỏ markdown code block
            response_text = response.text
            # Tìm JSON trong response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                response_text = json_match.group(1)
            else:
                # Nếu không tìm thấy code block, thử parse trực tiếp
                response_text = response_text.strip()
            
            # Parse JSON từ response đã xử lý
            cv_data = json.loads(response_text)
            print("CV Data:", cv_data)  # Debug print
            
            # Lưu CV vào session để có thể chỉnh sửa sau
            return render_template('cv.html', cv_data=cv_data, form=form)
        except json.JSONDecodeError as e:
            print("Error parsing JSON:", e)
            print("Raw response:", response.text)
            return render_template('cv.html', error="Lỗi khi tạo CV", form=form)
    
    return render_template('index.html', form=form)

@app.route('/download', methods=['POST'])
def download_cv():
    # Lấy dữ liệu từ form
    personal_info = {
        'name': request.form.get('name', ''),
        'email': request.form.get('email', ''),
        'phone': request.form.get('phone', ''),
        'summary': request.form.get('summary', '')
    }
    
    # Xử lý dữ liệu học vấn
    education = []
    degrees = request.form.getlist('education_degree[]')
    schools = request.form.getlist('education_school[]')
    years = request.form.getlist('education_year[]')
    descriptions = request.form.getlist('education_description[]')
    
    for i in range(len(degrees)):
        if degrees[i] or schools[i] or years[i] or descriptions[i]:
            education.append({
                'degree': degrees[i],
                'school': schools[i],
                'year': years[i],
                'description': descriptions[i]
            })
    
    # Xử lý dữ liệu kinh nghiệm
    experience = []
    positions = request.form.getlist('experience_position[]')
    companies = request.form.getlist('experience_company[]')
    periods = request.form.getlist('experience_period[]')
    exp_descriptions = request.form.getlist('experience_description[]')
    
    for i in range(len(positions)):
        if positions[i] or companies[i] or periods[i] or exp_descriptions[i]:
            experience.append({
                'position': positions[i],
                'company': companies[i],
                'period': periods[i],
                'description': exp_descriptions[i]
            })
    
    # Xử lý dữ liệu kỹ năng
    skills = []
    categories = request.form.getlist('skill_category[]')
    items_list = request.form.getlist('skill_items[]')
    
    for i in range(len(categories)):
        if categories[i] or items_list[i]:
            items = [item.strip() for item in items_list[i].split(',') if item.strip()]
            skills.append({
                'category': categories[i],
                'items': items
            })
    
    # Tạo file PDF tạm thời
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        # Thêm HTML wrapper cho nội dung
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{
                    margin: 2.5cm;
                }}
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                h1, h2, h3 {{
                    color: #2c3e50;
                    margin-top: 1.5em;
                    margin-bottom: 0.5em;
                }}
                h1 {{
                    font-size: 24px;
                    border-bottom: 2px solid #2c3e50;
                    padding-bottom: 0.3em;
                }}
                h2 {{
                    font-size: 20px;
                }}
                h3 {{
                    font-size: 18px;
                }}
                p {{
                    margin: 0.5em 0;
                }}
                ul, ol {{
                    margin: 0.5em 0;
                    padding-left: 2em;
                }}
                li {{
                    margin: 0.3em 0;
                }}
                .section {{
                    margin-bottom: 1.5em;
                }}
                .item {{
                    margin-bottom: 1em;
                }}
                .item-title {{
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .item-subtitle {{
                    color: #666;
                    font-style: italic;
                }}
            </style>
        </head>
        <body>
            <h1>Thông tin cá nhân</h1>
            <div class="section">
                <p><strong>Họ và tên:</strong> {personal_info['name']}</p>
                <p><strong>Email:</strong> {personal_info['email']}</p>
                <p><strong>Số điện thoại:</strong> {personal_info['phone']}</p>
                <p><strong>Mô tả bản thân:</strong></p>
                <p>{personal_info['summary']}</p>
            </div>

            <h2>Học vấn</h2>
            <div class="section">
                {''.join(f'''
                <div class="item">
                    <p class="item-title">{edu['degree']}</p>
                    <p class="item-subtitle">{edu['school']} - {edu['year']}</p>
                    <p>{edu['description']}</p>
                </div>
                ''' for edu in education)}
            </div>

            <h2>Kinh nghiệm</h2>
            <div class="section">
                {''.join(f'''
                <div class="item">
                    <p class="item-title">{exp['position']}</p>
                    <p class="item-subtitle">{exp['company']} - {exp['period']}</p>
                    <p>{exp['description']}</p>
                </div>
                ''' for exp in experience)}
            </div>

            <h2>Kỹ năng</h2>
            <div class="section">
                {''.join(f'''
                <div class="item">
                    <p class="item-title">{skill['category']}</p>
                    <ul>
                        {''.join(f'<li>{item}</li>' for item in skill['items'])}
                    </ul>
                </div>
                ''' for skill in skills)}
            </div>
        </body>
        </html>
        """
        
        # Cấu hình font
        font_config = FontConfiguration()
        
        # Tạo PDF
        HTML(string=html_content).write_pdf(
            tmp.name,
            font_config=font_config,
            stylesheets=[],
            zoom=1
        )
        
        return send_file(
            tmp.name,
            as_attachment=True,
            download_name='cv.pdf',
            mimetype='application/pdf'
        )

if __name__ == '__main__':
    app.run(debug=True) 