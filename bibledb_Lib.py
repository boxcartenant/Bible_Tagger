import json
import sqlite3


####  HOW TO USE:
# first call getBibleData on a valid bible json
# if you're using a new DB, then call makeDB with a path
# elif you're using an existing DB, then dwai
# use add_verse_tag, add_verse_note, and add_tag_note to add data to the DB


BIBLE_FILE_PATH = "asv.json"
SQLITE_DATABASE = "bible_database.sqlite"

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

def merge_dbs(current_db_path, new_db_path):
    print("Merge DBs functionality not yet implemented")
    pass

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

    # Create the 'verses' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_book INTEGER NOT NULL,
            start_chapter INTEGER NOT NULL,
            start_verse INTEGER NOT NULL,
            end_book INTEGER NOT NULL,
            end_chapter INTEGER NOT NULL,
            end_verse INTEGER NOT NULL,
            UNIQUE(start_book,start_chapter,start_verse,end_book,end_chapter,end_verse)
        )
    ''')

    # Create the 'tags' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT NOT NULL,
            UNIQUE(tag)
        )
    ''')

    # Create the 'notes' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note TEXT NOT NULL
        )
    ''')

    # Create the 'verse_tags' table to associate verses with tags
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verse_tags (
            verse_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (verse_id, tag_id),
            FOREIGN KEY (verse_id) REFERENCES verses (id),
            FOREIGN KEY (tag_id) REFERENCES tags (id),
            UNIQUE(verse_id, tag_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verse_notes (
            verse_id INTEGER,
            note_id INTEGER,
            PRIMARY KEY (verse_id, note_id),
            FOREIGN KEY (verse_id) REFERENCES verses (id),
            FOREIGN KEY (note_id) REFERENCES notes (id),
            UNIQUE(verse_id, note_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tag_notes (
            tag_id INTEGER,
            note_id INTEGER,
            PRIMARY KEY (tag_id, note_id),
            FOREIGN KEY (tag_id) REFERENCES tags (id),
            FOREIGN KEY (note_id) REFERENCES notes (id),
            UNIQUE(tag_id, note_id)
        )
    ''')

    #tag_tags is for synonyms
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tag_tags (
            tag1_id INTEGER,
            tag2_id INTEGER,
            PRIMARY KEY (tag1_id, tag2_id),
            FOREIGN KEY (tag1_id) REFERENCES tags (id),
            FOREIGN KEY (tag2_id) REFERENCES tags (id),
            UNIQUE(tag1_id, tag2_id)
        )
    ''')


    conn.commit()
    conn.close()
    
    return sqlite_database


######################
#STEP 3: MODIFY DB DATA
######################
def add_verse_tag(database_file, verse_ref, tag_name):
    tag_name = tag_name.lower()
    entry = tagVerseEntry(verse_ref, tag_name)
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    # possible usage: add_verse_tag(cursor, tagVerseEntry("gen 1:1", "creation"))
    
    # Insert verse into 'verses' table
    cursor.execute('''
        INSERT OR IGNORE INTO verses (start_book, end_book, start_chapter, end_chapter, start_verse, end_verse)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (entry["start_book"],entry["end_book"],entry["start_chapter"],entry["end_chapter"],entry["start_verse"],entry["end_verse"]))

    # Get verse and tag IDs
    cursor.execute('SELECT id FROM verses WHERE start_book = ? AND end_book = ? AND start_chapter = ? AND end_chapter = ? AND start_verse = ? AND end_verse = ?',
                   (entry["start_book"],entry["end_book"],entry["start_chapter"],entry["end_chapter"],entry["start_verse"],entry["end_verse"]))
    verse_id = cursor.fetchone()[0] #cursor.lastrowid
    
    # Insert tag into 'tags' table if it doesn't exist
    cursor.execute('''
        INSERT OR IGNORE INTO tags (tag) VALUES (?)
    ''', (entry["tag"],))
    
    cursor.execute('SELECT id FROM tags WHERE tag = ?', (entry["tag"],))
    tag_id = cursor.fetchone()[0]

    # Insert association into 'verse_tags' table
    cursor.execute('''
        INSERT OR IGNORE INTO verse_tags (verse_id, tag_id) VALUES (?, ?)
    ''', (verse_id, tag_id))
    
    conn.commit()
    conn.close()

