# AI Μέντορας - Οδηγός Εγκατάστασης

## 📋 Βήμα 1: Εγκατάσταση Προαπαιτούμενων

### 1.1 Ollama
1. Πήγαινε στο https://ollama.ai/
2. Κατέβασε το Ollama για Windows
3. Εγκατέστησε το (διπλό κλικ στο installer)
4. Άνοιξε Command Prompt και τρέξε:
   ```bash
   ollama pull llama3:latest
   ```
5. Περίμενε να ολοκληρωθεί το download (~4.7GB)

### 1.2 Python 3.10+
1. Πήγαινε στο https://www.python.org/downloads/
2. Κατέβασε την τελευταία έκδοση Python 3.10 ή νεότερη
3. Κατά την εγκατάσταση, **τσέκαρε το "Add Python to PATH"**
4. Επιβεβαίωση: Άνοιξε Command Prompt και τρέξε:
   ```bash
   python --version
   ```

### 1.3 Node.js 18+
1. Πήγαινε στο https://nodejs.org/
2. Κατέβασε την LTS έκδοση
3. Εγκατέστησε το (default settings)
4. Επιβεβαίωση:
   ```bash
   node --version
   npm --version
   ```

### 1.4 pnpm
Άνοιξε Command Prompt ως Administrator και τρέξε:
```bash
npm install -g pnpm
```

Επιβεβαίωση:
```bash
pnpm --version
```

## 📦 Βήμα 2: Εγκατάσταση Dependencies

### 2.1 Backend Dependencies
1. Άνοιξε Command Prompt
2. Navigate στον φάκελο backend:
   ```bash
   cd path\to\workspace\backend
   ```
3. Εγκατέστησε τις Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 2.2 Frontend Dependencies
1. Navigate στον φάκελο frontend:
   ```bash
   cd path\to\workspace\app\frontend
   ```
2. Εγκατέστησε τις Node dependencies:
   ```bash
   pnpm install
   ```

## 🚀 Βήμα 3: Πρώτη Εκτέλεση

### Μέθοδος 1: Αυτόματη (Συνιστάται)

1. Navigate στον κύριο φάκελο του project:
   ```bash
   cd path\to\workspace
   ```

2. Κάνε διπλό κλικ στο `start_windows.bat`

3. Θα ανοίξουν 3 παράθυρα:
   - Ollama (αν δεν τρέχει ήδη)
   - Backend (FastAPI)
   - Frontend (React)

4. Αυτόματα θα ανοίξει το browser στο http://localhost:3000

### Μέθοδος 2: Χειροκίνητη

**Terminal 1 - Ollama:**
```bash
ollama serve
```

**Terminal 2 - Backend:**
```bash
cd path\to\workspace\backend
uvicorn main:app --reload
```

**Terminal 3 - Frontend:**
```bash
cd path\to\workspace\app\frontend
pnpm run dev
```

**Browser:**
Άνοιξε http://localhost:3000

## 🖥️ Βήμα 4: Δημιουργία Desktop Shortcut

### Για start_windows.bat:

1. Πήγαινε στον φάκελο workspace
2. Δεξί κλικ στο `start_windows.bat`
3. Επίλεξε "Δημιουργία συντόμευσης"
4. Μετακίνησε τη συντόμευση στην Επιφάνεια Εργασίας
5. (Προαιρετικό) Μετονόμασε σε "AI Μέντορας"

### Για καλύτερο εικονίδιο (προαιρετικό):

1. Δεξί κλικ στη συντόμευση → Ιδιότητες
2. Κλικ στο "Αλλαγή εικονιδίου"
3. Επίλεξε ένα εικονίδιο που σου αρέσει
4. Κλικ OK

## ✅ Βήμα 5: Επαλήθευση Εγκατάστασης

### 5.1 Έλεγχος Ollama
1. Άνοιξε http://127.0.0.1:11434/api/tags
2. Θα πρέπει να δεις JSON με τα διαθέσιμα μοντέλα

### 5.2 Έλεγχος Backend
1. Άνοιξε http://127.0.0.1:8000/health
2. Θα πρέπει να δεις:
   ```json
   {
     "status": "ok",
     "ollama_connected": true,
     "timestamp": "..."
   }
   ```

