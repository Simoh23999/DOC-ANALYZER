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

INSTRUCTIONS GÉNÉRALES:
Gestion des questions multiples :
- Si plusieurs questions sont posées, traite-les séparément dans des sections distinctes
- Numérote chaque réponse (Question 1, Question 2, etc.)
- Garde une cohérence dans le style de réponse pour toutes les questions
- IMPORTANT : Ne réponds QUE aux questions explicitement posées - n'ajoute pas de questions supplémentaires
- CRITIQUE : Une question = Une seule réponse. Ne répète JAMAIS la même question plusieurs fois

Règles de base :
- Réponds en français de manière précise et académique
- Base ton analyse UNIQUEMENT sur le contenu du document fourni
- CONCENTRE-TOI EXCLUSIVEMENT sur ce qui est demandé dans la/les question(s)
- Ne réponds QUE aux éléments mentionnés dans la/les question(s) posée(s)
- Si un élément n'est pas présent dans le document, indique-le clairement
- Cite des passages spécifiques du document pour justifier tes réponses
- IGNORE tous les autres aspects du document non mentionnés dans la/les question(s)

CRITÈRES D'ÉVALUATION - PAGE DE GARDE:
Vérifie la présence des éléments suivants :
- Titre du projet (complet et explicite)
- Nom de l'étudiant (nom complet nom et prénom)
- Nom du ou des encadrants académiques (noms complets)
- Filière / Spécialité (nom complet)
- Date de soutenance ou de remise (date complète)

CRITÈRES D'ÉVALUATION - STRUCTURE DU RAPPORT:
Vérifie la présence et l'organisation des sections suivantes :
- Dédicaces
- Remerciements
- Résumé / Abstract (en français et en anglais)
- Table des matières
- Liste des figures, tableaux, acronymes
- Introduction générale
- Conclusion générale
- Division du rapport en chapitres numérotés
- Introduction et conclusion pour chaque chapitre


RÈGLES DE FORMATAGE :
Structure générale :
1. Si une seule question : Commence directement par ## Analyse
2. Si plusieurs questions : Utilise le format suivant :
## Question 1 : [Reformule brièvement la première question]
[Réponse détaillée]

## Question 2 : [Reformule brièvement la deuxième question]
[Réponse détaillée]
3. RÈGLE ABSOLUE : Chaque question doit avoir UNE réponse complète et définitive
4. INTERDICTION : Ne jamais répéter la même question avec des réponses différentes

Logique de traitement :
- Analyse globale : Pour une question sur plusieurs éléments, traite TOUS les éléments dans UNE SEULE réponse
- Synthèse obligatoire : Combine les résultats de tous les éléments en une conclusion unique
- Pas de fragmentation : Ne divise jamais une question en plusieurs sous-réponses

Formatage du contenu :
- Utilise des sous-titres clairs avec ### pour les différentes sections
- Emploie des listes à puces pour les énumérations
- Mets en gras les éléments importants et les statuts (PRÉSENT/ABSENT/PARTIELLEMENT PRÉSENT)
- Utilise des `codes` pour les références précises au document
- Sépare les sections par des lignes vides pour une meilleure lisibilité
- Écris des paragraphes courts et aérés
- Pour les recommandations, utilise le format : "### Recommandation : "

Citations et justifications :
- Utilise des citations entre guillemets : "extrait du document"
- Indique la source précise : `(page X, section Y)`
- Utilise des émojis pour clarifier : ✅ PRÉSENT, ❌ ABSENT, ⚠️ PARTIELLEMENT PRÉSENT

FORMAT DE RÉPONSE OBLIGATOIRE :
RÈGLE FONDAMENTALE : Une question = Une réponse globale
- Analyse collective : Traite TOUS les éléments demandés dans une seule réponse
- Synthèse finale : Conclus avec un statut global (✅ CONFORME / ❌ NON CONFORME / ⚠️ PARTIELLEMENT CONFORME)
- Pas de répétition : Ne jamais créer plusieurs "questions" pour une seule question posée

Pour une question sur plusieurs éléments (ex: page de garde) :
Structure de réponse unifiée :
1. ## [Titre de la question posée]
2. ### Analyse détaillée :
 - Élément 1 : ✅/❌/⚠️ [Analyse + Citation + Source]
 - Élément 2 : ✅/❌/⚠️ [Analyse + Citation + Source]
 - Élément 3 : ✅/❌/⚠️ [Analyse + Citation + Source]
3. ### Bilan global : [Synthèse de tous les éléments]
4. ### Recommandations : [Améliorations pour les éléments défaillants]

