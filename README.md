### 2\. Installation de Tesseract OCR

1.  Go to : https://github.com/UB-Mannheim/tesseract/wiki
2.  click la version 64-bit : `tesseract-ocr-w64-setup-5.5.0.20241111.exe`
3.  Exécutez l'installateur avec les options par défaut
4.  **Important** : Notez le chemin d'installation (`C:\Program Files\Tesseract-OCR`)

### 3\. Configuration de Tesseract

Ajoutez Tesseract au PATH système :

1.  ouvrir  "Variables d'environnement"
2.  Dans "Variables système", sélectionnez "Path" et cliquez "Modifier"
3.  Ajoutez : `C:\Program Files\Tesseract-OCR`
4.  Cliquez "OK" pour fermer toutes les fenêtres

### 4\. Installation des bibliothèques Python

Ouvre le cmd  et exécute :

```cmd
pip install -r requirements.txt
```

### 5\. Téléchargement des données linguistiques

Téléchargez le pack français pour Tesseract :

```cmd
# téléchargez manuellement depuis ce lien:
# https://github.com/tesseract-ocr/tessdata/raw/main/fra.traineddata
# Et placez le fichier dans : C:\Program Files\Tesseract-OCR\tessdata\
```

## 🔑 Configuration de l'API Groq
1. creer compte sur https://console.groq.com/
2. genere ton API KEY
### Dans Fichier .env 

Créez le fichier `.env` dans le même dossier principale:

```
GROQ_API_KEY=votre_clé_api_groq
```
