from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import os
import io
import uuid
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from werkzeug.security import generate_password_hash, check_password_hash
import PyPDF2
import docx
from docx import Document
import mammoth
import tempfile
from datetime import datetime
import sqlite3
import json
from functools import wraps
from analyzer import PDFAnalyzer, extract_text_from_pdf


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-this-in-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATABASE'] = 'documents.db'
DATABASE = 'documents.db'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
analyzer = PDFAnalyzer()

def init_db():
    """Initialiser la base de données"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # Table des utilisateurs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Table des documents
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            original_filename TEXT NOT NULL,
            pdf_file_path TEXT NOT NULL,
            extracted_text TEXT,
            file_type TEXT NOT NULL,
            file_size INTEGER,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
init_db()
def get_db():
    """Obtenir une connexion à la base de données"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    """Décorateur pour vérifier si l'utilisateur est connecté"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Connexion requise', 'redirect': '/login'}), 401
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes d'authentification
@app.route('/signup', methods=['GET', 'POST'])
def register():
    try:
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        print("Email:", email)
        print("Password:", password)

        if password != confirm_password:
            return redirect(url_for('signup'))

        # Connexion à la base de données
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Vérifier si l'email existe déjà
        cursor.execute('SELECT email FROM users WHERE email = ?', (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            return jsonify({'error': 'Cet email est déjà utilisé'}), 409
        
        # Hash du mot de passe
        # hashed_password = hash_password(password)
        
        # Insertion du nouvel utilisateur
        cursor.execute(
            'INSERT INTO users (email, password) VALUES (?, ?)',
            (email, password)
        )
        conn.commit()
        conn.close()
        
        # Création de la session
        session['email'] = email
        return render_template('upload.html', message='Inscription réussie', user_email=email)

        # return jsonify({
        #     'message': 'Inscription réussie',
        #     'user': {
        #         'email': email
        #     }
        # }), 201
        
    except sqlite3.Error as e:
        return jsonify({'error': f'Erreur de base de données: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'GET':
            return render_template('connexion.html')
        
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Validation des données
        if not email or not password:
            print("NO email")
            return render_template('connexion.html')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('SELECT id, password FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        

        if user and (user['password'] == password):
            print("User authenticated successfully")
            print("User ID:", user['id'])
            print("User Email:", email)
            print("DB Password:", user['password'])
            print("Input Password:", password)
            session['user_id'] = user['id']
        else:
            print("Email or password incorrect")
            return render_template('connexion.html', error='Email ou mot de passe incorrect')
        return render_template('upload.html', message='Connexion réussie')


        # return render_template('index.html', message='Connexion réussie', user_email=user_email)
        
    except sqlite3.Error as e:
        print("Database error:", str(e))
        return render_template('connexion.html', error=f'Erreur de base de données: {str(e)}')
    except Exception as e:
        print("Server error:", str(e))
        return render_template('connexion.html', error=f'Erreur serveur: {str(e)}')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user_id' not in session:
        # return render_template(url_for('index.html'))
        return render_template('index.html')
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Aucun fichier sélectionné'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Aucun fichier sélectionné'}), 400
        
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Type de fichier non autorisé. Utilisez PDF, DOC ou DOCX.'}), 400
        
        original_filename = secure_filename(file.filename)
        if not original_filename:
            return jsonify({'error': 'Nom de fichier invalide'}), 400
        
        # Générer un nom de fichier unique
        doc_id = str(uuid.uuid4())
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        filename = f"{doc_id}.{file_extension}"
        
        # Créer le dossier de l'utilisateur s'il n'existe pas
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']))
        os.makedirs(user_folder, exist_ok=True)
        
        # Sauvegarder le fichier
        file_path = os.path.join(user_folder, filename)
        print("File path:", file_path)
        file.save(file_path)
        
        # Obtenir la taille du fichier
        file_size = os.path.getsize(file_path)
        
        # Extraire le texte selon le type de fichier
        
            # if file_extension == 'pdf':
            #     extracted_text = extract_text_from_pdf(file_path)
            # elif file_extension == 'docx':
            #     extracted_text = extract_text_from_docx(file_path)
            # elif file_extension == 'doc':
            #     extracted_text = extract_text_from_doc(file_path)
            # else:
            #     return jsonify({'error': 'Type de fichier non supporté'}), 400            
        extracted_text, status_message = extract_text_from_pdf(file_path)
          

        # except Exception as e:
        #     # Supprimer le fichier en cas d'erreur d'extraction
        #     if os.path.exists(file_path):
        #         os.remove(file_path)
        #     return jsonify({'error': f'Erreur lors de l\'extraction du texte: {str(e)}'}), 500
        
        # Enregistrer dans la base de données
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO documents (id, user_id, original_filename, pdf_file_path, 
                                 extracted_text, file_type, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (doc_id, session['user_id'], original_filename, file_path, 
              extracted_text, file_extension, file_size))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'document': {
                'id': doc_id,
                'filename': original_filename,
                'file_type': file_extension,
                'file_size': file_size
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@app.route('/documents')
@login_required
def get_documents():
    """Retourner la liste des documents de l'utilisateur connecté"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, original_filename, file_type, file_size, upload_time, last_modified
        FROM documents 
        WHERE user_id = ? AND is_active = 1
        ORDER BY upload_time DESC
    ''', (session['user_id'],))
    
    documents = cursor.fetchall()
    conn.close()
    
    docs = []
    for doc in documents:
        docs.append({
            'id': doc['id'],
            'filename': doc['original_filename'],
            'file_type': doc['file_type'],
            'file_size': doc['file_size'],
            'upload_time': doc['upload_time'],
            'last_modified': doc['last_modified']
        })
    
    return jsonify(docs)

@app.route('/document/<doc_id>')
@login_required
def get_document(doc_id):
    """Retourner le contenu d'un document"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, original_filename, extracted_text, file_type, 
                   file_size, upload_time, last_modified, pdf_file_path
            FROM documents 
            WHERE id = ? AND user_id = ? AND is_active = 1
        ''', (doc_id, session['user_id']))
        
        document = cursor.fetchone()
        conn.close()
        
        if not document:
            return jsonify({'error': 'Document non trouvé'}), 404
        
        return jsonify({
            'id': document['id'],
            'filename': document['original_filename'],
            'content': document['extracted_text'],
            'file_type': document['file_type'],
            'file_size': document['file_size'],
            'upload_time': document['upload_time'],
            'last_modified': document['last_modified'],
            'file_path': document['pdf_file_path']
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération du document: {str(e)}'}), 500

@app.route('/document/<doc_id>/save', methods=['POST'])
@login_required
def save_document(doc_id):
    """Sauvegarder les modifications d'un document"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Vérifier que le document appartient à l'utilisateur
        cursor.execute('''
            SELECT id FROM documents 
            WHERE id = ? AND user_id = ? AND is_active = 1
        ''', (doc_id, session['user_id']))
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Document non trouvé'}), 404
        
        data = request.get_json()
        if not data or 'content' not in data:
            conn.close()
            return jsonify({'error': 'Contenu manquant'}), 400
        
        new_content = data['content'] if data['content'] is not None else ""
        
        # Mettre à jour le document
        cursor.execute('''
            UPDATE documents 
            SET extracted_text = ?, last_modified = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (new_content, doc_id, session['user_id']))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Document sauvegardé',
            'last_modified': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la sauvegarde: {str(e)}'}), 500

@app.route('/document/<doc_id>/delete', methods=['DELETE'])
@login_required
def delete_document(doc_id):
    """Supprimer un document (soft delete)"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Vérifier que le document appartient à l'utilisateur
        cursor.execute('''
            SELECT pdf_file_path FROM documents 
            WHERE id = ? AND user_id = ? AND is_active = 1
        ''', (doc_id, session['user_id']))
        
        document = cursor.fetchone()
        if not document:
            conn.close()
            return jsonify({'error': 'Document non trouvé'}), 404
        
        # Soft delete dans la base de données
        cursor.execute('''
            UPDATE documents 
            SET is_active = 0, last_modified = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (doc_id, session['user_id']))
        
        conn.commit()
        conn.close()
        
        # Optionnel: supprimer le fichier physique
        try:
            if os.path.exists(document['pdf_file_path']):  
                user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']))
                file_name = f"{doc_id}.txt"
        
                file_path = os.path.join(user_folder, file_name)         
                
                print("file_name txt : ", file_path)
                print("file_name pdf : ", document['pdf_file_path'])
                os.remove(document['pdf_file_path'])
                os.remove(file_path)
                
        except:
            pass  # Ne pas échouer si le fichier ne peut pas être supprimé
        
        return jsonify({'success': True, 'message': 'Document supprimé'})
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la suppression: {str(e)}'}), 500

# @app.route('/ai-chat/<doc_id>')
@app.route('/ai-chat', methods=['GET'])
@login_required
def ai_chat():
    """Rediriger vers l'interface AI avec le document"""
    doc_id = request.args.get('doc')
    if not doc_id:
        return redirect(url_for('index'))
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, original_filename, extracted_text, file_type
            FROM documents 
            WHERE id = ? AND user_id = ? AND is_active = 1
        ''', (doc_id, session['user_id']))
        
        document = cursor.fetchone()
        conn.close()
        print("doc name ",document["original_filename"])
        if not document:
            return jsonify({'error': 'Document non trouvé'}), 404
        return render_template('ai-chat.html', 
                             document_id=document['id'],
                             document_filename=document['original_filename'],
                             document_content=document['extracted_text'],
                             document_type=document['file_type'])        
        # return jsonify({
        #     'redirect_to_ai': True,
        #     'document_id': document['id'],
        #     'document_content': document['extracted_text'],
        #     'document_filename': document['original_filename'],
        #     'document_type': document['file_type']
        # })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de l\'accès à l\'interface IA: {str(e)}'}), 500

@app.route('/ask_question', methods=['POST'])
def ask_question_alternative():
    """Version alternative sans session"""
    try:
        data = request.get_json()
        doc_id = data.get('document_id')
        question = data.get('question', '').strip()
        
        if not doc_id or not question:
            return jsonify({'error': 'Document ID et question requis'}), 400

        conn = get_db()
        cursor = conn.cursor()        
        # Récupérer les données stockées
        cursor.execute('''
            SELECT id, original_filename, extracted_text, file_type
            FROM documents
            WHERE id = ? AND user_id = ? AND is_active = 1
        ''', (doc_id, session['user_id']))

        document = cursor.fetchone()
        if not document:
            return jsonify({'error': 'Document non trouvé'}), 404

        extracted_text = document['extracted_text']
        question = data['question'].strip()
        # Interroger l'IA
        ai_response = analyzer.query_ai_model(extracted_text, question)
        
        return jsonify({
            'success': True,
            'question': question,
            'response': ai_response,
            'document': session.get('original_filename', 'Document inconnu')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }), 500


@app.route('/user/profile')
@login_required
def user_profile():
    """Obtenir les informations du profil utilisateur"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username, email, created_at,
                   (SELECT COUNT(*) FROM documents WHERE user_id = ? AND is_active = 1) as document_count
            FROM users 
            WHERE id = ?
        ''', (session['user_id'], session['user_id']))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        return jsonify({
            'username': user['username'],
            'email': user['email'],
            'created_at': user['created_at'],
            'document_count': user['document_count']
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération du profil: {str(e)}'}), 500

if __name__ == '__main__':
    
    app.run(debug=True)