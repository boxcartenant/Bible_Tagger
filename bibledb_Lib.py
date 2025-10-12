import json
import sqlite3

CURRENT_DATABASE_VERSION = 1


####  HOW TO USE:
# first call getBibleData on a valid bible json
# if you're using a new DB, then call makeDB with a path
# elif you're using an existing DB, then dwai
# use add_verse_tag, add_verse_note, and add_tag_note to add data to the DB


#ordered list of names, to be used like: book_proper_names[0] #returns "Genesis"
book_proper_names = []

######################
# INTERNALLY USED FUNCTIONS
######################

# Function to get fully qualified book names from partial names
def qualifyBook(book_name):
    global book_proper_names

    if book_name == '':
        return None
    
    for name in book_proper_names:
        if book_name.lower() in name.lower():
            return name
        
    return None

def copy_db(source_path, dest_path):
    source = sqlite3.connect(source_path)
    dest = sqlite3.connect(dest_path)
    source.backup(dest)
    source.close()
    dest.close()

def normalize_vref(passage):
    # takes a verse reference in the form (1,1,1,2,2,2) like what we get from the verses db
    # and returns its normalized string name (Genesis 1:1-Exodus 2:2)
    vID, bA, cA, vA, bB, cB, vB = (str(n) for n in passage.values())
    
    pA = book_proper_names[int(bA)]
    pB = book_proper_names[int(bB)]
    if bA != bB: #different book
        if bA < bB:
            return(pA+" "+cA + ":" + vA + " - " + pB + " " +cB + ":" + vB)
        else:
            return(pB+" "+cB + ":" + vB + " - " + pA + " " +cA + ":" + vA)
    elif cA != cB: #same book, different chapter
        if int(cA) < int(cB):
            return(pA+" "+cA + ":" + vA + "-" + cB + ":" + vB)
        else:
            return(pA+" "+cB + ":" + vB + "-" + cA + ":" + vA)
    elif vA != vB: #same book, same chapter, different verse
        if int(vA) < int(vB):
            return(pA+" "+cA + ":" + vA + "-" + vB)
        else:
            return(pA+" "+cB + ":" + vB + "-" + vA)
    else: #same book, same chapter, same verse
        return (pA + " " + cB + ":" + vB)

def getBookIndex(book):
    book = qualifyBook(book)
    return book_proper_names.index(book) if book in book_proper_names else -1

def parseVerseReference(verse_ref):
    # Split the verse reference into parts
    parts = verse_ref.split()

    # Ensure that the verse reference has the correct format
    if len(parts) < 2:
        return None
    
    #extract the book name, chapter, and verses.

    #if two or more verses...
    if '-' in verse_ref:
        refs = verse_ref.split('-')
        refs[0]=refs[0].strip()#important to strip here in case the '-' has spaces around it.
        refs[1]=refs[1].strip()
        start = refs[0].split()
        i = 0
        sbname = ''
        while i < len(start)-1:
            sbname += start[i] + " "
            i += 1
        sb = getBookIndex(qualifyBook(sbname.strip()))
        sc = start[i].split(':')[0]
        sv = start[i].split(':')[1]
        #if two or more books... (e.g. Gen 1:1-Exod 1:1)
        if " " in refs[1]:
            end = refs[1].split()
            i = 0
            ebname = ''
            while i < len(start)-1:
                ebname += end[i] + " "
                i += 1
            eb = getBookIndex(qualifyBook(ebname.strip()))
            ec = end[i].split(':')[0]
            ev = end[i].split(':')[1]
        #elif two or more chapters... (e.g. Gen 1:1-2:2)
        elif ":" in refs[1].strip():
            eb = sb
            ec = refs[1].strip().split(':')[0]
            ev = refs[1].strip().split(':')[1]
        #two or more verses... (e.g. Gen 1:1-5)
        else:
            eb = sb
            ec = sc
            ev = refs[1].strip()
    #just one verse...(e.g. Gen 1:1)
    else:
        i = 0
        book_name = ''
        while i < len(parts)-1:
            book_name += parts[i] + " "
            i += 1
        verse_nums = parts[i]
        book_name = book_name.strip()
        vparts = verse_nums.split(':')
        #start and end book chapter and verse are the same.
        sb = getBookIndex(qualifyBook(book_name))
        eb = sb
        sc = vparts[0].strip()
        ec = sc
        sv = vparts[1].strip()
        ev = sv

    return {'sb':sb, 'sc':sc, 'sv': sv, 'eb':eb, 'ec':ec, 'ev': ev}

def get_row_by_column(list_of_dicts, target_value, column_name):
    for row in list_of_dicts:
        if row.get(column_name) == target_value:
            return row
    return None

# Helper function to generate verse_id from book, chapter, verse
def make_verse_id(book, chapter, verse):
    """Generate a verse_id in format 'book.chapter.verse' (e.g., '0.1.1' for Gen 1:1)"""
    return f"{book}.{chapter}.{verse}"