def delete_verse_tag(database_file, verse, tag):
    tag = tag.lower()
    # Create or connect to the SQLite database
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    entry = tagVerseEntry(verse, tag)
    
    # Get verse ID based on the provided verse reference
    cursor.execute('''
        SELECT id FROM verses WHERE start_book = ? AND end_book = ? AND start_chapter = ? AND end_chapter = ? AND start_verse = ? AND end_verse = ?
        ''',(entry["start_book"],entry["end_book"],entry["start_chapter"],entry["end_chapter"],entry["start_verse"],entry["end_verse"]))
    verse_id = cursor.fetchone()[0]

    cursor.execute('SELECT id FROM tags WHERE tag = ?', (entry["tag"],))
    tag_id = cursor.fetchone()[0]

    # Check if the verse exists
    if verse_id and tag_id:

        # Delete the association between the tag and verse in verse_tags
        cursor.execute('''
            DELETE FROM verse_tags WHERE verse_id = ? AND tag_id = ?
        ''', (verse_id, tag_id))

        cursor.execute('''
            SELECT COUNT(*) FROM verse_tags WHERE tag_id = ?
        ''', (tag_id,))

        remaining_associations = cursor.fetchone()[0]

        cursor.execute('''
            SELECT COUNT(*) FROM tag_tags WHERE tag1_id = ? or tag2_id = ?
        ''', (tag_id,tag_id))

        remaining_associations += cursor.fetchone()[0]

        if remaining_associations == 0:
            # Delete the tag from tags if it's orphaned
            cursor.execute('''
                DELETE FROM tags WHERE id = ?
            ''', (tag_id,))

        # Commit the changes
        conn.commit()
        #print(f"Association between verse '{verse}' and tag '{tag}' deleted.")

    else:
        print(f"Verse '{verse}' or tag '{tag}' not found.")

    # Close the connection
    conn.close()

def add_tag_tag(database_file, tag1, tag2):
    tag1 = tag1.lower()
    tag2 = tag2.lower()
    
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    # possible usage: add_verse_tag(cursor, tagVerseEntry("gen 1:1", "creation"))
    
    # Insert verse into 'verses' table
    cursor.execute('''
        INSERT OR IGNORE INTO tags (tag) VALUES (?)
    ''', (tag1,))

    # Get tag ID
    cursor.execute('SELECT id FROM tags WHERE tag = ?', (tag1,))
    tag1_id = cursor.fetchone()[0]
    
    # Insert tag into 'tags' table if it doesn't exist
    cursor.execute('''
        INSERT OR IGNORE INTO tags (tag) VALUES (?)
    ''', (tag2,))
    
    cursor.execute('SELECT id FROM tags WHERE tag = ?', (tag2,))
    tag2_id = cursor.fetchone()[0]

    # Insert association into 'verse_tags' table
    cursor.execute('''
        INSERT OR IGNORE INTO tag_tags (tag1_id, tag2_id) VALUES (?, ?)
    ''', (tag1_id, tag2_id))
    
    conn.commit()
    conn.close()

def delete_tag_tag(database_file, tag1, tag2):
    tag1 = tag1.lower()
    tag2 = tag2.lower()
    # Create or connect to the SQLite database
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    
    # Get tag ID
    cursor.execute('SELECT id FROM tags WHERE tag = ?', (tag1,))
    tag1_id = cursor.fetchone()[0]

    cursor.execute('SELECT id FROM tags WHERE tag = ?', (tag2,))
    tag2_id = cursor.fetchone()[0]

    # Check if the verse exists
    if tag1_id and tag2_id:

        # Delete the association between the tag and verse in verse_tags
        cursor.execute('''
            DELETE FROM tag_tags WHERE tag1_id = ? AND tag2_id = ?
        ''', (tag1_id, tag2_id))

        cursor.execute('''
            DELETE FROM tag_tags WHERE tag1_id = ? AND tag2_id = ?
        ''', (tag2_id, tag1_id))
        
        cursor.execute('''
            SELECT COUNT(*) FROM verse_tags WHERE tag_id = ?
        ''', (tag1_id,))
        remaining_associations1 = cursor.fetchone()[0]

        cursor.execute('''
            SELECT COUNT(*) FROM tag_tags WHERE tag1_id = ? or tag2_id = ?
        ''', (tag1_id,tag1_id))
        remaining_associations1 += cursor.fetchone()[0]

        if remaining_associations1 == 0:
            # Delete the tag from tags if it's orphaned
            cursor.execute('''
                DELETE FROM tags WHERE id = ?
            ''', (tag1_id,))


        cursor.execute('''
            SELECT COUNT(*) FROM verse_tags WHERE tag_id = ?
        ''', (tag2_id,))
        remaining_associations2 = cursor.fetchone()[0]

        cursor.execute('''
            SELECT COUNT(*) FROM tag_tags WHERE tag1_id = ? or tag2_id = ?
        ''', (tag2_id,tag2_id))
        remaining_associations2 += cursor.fetchone()[0]

        if remaining_associations2 == 0:
            # Delete the tag from tags if it's orphaned
            cursor.execute('''
                DELETE FROM tags WHERE id = ?
            ''', (tag2_id,))

        # Commit the changes
        conn.commit()
        #print(f"Association between verse '{verse}' and tag '{tag}' deleted.")

    else:
        print(f"tag '{tag1}' or tag '{tag2}' not found.")

    # Close the connection
    conn.close()