### 5.3 Έλεγχος Frontend
1. Άνοιξε http://localhost:3000
2. Θα πρέπει να δεις το UI του AI Μέντορα
3. Στο πάνω μέρος θα πρέπει να δεις: "Κατάσταση AI: Συνδεδεμένο" (πράσινο)

## 🎯 Βήμα 6: Πρώτη Χρήση

1. **Δημιούργησε μια συνομιλία:**
   - Κλικ στο sidebar "Συνομιλίες"
   - Γράψε έναν τίτλο (π.χ. "Πρώτη Συνομιλία")
   - Κλικ στο + κουμπί

2. **Στείλε το πρώτο σου μήνυμα:**
   - Γράψε "Γεια σου!" στο chat
   - Πάτησε Enter ή κλικ στο Send κουμπί
   - Περίμενε την απάντηση από το AI

3. **Δοκίμασε τη φωνητική εισαγωγή:**
   - Κλικ στο κουμπί μικροφώνου 🎤
   - Μίλησε στα ελληνικά
   - Το κείμενο θα εμφανιστεί αυτόματα

4. **Δοκίμασε τη σύνοψη:**
   - Μετά από μερικά μηνύματα
   - Κλικ στο "Σύνοψη μέχρι εδώ"
   - Θα δεις μια δομημένη σύνοψη της συνομιλίας

## 🔧 Troubleshooting

### Πρόβλημα: "Ollama is not running"

**Λύση 1:**
```bash
ollama serve
```

**Λύση 2:**
Επανεκκίνησε τον υπολογιστή και δοκίμασε ξανά

**Λύση 3:**
Έλεγξε αν το Ollama είναι στο PATH:
```bash
where ollama
```

### Πρόβλημα: "Port 8000 is already in use"

**Λύση:**
```bash
# Βρες την εφαρμογή που χρησιμοποιεί τη θύρα
netstat -ano | findstr :8000

# Τερμάτισε την εφαρμογή (αντικατέστησε PID με το νούμερο που βρήκες)
taskkill /F /PID <PID>
```

### Πρόβλημα: "Port 3000 is already in use"

**Λύση:**
Ίδια με το παραπάνω, αλλά για θύρα 3000

### Πρόβλημα: "Module not found" στο Backend

**Λύση:**
```bash
cd backend
pip install -r requirements.txt --force-reinstall
```

### Πρόβλημα: "Module not found" στο Frontend

**Λύση:**
```bash
cd app/frontend
pnpm install --force
```

### Πρόβλημα: Το AI δεν απαντά

**Έλεγχοι:**
1. Είναι το Ollama συνδεδεμένο; (πράσινο στο UI)
2. Τρέχει το backend; (έλεγξε το terminal)
3. Υπάρχει το μοντέλο llama3; (`ollama list`)

**Λύση:**
```bash
# Κατέβασε ξανά το μοντέλο
ollama pull llama3:latest

# Επανεκκίνησε το backend
# Ctrl+C στο backend terminal
uvicorn main:app --reload
```

## 🔐 Προαιρετικό: ChatGPT API Setup

Αν θέλεις να χρησιμοποιήσεις το ChatGPT API για online βοήθεια:

1. Πάρε ένα API key από: https://platform.openai.com/api-keys

2. Άνοιξε Command Prompt ως Administrator

3. Όρισε το API key:
   ```bash
   setx OPENAI_API_KEY "sk-your-api-key-here"
   ```

4. Κλείσε και άνοιξε ξανά όλα τα terminals

5. Επανεκκίνησε το backend

## 📝 Σημειώσεις

- Η πρώτη φορά που θα τρέξεις το backend, θα δημιουργηθεί το αρχείο `ai_mentor.db`
- Όλα τα δεδομένα αποθηκεύονται τοπικά
- Το Ollama μπορεί να χρησιμοποιήσει GPU αν έχεις NVIDIA card
- Για καλύτερη απόδοση, κλείσε άλλες βαρύ-resource εφαρμογές

## 🎉 Έτοιμο!

Τώρα μπορείς να χρησιμοποιήσεις τον AI Μέντορα! Απλά κάνε διπλό κλικ στο shortcut στην Επιφάνεια Εργασίας.

Για περισσότερες πληροφορίες, δες το README.md