# Helper function to get or create a verse_group_id
# temporary until a unique ID system is implemented
def get_or_create_verse_group_id(cursor):
    """Get the next available verse_group_id"""
    cursor.execute('SELECT MAX(verse_group_id) FROM verse_group')
    result = cursor.fetchone()[0]
    return (result + 1) if result is not None else 1

# Helper function to expand verse ranges using the loaded Bible data
def expand_verse_range(start_book, start_chapter, start_verse, end_book, end_chapter, end_verse, bible_data):
    """
    Expand a verse range into all individual verses using the loaded Bible data.
    Returns a list of (book, chapter, verse) tuples.
    
    Args:
        start_book, start_chapter, start_verse: Starting reference (0-indexed book)
        end_book, end_chapter, end_verse: Ending reference (0-indexed book)
        bible_data: Dictionary of Bible data {book_name: [[verses_ch1], [verses_ch2], ...]}
    """
    verses = []
    
    # Get book names list (book_proper_names should be populated by getBibleData)
    if not book_proper_names or start_book >= len(book_proper_names) or end_book >= len(book_proper_names):
        # Fallback: just return start and end if data not available
        raise Exception("Bible data is required to expand verse ranges.")
    
    start_book_name = book_proper_names[start_book]
    end_book_name = book_proper_names[end_book]
    
    # Same book
    if start_book == end_book:
        book_name = start_book_name
        if book_name not in bible_data:
            raise Exception(f"Book '{book_name}' not found in Bible data.")
        
        book_chapters = bible_data[book_name]
        
        # Same chapter
        if start_chapter == end_chapter:
            for v in range(start_verse, end_verse + 1):
                verses.append((start_book, start_chapter, v))
        # Different chapters
        else:
            # First chapter: from start_verse to end of chapter
            if start_chapter - 1 < len(book_chapters):
                max_verse = len(book_chapters[start_chapter - 1])  # chapter is 1-indexed
                for v in range(start_verse, max_verse + 1):
                    verses.append((start_book, start_chapter, v))
            
            # Middle chapters: all verses
            for ch in range(start_chapter + 1, end_chapter):
                if ch - 1 < len(book_chapters):
                    max_verse = len(book_chapters[ch - 1])
                    for v in range(1, max_verse + 1):
                        verses.append((start_book, ch, v))
            
            # Last chapter: from 1 to end_verse
            for v in range(1, end_verse + 1):
                verses.append((end_book, end_chapter, v))
    
    # Different books
    else:
        # First book, starting chapter: from start_verse to end of chapter
        if start_book_name in bible_data:
            book_chapters = bible_data[start_book_name]
            if start_chapter - 1 < len(book_chapters):
                max_verse = len(book_chapters[start_chapter - 1])
                for v in range(start_verse, max_verse + 1):
                    verses.append((start_book, start_chapter, v))
            
            # First book, remaining chapters: all verses
            for ch in range(start_chapter + 1, len(book_chapters) + 1):
                if ch - 1 < len(book_chapters):
                    max_verse = len(book_chapters[ch - 1])
                    for v in range(1, max_verse + 1):
                        verses.append((start_book, ch, v))
        
        # Middle books: all chapters and verses
        for bk in range(start_book + 1, end_book):
            if bk < len(book_proper_names):
                book_name = book_proper_names[bk]
                if book_name in bible_data:
                    book_chapters = bible_data[book_name]
                    for ch_idx, chapter_verses in enumerate(book_chapters):
                        ch = ch_idx + 1  # chapter is 1-indexed
                        max_verse = len(chapter_verses)
                        for v in range(1, max_verse + 1):
                            verses.append((bk, ch, v))
        
        # Last book
        if end_book_name in bible_data:
            book_chapters = bible_data[end_book_name]
            # Chapters before end_chapter: all verses
            for ch in range(1, end_chapter):
                if ch - 1 < len(book_chapters):
                    max_verse = len(book_chapters[ch - 1])
                    for v in range(1, max_verse + 1):
                        verses.append((end_book, ch, v))
            
            # Last chapter: from 1 to end_verse
            for v in range(1, end_verse + 1):
                verses.append((end_book, end_chapter, v))
    
    return verses

# Functions to parse verse references and return a formatted dictionary
def tagVerseEntry(verse_ref, tag_name):
    verses = parseVerseReference(verse_ref)
    return {"start_book": verses['sb'], "end_book": verses['eb'], "start_chapter": verses['sc'], "end_chapter": verses['ec'], "start_verse": verses['sv'], "end_verse": verses['ev'], "tag": tag_name}

def verseNoteEntry(verse_ref, note):
    verses = parseVerseReference(verse_ref)
    return {"start_book": verses['sb'], "end_book": verses['eb'], "start_chapter": verses['sc'], "end_chapter": verses['ec'], "start_verse": verses['sv'], "end_verse": verses['ev'], "note": note}

# I probably don't need this one....
def tagNoteEntry(tag_name, note_data):
    return {"note": note_data, "tag": tag_name}