def add_verse_note(database_file, verse_ref, note):
    entry = verseNoteEntry(verse_ref, note)
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    
    # Insert verse into 'verses' table
    cursor.execute('''
        INSERT OR IGNORE INTO verses (start_book, end_book, start_chapter, end_chapter, start_verse, end_verse)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (entry["start_book"],entry["end_book"],entry["start_chapter"],entry["end_chapter"],entry["start_verse"],entry["end_verse"]))

    # Get verse and note IDs      
    cursor.execute('SELECT id FROM verses WHERE start_book = ? AND end_book = ? AND start_chapter = ? AND end_chapter = ? AND start_verse = ? AND end_verse = ?',
                   (entry["start_book"],entry["end_book"],entry["start_chapter"],entry["end_chapter"],entry["start_verse"],entry["end_verse"]))
    verse_id = cursor.fetchone()[0] #cursor.lastrowid
    
    # Check if a note already exists for this verse_id in verse_notes
    cursor.execute('SELECT note_id FROM verse_notes WHERE verse_id = ?', (verse_id,))
    existing_note_id = cursor.fetchone()

    if existing_note_id:
        # If a note already exists, update the existing note
        cursor.execute('UPDATE notes SET note = ? WHERE id = ?', (entry["note"], existing_note_id[0]))
        note_id = existing_note_id[0]
    else:
        # Insert note into 'notes' table if it doesn't exist
        cursor.execute('''
            INSERT OR REPLACE INTO notes (note) VALUES (?)
        ''', (entry["note"],))

        note_id = cursor.lastrowid

        # Insert association into 'verse_notes' table
        cursor.execute('''
            INSERT OR IGNORE INTO verse_notes (verse_id, note_id) VALUES (?, ?)
        ''', (verse_id, note_id))
    conn.commit()
    conn.close()

def delete_verse_note(database_file, verse):
    entry = verseNoteEntry(verse, "")
    # Create or connect to the SQLite database
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    
    # Get verse ID based on the provided verse reference
    try:
        cursor.execute('''
            SELECT id FROM verses WHERE start_book = ? AND end_book = ? AND start_chapter = ? AND end_chapter = ? AND start_verse = ? AND end_verse = ?
            ''',(entry["start_book"],entry["end_book"],entry["start_chapter"],entry["end_chapter"],entry["start_verse"],entry["end_verse"]))
        verse_id = cursor.fetchone()[0]
        #print("verse id:",verse_id)
        
        cursor.execute('SELECT note_id FROM verse_notes WHERE verse_id = ?', (verse_id,))
        note_id = cursor.fetchone()[0]
        #print("note id:",note_id)
    except Exception as e:
        print("Can't delete note:",e)
        conn.close()
        return

    # Check if the verse exists
    if verse_id and note_id:

        # Delete the association between the tag and verse in verse_tags
        cursor.execute('''
            DELETE FROM verse_notes WHERE verse_id = ? AND note_id = ?
        ''', (verse_id, note_id))

        cursor.execute('''
            DELETE FROM notes WHERE id = ?
        ''', (note_id,))

        # Commit the changes
        conn.commit()
        #print(f"Association between verse '{verse}' and tag '{tag}' deleted.")

    else:
        print(f"Verse id '{verse_id}' or note id '{note_id}' not found.")

    # Close the connection
    conn.close()


def add_tag_note(database_file, tag_name, note):
    tag_name = tag_name.lower()
    entry = tagNoteEntry(tag_name, note)
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    # Insert tag into 'tags' table if it doesn't exist
    cursor.execute('''
        INSERT OR IGNORE INTO tags (tag) VALUES (?)
    ''', (entry["tag"],))

    cursor.execute('SELECT id FROM tags WHERE tag = ?', (entry["tag"],))
    tag_id = cursor.fetchone()[0]

    # Check if a note already exists for this tag_id in tag_notes
    cursor.execute('SELECT note_id FROM tag_notes WHERE tag_id = ?', (tag_id,))
    existing_note_id = cursor.fetchone()


    if existing_note_id:
        # If a note already exists, update the existing note
        cursor.execute('UPDATE notes SET note = ? WHERE id = ?', (entry["note"], existing_note_id[0]))
        note_id = existing_note_id[0]
    else:
        # Insert note into 'notes' table if it doesn't exist
        cursor.execute('''
            INSERT OR REPLACE INTO notes (note) VALUES (?)
        ''', (entry["note"],))

        note_id = cursor.lastrowid

        # Insert association into 'tag_notes' table
        cursor.execute('''
            INSERT OR IGNORE INTO tag_notes (tag_id, note_id) VALUES (?, ?)
        ''', (tag_id, note_id))
    
    conn.commit()
    conn.close()


def delete_tag_note(database_file, tag):
    # Create or connect to the SQLite database
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    
    # Get verse ID based on the provided verse reference
    cursor.execute('SELECT id FROM tags WHERE tag = ?', (tag,))
    tag_id = cursor.fetchone()[0]

    cursor.execute('SELECT note_id FROM tag_notes WHERE tag_id = ?', (tag_id,))
    note_id = cursor.fetchone()[0]

    # Check if the verse exists
    if tag_id and note_id:

        # Delete the association between the tag and verse in verse_tags
        cursor.execute('''
            DELETE FROM tag_notes WHERE tag_id = ? AND note_id = ?
        ''', (tag_id, note_id))

        cursor.execute('''
            DELETE FROM notes WHERE id = ?
        ''', (note_id,))

        # Commit the changes
        conn.commit()
        #print(f"Association between verse '{verse}' and tag '{tag}' deleted.")

    else:
        print(f"tag id '{tag_id}' or note id '{note_id}' not found.")

    # Close the connection
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

    #The tables are...
    # notes
    # verses
    # tags
    # verse_tags
    # verse_notes
    # tag_tags
    # tag_notes
    #There can be more than one verse per tag, or tag per verse, so we have to be flexible here:
    if (x_type == "verse") or (x_type == "tag") and not (y_type == "verse"):
        type1 = x_type
        type2 = y_type
    else:
        type1 = y_type
        type2 = x_type

    if y_type == "verse": #verse_tags or verse_notes
        y_value = parseVerseReference(y_value)
        query_string = f'''
            SELECT {x_type}s.*
            FROM {x_type}s
            JOIN {type1}_{type2}s ON {x_type}s.id = {type1}_{type2}s.{x_type}_id
            JOIN {y_type}s ON {type1}_{type2}s.{y_type}_id = {y_type}s.id
            WHERE {y_type}s.start_book = ? AND {y_type}s.end_book = ? AND {y_type}s.start_chapter = ? AND {y_type}s.end_chapter = ? AND {y_type}s.start_verse = ? AND {y_type}s.end_verse = ?
        '''
        cursor.execute(query_string, (y_value["sb"],y_value["eb"],y_value["sc"],y_value["ec"],y_value["sv"],y_value["ev"]))
    elif x_type == y_type == "tag":   #tag_tags     
        query_string = '''SELECT t2.*
            FROM tags as t1
            JOIN tag_tags AS tt ON ((t1.id = tt.tag1_id) AND (t1.tag = ?) AND (t2.id = tt.tag2_id))
                OR ((t1.id = tt.tag2_id) AND (t1.tag = ?) AND (t2.id = tt.tag1_id))
            JOIN tags AS t2 ON t2.id = tt.tag1_id OR t2.id = tt.tag2_id
            WHERE t2.tag  != ?
            '''
        cursor.execute(query_string, (y_value,y_value,y_value))
    else: #tag_notes
    #build the query string using x and y types.
        query_string = f'''
            SELECT {x_type}s.*
            FROM {x_type}s
            JOIN {type1}_{type2}s ON {x_type}s.id = {type1}_{type2}s.{x_type}_id
            JOIN {y_type}s ON {type1}_{type2}s.{y_type}_id = {y_type}s.id
            WHERE {y_type}s.{y_type} = ?
        '''
        # Execute the query with the provided parameters
        cursor.execute(query_string, (y_value,))

    column_names = [description[0] for description in cursor.description]
    # Fetch all rows
    rows = cursor.fetchall()

    result = []
    for row in rows:
        row_dict = dict(zip(column_names, row))
        result.append(row_dict)

    # Close the connection
    conn.close()

    #returns a list like.....
    #for verses:
    #[{'id': 1638, 'start_book': 2, 'start_chapter': 1, 'start_verse': 2, 'end_book': 2, 'end_chapter': 1, 'end_verse': 9}, ...
    #for tags:
    #[{'id': 1659, 'tag': 'herd'}, {'id': 440, 'tag': 'heifer'}, ...]
    
    return result

def get_tag_list(database_file):
    # returns a dictionary of all the tags in the database
    if database_file is None:
        return []
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    cursor.execute("select * from tags")

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

    query = f"SELECT EXISTS(SELECT 1 FROM tags WHERE tag = ? LIMIT 1)"
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

    #get all verse ranges which have tags
    cursor.execute('''
        SELECT DISTINCT 
            v.start_book AS book,
            v.start_chapter AS chapter
        FROM verses v
        LEFT JOIN verse_tags vt ON v.id = vt.verse_id
        LEFT JOIN verse_notes vn ON v.id = vn.verse_id
        WHERE vt.tag_id IS NOT NULL 
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

    cursor.execute("""
            SELECT DISTINCT v.id, v.start_book, v.start_chapter, v.start_verse, 
                            v.end_book, v.end_chapter, v.end_verse
            FROM verses v
            JOIN verse_notes vn ON v.id = vn.verse_id
        """)

    column_names = [description[0] for description in cursor.description]
    # Fetch all rows
    rows = cursor.fetchall()

    verses = []
    for row in rows:
        row_dict = dict(zip(column_names, row))
        verses.append(row_dict)
        
    #verses = cursor.fetchall()
    verse_refs = [normalize_vref(v) for v in verses]
    verses_notes = [{"verse":v,"note":get_db_stuff(database_file, "note","verse",v)[0]['note']} for v in verse_refs]
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

    #get all verse ranges which have tags
    cursor.execute('''
        SELECT *
        FROM verses
        WHERE (
            (
                (start_book = ? AND start_chapter <= ?) OR
                (start_book < ?)
            ) AND (
                (end_book = ? AND end_chapter >= ?) OR
                (end_book > ?)
            ) AND id IN (SELECT verse_id FROM verse_tags)
        )
        ''', (book, chapter, book, book, chapter, book))

    column_names = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    #zip them into a dictionary for easy use
    tagged_verses = []
    for row in rows:
        row_dict = dict(zip(column_names, row))
        tagged_verses.append(row_dict)

    #get all verse ranges which have notes
    cursor.execute('''
        SELECT *
        FROM verses
        WHERE (
            (
                (start_book = ? AND start_chapter <= ?) OR
                (start_book < ?)
            ) AND (
                (end_book = ? AND end_chapter >= ?) OR
                (end_book > ?)
            ) AND id IN (SELECT verse_id FROM verse_notes)
        )
        ''', (book, chapter, book, book, chapter, book))

    column_names = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    #zip them into a dictionary for easy use
    noted_verses = []
    for row in rows:
        row_dict = dict(zip(column_names, row))
        noted_verses.append(row_dict)

    # Create sets of unique IDs from each list of dictionaries
    tagged_ids = set(verse["id"] for verse in tagged_verses)
    noted_ids = set(verse["id"] for verse in noted_verses)

    # Combine the dictionaries
    total_verses = set([verse["id"] for verse in tagged_verses] + [verse["id"] for verse in noted_verses])
    
    combined_verses = []
    for verse_id in total_verses:
        if verse_id in tagged_ids and verse_id in noted_ids:
            row = get_row_by_column(tagged_verses, verse_id, "id")
            row["type"] = "both"
            combined_verses.append(row)
        elif verse_id in tagged_ids:
            row = get_row_by_column(tagged_verses, verse_id, "id")
            row["type"] = "tag"
            combined_verses.append(row)
        elif verse_id in noted_ids:
            row = get_row_by_column(noted_verses, verse_id, "id")
            row["type"] = "note"
            combined_verses.append(row)
    
    

    return combined_verses

def get_tags_like(database_file, partial_tag):
    # returns a dictionary of all the tags in the database that are like the partial_tag
    if database_file is None:
        return []
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    partial_tag = partial_tag.lower() #all my tags are lowercase
    
    cursor.execute("select tag from tags where tag like ?;",("%" + partial_tag + "%",))

    rows = cursor.fetchall()

    # Close the connection
    conn.close()

    #return a list of tag names
    return rows
