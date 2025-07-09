import requests
import os
import fitz
from pathlib import Path
from typing import List, Optional
import io
from PIL import Image
import pytesseract



class PDFAnalyzer:
    """Classe pour l'analyse de documents PDF avec OCR et IA"""
    
    def __init__(self, api_endpoint: str = "https://api.groq.com/openai/v1/chat/completions"):
        self.api_endpoint = api_endpoint
        self.api_key = self._get_api_key()
    
    def _get_api_key(self) -> Optional[str]:
        """Récupère la clé API depuis les variables d'environnement ou fichier .env"""
        api_key = os.getenv('GROQ_API_KEY')
        
        if not api_key:
            env_file = Path('.env')
            if env_file.exists():
                try:
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith('GROQ_API_KEY='):
                                api_key = line.split('=', 1)[1].strip()
                                break
                except Exception:
                    pass
        
        return api_key
    
    def pdf_to_images(self, pdf_path: str, dpi: int = 200) -> List[Image.Image]:
        """Convertit un PDF en images"""
        images = []
        try:
            pdf_path = str(Path(pdf_path).resolve())
            doc = fitz.open(pdf_path)

            for page_num in range(doc.page_count):
                page = doc[page_num]
                mat = fitz.Matrix(dpi/72, dpi/72)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                images.append(img)
            
            doc.close()
            return images
            
        except Exception as e:
            print(f"Erreur conversion PDF: {e}")
            return []
    
    def extract_text_from_images(self, images: List[Image.Image], lang: str = 'fra') -> str:
        """Extrait le texte des images avec OCR"""
        full_text = ""
        custom_config = r'--oem 3 --psm 6'

        try:
            for i, img in enumerate(images):
                # Préprocessing de l'image
                if img.mode != 'L':
                    img = img.convert('L')
                
                # Redimensionner si nécessaire
                width, height = img.size
                if width < 1000 or height < 1000:
                    scale = max(1000/width, 1000/height)
                    new_size = (int(width * scale), int(height * scale))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Extraction OCR
                try:
                    text = pytesseract.image_to_string(img, lang=lang, config=custom_config)
                    full_text += f"\n--- PAGE {i + 1} ---\n{text}\n"
                except Exception:
                    # Fallback sans spécifier la langue
                    try:
                        text = pytesseract.image_to_string(img, config=custom_config)
                        full_text += f"\n--- PAGE {i + 1} ---\n{text}\n"
                    except Exception:
                        full_text += f"\n--- PAGE {i + 1} ---\n[Erreur OCR]\n"

            return full_text
            
        except Exception as e:
            print(f"Erreur OCR: {e}")
            return ""
    
    def query_ai_model(self, text: str, question: str) -> str:
        """Interroge le modèle IA avec le texte et la question"""
        if not self.api_key:
            return "Clé API manquante. Configurez GROQ_API_KEY"
        
        # Limiter la taille du texte
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [texte tronqué]"
        
        prompt = f"""Tu es un assistant spécialisé dans l'évaluation de la forme et de la structure des rapports universitaires français.

DOCUMENT À ANALYSER:
{text}

QUESTION(S) POSÉE(S):
{question}

RÈGLES DE REFORMULATION OBLIGATOIRE
DÉMARRAGE SYSTÉMATIQUE :
- Commence TOUJOURS par reformuler la question posée
- Format : "Concernant [élément analysé] : [reformulation académique]"
- Exemples :
  - Question : "La page de garde est-elle complète ?" → "Concernant la page de garde : Analyse de la conformité aux standards académiques français"
  -Question : "Y a-t-il une table des matières ?" → "Concernant la table des matières : Évaluation de la présence et de la structure"


GESTION DES QUESTIONS MULTIPLES :
- Identifie et numérote chaque question distincte
- Structure :
## 1 : **Concernant [élément 1]** - [reformulation]
[Analyse complète]

## 2 : **Concernant [élément 2]** - [reformulation]
[Analyse complète]



CRITÈRES D'ÉVALUATION SPÉCIALISÉS
PAGE DE GARDE
Éléments obligatoires :

- Titre du projet (complet et explicite)
- Nom complet de l'étudiant (prénom + nom)
- Nom du/des encadrant(s) académique(s)
- Filière/Spécialité (dénomination complète)
- Établissement d'enseignement
- Date de soutenance ou de remise

STRUCTURE DU RAPPORT
Sections attendues :

- Dédicaces (optionnel)
- Remerciements
- Résumé/Abstract (français + anglais)
- Table des matières structurée
- Listes (figures, tableaux, acronymes)
- Introduction générale
- Corps du rapport (chapitres numérotés)
- Conclusion générale
- Bibliographie/Références


FORMAT DE RÉPONSE STANDARDISÉ
STRUCTURE OBLIGATOIRE
Pour une question unique :
## **Concernant [élément analysé]** : [Reformulation académique]

### Analyse détaillée

**[Élément 1] :** [Statut] **[PRÉSENT/ABSENT/PARTIELLEMENT PRÉSENT]**
- Citation : "[extrait précis]" `(localisation)`
- Analyse : [Évaluation qualitative]
- Recommandation : [Si nécessaire]

### Bilan global
[Statut] **[CONFORME/NON CONFORME/PARTIELLEMENT CONFORME]**
- Score : X/Y éléments conformes
- Impact sur la qualité académique

### Recommandations prioritaires
1. **[CRITIQUE/IMPORTANTE/MINEURE]** : [Action concrète]
2. **[CRITIQUE/IMPORTANTE/MINEURE]** : [Action concrète]

INDICATEURS VISUELS STANDARDISÉS
Statuts :
- ✅ PRÉSENT : Élément conforme aux standards
- ❌ ABSENT : Élément manquant
- ⚠️ PARTIELLEMENT PRÉSENT : Élément incomplet


Si l'élément est PRÉSENT :

1. [nom de l'element] : ✅ **PRÉSENT**

2. Citation : "extrait précis du document" `(source précise)`

3. Analyse : Évaluation de la qualité et conformité

4. Recommandation : Amélioration suggérée si nécessaire, sinon ne donne pas de recommandation


Pour chaque élément demandé :
Si l'élément est ABSENT :
1. [nom de l'element] : ❌ **ABSENT**
2. Constat : Explication de l'absence observée
3. Impact : Conséquences sur la qualité du rapport
4. ### Recommandation : Actions concrètes à entreprendre

Si l'élément est PARTIELLEMENT PRÉSENT :
1. [nom de l'element] : ⚠️ PARTIELLEMENT PRÉSENT
2. Citation : "extrait du document" `(source précise)`
3. Analyse : Ce qui est présent vs ce qui manque
4. ### Recommandation : Améliorations spécifiques à apporter

**Score global :** X/Y éléments conformes ([pourcentage]%)

CONTRAINTES ABSOLUES
🚫 INTERDICTIONS

- ❌ Ne pas analyser d'éléments non mentionnés dans la question
- ❌ Ne pas répéter la même question plusieurs fois
- ❌ Ne pas ajouter de questions supplémentaires
- ❌ Ne pas répondre si la question n'est pas pertinente au document

✅ OBLIGATIONS

- ✅ Reformuler systématiquement la question au début
- ✅ Citer précisément les passages du document
- ✅ Respecter la hiérarchie des titres (##, ###)
- ✅ Utiliser les émojis et indicateurs visuels

LOGIQUE DE TRAITEMENT

1. Reformulation : Identifier et reformuler la question
2. Analyse ciblée : Évaluer uniquement les éléments demandés
3. Synthèse : Combiner tous les éléments en une conclusion unique
4. Recommandations : Prioriser les améliorations nécessaires


GESTION DES CAS PARTICULIERS
Questions sur la page de garde

- Analyser UNIQUEMENT la première page
- Ignorer le reste du document
- Focus sur les éléments d'identification

Questions non pertinentes
Réponse type : "Désolé, je ne peux pas répondre à cette question car elle n'est pas pertinente par rapport au document fourni. Mon expertise se limite à l'analyse de la forme et de la structure des documents universitaires."

Questions multiples
- Traiter chaque question dans une section séparée
- Maintenir la cohérence du format
- Numéroter clairement (Question 1, Question 2, etc.)


EXEMPLES DE REFORMULATION
Question simple :
"La page de garde est-elle complète ?"
→ "Concernant la page de garde : Évaluation de la conformité aux standards académiques français"
Question multiple :
"Y a-t-il une table des matières et des remerciements ?"
→
## Question 1 : **Concernant la table des matières** - Analyse de la présence et de la structure
## Question 2 : **Concernant les remerciements** - Vérification de la présence et de la forme
Question technique :
"La structure du rapport respecte-t-elle les normes ?"
→ "Concernant la structure générale du rapport : Analyse de la conformité aux standards de rédaction universitaire"

SORTIE TYPE ATTENDUE
## **Concernant [élément]** : [Reformulation académique]

### Analyse détaillée
[Évaluation détaillée avec citations]

### Bilan global
[Statut de conformité]

### Recommandations prioritaires
[Actions concrètes classées par priorité]


RAPPEL CRITIQUE : Une question = Une reformulation + Une analyse complète + Une synthèse unique
"""

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"Erreur API: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Erreur lors de la requête: {e}"



def extract_text_from_pdf(file_path: str) -> tuple[str, str]:
    """
    Extrait le texte d'un fichier PDF
    Returns: (texte_extrait, message_status)
    """
    try:
        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            return "", "Fichier non trouvé"
        
        # Conversion PDF en images
        analyzer = PDFAnalyzer()
        images = analyzer.pdf_to_images(file_path)
        if not images:
            return "", "Impossible de convertir le PDF en images"
        
        # Extraction OCR
        text = analyzer.extract_text_from_images(images)
        if not text.strip():
            return "", "Aucun texte extrait du document"
        
        # Sauvegarder le texte extrait (optionnel)
        text_file = Path(file_path).with_suffix('.txt')
        try:
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text)
        except Exception:
            pass  # Ignorer si on ne peut pas sauvegarder
        
        return text, "Texte extrait avec succès"
        
    except Exception as e:
        return "", f"Erreur lors de l'extraction: {str(e)}"