######################
#STEP 1: READ A BIBLE
######################

# Resulting data structure is a dictionary with ordered list items:
# bibleData = {'book name' : [[v,v,v,v],[v,v,v,v]...]}
# so verses are accessed like this:
# bibleData['Psalm'][19][7]

def getBibleData(bible_file_content):
    # Load JSON data
    data = json.loads(bible_file_content)

    # Initialize the result dictionary
    bibleData = {}

    # Iterate over books
    for book in data["books"]:
        # Extract book name
        book_name = book["name"]
        book_proper_names.append(book_name)
        # Initialize chapters for the book
        book_chapters = []
        
        # Iterate over chapters
        for chapter in book["chapters"]:
            # Extract chapter number
            chapter_number = chapter["chapter"]
            
            # Extract verses for the chapter
            chapter_verses = [verse["text"] for verse in chapter["verses"]]
            
            # Add chapter verses to the book's chapters
            book_chapters.append(chapter_verses)
        
        # Add book chapters to the result dictionary
        bibleData[book_name] = book_chapters

    # Print the result
    return bibleData


######################
#STEP 2: PREP DATABASE
######################

# Resulting database has tables for verses, tags, and notes; and tables to relate verse_tags, verse_notes, and tag_notes.

def makeDB(sqlite_database):
    # Create or connect to the SQLite database
    conn = sqlite3.connect(sqlite_database)
    cursor = conn.cursor()

    # Create the 'verse' table (temporary until a unique verse id system)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verse (
            verse_id TEXT PRIMARY KEY,
            book INTEGER NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            UNIQUE(book, chapter, verse)
        )
    ''')

    # Create the 'tag' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tag (
            tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT NOT NULL,
            UNIQUE(tag)
        )
    ''')

    # Create the 'note' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS note (
            note_id INTEGER PRIMARY KEY AUTOINCREMENT,
            note TEXT NOT NULL
        )
    ''')

    # Create the 'verse_group' table
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS verse_group (
                verse_group_id INTEGER NOT NULL,
                verse_id TEXT NOT NULL,
                PRIMARY KEY (verse_group_id, verse_id),
                FOREIGN KEY (verse_id) REFERENCES verse (verse_id),
                UNIQUE(verse_group_id, verse_id)
            )
    ''')

    # Create the 'verse_group_tag' table to associate verse_groups with tags
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verse_group_tag (
            verse_group_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (verse_group_id, tag_id),
            FOREIGN KEY (verse_group_id) REFERENCES verse_group (verse_group_id),
            FOREIGN KEY (tag_id) REFERENCES tag (tag_id),
            UNIQUE(verse_group_id, tag_id)
        )
    ''')

    # Create the 'verse_group_note' table to associate verse_groups with notes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verse_note (
            verse_group_id INTEGER NOT NULL,
            note_id INTEGER NOT NULL,
            PRIMARY KEY (verse_group_id, note_id),
            FOREIGN KEY (verse_group_id) REFERENCES verse_group (verse_group_id),
            FOREIGN KEY (note_id) REFERENCES note (note_id),
            UNIQUE(verse_group_id, note_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tag_note (
            tag_id INTEGER NOT NULL,
            note_id INTEGER NOT NULL,
            PRIMARY KEY (tag_id, note_id),
            FOREIGN KEY (tag_id) REFERENCES tag (tag_id),
            FOREIGN KEY (note_id) REFERENCES note (note_id),
            UNIQUE(tag_id, note_id)
        )
    ''')

    #tag_tags is for synonyms
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tag_tag (
            tag_1_id INTEGER NOT NULL,
            tag_2_id INTEGER NOT NULL,
            PRIMARY KEY (tag_1_id, tag_2_id),
            FOREIGN KEY (tag_1_id) REFERENCES tag (tag_id),
            FOREIGN KEY (tag_2_id) REFERENCES tag (tag_id),
            UNIQUE(tag_1_id, tag_2_id)
        )
    ''')

    cursor.execute(f"PRAGMA user_version = {CURRENT_DATABASE_VERSION}")

    conn.commit()
    conn.close()
    
    return sqlite_database


######################
#STEP 3: MODIFY DB DATA
######################
def add_verse_tag(database_file, verse_ref, tag_name, bible_data):
    tag_name = tag_name.lower()
    entry = tagVerseEntry(verse_ref, tag_name)
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    # Create a verse_group for this verse range
    verse_group_id = get_or_create_verse_group_id(cursor)

    start_book    = entry["start_book"]
    end_book      = entry["end_book"]
    start_chapter = int(entry["start_chapter"])
    end_chapter   = int(entry["end_chapter"])
    start_verse   = int(entry["start_verse"])
    end_verse     = int(entry["end_verse"])

    if bible_data:
        all_verses = expand_verse_range(start_book, start_chapter, start_verse, end_book, end_chapter, end_verse, bible_data)
    else:
        raise Exception("Bible data is required to expand verse ranges.")

    # Insert all verses in the range
    for book, chapter, verse in all_verses:
        verse_id = make_verse_id(book, chapter, verse)
        cursor.execute('''
            INSERT OR IGNORE INTO verse (verse_id, book, chapter, verse)
            VALUES (?, ?, ?, ?)
        ''', (verse_id, book, chapter, verse))
        cursor.execute('''
            INSERT OR IGNORE INTO verse_group (verse_group_id, verse_id)
            VALUES (?, ?)
        ''', (verse_group_id, verse_id))
    
    # Insert tag into 'tag' table if it doesn't exist
    cursor.execute('''
        INSERT OR IGNORE INTO tag (tag) VALUES (?)
    ''', (entry["tag"],))
    
    cursor.execute('SELECT tag_id FROM tag WHERE tag = ?', (entry["tag"],))
    tag_id = cursor.fetchone()[0]

    # Insert association into 'verse_group_tag' table
    cursor.execute('''
        INSERT OR IGNORE INTO verse_group_tag (verse_group_id, tag_id) VALUES (?, ?)
    ''', (verse_group_id, tag_id))
    
    conn.commit()
    conn.close()

def delete_verse_tag(database_file, verse, tag):
    tag = tag.lower()
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    entry = tagVerseEntry(verse, tag)
    
    # Find verse_group_id(s) that contain this verse range
    start_verse_id = make_verse_id(entry["start_book"], entry["start_chapter"], entry["start_verse"])
    
    # Get tag_id
    cursor.execute('SELECT tag_id FROM tag WHERE tag = ?', (entry["tag"],))
    tag_result = cursor.fetchone()
    
    if not tag_result:
        print(f"Tag '{tag}' not found.")
        conn.close()
        return
        
    tag_id = tag_result[0]

    # Find verse_groups containing this verse
    cursor.execute('''
        SELECT verse_group_id FROM verse_group WHERE verse_id = ?
    ''', (start_verse_id,))
    verse_groups = cursor.fetchall()

    if verse_groups:
        for (verse_group_id,) in verse_groups:
            # Delete the association between the verse_group and tag
            cursor.execute('''
                DELETE FROM verse_group_tag WHERE verse_group_id = ? AND tag_id = ?
            ''', (verse_group_id, tag_id))
            
            # Check if this verse_group has any other tags or notes
            cursor.execute('''
                SELECT COUNT(*) FROM verse_group_tag WHERE verse_group_id = ?
            ''', (verse_group_id,))
            tag_count = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM verse_note WHERE verse_group_id = ?
            ''', (verse_group_id,))
            note_count = cursor.fetchone()[0]
            
            # If no more tags or notes, delete the verse_group
            if tag_count == 0 and note_count == 0:
                cursor.execute('''
                    DELETE FROM verse_group WHERE verse_group_id = ?
                ''', (verse_group_id,))

        # Check if tag is orphaned (no more verse_groups or tag_tag associations)
        cursor.execute('''
            SELECT COUNT(*) FROM verse_group_tag WHERE tag_id = ?
        ''', (tag_id,))
        remaining_verse_tags = cursor.fetchone()[0]

        cursor.execute('''
            SELECT COUNT(*) FROM tag_tag WHERE tag_1_id = ? OR tag_2_id = ?
        ''', (tag_id, tag_id))
        remaining_tag_tags = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM tag_note WHERE tag_id = ?
        ''', (tag_id,))
        remaining_tag_notes = cursor.fetchone()[0]

        if remaining_verse_tags == 0 and remaining_tag_tags == 0 and remaining_tag_notes == 0:
            # Delete the tag if it's orphaned
            cursor.execute('''
                DELETE FROM tag WHERE tag_id = ?
            ''', (tag_id,))

        conn.commit()
    else:
        print(f"Verse '{verse}' not found.")

    conn.close()

def add_tag_tag(database_file, tag1, tag2):
    tag1 = tag1.lower()
    tag2 = tag2.lower()
    
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    
    # Insert both tags into 'tag' table if they don't exist
    cursor.execute('''
        INSERT OR IGNORE INTO tag (tag) VALUES (?)
    ''', (tag1,))

    cursor.execute('SELECT tag_id FROM tag WHERE tag = ?', (tag1,))
    tag1_id = cursor.fetchone()[0]
    
    cursor.execute('''
        INSERT OR IGNORE INTO tag (tag) VALUES (?)
    ''', (tag2,))
    
    cursor.execute('SELECT tag_id FROM tag WHERE tag = ?', (tag2,))
    tag2_id = cursor.fetchone()[0]

    # Insert association into 'tag_tag' table
    cursor.execute('''
        INSERT OR IGNORE INTO tag_tag (tag_1_id, tag_2_id) VALUES (?, ?)
    ''', (tag1_id, tag2_id))
    
    conn.commit()
    conn.close()

def delete_tag_tag(database_file, tag1, tag2):
    tag1 = tag1.lower()
    tag2 = tag2.lower()
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    
    # Get tag IDs
    cursor.execute('SELECT tag_id FROM tag WHERE tag = ?', (tag1,))
    tag1_result = cursor.fetchone()
    cursor.execute('SELECT tag_id FROM tag WHERE tag = ?', (tag2,))
    tag2_result = cursor.fetchone()

    if not tag1_result or not tag2_result:
        print(f"Tag '{tag1}' or tag '{tag2}' not found.")
        conn.close()
        return
        
    tag1_id = tag1_result[0]
    tag2_id = tag2_result[0]

    # Delete both directional associations
    cursor.execute('''
        DELETE FROM tag_tag WHERE tag_1_id = ? AND tag_2_id = ?
    ''', (tag1_id, tag2_id))

    cursor.execute('''
        DELETE FROM tag_tag WHERE tag_1_id = ? AND tag_2_id = ?
    ''', (tag2_id, tag1_id))
    
    # Check if tag1 is orphaned
    cursor.execute('''
        SELECT COUNT(*) FROM verse_group_tag WHERE tag_id = ?
    ''', (tag1_id,))
    remaining_verse_tags1 = cursor.fetchone()[0]

    cursor.execute('''
        SELECT COUNT(*) FROM tag_tag WHERE tag_1_id = ? OR tag_2_id = ?
    ''', (tag1_id, tag1_id))
    remaining_tag_tags1 = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM tag_note WHERE tag_id = ?
    ''', (tag1_id,))
    remaining_tag_notes1 = cursor.fetchone()[0]

    if remaining_verse_tags1 == 0 and remaining_tag_tags1 == 0 and remaining_tag_notes1 == 0:
        cursor.execute('''
            DELETE FROM tag WHERE tag_id = ?
        ''', (tag1_id,))

    # Check if tag2 is orphaned
    cursor.execute('''
        SELECT COUNT(*) FROM verse_group_tag WHERE tag_id = ?
    ''', (tag2_id,))
    remaining_verse_tags2 = cursor.fetchone()[0]

    cursor.execute('''
        SELECT COUNT(*) FROM tag_tag WHERE tag_1_id = ? OR tag_2_id = ?
    ''', (tag2_id, tag2_id))
    remaining_tag_tags2 = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM tag_note WHERE tag_id = ?
    ''', (tag2_id,))
    remaining_tag_notes2 = cursor.fetchone()[0]

    if remaining_verse_tags2 == 0 and remaining_tag_tags2 == 0 and remaining_tag_notes2 == 0:
        cursor.execute('''
            DELETE FROM tag WHERE tag_id = ?
        ''', (tag2_id,))

    conn.commit()
    conn.close()


def add_verse_note(database_file, verse_ref, note, bible_data):
    entry = verseNoteEntry(verse_ref, note)
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    
    # Create a verse_group for this verse range
    verse_group_id = get_or_create_verse_group_id(cursor)
    
    # Insert all verses in the range into 'verse' table and link to verse_group
    start_book = entry["start_book"]
    end_book = entry["end_book"]
    start_chapter = int(entry["start_chapter"])
    end_chapter = int(entry["end_chapter"])
    start_verse = int(entry["start_verse"])
    end_verse = int(entry["end_verse"])

    if bible_data:
        all_verses = expand_verse_range(start_book, start_chapter, start_verse, end_book, end_chapter, end_verse, bible_data)
    else:
        raise Exception("Bible data is required to expand verse ranges.")

    # Insert all verses in the range
    for book, chapter, verse in all_verses:
        verse_id = make_verse_id(book, chapter, verse)
        cursor.execute('''
            INSERT OR IGNORE INTO verse (verse_id, book, chapter, verse)
            VALUES (?, ?, ?, ?)
        ''', (verse_id, book, chapter, verse))
        cursor.execute('''
            INSERT OR IGNORE INTO verse_group (verse_group_id, verse_id)
            VALUES (?, ?)
        ''', (verse_group_id, verse_id))
    
    # Check if a note already exists for this verse_group_id in verse_note
    cursor.execute('SELECT note_id FROM verse_note WHERE verse_group_id = ?', (verse_group_id,))
    existing_note_id = cursor.fetchone()

    if existing_note_id:
        # If a note already exists, update the existing note
        cursor.execute('UPDATE note SET note = ? WHERE note_id = ?', (entry["note"], existing_note_id[0]))
    else:
        # Insert note into 'note' table
        cursor.execute('''
            INSERT INTO note (note) VALUES (?)
        ''', (entry["note"],))
        note_id = cursor.lastrowid

        # Insert association into 'verse_note' table
        cursor.execute('''
            INSERT OR IGNORE INTO verse_note (verse_group_id, note_id) VALUES (?, ?)
        ''', (verse_group_id, note_id))
        
    conn.commit()
    conn.close()

def delete_verse_note(database_file, verse):
    entry = verseNoteEntry(verse, "")
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    
    # Find verse_group_id(s) that contain this verse range
    start_verse_id = make_verse_id(entry["start_book"], entry["start_chapter"], entry["start_verse"])
    
    try:
        # Find verse_groups containing this verse
        cursor.execute('''
            SELECT verse_group_id FROM verse_group WHERE verse_id = ?
        ''', (start_verse_id,))
        verse_groups = cursor.fetchall()

        if not verse_groups:
            print(f"Verse '{verse}' not found.")
            conn.close()
            return

        for (verse_group_id,) in verse_groups:
            # Get note_id for this verse_group
            cursor.execute('SELECT note_id FROM verse_note WHERE verse_group_id = ?', (verse_group_id,))
            note_result = cursor.fetchone()
            
            if note_result:
                note_id = note_result[0]
                
                # Delete the association
                cursor.execute('''
                    DELETE FROM verse_note WHERE verse_group_id = ? AND note_id = ?
                ''', (verse_group_id, note_id))

                # Delete the note itself
                cursor.execute('''
                    DELETE FROM note WHERE note_id = ?
                ''', (note_id,))
                
                # Check if this verse_group has any other tags or notes
                cursor.execute('''
                    SELECT COUNT(*) FROM verse_group_tag WHERE verse_group_id = ?
                ''', (verse_group_id,))
                tag_count = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(*) FROM verse_note WHERE verse_group_id = ?
                ''', (verse_group_id,))
                note_count = cursor.fetchone()[0]
                
                # If no more tags or notes, delete the verse_group
                if tag_count == 0 and note_count == 0:
                    cursor.execute('''
                        DELETE FROM verse_group WHERE verse_group_id = ?
                    ''', (verse_group_id,))

        conn.commit()
        
    except Exception as e:
        print("Can't delete note:", e)
        conn.close()
        return

    conn.close()