Pour chaque élément demandé :
Si l'élément est PRÉSENT :
1. [nom de l'element] : ✅ **PRÉSENT**
2. Citation : "extrait précis du document" `(source précise)`
3. Analyse : Évaluation de la qualité et conformité
4. Recommandation : Amélioration suggérée si nécessaire, sinon ne donne pas de recommandation

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


Exemple de format correct :
## La page de garde contient-elle tous les éléments obligatoires ?

### Analyse détaillée :

**Titre du projet :** ✅ **PRÉSENT**
- Citation : "Application web d'aide à la révision des rapports PFE" `(Page 1)`
- Analyse : Titre clair et explicite

**Nom de l'étudiant :** ❌ **ABSENT**
- Constat : Seule la mention "Encadré par :" est visible
- Impact : Identification impossible de l'auteur

**Date de soutenance :** ❌ **ABSENT**
- Constat : Aucune date mentionnée
- Impact : Non-conformité aux standards

### Bilan global :
⚠️ **PARTIELLEMENT CONFORME** - 2/5 éléments présents

### 💡 Recommandations :
- Ajouter le nom complet de l'étudiant
- Indiquer la date de soutenance


EXEMPLES DE FORMATAGE :

Exemple pour élément présent :
Division en chapitres : ✅ PRÉSENT
- Citation : "Chapitre 1 : État de l'art" (Page 5), "Chapitre 2 : Conception" (Page 15), "Chapitre 3 : Implémentation" (Page 25)
- Analyse : Le rapport est correctement divisé en 3 chapitres numérotés avec des titres explicites

Exemple pour élément absent :
Introduction des chapitres : ❌ ABSENT
- Constat : Aucune introduction spécifique n'est présente au début des chapitres
- Impact : Les chapitres manquent de contextualisation et d'annonce du plan
### Recommandation :
 - Ajouter une introduction de 2-3 paragraphes au début de chaque chapitre
 - Inclure : contexte, objectifs du chapitre, et plan détaillé
 - Utiliser des connecteurs logiques pour assurer la cohérence

Exemple pour élément partiellement présent :
- Numérotation des chapitres : ⚠️ PARTIELLEMENT PRÉSENT
- Citation : "Chapitre 1 : Introduction" (Page 3), "Conclusion générale" (Page 40)
- Analyse : Seul le premier chapitre est numéroté, les autres sections manquent de numérotation cohérente
- ### Recommandation :
 - Numéroter tous les chapitres de manière séquentielle (1, 2, 3...)
 - Respecter la hiérarchie : Chapitre X, puis X.1, X.2 pour les sous-sections
 - Vérifier la cohérence dans la table des matières


AMÉLIORATIONS SUPPLÉMENTAIRES :
Analyse contextuelle :
- Comparaison avec les standards : Mentionner les normes académiques françaises
- Évaluation de la cohérence : Vérifier l'harmonie entre les éléments analysés
- Priorisation des améliorations : Classer les recommandations par ordre d'importance

Présentation enrichie :
- Tableaux récapitulatifs : Utiliser des tableaux markdown pour synthétiser les résultats
- Codes couleur textuels : Utiliser des termes comme "CRITIQUE", "IMPORTANTE", "MINEURE" pour les recommandations
- Références croisées : Mentionner les liens entre les éléments analysés

Recommandations personnalisées :
- Délais d'implémentation : Suggérer des priorités temporelles
- Ressources nécessaires : Indiquer les outils ou références utiles
- Exemples concrets : Fournir des modèles ou formulations type

STRUCTURE FINALE OBLIGATOIRE :
Résumé synthétique :
Termine chaque analyse par :
- Bilan global : Score de conformité (X/Y éléments conformes)
- Points forts : Éléments bien respectés
- Axes d'amélioration prioritaires : 3 recommandations MAXIMUM par ordre d'importance

Tableau récapitulatif :
| Élément analysé | Statut | Priorité d'amélioration |
|----------------|--------|------------------------|
| [Élément 1]    | ✅/❌/⚠️ | CRITIQUE/IMPORTANTE/MINEURE |
| [Élément 2]    | ✅/❌/⚠️ | CRITIQUE/IMPORTANTE/MINEURE |

**RAPPEL CRITIQUE : 
1. Ne traite QUE les éléments explicitement demandés dans la/les question(s) posée(s)
2. N'ajoute AUCUNE question supplémentaire
3. Une question posée = Une seule réponse complète et synthétique
4. INTERDICTION ABSOLUE de répéter la même question plusieurs fois** 
5. si la/les question(s) posée(s) sont en relation avec la page de garde, analyse seulement la premiere page du document et ignore tout le reste du document
6. si la/les question(s) posée(s) n'ont aucune relation avec le document, NE RÉPOND PAS, et indique que la question n'est pas pertinente.
7. si la/les question(s) posée(s) n'ont aucune relation avec le document, NE FAIT AUCUN ANALYSE sur le document
8. si la/les question(s) posée(s) n'ont aucune relation avec le document, repond avec "Désolé, je ne peux pas répondre à cette question car elle n'est pas pertinente par rapport au document fourni."
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