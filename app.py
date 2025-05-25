import os
from dotenv import load_dotenv
import json
import re
import logging

from flask import Flask, render_template, request, jsonify, send_file
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
import google.generativeai as genai
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListItem, ListFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile


logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load biến môi trường từ file .env
load_dotenv()

# Khởi tạo Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Cấu hình Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
AI_MODEL = os.getenv('AI_MODEL', 'gemini-2.0-flash')  # Sử dụng giá trị mặc định nếu không có trong .env

if not GOOGLE_API_KEY:
    raise ValueError("Không tìm thấy GOOGLE_API_KEY trong biến môi trường")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(AI_MODEL)

# Đăng ký font Times New Roman
pdfmetrics.registerFont(TTFont('TimesNewRoman', 'fonts/TimesNewRoman.ttf'))

# Tạo styles với font Unicode
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name='CustomTitle',
    parent=styles['Heading1'],
    fontName='TimesNewRoman',
    fontSize=24,
    spaceAfter=30,
    encoding='utf-8',
    leading=30
))
styles.add(ParagraphStyle(
    name='CustomHeading',
    parent=styles['Heading2'],
    fontName='TimesNewRoman',
    fontSize=18,
    spaceAfter=12,
    encoding='utf-8',
    leading=22
))
styles.add(ParagraphStyle(
    name='CustomNormal',
    parent=styles['Normal'],
    fontName='TimesNewRoman',
    fontSize=12,
    spaceAfter=6,
    encoding='utf-8',
    leading=14
))

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
        # Tạo PDF với ReportLab
        doc = SimpleDocTemplate(
            tmp.name,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Tạo nội dung
        story = []
        
        # Thông tin cá nhân
        story.append(Paragraph("Thông tin cá nhân", styles['CustomTitle']))
        story.append(Paragraph(f"<b>Họ và tên:</b> {personal_info['name']}", styles['CustomNormal']))
        story.append(Paragraph("<b>Họ tên:</b>", styles['CustomNormal']))
        story.append(Paragraph(f"<b>Email:</b> {personal_info['email']}", styles['CustomNormal']))
        story.append(Paragraph(f"<b>Số điện thoại:</b> {personal_info['phone']}", styles['CustomNormal']))
        story.append(Paragraph(f"<b>Mô tả bản thân:</b>", styles['CustomNormal']))
        story.append(Paragraph(personal_info['summary'], styles['CustomNormal']))
        story.append(Spacer(1, 20))
        
        # Học vấn
        story.append(Paragraph("Học vấn", styles['CustomHeading']))
        for edu in education:
            story.append(Paragraph(f"<b>{edu['degree']}</b>", styles['CustomNormal']))
            story.append(Paragraph(f"{edu['school']} - {edu['year']}", styles['CustomNormal']))
            story.append(Paragraph(edu['description'], styles['CustomNormal']))
            story.append(Spacer(1, 12))
        
        # Kinh nghiệm
        story.append(Paragraph("Kinh nghiệm", styles['CustomHeading']))
        for exp in experience:
            story.append(Paragraph(f"<b>{exp['position']}</b>", styles['CustomNormal']))
            story.append(Paragraph(f"{exp['company']} - {exp['period']}", styles['CustomNormal']))
            story.append(Paragraph(exp['description'], styles['CustomNormal']))
            story.append(Spacer(1, 12))
        
        # Kỹ năng
        story.append(Paragraph("Kỹ năng", styles['CustomHeading']))
        for skill in skills:
            story.append(Paragraph(f"<b>{skill['category']}</b>", styles['CustomNormal']))
            items = [ListItem(Paragraph(item, styles['CustomNormal'])) for item in skill['items']]
            story.append(ListFlowable(items, bulletType='bullet'))
            story.append(Spacer(1, 12))
        
        # Tạo PDF
        doc.build(story)
        
        return send_file(
            tmp.name,
            as_attachment=True,
            download_name='cv.pdf',
            mimetype='application/pdf'
        )

if __name__ == '__main__':
    app.run()