def add_tag_note(database_file, tag_name, note):
    tag_name = tag_name.lower()
    entry = tagNoteEntry(tag_name, note)
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    # Insert tag into 'tag' table if it doesn't exist
    cursor.execute('''
        INSERT OR IGNORE INTO tag (tag) VALUES (?)
    ''', (entry["tag"],))

    cursor.execute('SELECT tag_id FROM tag WHERE tag = ?', (entry["tag"],))
    tag_id = cursor.fetchone()[0]

    # Check if a note already exists for this tag_id in tag_note
    cursor.execute('SELECT note_id FROM tag_note WHERE tag_id = ?', (tag_id,))
    existing_note_id = cursor.fetchone()

    if existing_note_id:
        # If a note already exists, update the existing note
        cursor.execute('UPDATE note SET note = ? WHERE note_id = ?', (entry["note"], existing_note_id[0]))
    else:
        # Insert note into 'note' table
        cursor.execute('''
            INSERT INTO note (note) VALUES (?)
        ''', (entry["note"],))

        note_id = cursor.lastrowid

        # Insert association into 'tag_note' table
        cursor.execute('''
            INSERT OR IGNORE INTO tag_note (tag_id, note_id) VALUES (?, ?)
        ''', (tag_id, note_id))
    
    conn.commit()
    conn.close()


