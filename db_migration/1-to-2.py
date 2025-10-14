"""
Database Schema Migration Script: Version 1 to Version 2
Migrates Bible Tagger databases from schema v1 to schema v2.

CHANGES FROM V1 TO V2:
- Remove 'note' table (was: note_id INTEGER PRIMARY KEY AUTOINCREMENT, note TEXT)
- Remove 'verse_group_note' junction table
- Remove 'tag_note' junction table
- Remove separate 'verse' table
- Add 'note' column (TEXT) to 'tag' table
- Add 'note' column (TEXT) to 'verse_group' table
- Restructure verse_group table: 
  - OLD: verse_group(verse_group_id INT, verse_id TEXT) - was a "multi-row" table
  - NEW: verse_group(verse_group_id INTEGER PRIMARY KEY AUTOINCREMENT, note TEXT)
- Add 'verse_group_verse' junction table (verse_group_id, verse_id, book, chapter, verse)
- Update tag_tag table to have CHECK constraint: tag_1_id < tag_2_id
- Add CASCADE DELETE to foreign keys

OLD SCHEMA (v1):
- verse (verse_id TEXT PRIMARY KEY, book, chapter, verse)
- verse_group (verse_group_id INT, verse_id TEXT) - multiple rows per group!
- tag (tag_id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT UNIQUE)
- note (note_id INTEGER PRIMARY KEY AUTOINCREMENT, note TEXT)
- verse_group_tag (verse_group_id INT, tag_id INT)
- verse_group_note (verse_group_id INT, note_id INT)
- tag_note (tag_id INT, note_id INT)
- tag_tag (tag_1_id INT, tag_2_id INT)

NEW SCHEMA (v2):
- verse_group (verse_group_id INTEGER PRIMARY KEY AUTOINCREMENT, note TEXT)
- verse_group_verse (verse_group_id, verse_id, book, chapter, verse) - junction table with CASCADE
- tag (tag_id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT NOT NULL UNIQUE, note TEXT)
- verse_group_tag (verse_group_id INT, tag_id INT) - with CASCADE
- tag_tag (tag_1_id INT, tag_2_id INT, CHECK (tag_1_id < tag_2_id)) - with CASCADE

Usage:
    python 1-to-2.py <database_path> [--no-backup]
"""

import sqlite3
import os
import sys
import shutil
import argparse
from datetime import datetime


