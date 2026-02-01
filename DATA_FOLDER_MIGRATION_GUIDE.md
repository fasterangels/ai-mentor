# Data Folder Migration Guide

## Τι Άλλαξε;

Από αυτή την έκδοση, **όλα τα δεδομένα χρήστη αποθηκεύονται σε ξεχωριστό φάκελο** εκτός του project directory.

### Παλιά Αρχιτεκτονική
```
workspace/
└── backend/
    └── ai_mentor.db  ❌ (μέσα στο project)
```

### Νέα Αρχιτεκτονική
```
%USERPROFILE%\AI_Mentor_Data\
└── ai_mentor.db  ✅ (ξεχωριστός φάκελος)
```

## Πλεονεκτήματα

✅ **Ασφαλή Updates**: Αντικατάστησε το project folder χωρίς να χάσεις δεδομένα
✅ **Εύκολα Backups**: Ένας φάκελος για όλα τα δεδομένα
✅ **Καθαρός Διαχωρισμός**: Code και data ξεχωριστά
✅ **Ιδιωτικότητα**: Δεδομένα στο user profile

## Αυτόματο Migration

Όταν ξεκινήσεις την εφαρμογή για πρώτη φορά με τη νέα έκδοση:

1. **Ανίχνευση**: Το σύστημα ελέγχει αν υπάρχει παλιά βάση στο `backend/ai_mentor.db`
2. **Αντιγραφή**: Αν βρεθεί, αντιγράφεται αυτόματα στο `%USERPROFILE%\AI_Mentor_Data\`
3. **Διατήρηση**: Η παλιά βάση παραμένει στο backend/ (μπορείς να τη διαγράψεις)
4. **Επιβεβαίωση**: Δες τα logs στο backend terminal για επιβεβαίωση

### Παράδειγμα Migration Logs
```
[Migration] Found old database at C:\workspace\backend\ai_mentor.db
[Migration] Migrating to C:\Users\YourName\AI_Mentor_Data\ai_mentor.db
[Migration] Successfully migrated database
[Database] Using database at: C:\Users\YourName\AI_Mentor_Data\ai_mentor.db
```

## Χειροκίνητη Επαλήθευση

### 1. Έλεγξε το Data Folder
```bash
dir "%USERPROFILE%\AI_Mentor_Data"
```

Θα πρέπει να δεις:
```
ai_mentor.db
```

### 2. Έλεγξε μέσω API
Άνοιξε: http://127.0.0.1:8000/health

Θα δεις:
```json
{
  "status": "ok",
  "database_path": "C:\\Users\\YourName\\AI_Mentor_Data\\ai_mentor.db",
  "data_directory": "C:\\Users\\YourName\\AI_Mentor_Data"
}
```

### 3. Επιβεβαίωση Δεδομένων
- Άνοιξε την εφαρμογή
- Έλεγξε ότι οι παλιές συνομιλίες/μνήμες είναι εκεί
- Δημιούργησε νέα μνήμη
- Επανεκκίνησε την εφαρμογή
- Επιβεβαίωσε ότι η νέα μνήμη παραμένει

## Custom Data Directory

Αν θέλεις να χρησιμοποιήσεις διαφορετικό φάκελο:

```bash
setx DATA_DIR "D:\MyCustomPath\AI_Mentor_Data"
```

Επανεκκίνησε τα terminals και ξεκίνα την εφαρμογή.

## Backup Strategy

### Απλό Backup
```bash
xcopy "%USERPROFILE%\AI_Mentor_Data" "D:\Backups\AI_Mentor_Data_%date:~-4,4%%date:~-10,2%%date:~-7,2%" /E /I /Y
```

### Αυτόματο Backup με Task Scheduler

1. Άνοιξε Task Scheduler
2. Create Basic Task
3. Trigger: Daily
4. Action: Start a program
5. Program: `xcopy`
6. Arguments: `"%USERPROFILE%\AI_Mentor_Data" "D:\Backups\AI_Mentor_Data" /E /I /Y /D`

## Troubleshooting

### Δεν βρίσκω τα δεδομένα μου

**Έλεγξε το path:**
```bash
echo %USERPROFILE%\AI_Mentor_Data
```

**Άνοιξε το folder:**
```bash
explorer "%USERPROFILE%\AI_Mentor_Data"
```

### Το migration δεν έγινε

**Χειροκίνητη αντιγραφή:**
```bash
copy "backend\ai_mentor.db" "%USERPROFILE%\AI_Mentor_Data\ai_mentor.db"
```

### Θέλω να επιστρέψω στην παλιά αρχιτεκτονική

**Όρισε custom path:**
```bash
setx DATA_DIR "%cd%\backend"
```

Επανεκκίνησε τα terminals.

## FAQ

**Q: Τι γίνεται με τα δεδομένα μου όταν αναβαθμίζω;**
A: Παραμένουν ασφαλή στο `AI_Mentor_Data` folder. Απλά αντικατέστησε το project folder.

**Q: Μπορώ να μετακινήσω το data folder;**
A: Ναι, όρισε το `DATA_DIR` environment variable.

**Q: Πώς κάνω backup;**
A: Απλά αντίγραψε τον φάκελο `%USERPROFILE%\AI_Mentor_Data`.

**Q: Τι περιέχει το data folder;**
A: Αυτή τη στιγμή μόνο το `ai_mentor.db`. Μελλοντικά μπορεί να προστεθούν logs, exports, κλπ.

**Q: Είναι ασφαλές να διαγράψω την παλιά βάση από το backend/;**
A: Ναι, αφού επιβεβαιώσεις ότι τα δεδομένα σου είναι στο νέο folder.

## Επόμενα Βήματα

1. ✅ Επιβεβαίωσε ότι το migration έγινε επιτυχώς
2. ✅ Δοκίμασε να δημιουργήσεις νέα δεδομένα
3. ✅ Επανεκκίνησε την εφαρμογή και επιβεβαίωσε data persistence
4. ✅ Ρύθμισε backup strategy
5. ✅ (Προαιρετικό) Διέγραψε την παλιά βάση από backend/

Καλή χρήση! 🚀