def delete_tag_note(database_file, tag):
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    
    # Get tag ID
    cursor.execute('SELECT tag_id FROM tag WHERE tag = ?', (tag,))
    tag_result = cursor.fetchone()
    
    if not tag_result:
        print(f"Tag '{tag}' not found.")
        conn.close()
        return
        
    tag_id = tag_result[0]

    cursor.execute('SELECT note_id FROM tag_note WHERE tag_id = ?', (tag_id,))
    note_result = cursor.fetchone()
    
    if not note_result:
        print(f"No note found for tag '{tag}'.")
        conn.close()
        return
        
    note_id = note_result[0]

    # Delete the association
    cursor.execute('''
        DELETE FROM tag_note WHERE tag_id = ? AND note_id = ?
    ''', (tag_id, note_id))

    # Delete the note itself
    cursor.execute('''
        DELETE FROM note WHERE note_id = ?
    ''', (note_id,))

    conn.commit()
    conn.close()



######################
#STEP 4: READ THE DB
######################

def get_db_stuff(database_file, x_type, y_type, y_value):
    # one-size-fits-all to get all X's in relation to Y.
    # for example, if X is note, and Y is verse: select all notes for that verse.
    # tolerable xy_type values are.... "note", "verse", "tag"

    if y_type == "tag":
        y_value = y_value.lower()
    
    #let's just double check that I didn't make a programming error.....
    if x_type not in ["verse", "tag", "note"] or y_type not in ["verse", "tag", "note"]:
        print("bad parameters in get_db_stuff. types must be verse, tag, or note.")
        return None

    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    result = []

    if y_type == "verse": 
        # Get tags or notes for a verse
        y_value_parsed = parseVerseReference(y_value)
        verse_id = make_verse_id(y_value_parsed["sb"], y_value_parsed["sc"], y_value_parsed["sv"])
        
        if x_type == "tag":
            query_string = '''
                SELECT t.*
                FROM tag t
                JOIN verse_group_tag vgt ON t.tag_id = vgt.tag_id
                JOIN verse_group vg ON vgt.verse_group_id = vg.verse_group_id
                WHERE vg.verse_id = ?
            '''
            cursor.execute(query_string, (verse_id,))
        elif x_type == "note":
            query_string = '''
                SELECT n.*
                FROM note n
                JOIN verse_note vn ON n.note_id = vn.note_id
                JOIN verse_group vg ON vn.verse_group_id = vg.verse_group_id
                WHERE vg.verse_id = ?
            '''
            cursor.execute(query_string, (verse_id,))
            
    elif x_type == y_type == "tag":   
        # Get related tags (tag_tag)     
        query_string = '''
            SELECT t2.*
            FROM tag as t1
            JOIN tag_tag AS tt ON ((t1.tag_id = tt.tag_1_id AND t2.tag_id = tt.tag_2_id)
                OR (t1.tag_id = tt.tag_2_id AND t2.tag_id = tt.tag_1_id))
            JOIN tag AS t2 ON (t2.tag_id = tt.tag_1_id OR t2.tag_id = tt.tag_2_id)
            WHERE t1.tag = ? AND t2.tag != ?
        '''
        cursor.execute(query_string, (y_value, y_value))
        
    elif y_type == "tag":
        # Get verses or notes for a tag
        if x_type == "verse":
            # Get all verse_groups that have this tag
            query_string = '''
                SELECT DISTINCT vg.verse_group_id
                FROM verse_group vg
                JOIN verse_group_tag vgt ON vg.verse_group_id = vgt.verse_group_id
                JOIN tag t ON vgt.tag_id = t.tag_id
                WHERE t.tag = ?
            '''
            cursor.execute(query_string, (y_value,))
            verse_group_ids = [row[0] for row in cursor.fetchall()]
            
            # For each verse_group, get the range of verses
            for vg_id in verse_group_ids:
                cursor.execute('''
                    SELECT v.book, v.chapter, v.verse
                    FROM verse v
                    JOIN verse_group vg ON v.verse_id = vg.verse_id
                    WHERE vg.verse_group_id = ?
                    ORDER BY v.book, v.chapter, v.verse
                ''', (vg_id,))
                verses_in_group = cursor.fetchall()
                
                if verses_in_group:
                    first = verses_in_group[0]
                    last = verses_in_group[-1]
                    result.append({
                        'verse_group_id': vg_id,
                        'start_book': first[0],
                        'start_chapter': first[1],
                        'start_verse': first[2],
                        'end_book': last[0],
                        'end_chapter': last[1],
                        'end_verse': last[2]
                    })
            
            conn.close()
            return result
        elif x_type == "note":
            # Get note for this tag
            query_string = '''
                SELECT n.*
                FROM note n
                JOIN tag_note tn ON n.note_id = tn.note_id
                JOIN tag t ON tn.tag_id = t.tag_id
                WHERE t.tag = ?
            '''
            cursor.execute(query_string, (y_value,))
    else:
        # Other cases not yet implemented
        print(f"get_db_stuff: combination x_type={x_type}, y_type={y_type} not yet implemented")
        conn.close()
        return []

    column_names = [description[0] for description in cursor.description]
    rows = cursor.fetchall()

    for row in rows:
        row_dict = dict(zip(column_names, row))
        result.append(row_dict)

    conn.close()
    return result

