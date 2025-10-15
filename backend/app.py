from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pdfplumber
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_credit_card_statement(filepath):
    extracted_data = {
        'cardIssuer': 'Unknown',
        'cardLastFour': 'Unknown',
        'statementDate': 'Unknown',
        'dueDate': 'Unknown',
        'totalAmountDue': 'Unknown',
        'cardVariant': 'Unknown'
    }
    
    try:
        with pdfplumber.open(filepath) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"
            print('This is only to debuggggggggg')
            print(full_text[:2000])  
            extracted_data = extract_data_from_text(full_text)
            
    except Exception as e:
        print(f"Error parsing PDF: {e}")
    
    return extracted_data

def extract_data_from_text(text):
    data = {
        'cardIssuer': 'Unknown',
        'cardLastFour': '**** XXXX',
        'statementDate': 'Unknown',
        'dueDate': 'Unknown',
        'totalAmountDue': 'Unknown',
        'cardVariant': 'Unknown'
    }
    
    
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    if 'ICICI' in text.upper() or 'ICICIBANK' in text.upper():
        data['cardIssuer'] = 'ICICI Bank'
        data['cardVariant'] = 'ICICI Coral'
    elif 'HDFC BANK' in text.upper():
        data['cardIssuer'] = 'HDFC Bank'
        data['cardVariant'] = 'HDFC Regalia'
    elif 'AXIS' in text.upper() or 'AXIBANK' in text.upper():
        data['cardIssuer'] = 'Axis Bank'
        data['cardVariant'] = 'Axis Ace'
    elif 'SBI' in text.upper() or 'STATE BANK' in text.upper():
        data['cardIssuer'] = 'SBI Bank'
        if 'IRCTC' in text.upper():
            data['cardVariant'] = 'IRCTC Platinum Card'
        else:
            data['cardVariant'] = 'SBI Prime Credit Card'
    elif 'KOTAK' in text.upper():
        data['cardIssuer'] = 'Kotak Bank'
        data['cardVariant'] = 'Credit Card'
    
    card_patterns = [
        r'XXXX-XXXX-XXXX-(\d{4})',
        r'\(\d{4}-\d{4}-\d{4}-(\d{4})\)',  
        r'\b\d{4}-\d{4}-\d{4}-(\d{4})\b', 
        r'\b\d{4}\s?\d{4}\s?\d{4}\s?(\d{4})\b',  
        r'Card Number[^\d]*[\*X]*(?:\d{4})?[\*\sX]*(\d{4})',
        r'Credit Card Number[^\d]*[\*X]*(?:\d{4})?[\*\sX]*(\d{4})',
        r'\b\d{16}\b', 
        r'\*{8,12}(\d{4})', 
        r'XXXX\sXXXX\sXXXX\s(\d{4})',
    ]
    
    for pattern in card_patterns:
        matches = re.findall(pattern, text)
        if matches:
            if pattern == r'\b\d{16}\b':
                data['cardLastFour'] = matches[0][-4:]
            else:
                data['cardLastFour'] = matches[0]
            break
    

    stmt_patterns = [
        r'Statement Date\s*[:\-]?\s*(\d{1,2}\s+\w+\s+\d{4})',
        r'Statement Date\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'Statement Generation Date\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'For Statement dated\s*(\d{1,2}\s+\w+\s+\d{4})'
    ]
    
    for pattern in stmt_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) > 1:
                data['statementDate'] = f"{match.group(1)} {match.group(2)}"
            else:
                data['statementDate'] = match.group(1)
            break

    due_patterns = [
        r'Due Date\s*[:\-]?\s*(\d{1,2}\s+\w+\s+\d{4})',
        r'Due Date\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'Payment Due Date\s*[:\-]?\s*(\d{1,2}\s+\w+\s+\d{4})',
        r'Payment Due Date\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'Payment Due Date\s+(\d{1,2}\s+\w+)\s+(\d{4})', 
        r'IMMEDIATE',  
    ]
    
    for pattern in due_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if pattern == r'IMMEDIATE':
                data['dueDate'] = 'Immediate'
            elif len(match.groups()) > 1:
                data['dueDate'] = f"{match.group(1)} {match.group(2)}"
            else:
                data['dueDate'] = match.group(1)
            break
    amount_patterns = [
        r'Total Amount Due\s*[:\-]?\s*[^\d]*([\d,]+\.?\d*)',
        r'Total Payment Due\s*[:\-]?\s*[^\d]*([\d,]+\.?\d*)',
        r'Total Amount Due\s*\(\$\)\s*[:\-]?\s*([\d,]+\.?\d*)',
        r'TOTAL AMOUNT DUE\s*[:\-]?\s*[^\d]*([\d,]+\.?\d*)',
        r'Total Amount Due\s+PHP\s+([\d,]+\.?\d*)', 
        r'Total Amount Due\s+₹\s*([\d,]+\.?\d*)',   
        r'Total Outstanding\s*[:\-]?\s*[^\d]*([\d,]+\.?\d*)',
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = match.group(1).replace(',', '')
            if re.match(r'^\d+\.?\d*$', amount):
                data['totalAmountDue'] = amount
                break
    
    if data['totalAmountDue'] == 'Unknown':
        
        amount_fallback = re.search(r'Total Amount Due[^\d]*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if amount_fallback:
            data['totalAmountDue'] = amount_fallback.group(1).replace(',', '')
    return data

@app.route('/parse-statement', methods=['POST'])
def parse_statement():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            result = parse_credit_card_statement(filepath)
            os.remove(filepath)
            return jsonify(result)
        else:
            return jsonify({'error': 'Invalid file type. Please upload PDF only.'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Credit Card Parser API is running'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  
    app.run(host='0.0.0.0', port=port, debug=False)