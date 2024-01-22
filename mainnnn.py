from flask import Flask, render_template,request
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from werkzeug.utils import secure_filename
import os
from wtforms.validators import InputRequired
from flask_wtf.file import MultipleFileField
import docx2txt
import fitz  
import openai
from dotenv import load_dotenv, find_dotenv
import nltk
import re
nltk.download('punkt')
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/files'


tags=[]
pdf_only=[]
docx_only=[]
bin=[]
all_data=[]
skills_all=[]
skills_list = [
    "Python", "Java", "C++", "JavaScript", "HTML", "CSS", "React", "Angular", "Vue.js",
    "Node.js", "Express.js", "Django", "Flask", "Ruby", "Ruby on Rails", "PHP", "ASP.NET",
    "SQL", "MongoDB", "Firebase", "RESTful APIs", "GraphQL", "Git", "GitHub", "Docker",
    "Kubernetes", "AWS", "Azure", "Google Cloud", "Heroku", "Linux", "Unix", "Shell scripting",
    "Machine Learning", "Deep Learning", "Natural Language Processing", "Computer Vision",
    "Data Science", "Big Data", "Hadoop", "Spark", "TensorFlow", "PyTorch", "Scikit-Learn",
    "Pandas", "NumPy", "Matplotlib", "Seaborn", "Tableau", "Power BI", "Excel", "Data Analysis",
    "Database Management", "MySQL", "PostgreSQL", "SQLite", "Oracle", "NoSQL", "Web Development",
    "Front-end Development", "Back-end Development", "Full-stack Development",
    "Responsive Design", "UI/UX Design", "Agile", "Scrum", "Kanban", "Jira", "Confluence",
    "CI/CD", "Jenkins", "Travis CI", "Testing", "JUnit", "Selenium", "API Testing", "RESTAssured",
    "Cybersecurity", "Network Security", "Penetration Testing", "OWASP", "Encryption",
    "Blockchain", "Smart Contracts", "IoT", "AR/VR", "Mobile App Development", "Android", "iOS",
    "React Native", "Flutter", "Unity", "Game Development", "UI Automation", "Chatbots",
    "Microservices", "Serverless", "DevOps", "Monitoring", "Logging", "Scripting",
    "Technical Writing", "Documentation", "Problem Solving", "Critical Thinking", "Communication",
    "Teamwork", "Leadership", "Project Management", "Agile Project Management","DSA","Data Structures and Algorithms"
]
def extract_skills(resume_text, skills_list):
    # Tokenize the resume text into sentences
    sentences = nltk.sent_tokenize(resume_text)
    
    # Initialize an empty list to store extracted skills
    extracted_skills = []
    
    # Iterate through each sentence
    for sentence in sentences:
        # Tokenize the sentence into words
        words = nltk.word_tokenize(sentence)
        
        # Use regular expression to match skills
        matched_skills = [skill for skill in skills_list if re.search(r'\b{}\b'.format(re.escape(skill)), ' '.join(words), re.IGNORECASE)]
        
        # Add matched skills to the result list
        extracted_skills.extend(matched_skills)
    
    return extracted_skills



def get_skill(allsk):
    for i in allsk:
        j=extract_skills(i,skills_list)
        skills_all.append(j)
    print( skills_all)
def store_tags(all_tags):
    tags.extend(all_tags)
    print(tags)
def createprompt(tags):
    s='('
    for i in tags:
        s+=tags+','
    s+=")"

_ = load_dotenv(find_dotenv())
openai.api_key  = os.getenv('OPENAI_API_KEY')
#openai.api_key  ="{sk-6tn6xu49FvUxfTbGLHu9T3BlbkFJ3qp29cxgBHFagjBvjzgzR}"

def get_completion(prompt, model="gpt-3.5-turbo"):
    messages = [{"role": "user", "content": prompt}]
    response = openai.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0, # this is the degree of randomness of the model's output
    )
    return response.choices[0].message.content

def openchat(all_data,tags):
    prompt = f"""
    iterate the list and tell me the name of candidate whoes resume is the best match for the given skills: {tags}
    ```{all_data}```
    """
    response = get_completion(prompt)
    print(response)




def extract_text_from_docx(docx_path):
    txt = docx2txt.process(docx_path)
    if txt:
        return txt.replace('\t', ' ')
    return None

def extract_text_from_pdf(pdf_path):
    text=''
    pdf_document = fitz.open(pdf_path)
    for page_number in range(pdf_document.page_count):
        page = pdf_document[page_number]
        text = page.get_text()
        # Print or process the extracted text
        return(f"{text}")
    pdf_document.close()
    

def pdf_content(allpdf):
    #print(allpdf)
    for i in allpdf:
       demotxt= extract_text_from_pdf(i)
       all_data.append(demotxt)
    #print(all_data)
def doc_content(alldoc):
    for i in alldoc:
        demotxt= extract_text_from_docx(i)
        all_data.append(demotxt)
    #print(all_data)
    
def count_tokens(paragraph):
    # Split the paragraph into words
    words = paragraph.split()

    # Count the number of words
    num_tokens = len(words)

    return num_tokens
       

    
def seperate(allfile):
    for i in allfile:
        
        if i[-3:]=='ocx':
            docx_only.append('static/files/'+i)
        elif i[-3:]=='pdf':
            pdf_only.append('static/files/'+i)
        else:
            bin.append(i)
    pdf_content(pdf_only)
    doc_content(docx_only)
    #print(all_data)
    #get_skill(all_data)
    openchat(all_data,tags)
    
    
FOLDER_PATH = r'C:\Users\ASUS\Desktop\New folder (2)\static\files'

all_files=[]
def list_files(directory):
    filenames = os.listdir(directory)
    for filename in filenames:
        all_files.append(filename)
   # print(all_files)
    seperate(all_files)


class UploadFileForm(FlaskForm):
    files = MultipleFileField("Files", validators=[InputRequired()])
    submit = SubmitField("Upload Files")

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
# def home():
#     form = UploadFileForm()
#     if form.validate_on_submit():
#         files = form.files.data
#         for file in files:
#             file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
#         print("Files have been uploaded.")
#     list_files(FOLDER_PATH)
#     return render_template('index.html', form=form)
def home():
    form = UploadFileForm()
    if form.validate_on_submit():
        files = form.files.data
        for file in files:
            file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
        
        tags = request.form['tags']
        tag_list = [tag.strip() for tag in tags.split('\n') if tag.strip()]
        
        store_tags(tag_list)
        
        print("Files have been uploaded.")
    list_files(FOLDER_PATH)
    return render_template('index.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)