def get_tag_list(database_file):
    # returns a dictionary of all the tags in the database
    if database_file is None:
        return []
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tag")

    column_names = [description[0] for description in cursor.description]

    rows = cursor.fetchall()

    result = []
    for row in rows:
        row_dict = dict(zip(column_names, row))
        result.append(row_dict)

    # Close the connection
    conn.close()
    
    return result

def tag_exists(database_file, tag):
    # Return True if tag exists, otherwise False
    if database_file is None:
        return False

    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    query = f"SELECT EXISTS(SELECT 1 FROM tag WHERE tag = ? LIMIT 1)"
    cursor.execute(query, (tag,))
    tag_exists = cursor.fetchone()[0]  # fetchone returns a tuple, get the first element

    conn.close()

    return bool(tag_exists)

def find_note_tag_chapters(database_file):
    #return a list of book/chapter, formatted like the Treeview tags, for every chapter that has notes and tags.
    if database_file is None:
        return []
    
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    #get all verses which have tags or notes via verse_groups
    cursor.execute('''
        SELECT DISTINCT 
            v.book AS book,
            v.chapter AS chapter
        FROM verse v
        JOIN verse_group vg ON v.verse_id = vg.verse_id
        LEFT JOIN verse_group_tag vgt ON vg.verse_group_id = vgt.verse_group_id
        LEFT JOIN verse_note vn ON vg.verse_group_id = vn.verse_group_id
        WHERE vgt.tag_id IS NOT NULL 
           OR vn.note_id IS NOT NULL
        ORDER BY book, chapter;
        ''',)

    column_names = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    #zip them into a dictionary for easy use
    tagged_chapters = []
    for row in rows:
        bc = "/"+book_proper_names[int(row[0])] + '/Ch ' + str(row[1])
        tagged_chapters.append(bc)

    return tagged_chapters

