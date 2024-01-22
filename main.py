from flask import Flask, render_template, request, send_from_directory, jsonify, g, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, TextAreaField
from werkzeug.utils import secure_filename
import os
from wtforms.validators import InputRequired
from flask_wtf.file import MultipleFileField
import docx2txt
import fitz
#import openai
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
import re
import ssl
import smtplib
from email.message import EmailMessage
import sqlite3
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/files'

_ = load_dotenv(find_dotenv())
api_key=os.getenv('OPENAI_API_KEY')
#openai.api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    
)
DATABASE = 'resume_database.db'

conn = sqlite3.connect('resume_database.db')
cursor = conn.cursor()


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                summary TEXT
            )
        ''')
        db.commit()


init_db()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        summary TEXT
    )
''')

entered_tags = []

def get_completion(prompt, model="gpt-3.5-turbo"):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def summer(data):
    prompt = f"""
    f"Extract a list of technical skills, any programming languages, software, or tools, education, location, year of experience (if not mentioned then 0),
    candidate's work experience, including key responsibilities and achievements,
    any certifications or specialized training mentioned,
    any additional insights or relevant information,
    and list them with commas within 100 words:{data}
    provide output in format: all_extracted:[all extracted skills, experience, responsibility, programming languages, software, or tools,
    work experience, certifications or specialized training, year of experience]"
    """
    response = get_completion(prompt)
    return response


@app.route('/process_text', methods=['POST'])
def process_text():
    global entered_tags

    entered_text = request.form.get('input_text', '')

    tags = [tag.strip() for tag in entered_text.split('\n') if tag.strip()]

    print("Entered Tags:", tags)

    entered_tags.extend(tags)
    print("Entered Tags List:", entered_tags)

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT filename, summary FROM resumes')
    resume_data = cursor.fetchall()
    print("res__-data")
    
    
    data_map = {}

    for key, value in resume_data:
        try:
        # Try to evaluate the value as a list
            data_map[key] = eval(value)
        except SyntaxError:
        # If evaluation fails, it means the value is in a different format
        # You may need to handle this case based on your specific requirements
            data_map[key] = value
    
    file_names, ranks, matched_tags = openchat(data_map, entered_tags)
    sorted_resumes = sorted(zip(file_names, ranks, matched_tags), key=lambda x: float(x[1].rstrip('%')), reverse=True)

    sorted_filenames, sorted_ranks, sorted_matched_tags = zip(*sorted_resumes)

    return render_template('resumes.html', filenames_list=sorted_filenames, rankings_list=sorted_ranks,
                           matched_tags=sorted_matched_tags)


@app.route('/find_resume', methods=['GET'])
def find_resume():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT filename, summary FROM resumes')
    all_resumes = cursor.fetchall()

    candidate_names = [row[0] for row in all_resumes]
    resumes = [row[1] for row in all_resumes]

    return render_template('resumes.html', resumes=resumes, candidate_names=candidate_names)