def backup_database(db_path):
    """
    Create a backup of the database with _backup.bdb suffix.
    """
    # Remove extension and add _backup.bdb
    base_path = os.path.splitext(db_path)[0]
    backup_path = f"{base_path}_backup.bdb"
    
    print(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print(f"✓ Backup created")
    
    return backup_path


def migrate_database(old_db_path, create_backup=True):
    """
    Main migration function.
    Migrates a Bible Tagger database from version 1 to version 2.
    
    Args:
        old_db_path: Path to the database file to migrate
        create_backup: Whether to create a backup (default True)
    
    Returns:
        True if migration successful, False otherwise
    """
    print("\n" + "=" * 60)
    print("Bible Tagger Database Migration: Version 1 -> 2")
    print("=" * 60)
    print(f"Database: {old_db_path}\n")
    
    # Check if database exists
    if not os.path.exists(old_db_path):
        print(f"✗ Error: Database file not found: {old_db_path}")
        return False
    
    # Create backup if requested
    backup_path = None
    if create_backup:
        try:
            backup_path = backup_database(old_db_path)
        except Exception as e:
            print(f"✗ Error creating backup: {e}")
            return False
    else:
        print("⚠ Skipping backup (--no-backup specified)")
    
    # Connect to database
    conn = sqlite3.connect(old_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check current version
        cursor.execute("PRAGMA user_version")
        current_version = cursor.fetchone()[0]
        
        if current_version != 1:
            print(f"✗ Error: Database version is {current_version}, expected 1")
            print("  This migration script only works for version 1 databases")
            conn.close()
            return False
        
        print(f"✓ Database version confirmed: {current_version}")
        
        # Begin transaction
        print("\n" + "-" * 60)
        print("Starting migration...")
        print("-" * 60)
        
        # Step 1: Create new schema tables
        print("\n1. Creating new schema tables...")
        
        # Create new verse_group table (AUTOINCREMENT for new IDs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verse_group_new (
                verse_group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                note TEXT
            )
        """)
        print("  ✓ Created verse_group_new table")
        
        # Create verse_group_verse junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verse_group_verse (
                verse_group_id INTEGER NOT NULL,
                verse_id TEXT NOT NULL,
                book INTEGER NOT NULL,
                chapter INTEGER NOT NULL,
                verse INTEGER NOT NULL,
                PRIMARY KEY (verse_group_id, verse_id),
                FOREIGN KEY (verse_group_id) REFERENCES verse_group(verse_group_id) ON DELETE CASCADE
            )
        """)
        print("  ✓ Created verse_group_verse junction table")
        
        # Create new tag table with note column
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tag_new (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag TEXT NOT NULL UNIQUE,
                note TEXT
            )
        """)
        print("  ✓ Created tag_new table")
        
        # Create new tag_tag table with CHECK constraint
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tag_tag_new (
                tag_1_id INTEGER NOT NULL,
                tag_2_id INTEGER NOT NULL,
                PRIMARY KEY (tag_1_id, tag_2_id),
                FOREIGN KEY (tag_1_id) REFERENCES tag(tag_id) ON DELETE CASCADE,
                FOREIGN KEY (tag_2_id) REFERENCES tag(tag_id) ON DELETE CASCADE,
                CHECK (tag_1_id < tag_2_id)
            )
        """)
        print("  ✓ Created tag_tag_new table")
        
        # Create new verse_group_tag table with CASCADE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verse_group_tag_new (
                verse_group_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (verse_group_id, tag_id),
                FOREIGN KEY (verse_group_id) REFERENCES verse_group(verse_group_id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tag(tag_id) ON DELETE CASCADE
            )
        """)
        print("  ✓ Created verse_group_tag_new table")
        
        # Step 2: Migrate data
        print("\n2. Migrating data...")
        
        # Migrate tags and their notes
        print("  - Migrating tags...")
        cursor.execute("SELECT tag_id, tag FROM tag")
        old_tags = cursor.fetchall()
        
        for tag_row in old_tags:
            tag_id = tag_row['tag_id']
            tag_text = tag_row['tag']
            
            # Get note for this tag if it exists (from tag_note junction)
            cursor.execute("""
                SELECT n.note 
                FROM note n
                JOIN tag_note tn ON n.note_id = tn.note_id
                WHERE tn.tag_id = ?
            """, (tag_id,))
            note_rows = cursor.fetchall()
            
            # Concatenate multiple notes if they exist
            note_text = None
            if note_rows:
                notes = [row['note'] for row in note_rows]
                note_text = "\n\n---MERGED---\n\n".join(notes)
            
            # Insert into new tag table
            cursor.execute("""
                INSERT INTO tag_new (tag_id, tag, note)
                VALUES (?, ?, ?)
            """, (tag_id, tag_text, note_text))
        
        print(f"    ✓ Migrated {len(old_tags)} tags")
        
        # Migrate verse_groups and their notes
        print("  - Migrating verse_groups...")
        
        # Get all unique verse_group_ids from old schema
        cursor.execute("SELECT DISTINCT verse_group_id FROM verse_group ORDER BY verse_group_id")
        verse_group_ids = [row['verse_group_id'] for row in cursor.fetchall()]
        
        for vg_id in verse_group_ids:
            # Get notes for this verse_group (from verse_group_note junction)
            cursor.execute("""
                SELECT n.note 
                FROM note n
                JOIN verse_group_note vn ON n.note_id = vn.note_id
                WHERE vn.verse_group_id = ?
            """, (vg_id,))
            note_rows = cursor.fetchall()
            
            # Concatenate multiple notes if they exist
            note_text = None
            if note_rows:
                notes = [row['note'] for row in note_rows]
                note_text = "\n\n---MERGED---\n\n".join(notes)
            
            # Insert into new verse_group table
            cursor.execute("""
                INSERT INTO verse_group_new (verse_group_id, note)
                VALUES (?, ?)
            """, (vg_id, note_text))
            
            # Get all verses in this group from old verse_group table
            cursor.execute("""
                SELECT verse_id FROM verse_group
                WHERE verse_group_id = ?
                ORDER BY verse_id
            """, (vg_id,))
            verses = cursor.fetchall()
            
            # Insert into verse_group_verse junction table
            for verse_row in verses:
                verse_id = verse_row['verse_id']
                # Parse verse_id to get book, chapter, verse
                parts = verse_id.split('.')
                book = int(parts[0])
                chapter = int(parts[1])
                verse = int(parts[2])
                
                cursor.execute("""
                    INSERT INTO verse_group_verse (verse_group_id, verse_id, book, chapter, verse)
                    VALUES (?, ?, ?, ?, ?)
                """, (vg_id, verse_id, book, chapter, verse))
        
        print(f"    ✓ Migrated {len(verse_group_ids)} verse_groups")
        
        # Migrate verse_group_tag relationships
        print("  - Migrating verse_group_tag relationships...")
        cursor.execute("SELECT verse_group_id, tag_id FROM verse_group_tag")
        vg_tags = cursor.fetchall()
        
        for vg_tag in vg_tags:
            cursor.execute("""
                INSERT INTO verse_group_tag_new (verse_group_id, tag_id)
                VALUES (?, ?)
            """, (vg_tag['verse_group_id'], vg_tag['tag_id']))
        
        print(f"    ✓ Migrated {len(vg_tags)} verse-tag relationships")
        
        # Migrate tag_tag relationships (normalize to tag_1_id < tag_2_id)
        print("  - Migrating tag_tag relationships...")
        cursor.execute("SELECT tag_1_id, tag_2_id FROM tag_tag")
        tag_tags = cursor.fetchall()
        
        # Track unique pairs (normalized)
        unique_pairs = set()
        failed_pairs = []
        for tt in tag_tags:
            tag1 = tt['tag_1_id']
            tag2 = tt['tag_2_id']
            # Normalize: smaller id first (enforce CHECK constraint tag_1_id < tag_2_id)
            if tag1 > tag2:
                tag1, tag2 = tag2, tag1
            # Ensure they're different tags
            if tag1 != tag2:
                unique_pairs.add((tag1, tag2))
            else:
                failed_pairs.append((tt['tag_1_id'], tt['tag_2_id']))
        
        if failed_pairs:
            print(f"    ⚠ Warning: Skipped {len(failed_pairs)} self-referencing tag pairs")
        
        inserted_count = 0
        for tag1, tag2 in unique_pairs:
            try:
                # Use INSERT OR IGNORE to handle any duplicates gracefully
                cursor.execute("""
                    INSERT OR IGNORE INTO tag_tag_new (tag_1_id, tag_2_id)
                    VALUES (?, ?)
                """, (tag1, tag2))
                if cursor.rowcount > 0:
                    inserted_count += 1
            except Exception as e:
                print(f"    ⚠ Warning: Failed to insert tag_tag pair ({tag1}, {tag2}): {e}")
        
        print(f"    ✓ Migrated {inserted_count} tag-tag relationships")
        
        # Step 3: Drop old tables and rename new ones
        print("\n3. Replacing old tables with new schema...")
        
        # Drop old tables
        cursor.execute("DROP TABLE IF EXISTS tag_note")
        cursor.execute("DROP TABLE IF EXISTS verse_group_note")
        cursor.execute("DROP TABLE IF EXISTS note")
        cursor.execute("DROP TABLE IF EXISTS verse")  # Remove verse table
        cursor.execute("DROP TABLE IF EXISTS tag_tag")
        cursor.execute("DROP TABLE IF EXISTS verse_group_tag")
        cursor.execute("DROP TABLE IF EXISTS tag")
        cursor.execute("DROP TABLE IF EXISTS verse_group")
        print("  ✓ Dropped old tables")
        
        # Rename new tables to permanent names
        cursor.execute("ALTER TABLE verse_group_new RENAME TO verse_group")
        cursor.execute("ALTER TABLE tag_new RENAME TO tag")
        cursor.execute("ALTER TABLE tag_tag_new RENAME TO tag_tag")
        cursor.execute("ALTER TABLE verse_group_tag_new RENAME TO verse_group_tag")
        print("  ✓ Renamed new tables")
        
        # Step 4: Update database version
        print("\n4. Updating database version...")
        cursor.execute("PRAGMA user_version = 2")
        print("  ✓ Database version set to 2")
        
        # Commit all changes
        conn.commit()
        
        # Verify migration
        print("\n5. Verifying migration...")
        cursor.execute("PRAGMA user_version")
        new_version = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tag")
        tag_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM verse_group")
        vg_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM verse_group_verse")
        vgv_count = cursor.fetchone()[0]
        
        print(f"  ✓ Database version: {new_version}")
        print(f"  ✓ Tags: {tag_count}")
        print(f"  ✓ Verse groups: {vg_count}")
        print(f"  ✓ Verse-group associations: {vgv_count}")
        
        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        
        if backup_path:
            print(f"\nBackup saved at: {backup_path}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        
        conn.rollback()
        conn.close()
        
        if backup_path:
            print(f"\n⚠ Migration failed. Your original database is backed up at:")
            print(f"  {backup_path}")
            print("\nYou can restore it by copying it back:")
            print(f"  copy \"{backup_path}\" \"{old_db_path}\"")
        
        return False


def main():
    """
    Main entry point for the migration script.
    """
    parser = argparse.ArgumentParser(
        description="Migrate Bible Tagger database from version 1 to version 2"
    )
    parser.add_argument(
        "database",
        help="Path to the database file to migrate"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a backup (not recommended)"
    )
    
    args = parser.parse_args()
    
    # Run migration
    success = migrate_database(args.database, create_backup=not args.no_backup)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