def get_all_verses_with_notes(database_file):
    #returns a list of dictionary entries:
    # [ {"verse":string_verse_ref, "note", string_note},...]

    if database_file is None:
        return []

    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    # Get all verse_groups that have notes
    cursor.execute("""
            SELECT DISTINCT vg.verse_group_id
            FROM verse_group vg
            JOIN verse_note vn ON vg.verse_group_id = vn.verse_group_id
        """)

    verse_group_ids = [row[0] for row in cursor.fetchall()]
    
    verses_notes = []
    for vg_id in verse_group_ids:
        # Get all verses in this verse_group
        cursor.execute("""
            SELECT v.book, v.chapter, v.verse
            FROM verse v
            JOIN verse_group vg ON v.verse_id = vg.verse_id
            WHERE vg.verse_group_id = ?
            ORDER BY v.book, v.chapter, v.verse
        """, (vg_id,))
        
        verses_in_group = cursor.fetchall()
        if verses_in_group:
            # Build a verse range from first to last verse
            first = verses_in_group[0]
            last = verses_in_group[-1]
            verse_dict = {
                'verse_group_id': vg_id,
                'start_book': first[0],
                'start_chapter': first[1],
                'start_verse': first[2],
                'end_book': last[0],
                'end_chapter': last[1],
                'end_verse': last[2]
            }
            verse_ref = normalize_vref(verse_dict)
            notes = get_db_stuff(database_file, "note", "verse", verse_ref)
            if notes:
                verses_notes.append({"verse": verse_ref, "note": notes[0]['note']})
    
    conn.close()
    return verses_notes