@app.route('/view_resume/<filename>', methods=['GET'])
def view_resume(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


def openchat(data_list, tags):
    tags_lower = [tag.lower() for tag in tags]
    
    matched_filenames = []
    matched_tags = []
    matched_percent = []
    output_dict = {}

    for key, value in data_list.items():
        if isinstance(value, list):
            output_dict[key] = value
        else:
            content = value.strip('[]')
            elements = [elem.strip() for elem in content.split(',')]
            elem1=[elem.strip() for elem in elements.split(',')]
            output_dict[key] = elem1
    for key, value in output_dict.items():
    # Check if the last element is a digit
        if isinstance(value, str) and value[-1].isdigit():
        # If yes, convert it to the desired format
            value[-1] = f'<{value[-1]}'
            output_dict[key] = value
    print("openchat------------")
    print(output_dict)
    print("openchat------------")
    for filename, skills_list in output_dict.items():
        skills_list_lower = [skill.lower() if isinstance(skill, str) else str(skill).lower() for skill in skills_list]

        print("skkkkkkkkkk")
        print(skills_list_lower)
        for i in skills_list_lower:
            if i in tags_lower:
                print(i)
        common_tags = [tag for tag in tags_lower if any(skill.startswith(tag) or tag in skill for skill in skills_list_lower)]

        total_tags_count = len(skills_list_lower)
        if total_tags_count > 0:
            match_percentage = (len(common_tags) / len(tags)) * 100
        else:
            match_percentage = 0

        matched_filenames.append(filename)
        matched_tags.append(common_tags)
        matched_percent.append(str(int(match_percentage)) + "%")
    print(matched_filenames)
    print(matched_tags)
    print(matched_percent)
    return matched_filenames, matched_percent, matched_tags

class UploadFileForm(FlaskForm):
    file = FileField("File", validators=[InputRequired()])
    tags = TextAreaField("Tags (separate with Enter/Return)")
    submit = SubmitField("Upload File")


rec_mail = ""


def extract_mail(text):
    global rec_mail
    mail = re.findall(r'\S+@\S+', text)
    rec_mail += ','.join(mail)


tags = []


def store_tags(all_tags):
    tags.extend(all_tags)
    print(tags)


chunk_size = 3500


def split_into_chunks(paragraph, chunk_size):
    chunks = [paragraph[i:i + chunk_size] for i in range(0, len(paragraph), chunk_size)]
    return chunks


def extract_text_from_docx(docx_path):
    txt = docx2txt.process(docx_path)
    extract_mail(txt)
    if txt:
        return txt.replace('\t', ' ')
    return None


def extract_text_from_pdf(pdf_path):
    pdf_document = fitz.open(pdf_path)
    temp = " "
    for page_number in range(pdf_document.page_count):
        page = pdf_document[page_number]
        text = page.get_text()
        temp += text

    pdf_document.close()
    extract_mail(temp)
    return temp


def replace_last_element(lst):
    if lst:
        last_element = lst[-1]
        try:
            last_element_value = int(last_element)
            lst[-1] = f"<{last_element_value}"
        except ValueError:
            pass
    return lst


cmd = ""


def command_(txtt, filename):
    if len(txtt) == 1:
        summ = summer(txtt[0])
        if "all_extracted:" in summ:
            output_string = summ.split("all_extracted:")[1].strip()

        output_string = replace_last_element(output_string)
        print(output_string)
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO resumes (filename, summary) VALUES (?, ?)', (filename, output_string))
        db.commit()
    else:
        tmp = txtt[0]
        tmp1 = txtt[1]
        tx1 = summer(tmp)
        if "all_extracted:" in tx1:
            os1 = tx1.split("all_extracted:")[1].strip()
        tx2 = summer(tmp1)
        if "all_extracted:" in tx2:
            os2 = tx2.split("all_extracted:")[1].strip()
        summ = os1[:-1] + "," + os2[1:]
        summ = replace_last_element(summ)
        print(summ)
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO resumes (filename, summary) VALUES (?, ?)', (filename, summ))
        db.commit()


@app.route('/process_tags', methods=['POST'])
def process_tags():
    tags_input = request.form.get('tags', '')
    tags = [tag.strip() for tag in tags_input.split('\n') if tag.strip()]

    print("Entered tags:", tags)

    return redirect(url_for('find_resume'))


@app.route('/', methods=['GET', 'POST'])
def home():
    form = UploadFileForm()
    result = None
    filename = None
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        flash('File uploaded successfully!', 'success')
        token_chunks = []
        if filename[-4:] == 'docx':
            ttxxtt = extract_text_from_docx(file_path)
            token_chunks = split_into_chunks(ttxxtt, chunk_size)
        elif filename[-3:] == 'pdf':
            ttxxtt = extract_text_from_pdf(file_path)
            token_chunks = split_into_chunks(ttxxtt, chunk_size)
        result = command_(token_chunks, filename)
        print("File has been uploaded.")
    return render_template('index.html', form=form, result=result, filename=filename)


@app.route('/interview_form')
def interview_form():
    return render_template('interview_form.html')



@app.route('/reject', methods=['GET'])
def reject():
    filepath = request.args.get('filepath')
    last_slash_index = filepath.rfind('/')
    modified_path = filepath[:last_slash_index] + '\\' + filepath[last_slash_index + 1:]
    new_path = modified_path[1:]

    filename = modified_path.split('\\')[-1]
    if filename[-4:] == 'docx':
        ttxxtt = extract_text_from_docx(new_path)    
    elif filename[-3:] == 'pdf':
        ttxxtt = extract_text_from_pdf(new_path)
    email_sender='sabyabapun20@gmail.com'
    email_password='pfci vawq uoll zmau'
    email_receiver=rec_mail
    subject='Reguarding job posting'
    body="""
    We want to express our gratitude for your interest in joining our team.
    we regret to inform you that we have chosen not to move forward with your application at this time. 
    The competition for this position was exceptionally strong, and the decision-making process was challenging. 
    Please know that this decision was not easy, and it does not diminish the value of your skills and experience.


    We appreciate your understanding and wish you every success in your future endeavors. 
    If you have any questions or would like feedback on your interview, please feel free to reach out.

    Thank you again for considering a career with Brillio

    Best regards,

    sohan sahoo
    """

    em=EmailMessage()
    em["from"]=email_sender
    em["To"]=rec_mail
    em["Subject"]=subject
    em.set_content(body)

    context=ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com',465,context=context) as smtp:
        smtp.login(email_sender,email_password)
        smtp.sendmail(email_sender,email_receiver,em.as_string())
    return jsonify({"status": "success", "message": "candidate rejected"})
    

@app.route('/accept', methods=['GET'])
def accept():
    filepath = request.args.get('filepath')
    last_slash_index = filepath.rfind('/')
    modified_path = filepath[:last_slash_index] + '\\' + filepath[last_slash_index + 1:]
    new_path = modified_path[1:]

    interview_date = request.args.get('interview_date')
    interview_time = request.args.get('interview_time')
    interview_link = request.args.get('interview_link')

    filename = modified_path.split('\\')[-1]
    if filename[-4:] == 'docx':
        ttxxtt = extract_text_from_docx(new_path)    
    elif filename[-3:] == 'pdf':
        ttxxtt = extract_text_from_pdf(new_path)
        
    email_sender='sabyabapun20@gmail.com'
    email_password='pfci vawq uoll zmau'
    email_receiver=rec_mail
    subject='Reguarding job posting'
    print("mail----")
    print(rec_mail)
    body = f"""
    I hope this email finds you well. We appreciate your interest at Brillio,
    and we would like to invite you for an interview.

    Interview Date: {interview_date}
    Interview Time: {interview_time}
    Interview Link: {interview_link}

    Your qualifications and experiences have impressed us,
    and we are eager to learn more about how your skills align with the requirements of the role.

    Congratulations once again on reaching this stage,
    and we look forward to meeting you in person/over Zoom/phone to discuss your candidacy further.

    If you have any questions or need additional information, please feel free to reach out.

    Best regards,
    Brillio
    """

    em=EmailMessage()
    em["from"]=email_sender
    em["To"]=rec_mail
    em["Subject"]=subject
    em.set_content(body)

    context=ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com',465,context=context) as smtp:
        smtp.login(email_sender,email_password)
        smtp.sendmail(email_sender,email_receiver,em.as_string())
    return jsonify({"status": "success", "message": "Interview mail sent sucessfully"})
    

if __name__ == '__main__':
    app.run(debug=True)