def find_note_tag_verses(database_file, book, chapter):
    # for a given book and chapter, get all verse ranges that have tags and/or notes.
    # this function is used to make the little indicator lines to the left of the verses in the UI.
    if database_file is None:
        return []

    book = getBookIndex(qualifyBook(book))
    if book == -1:
        return None
    
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    # Get all verse_groups that have tags
    cursor.execute('''
        SELECT DISTINCT vg.verse_group_id
        FROM verse v
        JOIN verse_group vg ON v.verse_id = vg.verse_id
        WHERE v.book = ? AND v.chapter = ?
            AND vg.verse_group_id IN (
                SELECT verse_group_id FROM verse_group_tag
            )
        ''', (book, chapter))
    tagged_group_ids = set(row[0] for row in cursor.fetchall())

    # Get all verse_groups that have notes
    cursor.execute('''
        SELECT DISTINCT vg.verse_group_id
        FROM verse v
        JOIN verse_group vg ON v.verse_id = vg.verse_id
        WHERE v.book = ? AND v.chapter = ?
            AND vg.verse_group_id IN (
                SELECT verse_group_id FROM verse_note
            )
        ''', (book, chapter))
    noted_group_ids = set(row[0] for row in cursor.fetchall())

    # Combine all unique verse_group_ids
    all_group_ids = tagged_group_ids | noted_group_ids
    
    combined_verses = []
    for verse_group_id in all_group_ids:
        # Get all verses in this verse_group to determine the range
        cursor.execute('''
            SELECT v.book, v.chapter, v.verse
            FROM verse v
            JOIN verse_group vg ON v.verse_id = vg.verse_id
            WHERE vg.verse_group_id = ?
            ORDER BY v.book, v.chapter, v.verse
        ''', (verse_group_id,))
        
        verses_in_group = cursor.fetchall()
        if verses_in_group:
            first = verses_in_group[0]
            last = verses_in_group[-1]
            
            # Determine the type
            if verse_group_id in tagged_group_ids and verse_group_id in noted_group_ids:
                type_str = "both"
            elif verse_group_id in tagged_group_ids:
                type_str = "tag"
            else:
                type_str = "note"
            
            # Build result in old format for compatibility
            row_dict = {
                'verse_group_id': verse_group_id,
                'start_book': first[0],
                'start_chapter': first[1],
                'start_verse': first[2],
                'end_book': last[0],
                'end_chapter': last[1],
                'end_verse': last[2],
                'type': type_str
            }
            combined_verses.append(row_dict)
    
    conn.close()
    return combined_verses

def get_tags_like(database_file, partial_tag):
    # returns a dictionary of all the tags in the database that are like the partial_tag
    if database_file is None:
        return []
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    partial_tag = partial_tag.lower() #all my tags are lowercase
    
    cursor.execute("SELECT tag FROM tag WHERE tag LIKE ?;",("%" + partial_tag + "%",))

    rows = cursor.fetchall()

    # Close the connection
    conn.close()

    #return a list of tag names
    return rows
