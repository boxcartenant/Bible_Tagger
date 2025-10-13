"""
Database Schema Migration Script: Version 0 to Version 1
Migrates Bible Tagger databases from old schema (v0) to new schema (v1).

OLD SCHEMA (v0):
- verses (id, start_book, start_chapter, start_verse, end_book, end_chapter, end_verse)
- tags (id, tag)
- notes (id, note)
- verse_tags (verse_id, tag_id)
- verse_notes (verse_id, note_id)
- tag_notes (tag_id, note_id)
- tag_tags (tag1_id, tag2_id)

NEW SCHEMA (v1):
- verse (verse_id TEXT PRIMARY KEY, book, chapter, verse)
- verse_group (verse_group_id INT, verse_id TEXT)
- tag (tag_id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT UNIQUE)
- note (note_id INTEGER PRIMARY KEY AUTOINCREMENT, note TEXT)
- verse_group_tag (verse_group_id INT, tag_id INT)
- verse_group_note (verse_group_id INT, note_id INT)
- tag_note (tag_id INT, note_id INT)
- tag_tag (tag_1_id INT, tag_2_id INT)

Usage:
    python 0-to-1.py <database_path> [--no-backup]
"""

import sqlite3
import os
import sys
import shutil
import argparse

verse_counts = [{ "book": 1, "chapter": 1, "verse_count": 31 },
{ "book": 1, "chapter": 2, "verse_count": 25 },
{ "book": 1, "chapter": 3, "verse_count": 24 },
{ "book": 1, "chapter": 4, "verse_count": 26 },
{ "book": 1, "chapter": 5, "verse_count": 32 },
{ "book": 1, "chapter": 6, "verse_count": 22 },
{ "book": 1, "chapter": 7, "verse_count": 24 },
{ "book": 1, "chapter": 8, "verse_count": 22 },
{ "book": 1, "chapter": 9, "verse_count": 29 },
{ "book": 1, "chapter": 10, "verse_count": 32 },
{ "book": 1, "chapter": 11, "verse_count": 32 },
{ "book": 1, "chapter": 12, "verse_count": 20 },
{ "book": 1, "chapter": 13, "verse_count": 18 },
{ "book": 1, "chapter": 14, "verse_count": 24 },
{ "book": 1, "chapter": 15, "verse_count": 21 },
{ "book": 1, "chapter": 16, "verse_count": 16 },
{ "book": 1, "chapter": 17, "verse_count": 27 },
{ "book": 1, "chapter": 18, "verse_count": 33 },
{ "book": 1, "chapter": 19, "verse_count": 38 },
{ "book": 1, "chapter": 20, "verse_count": 18 },
{ "book": 1, "chapter": 21, "verse_count": 34 },
{ "book": 1, "chapter": 22, "verse_count": 24 },
{ "book": 1, "chapter": 23, "verse_count": 20 },
{ "book": 1, "chapter": 24, "verse_count": 67 },
{ "book": 1, "chapter": 25, "verse_count": 34 },
{ "book": 1, "chapter": 26, "verse_count": 35 },
{ "book": 1, "chapter": 27, "verse_count": 46 },
{ "book": 1, "chapter": 28, "verse_count": 22 },
{ "book": 1, "chapter": 29, "verse_count": 35 },
{ "book": 1, "chapter": 30, "verse_count": 43 },
{ "book": 1, "chapter": 31, "verse_count": 55 },
{ "book": 1, "chapter": 32, "verse_count": 32 },
{ "book": 1, "chapter": 33, "verse_count": 20 },
{ "book": 1, "chapter": 34, "verse_count": 31 },
{ "book": 1, "chapter": 35, "verse_count": 29 },
{ "book": 1, "chapter": 36, "verse_count": 43 },
{ "book": 1, "chapter": 37, "verse_count": 36 },
{ "book": 1, "chapter": 38, "verse_count": 30 },
{ "book": 1, "chapter": 39, "verse_count": 23 },
{ "book": 1, "chapter": 40, "verse_count": 23 },
{ "book": 1, "chapter": 41, "verse_count": 57 },
{ "book": 1, "chapter": 42, "verse_count": 38 },
{ "book": 1, "chapter": 43, "verse_count": 34 },
{ "book": 1, "chapter": 44, "verse_count": 34 },
{ "book": 1, "chapter": 45, "verse_count": 28 },
{ "book": 1, "chapter": 46, "verse_count": 34 },
{ "book": 1, "chapter": 47, "verse_count": 31 },
{ "book": 1, "chapter": 48, "verse_count": 22 },
{ "book": 1, "chapter": 49, "verse_count": 33 },
{ "book": 1, "chapter": 50, "verse_count": 26 },
{ "book": 2, "chapter": 1, "verse_count": 22 },
{ "book": 2, "chapter": 2, "verse_count": 25 },
{ "book": 2, "chapter": 3, "verse_count": 22 },
{ "book": 2, "chapter": 4, "verse_count": 31 },
{ "book": 2, "chapter": 5, "verse_count": 23 },
{ "book": 2, "chapter": 6, "verse_count": 30 },
{ "book": 2, "chapter": 7, "verse_count": 25 },
{ "book": 2, "chapter": 8, "verse_count": 32 },
{ "book": 2, "chapter": 9, "verse_count": 35 },
{ "book": 2, "chapter": 10, "verse_count": 29 },
{ "book": 2, "chapter": 11, "verse_count": 10 },
{ "book": 2, "chapter": 12, "verse_count": 51 },
{ "book": 2, "chapter": 13, "verse_count": 22 },
{ "book": 2, "chapter": 14, "verse_count": 31 },
{ "book": 2, "chapter": 15, "verse_count": 27 },
{ "book": 2, "chapter": 16, "verse_count": 36 },
{ "book": 2, "chapter": 17, "verse_count": 16 },
{ "book": 2, "chapter": 18, "verse_count": 27 },
{ "book": 2, "chapter": 19, "verse_count": 25 },
{ "book": 2, "chapter": 20, "verse_count": 26 },
{ "book": 2, "chapter": 21, "verse_count": 36 },
{ "book": 2, "chapter": 22, "verse_count": 31 },
{ "book": 2, "chapter": 23, "verse_count": 33 },
{ "book": 2, "chapter": 24, "verse_count": 18 },
{ "book": 2, "chapter": 25, "verse_count": 40 },
{ "book": 2, "chapter": 26, "verse_count": 37 },
{ "book": 2, "chapter": 27, "verse_count": 21 },
{ "book": 2, "chapter": 28, "verse_count": 43 },
{ "book": 2, "chapter": 29, "verse_count": 46 },
{ "book": 2, "chapter": 30, "verse_count": 38 },
{ "book": 2, "chapter": 31, "verse_count": 18 },
{ "book": 2, "chapter": 32, "verse_count": 35 },
{ "book": 2, "chapter": 33, "verse_count": 23 },
{ "book": 2, "chapter": 34, "verse_count": 35 },
{ "book": 2, "chapter": 35, "verse_count": 35 },
{ "book": 2, "chapter": 36, "verse_count": 38 },
{ "book": 2, "chapter": 37, "verse_count": 29 },
{ "book": 2, "chapter": 38, "verse_count": 31 },
{ "book": 2, "chapter": 39, "verse_count": 43 },
{ "book": 2, "chapter": 40, "verse_count": 38 },
{ "book": 3, "chapter": 1, "verse_count": 17 },
{ "book": 3, "chapter": 2, "verse_count": 16 },
{ "book": 3, "chapter": 3, "verse_count": 17 },
{ "book": 3, "chapter": 4, "verse_count": 35 },
{ "book": 3, "chapter": 5, "verse_count": 19 },
{ "book": 3, "chapter": 6, "verse_count": 30 },
{ "book": 3, "chapter": 7, "verse_count": 38 },
{ "book": 3, "chapter": 8, "verse_count": 36 },
{ "book": 3, "chapter": 9, "verse_count": 24 },
{ "book": 3, "chapter": 10, "verse_count": 20 },
{ "book": 3, "chapter": 11, "verse_count": 47 },
{ "book": 3, "chapter": 12, "verse_count": 8 },
{ "book": 3, "chapter": 13, "verse_count": 59 },
{ "book": 3, "chapter": 14, "verse_count": 57 },
{ "book": 3, "chapter": 15, "verse_count": 33 },
{ "book": 3, "chapter": 16, "verse_count": 34 },
{ "book": 3, "chapter": 17, "verse_count": 16 },
{ "book": 3, "chapter": 18, "verse_count": 30 },
{ "book": 3, "chapter": 19, "verse_count": 37 },
{ "book": 3, "chapter": 20, "verse_count": 27 },
{ "book": 3, "chapter": 21, "verse_count": 24 },
{ "book": 3, "chapter": 22, "verse_count": 33 },
{ "book": 3, "chapter": 23, "verse_count": 44 },
{ "book": 3, "chapter": 24, "verse_count": 23 },
{ "book": 3, "chapter": 25, "verse_count": 55 },
{ "book": 3, "chapter": 26, "verse_count": 46 },
{ "book": 3, "chapter": 27, "verse_count": 34 },
{ "book": 4, "chapter": 1, "verse_count": 54 },
{ "book": 4, "chapter": 2, "verse_count": 34 },
{ "book": 4, "chapter": 3, "verse_count": 51 },
{ "book": 4, "chapter": 4, "verse_count": 49 },
{ "book": 4, "chapter": 5, "verse_count": 31 },
{ "book": 4, "chapter": 6, "verse_count": 27 },
{ "book": 4, "chapter": 7, "verse_count": 89 },
{ "book": 4, "chapter": 8, "verse_count": 26 },
{ "book": 4, "chapter": 9, "verse_count": 23 },
{ "book": 4, "chapter": 10, "verse_count": 36 },
{ "book": 4, "chapter": 11, "verse_count": 35 },
{ "book": 4, "chapter": 12, "verse_count": 16 },
{ "book": 4, "chapter": 13, "verse_count": 33 },
{ "book": 4, "chapter": 14, "verse_count": 45 },
{ "book": 4, "chapter": 15, "verse_count": 41 },
{ "book": 4, "chapter": 16, "verse_count": 50 },
{ "book": 4, "chapter": 17, "verse_count": 13 },
{ "book": 4, "chapter": 18, "verse_count": 32 },
{ "book": 4, "chapter": 19, "verse_count": 22 },
{ "book": 4, "chapter": 20, "verse_count": 29 },
{ "book": 4, "chapter": 21, "verse_count": 35 },
{ "book": 4, "chapter": 22, "verse_count": 41 },
{ "book": 4, "chapter": 23, "verse_count": 30 },
{ "book": 4, "chapter": 24, "verse_count": 25 },
{ "book": 4, "chapter": 25, "verse_count": 18 },
{ "book": 4, "chapter": 26, "verse_count": 65 },
{ "book": 4, "chapter": 27, "verse_count": 23 },
{ "book": 4, "chapter": 28, "verse_count": 31 },
{ "book": 4, "chapter": 29, "verse_count": 40 },
{ "book": 4, "chapter": 30, "verse_count": 16 },
{ "book": 4, "chapter": 31, "verse_count": 54 },
{ "book": 4, "chapter": 32, "verse_count": 42 },
{ "book": 4, "chapter": 33, "verse_count": 56 },
{ "book": 4, "chapter": 34, "verse_count": 29 },
{ "book": 4, "chapter": 35, "verse_count": 34 },
{ "book": 4, "chapter": 36, "verse_count": 13 },
{ "book": 5, "chapter": 1, "verse_count": 46 },
{ "book": 5, "chapter": 2, "verse_count": 37 },
{ "book": 5, "chapter": 3, "verse_count": 29 },
{ "book": 5, "chapter": 4, "verse_count": 49 },
{ "book": 5, "chapter": 5, "verse_count": 33 },
{ "book": 5, "chapter": 6, "verse_count": 25 },
{ "book": 5, "chapter": 7, "verse_count": 26 },
{ "book": 5, "chapter": 8, "verse_count": 20 },
{ "book": 5, "chapter": 9, "verse_count": 29 },
{ "book": 5, "chapter": 10, "verse_count": 22 },
{ "book": 5, "chapter": 11, "verse_count": 32 },
{ "book": 5, "chapter": 12, "verse_count": 32 },
{ "book": 5, "chapter": 13, "verse_count": 18 },
{ "book": 5, "chapter": 14, "verse_count": 29 },
{ "book": 5, "chapter": 15, "verse_count": 23 },
{ "book": 5, "chapter": 16, "verse_count": 22 },
{ "book": 5, "chapter": 17, "verse_count": 20 },
{ "book": 5, "chapter": 18, "verse_count": 22 },
{ "book": 5, "chapter": 19, "verse_count": 21 },
{ "book": 5, "chapter": 20, "verse_count": 20 },
{ "book": 5, "chapter": 21, "verse_count": 23 },
{ "book": 5, "chapter": 22, "verse_count": 30 },
{ "book": 5, "chapter": 23, "verse_count": 25 },
{ "book": 5, "chapter": 24, "verse_count": 22 },
{ "book": 5, "chapter": 25, "verse_count": 19 },
{ "book": 5, "chapter": 26, "verse_count": 19 },
{ "book": 5, "chapter": 27, "verse_count": 26 },
{ "book": 5, "chapter": 28, "verse_count": 68 },
{ "book": 5, "chapter": 29, "verse_count": 29 },
{ "book": 5, "chapter": 30, "verse_count": 20 },
{ "book": 5, "chapter": 31, "verse_count": 30 },
{ "book": 5, "chapter": 32, "verse_count": 52 },
{ "book": 5, "chapter": 33, "verse_count": 29 },
{ "book": 5, "chapter": 34, "verse_count": 12 },
{ "book": 6, "chapter": 1, "verse_count": 18 },
{ "book": 6, "chapter": 2, "verse_count": 24 },
{ "book": 6, "chapter": 3, "verse_count": 17 },
{ "book": 6, "chapter": 4, "verse_count": 24 },
{ "book": 6, "chapter": 5, "verse_count": 15 },
{ "book": 6, "chapter": 6, "verse_count": 27 },
{ "book": 6, "chapter": 7, "verse_count": 26 },
{ "book": 6, "chapter": 8, "verse_count": 35 },
{ "book": 6, "chapter": 9, "verse_count": 27 },
{ "book": 6, "chapter": 10, "verse_count": 43 },
{ "book": 6, "chapter": 11, "verse_count": 23 },
{ "book": 6, "chapter": 12, "verse_count": 24 },
{ "book": 6, "chapter": 13, "verse_count": 33 },
{ "book": 6, "chapter": 14, "verse_count": 15 },
{ "book": 6, "chapter": 15, "verse_count": 63 },
{ "book": 6, "chapter": 16, "verse_count": 10 },
{ "book": 6, "chapter": 17, "verse_count": 18 },
{ "book": 6, "chapter": 18, "verse_count": 28 },
{ "book": 6, "chapter": 19, "verse_count": 51 },
{ "book": 6, "chapter": 20, "verse_count": 9 },
{ "book": 6, "chapter": 21, "verse_count": 45 },
{ "book": 6, "chapter": 22, "verse_count": 34 },
{ "book": 6, "chapter": 23, "verse_count": 16 },
{ "book": 6, "chapter": 24, "verse_count": 33 },
{ "book": 7, "chapter": 1, "verse_count": 36 },
{ "book": 7, "chapter": 2, "verse_count": 23 },
{ "book": 7, "chapter": 3, "verse_count": 31 },
{ "book": 7, "chapter": 4, "verse_count": 24 },
{ "book": 7, "chapter": 5, "verse_count": 31 },
{ "book": 7, "chapter": 6, "verse_count": 40 },
{ "book": 7, "chapter": 7, "verse_count": 25 },
{ "book": 7, "chapter": 8, "verse_count": 35 },
{ "book": 7, "chapter": 9, "verse_count": 57 },
{ "book": 7, "chapter": 10, "verse_count": 18 },
{ "book": 7, "chapter": 11, "verse_count": 40 },
{ "book": 7, "chapter": 12, "verse_count": 15 },
{ "book": 7, "chapter": 13, "verse_count": 25 },
{ "book": 7, "chapter": 14, "verse_count": 20 },
{ "book": 7, "chapter": 15, "verse_count": 20 },
{ "book": 7, "chapter": 16, "verse_count": 31 },
{ "book": 7, "chapter": 17, "verse_count": 13 },
{ "book": 7, "chapter": 18, "verse_count": 31 },
{ "book": 7, "chapter": 19, "verse_count": 30 },
{ "book": 7, "chapter": 20, "verse_count": 48 },
{ "book": 7, "chapter": 21, "verse_count": 25 },
{ "book": 8, "chapter": 1, "verse_count": 22 },
{ "book": 8, "chapter": 2, "verse_count": 23 },
{ "book": 8, "chapter": 3, "verse_count": 18 },
{ "book": 8, "chapter": 4, "verse_count": 22 },
{ "book": 9, "chapter": 1, "verse_count": 28 },
{ "book": 9, "chapter": 2, "verse_count": 36 },
{ "book": 9, "chapter": 3, "verse_count": 21 },
{ "book": 9, "chapter": 4, "verse_count": 22 },
{ "book": 9, "chapter": 5, "verse_count": 12 },
{ "book": 9, "chapter": 6, "verse_count": 21 },
{ "book": 9, "chapter": 7, "verse_count": 17 },
{ "book": 9, "chapter": 8, "verse_count": 22 },
{ "book": 9, "chapter": 9, "verse_count": 27 },
{ "book": 9, "chapter": 10, "verse_count": 27 },
{ "book": 9, "chapter": 11, "verse_count": 15 },
{ "book": 9, "chapter": 12, "verse_count": 25 },
{ "book": 9, "chapter": 13, "verse_count": 23 },
{ "book": 9, "chapter": 14, "verse_count": 52 },
{ "book": 9, "chapter": 15, "verse_count": 35 },
{ "book": 9, "chapter": 16, "verse_count": 23 },
{ "book": 9, "chapter": 17, "verse_count": 58 },
{ "book": 9, "chapter": 18, "verse_count": 30 },
{ "book": 9, "chapter": 19, "verse_count": 24 },
{ "book": 9, "chapter": 20, "verse_count": 42 },
{ "book": 9, "chapter": 21, "verse_count": 15 },
{ "book": 9, "chapter": 22, "verse_count": 23 },
{ "book": 9, "chapter": 23, "verse_count": 29 },
{ "book": 9, "chapter": 24, "verse_count": 22 },
{ "book": 9, "chapter": 25, "verse_count": 44 },
{ "book": 9, "chapter": 26, "verse_count": 25 },
{ "book": 9, "chapter": 27, "verse_count": 12 },
{ "book": 9, "chapter": 28, "verse_count": 25 },
{ "book": 9, "chapter": 29, "verse_count": 11 },
{ "book": 9, "chapter": 30, "verse_count": 31 },
{ "book": 9, "chapter": 31, "verse_count": 13 },
{ "book": 10, "chapter": 1, "verse_count": 27 },
{ "book": 10, "chapter": 2, "verse_count": 32 },
{ "book": 10, "chapter": 3, "verse_count": 39 },
{ "book": 10, "chapter": 4, "verse_count": 12 },
{ "book": 10, "chapter": 5, "verse_count": 25 },
{ "book": 10, "chapter": 6, "verse_count": 23 },
{ "book": 10, "chapter": 7, "verse_count": 29 },
{ "book": 10, "chapter": 8, "verse_count": 18 },
{ "book": 10, "chapter": 9, "verse_count": 13 },
{ "book": 10, "chapter": 10, "verse_count": 19 },
{ "book": 10, "chapter": 11, "verse_count": 27 },
{ "book": 10, "chapter": 12, "verse_count": 31 },
{ "book": 10, "chapter": 13, "verse_count": 39 },
{ "book": 10, "chapter": 14, "verse_count": 33 },
{ "book": 10, "chapter": 15, "verse_count": 37 },
{ "book": 10, "chapter": 16, "verse_count": 23 },
{ "book": 10, "chapter": 17, "verse_count": 29 },
{ "book": 10, "chapter": 18, "verse_count": 33 },
{ "book": 10, "chapter": 19, "verse_count": 43 },
{ "book": 10, "chapter": 20, "verse_count": 26 },
{ "book": 10, "chapter": 21, "verse_count": 22 },
{ "book": 10, "chapter": 22, "verse_count": 51 },
{ "book": 10, "chapter": 23, "verse_count": 39 },
{ "book": 10, "chapter": 24, "verse_count": 25 },
{ "book": 11, "chapter": 1, "verse_count": 53 },
{ "book": 11, "chapter": 2, "verse_count": 46 },
{ "book": 11, "chapter": 3, "verse_count": 28 },
{ "book": 11, "chapter": 4, "verse_count": 34 },
{ "book": 11, "chapter": 5, "verse_count": 18 },
{ "book": 11, "chapter": 6, "verse_count": 38 },
{ "book": 11, "chapter": 7, "verse_count": 51 },
{ "book": 11, "chapter": 8, "verse_count": 66 },
{ "book": 11, "chapter": 9, "verse_count": 28 },
{ "book": 11, "chapter": 10, "verse_count": 29 },
{ "book": 11, "chapter": 11, "verse_count": 43 },
{ "book": 11, "chapter": 12, "verse_count": 33 },
{ "book": 11, "chapter": 13, "verse_count": 34 },
{ "book": 11, "chapter": 14, "verse_count": 31 },
{ "book": 11, "chapter": 15, "verse_count": 34 },
{ "book": 11, "chapter": 16, "verse_count": 34 },
{ "book": 11, "chapter": 17, "verse_count": 24 },
{ "book": 11, "chapter": 18, "verse_count": 46 },
{ "book": 11, "chapter": 19, "verse_count": 21 },
{ "book": 11, "chapter": 20, "verse_count": 43 },
{ "book": 11, "chapter": 21, "verse_count": 29 },
{ "book": 11, "chapter": 22, "verse_count": 53 },
{ "book": 12, "chapter": 1, "verse_count": 18 },
{ "book": 12, "chapter": 2, "verse_count": 25 },
{ "book": 12, "chapter": 3, "verse_count": 27 },
{ "book": 12, "chapter": 4, "verse_count": 44 },
{ "book": 12, "chapter": 5, "verse_count": 27 },
{ "book": 12, "chapter": 6, "verse_count": 33 },
{ "book": 12, "chapter": 7, "verse_count": 20 },
{ "book": 12, "chapter": 8, "verse_count": 29 },
{ "book": 12, "chapter": 9, "verse_count": 37 },
{ "book": 12, "chapter": 10, "verse_count": 36 },
{ "book": 12, "chapter": 11, "verse_count": 21 },
{ "book": 12, "chapter": 12, "verse_count": 21 },
{ "book": 12, "chapter": 13, "verse_count": 25 },
{ "book": 12, "chapter": 14, "verse_count": 29 },
{ "book": 12, "chapter": 15, "verse_count": 38 },
{ "book": 12, "chapter": 16, "verse_count": 20 },
{ "book": 12, "chapter": 17, "verse_count": 41 },
{ "book": 12, "chapter": 18, "verse_count": 37 },
{ "book": 12, "chapter": 19, "verse_count": 37 },
{ "book": 12, "chapter": 20, "verse_count": 21 },
{ "book": 12, "chapter": 21, "verse_count": 26 },
{ "book": 12, "chapter": 22, "verse_count": 20 },
{ "book": 12, "chapter": 23, "verse_count": 37 },
{ "book": 12, "chapter": 24, "verse_count": 20 },
{ "book": 12, "chapter": 25, "verse_count": 30 },
{ "book": 13, "chapter": 1, "verse_count": 54 },
{ "book": 13, "chapter": 2, "verse_count": 55 },
{ "book": 13, "chapter": 3, "verse_count": 24 },
{ "book": 13, "chapter": 4, "verse_count": 43 },
{ "book": 13, "chapter": 5, "verse_count": 26 },
{ "book": 13, "chapter": 6, "verse_count": 81 },
{ "book": 13, "chapter": 7, "verse_count": 40 },
{ "book": 13, "chapter": 8, "verse_count": 40 },
{ "book": 13, "chapter": 9, "verse_count": 44 },
{ "book": 13, "chapter": 10, "verse_count": 14 },
{ "book": 13, "chapter": 11, "verse_count": 47 },
{ "book": 13, "chapter": 12, "verse_count": 40 },
{ "book": 13, "chapter": 13, "verse_count": 14 },
{ "book": 13, "chapter": 14, "verse_count": 17 },
{ "book": 13, "chapter": 15, "verse_count": 29 },
{ "book": 13, "chapter": 16, "verse_count": 43 },
{ "book": 13, "chapter": 17, "verse_count": 27 },
{ "book": 13, "chapter": 18, "verse_count": 17 },
{ "book": 13, "chapter": 19, "verse_count": 19 },
{ "book": 13, "chapter": 20, "verse_count": 8 },
{ "book": 13, "chapter": 21, "verse_count": 30 },
{ "book": 13, "chapter": 22, "verse_count": 19 },
{ "book": 13, "chapter": 23, "verse_count": 32 },
{ "book": 13, "chapter": 24, "verse_count": 31 },
{ "book": 13, "chapter": 25, "verse_count": 31 },
{ "book": 13, "chapter": 26, "verse_count": 32 },
{ "book": 13, "chapter": 27, "verse_count": 34 },
{ "book": 13, "chapter": 28, "verse_count": 21 },
{ "book": 13, "chapter": 29, "verse_count": 30 },
{ "book": 14, "chapter": 1, "verse_count": 17 },
{ "book": 14, "chapter": 2, "verse_count": 18 },
{ "book": 14, "chapter": 3, "verse_count": 17 },
{ "book": 14, "chapter": 4, "verse_count": 22 },
{ "book": 14, "chapter": 5, "verse_count": 14 },
{ "book": 14, "chapter": 6, "verse_count": 42 },
{ "book": 14, "chapter": 7, "verse_count": 22 },
{ "book": 14, "chapter": 8, "verse_count": 18 },
{ "book": 14, "chapter": 9, "verse_count": 31 },
{ "book": 14, "chapter": 10, "verse_count": 19 },
{ "book": 14, "chapter": 11, "verse_count": 23 },
{ "book": 14, "chapter": 12, "verse_count": 16 },
{ "book": 14, "chapter": 13, "verse_count": 22 },
{ "book": 14, "chapter": 14, "verse_count": 15 },
{ "book": 14, "chapter": 15, "verse_count": 19 },
{ "book": 14, "chapter": 16, "verse_count": 14 },
{ "book": 14, "chapter": 17, "verse_count": 19 },
{ "book": 14, "chapter": 18, "verse_count": 34 },
{ "book": 14, "chapter": 19, "verse_count": 11 },
{ "book": 14, "chapter": 20, "verse_count": 37 },
{ "book": 14, "chapter": 21, "verse_count": 20 },
{ "book": 14, "chapter": 22, "verse_count": 12 },
{ "book": 14, "chapter": 23, "verse_count": 21 },
{ "book": 14, "chapter": 24, "verse_count": 27 },
{ "book": 14, "chapter": 25, "verse_count": 28 },
{ "book": 14, "chapter": 26, "verse_count": 23 },
{ "book": 14, "chapter": 27, "verse_count": 9 },
{ "book": 14, "chapter": 28, "verse_count": 27 },
{ "book": 14, "chapter": 29, "verse_count": 36 },
{ "book": 14, "chapter": 30, "verse_count": 27 },
{ "book": 14, "chapter": 31, "verse_count": 21 },
{ "book": 14, "chapter": 32, "verse_count": 33 },
{ "book": 14, "chapter": 33, "verse_count": 25 },
{ "book": 14, "chapter": 34, "verse_count": 33 },
{ "book": 14, "chapter": 35, "verse_count": 27 },
{ "book": 14, "chapter": 36, "verse_count": 23 },
{ "book": 15, "chapter": 1, "verse_count": 11 },
{ "book": 15, "chapter": 2, "verse_count": 70 },
{ "book": 15, "chapter": 3, "verse_count": 13 },
{ "book": 15, "chapter": 4, "verse_count": 24 },
{ "book": 15, "chapter": 5, "verse_count": 17 },
{ "book": 15, "chapter": 6, "verse_count": 22 },
{ "book": 15, "chapter": 7, "verse_count": 28 },
{ "book": 15, "chapter": 8, "verse_count": 36 },
{ "book": 15, "chapter": 9, "verse_count": 15 },
{ "book": 15, "chapter": 10, "verse_count": 44 },
{ "book": 16, "chapter": 1, "verse_count": 11 },
{ "book": 16, "chapter": 2, "verse_count": 20 },
{ "book": 16, "chapter": 3, "verse_count": 32 },
{ "book": 16, "chapter": 4, "verse_count": 23 },
{ "book": 16, "chapter": 5, "verse_count": 19 },
{ "book": 16, "chapter": 6, "verse_count": 19 },
{ "book": 16, "chapter": 7, "verse_count": 73 },
{ "book": 16, "chapter": 8, "verse_count": 18 },
{ "book": 16, "chapter": 9, "verse_count": 38 },
{ "book": 16, "chapter": 10, "verse_count": 39 },
{ "book": 16, "chapter": 11, "verse_count": 36 },
{ "book": 16, "chapter": 12, "verse_count": 47 },
{ "book": 16, "chapter": 13, "verse_count": 31 },
{ "book": 17, "chapter": 1, "verse_count": 22 },
{ "book": 17, "chapter": 2, "verse_count": 23 },
{ "book": 17, "chapter": 3, "verse_count": 15 },
{ "book": 17, "chapter": 4, "verse_count": 17 },
{ "book": 17, "chapter": 5, "verse_count": 14 },
{ "book": 17, "chapter": 6, "verse_count": 14 },
{ "book": 17, "chapter": 7, "verse_count": 10 },
{ "book": 17, "chapter": 8, "verse_count": 17 },
{ "book": 17, "chapter": 9, "verse_count": 32 },
{ "book": 17, "chapter": 10, "verse_count": 3 },
{ "book": 18, "chapter": 1, "verse_count": 22 },
{ "book": 18, "chapter": 2, "verse_count": 13 },
{ "book": 18, "chapter": 3, "verse_count": 26 },
{ "book": 18, "chapter": 4, "verse_count": 21 },
{ "book": 18, "chapter": 5, "verse_count": 27 },
{ "book": 18, "chapter": 6, "verse_count": 30 },
{ "book": 18, "chapter": 7, "verse_count": 21 },
{ "book": 18, "chapter": 8, "verse_count": 22 },
{ "book": 18, "chapter": 9, "verse_count": 35 },
{ "book": 18, "chapter": 10, "verse_count": 22 },
{ "book": 18, "chapter": 11, "verse_count": 20 },
{ "book": 18, "chapter": 12, "verse_count": 25 },
{ "book": 18, "chapter": 13, "verse_count": 28 },
{ "book": 18, "chapter": 14, "verse_count": 22 },
{ "book": 18, "chapter": 15, "verse_count": 35 },
{ "book": 18, "chapter": 16, "verse_count": 22 },
{ "book": 18, "chapter": 17, "verse_count": 16 },
{ "book": 18, "chapter": 18, "verse_count": 21 },
{ "book": 18, "chapter": 19, "verse_count": 29 },
{ "book": 18, "chapter": 20, "verse_count": 29 },
{ "book": 18, "chapter": 21, "verse_count": 34 },
{ "book": 18, "chapter": 22, "verse_count": 30 },
{ "book": 18, "chapter": 23, "verse_count": 17 },
{ "book": 18, "chapter": 24, "verse_count": 25 },
{ "book": 18, "chapter": 25, "verse_count": 6 },
{ "book": 18, "chapter": 26, "verse_count": 14 },
{ "book": 18, "chapter": 27, "verse_count": 23 },
{ "book": 18, "chapter": 28, "verse_count": 28 },
{ "book": 18, "chapter": 29, "verse_count": 25 },
{ "book": 18, "chapter": 30, "verse_count": 31 },
{ "book": 18, "chapter": 31, "verse_count": 40 },
{ "book": 18, "chapter": 32, "verse_count": 22 },
{ "book": 18, "chapter": 33, "verse_count": 33 },
{ "book": 18, "chapter": 34, "verse_count": 37 },
{ "book": 18, "chapter": 35, "verse_count": 16 },
{ "book": 18, "chapter": 36, "verse_count": 33 },
{ "book": 18, "chapter": 37, "verse_count": 24 },
{ "book": 18, "chapter": 38, "verse_count": 41 },
{ "book": 18, "chapter": 39, "verse_count": 30 },
{ "book": 18, "chapter": 40, "verse_count": 24 },
{ "book": 18, "chapter": 41, "verse_count": 34 },
{ "book": 18, "chapter": 42, "verse_count": 17 },
{ "book": 19, "chapter": 1, "verse_count": 6 },
{ "book": 19, "chapter": 2, "verse_count": 12 },
{ "book": 19, "chapter": 3, "verse_count": 8 },
{ "book": 19, "chapter": 4, "verse_count": 8 },
{ "book": 19, "chapter": 5, "verse_count": 12 },
{ "book": 19, "chapter": 6, "verse_count": 10 },
{ "book": 19, "chapter": 7, "verse_count": 17 },
{ "book": 19, "chapter": 8, "verse_count": 9 },
{ "book": 19, "chapter": 9, "verse_count": 20 },
{ "book": 19, "chapter": 10, "verse_count": 18 },
{ "book": 19, "chapter": 11, "verse_count": 7 },
{ "book": 19, "chapter": 12, "verse_count": 8 },
{ "book": 19, "chapter": 13, "verse_count": 6 },
{ "book": 19, "chapter": 14, "verse_count": 7 },
{ "book": 19, "chapter": 15, "verse_count": 5 },
{ "book": 19, "chapter": 16, "verse_count": 11 },
{ "book": 19, "chapter": 17, "verse_count": 15 },
{ "book": 19, "chapter": 18, "verse_count": 50 },
{ "book": 19, "chapter": 19, "verse_count": 14 },
{ "book": 19, "chapter": 20, "verse_count": 9 },
{ "book": 19, "chapter": 21, "verse_count": 13 },
{ "book": 19, "chapter": 22, "verse_count": 31 },
{ "book": 19, "chapter": 23, "verse_count": 6 },
{ "book": 19, "chapter": 24, "verse_count": 10 },
{ "book": 19, "chapter": 25, "verse_count": 22 },
{ "book": 19, "chapter": 26, "verse_count": 12 },
{ "book": 19, "chapter": 27, "verse_count": 14 },
{ "book": 19, "chapter": 28, "verse_count": 9 },
{ "book": 19, "chapter": 29, "verse_count": 11 },
{ "book": 19, "chapter": 30, "verse_count": 12 },
{ "book": 19, "chapter": 31, "verse_count": 24 },
{ "book": 19, "chapter": 32, "verse_count": 11 },
{ "book": 19, "chapter": 33, "verse_count": 22 },
{ "book": 19, "chapter": 34, "verse_count": 22 },
{ "book": 19, "chapter": 35, "verse_count": 28 },
{ "book": 19, "chapter": 36, "verse_count": 12 },
{ "book": 19, "chapter": 37, "verse_count": 40 },
{ "book": 19, "chapter": 38, "verse_count": 22 },
{ "book": 19, "chapter": 39, "verse_count": 13 },
{ "book": 19, "chapter": 40, "verse_count": 17 },
{ "book": 19, "chapter": 41, "verse_count": 13 },
{ "book": 19, "chapter": 42, "verse_count": 11 },
{ "book": 19, "chapter": 43, "verse_count": 5 },
{ "book": 19, "chapter": 44, "verse_count": 26 },
{ "book": 19, "chapter": 45, "verse_count": 17 },
{ "book": 19, "chapter": 46, "verse_count": 11 },
{ "book": 19, "chapter": 47, "verse_count": 9 },
{ "book": 19, "chapter": 48, "verse_count": 14 },
{ "book": 19, "chapter": 49, "verse_count": 20 },
{ "book": 19, "chapter": 50, "verse_count": 23 },
{ "book": 19, "chapter": 51, "verse_count": 19 },
{ "book": 19, "chapter": 52, "verse_count": 9 },
{ "book": 19, "chapter": 53, "verse_count": 6 },
{ "book": 19, "chapter": 54, "verse_count": 7 },
{ "book": 19, "chapter": 55, "verse_count": 23 },
{ "book": 19, "chapter": 56, "verse_count": 13 },
{ "book": 19, "chapter": 57, "verse_count": 11 },
{ "book": 19, "chapter": 58, "verse_count": 11 },
{ "book": 19, "chapter": 59, "verse_count": 17 },
{ "book": 19, "chapter": 60, "verse_count": 12 },
{ "book": 19, "chapter": 61, "verse_count": 8 },
{ "book": 19, "chapter": 62, "verse_count": 12 },
{ "book": 19, "chapter": 63, "verse_count": 11 },
{ "book": 19, "chapter": 64, "verse_count": 10 },
{ "book": 19, "chapter": 65, "verse_count": 13 },
{ "book": 19, "chapter": 66, "verse_count": 20 },
{ "book": 19, "chapter": 67, "verse_count": 7 },
{ "book": 19, "chapter": 68, "verse_count": 35 },
{ "book": 19, "chapter": 69, "verse_count": 36 },
{ "book": 19, "chapter": 70, "verse_count": 5 },
{ "book": 19, "chapter": 71, "verse_count": 24 },
{ "book": 19, "chapter": 72, "verse_count": 20 },
{ "book": 19, "chapter": 73, "verse_count": 28 },
{ "book": 19, "chapter": 74, "verse_count": 23 },
{ "book": 19, "chapter": 75, "verse_count": 10 },
{ "book": 19, "chapter": 76, "verse_count": 12 },
{ "book": 19, "chapter": 77, "verse_count": 20 },
{ "book": 19, "chapter": 78, "verse_count": 72 },
{ "book": 19, "chapter": 79, "verse_count": 13 },
{ "book": 19, "chapter": 80, "verse_count": 19 },
{ "book": 19, "chapter": 81, "verse_count": 16 },
{ "book": 19, "chapter": 82, "verse_count": 8 },
{ "book": 19, "chapter": 83, "verse_count": 18 },
{ "book": 19, "chapter": 84, "verse_count": 12 },
{ "book": 19, "chapter": 85, "verse_count": 13 },
{ "book": 19, "chapter": 86, "verse_count": 17 },
{ "book": 19, "chapter": 87, "verse_count": 7 },
{ "book": 19, "chapter": 88, "verse_count": 18 },
{ "book": 19, "chapter": 89, "verse_count": 52 },
{ "book": 19, "chapter": 90, "verse_count": 17 },
{ "book": 19, "chapter": 91, "verse_count": 16 },
{ "book": 19, "chapter": 92, "verse_count": 15 },
{ "book": 19, "chapter": 93, "verse_count": 5 },
{ "book": 19, "chapter": 94, "verse_count": 23 },
{ "book": 19, "chapter": 95, "verse_count": 11 },
{ "book": 19, "chapter": 96, "verse_count": 13 },
{ "book": 19, "chapter": 97, "verse_count": 12 },
{ "book": 19, "chapter": 98, "verse_count": 9 },
{ "book": 19, "chapter": 99, "verse_count": 9 },
{ "book": 19, "chapter": 100, "verse_count": 5 },
{ "book": 19, "chapter": 101, "verse_count": 8 },
{ "book": 19, "chapter": 102, "verse_count": 28 },
{ "book": 19, "chapter": 103, "verse_count": 22 },
{ "book": 19, "chapter": 104, "verse_count": 35 },
{ "book": 19, "chapter": 105, "verse_count": 45 },
{ "book": 19, "chapter": 106, "verse_count": 48 },
{ "book": 19, "chapter": 107, "verse_count": 43 },
{ "book": 19, "chapter": 108, "verse_count": 13 },
{ "book": 19, "chapter": 109, "verse_count": 31 },
{ "book": 19, "chapter": 110, "verse_count": 7 },
{ "book": 19, "chapter": 111, "verse_count": 10 },
{ "book": 19, "chapter": 112, "verse_count": 10 },
{ "book": 19, "chapter": 113, "verse_count": 9 },
{ "book": 19, "chapter": 114, "verse_count": 8 },
{ "book": 19, "chapter": 115, "verse_count": 18 },
{ "book": 19, "chapter": 116, "verse_count": 19 },
{ "book": 19, "chapter": 117, "verse_count": 2 },
{ "book": 19, "chapter": 118, "verse_count": 29 },
{ "book": 19, "chapter": 119, "verse_count": 176 },
{ "book": 19, "chapter": 120, "verse_count": 7 },
{ "book": 19, "chapter": 121, "verse_count": 8 },
{ "book": 19, "chapter": 122, "verse_count": 9 },
{ "book": 19, "chapter": 123, "verse_count": 4 },
{ "book": 19, "chapter": 124, "verse_count": 8 },
{ "book": 19, "chapter": 125, "verse_count": 5 },
{ "book": 19, "chapter": 126, "verse_count": 6 },
{ "book": 19, "chapter": 127, "verse_count": 5 },
{ "book": 19, "chapter": 128, "verse_count": 6 },
{ "book": 19, "chapter": 129, "verse_count": 8 },
{ "book": 19, "chapter": 130, "verse_count": 8 },
{ "book": 19, "chapter": 131, "verse_count": 3 },
{ "book": 19, "chapter": 132, "verse_count": 18 },
{ "book": 19, "chapter": 133, "verse_count": 3 },
{ "book": 19, "chapter": 134, "verse_count": 3 },
{ "book": 19, "chapter": 135, "verse_count": 21 },
{ "book": 19, "chapter": 136, "verse_count": 26 },
{ "book": 19, "chapter": 137, "verse_count": 9 },
{ "book": 19, "chapter": 138, "verse_count": 8 },
{ "book": 19, "chapter": 139, "verse_count": 24 },
{ "book": 19, "chapter": 140, "verse_count": 13 },
{ "book": 19, "chapter": 141, "verse_count": 10 },
{ "book": 19, "chapter": 142, "verse_count": 7 },
{ "book": 19, "chapter": 143, "verse_count": 12 },
{ "book": 19, "chapter": 144, "verse_count": 15 },
{ "book": 19, "chapter": 145, "verse_count": 21 },
{ "book": 19, "chapter": 146, "verse_count": 10 },
{ "book": 19, "chapter": 147, "verse_count": 20 },
{ "book": 19, "chapter": 148, "verse_count": 14 },
{ "book": 19, "chapter": 149, "verse_count": 9 },
{ "book": 19, "chapter": 150, "verse_count": 6 },
{ "book": 20, "chapter": 1, "verse_count": 33 },
{ "book": 20, "chapter": 2, "verse_count": 22 },
{ "book": 20, "chapter": 3, "verse_count": 35 },
{ "book": 20, "chapter": 4, "verse_count": 27 },
{ "book": 20, "chapter": 5, "verse_count": 23 },
{ "book": 20, "chapter": 6, "verse_count": 35 },
{ "book": 20, "chapter": 7, "verse_count": 27 },
{ "book": 20, "chapter": 8, "verse_count": 36 },
{ "book": 20, "chapter": 9, "verse_count": 18 },
{ "book": 20, "chapter": 10, "verse_count": 32 },
{ "book": 20, "chapter": 11, "verse_count": 31 },
{ "book": 20, "chapter": 12, "verse_count": 28 },
{ "book": 20, "chapter": 13, "verse_count": 25 },
{ "book": 20, "chapter": 14, "verse_count": 35 },
{ "book": 20, "chapter": 15, "verse_count": 33 },
{ "book": 20, "chapter": 16, "verse_count": 33 },
{ "book": 20, "chapter": 17, "verse_count": 28 },
{ "book": 20, "chapter": 18, "verse_count": 24 },
{ "book": 20, "chapter": 19, "verse_count": 29 },
{ "book": 20, "chapter": 20, "verse_count": 30 },
{ "book": 20, "chapter": 21, "verse_count": 31 },
{ "book": 20, "chapter": 22, "verse_count": 29 },
{ "book": 20, "chapter": 23, "verse_count": 35 },
{ "book": 20, "chapter": 24, "verse_count": 34 },
{ "book": 20, "chapter": 25, "verse_count": 28 },
{ "book": 20, "chapter": 26, "verse_count": 28 },
{ "book": 20, "chapter": 27, "verse_count": 27 },
{ "book": 20, "chapter": 28, "verse_count": 28 },
{ "book": 20, "chapter": 29, "verse_count": 27 },
{ "book": 20, "chapter": 30, "verse_count": 33 },
{ "book": 20, "chapter": 31, "verse_count": 31 },
{ "book": 21, "chapter": 1, "verse_count": 18 },
{ "book": 21, "chapter": 2, "verse_count": 26 },
{ "book": 21, "chapter": 3, "verse_count": 22 },
{ "book": 21, "chapter": 4, "verse_count": 16 },
{ "book": 21, "chapter": 5, "verse_count": 20 },
{ "book": 21, "chapter": 6, "verse_count": 12 },
{ "book": 21, "chapter": 7, "verse_count": 29 },
{ "book": 21, "chapter": 8, "verse_count": 17 },
{ "book": 21, "chapter": 9, "verse_count": 18 },
{ "book": 21, "chapter": 10, "verse_count": 20 },
{ "book": 21, "chapter": 11, "verse_count": 10 },
{ "book": 21, "chapter": 12, "verse_count": 14 },
{ "book": 22, "chapter": 1, "verse_count": 17 },
{ "book": 22, "chapter": 2, "verse_count": 17 },
{ "book": 22, "chapter": 3, "verse_count": 11 },
{ "book": 22, "chapter": 4, "verse_count": 16 },
{ "book": 22, "chapter": 5, "verse_count": 16 },
{ "book": 22, "chapter": 6, "verse_count": 13 },
{ "book": 22, "chapter": 7, "verse_count": 13 },
{ "book": 22, "chapter": 8, "verse_count": 14 },
{ "book": 23, "chapter": 1, "verse_count": 31 },
{ "book": 23, "chapter": 2, "verse_count": 22 },
{ "book": 23, "chapter": 3, "verse_count": 26 },
{ "book": 23, "chapter": 4, "verse_count": 6 },
{ "book": 23, "chapter": 5, "verse_count": 30 },
{ "book": 23, "chapter": 6, "verse_count": 13 },
{ "book": 23, "chapter": 7, "verse_count": 25 },
{ "book": 23, "chapter": 8, "verse_count": 22 },
{ "book": 23, "chapter": 9, "verse_count": 21 },
{ "book": 23, "chapter": 10, "verse_count": 34 },
{ "book": 23, "chapter": 11, "verse_count": 16 },
{ "book": 23, "chapter": 12, "verse_count": 6 },
{ "book": 23, "chapter": 13, "verse_count": 22 },
{ "book": 23, "chapter": 14, "verse_count": 32 },
{ "book": 23, "chapter": 15, "verse_count": 9 },
{ "book": 23, "chapter": 16, "verse_count": 14 },
{ "book": 23, "chapter": 17, "verse_count": 14 },
{ "book": 23, "chapter": 18, "verse_count": 7 },
{ "book": 23, "chapter": 19, "verse_count": 25 },
{ "book": 23, "chapter": 20, "verse_count": 6 },
{ "book": 23, "chapter": 21, "verse_count": 17 },
{ "book": 23, "chapter": 22, "verse_count": 25 },
{ "book": 23, "chapter": 23, "verse_count": 18 },
{ "book": 23, "chapter": 24, "verse_count": 23 },
{ "book": 23, "chapter": 25, "verse_count": 12 },
{ "book": 23, "chapter": 26, "verse_count": 21 },
{ "book": 23, "chapter": 27, "verse_count": 13 },
{ "book": 23, "chapter": 28, "verse_count": 29 },
{ "book": 23, "chapter": 29, "verse_count": 24 },
{ "book": 23, "chapter": 30, "verse_count": 33 },
{ "book": 23, "chapter": 31, "verse_count": 9 },
{ "book": 23, "chapter": 32, "verse_count": 20 },
{ "book": 23, "chapter": 33, "verse_count": 24 },
{ "book": 23, "chapter": 34, "verse_count": 17 },
{ "book": 23, "chapter": 35, "verse_count": 10 },
{ "book": 23, "chapter": 36, "verse_count": 22 },
{ "book": 23, "chapter": 37, "verse_count": 38 },
{ "book": 23, "chapter": 38, "verse_count": 22 },
{ "book": 23, "chapter": 39, "verse_count": 8 },
{ "book": 23, "chapter": 40, "verse_count": 31 },
{ "book": 23, "chapter": 41, "verse_count": 29 },
{ "book": 23, "chapter": 42, "verse_count": 25 },
{ "book": 23, "chapter": 43, "verse_count": 28 },
{ "book": 23, "chapter": 44, "verse_count": 28 },
{ "book": 23, "chapter": 45, "verse_count": 25 },
{ "book": 23, "chapter": 46, "verse_count": 13 },
{ "book": 23, "chapter": 47, "verse_count": 15 },
{ "book": 23, "chapter": 48, "verse_count": 22 },
{ "book": 23, "chapter": 49, "verse_count": 26 },
{ "book": 23, "chapter": 50, "verse_count": 11 },
{ "book": 23, "chapter": 51, "verse_count": 23 },
{ "book": 23, "chapter": 52, "verse_count": 15 },
{ "book": 23, "chapter": 53, "verse_count": 12 },
{ "book": 23, "chapter": 54, "verse_count": 17 },
{ "book": 23, "chapter": 55, "verse_count": 13 },
{ "book": 23, "chapter": 56, "verse_count": 12 },
{ "book": 23, "chapter": 57, "verse_count": 21 },
{ "book": 23, "chapter": 58, "verse_count": 14 },
{ "book": 23, "chapter": 59, "verse_count": 21 },
{ "book": 23, "chapter": 60, "verse_count": 22 },
{ "book": 23, "chapter": 61, "verse_count": 11 },
{ "book": 23, "chapter": 62, "verse_count": 12 },
{ "book": 23, "chapter": 63, "verse_count": 19 },
{ "book": 23, "chapter": 64, "verse_count": 12 },
{ "book": 23, "chapter": 65, "verse_count": 25 },
{ "book": 23, "chapter": 66, "verse_count": 24 },
{ "book": 24, "chapter": 1, "verse_count": 19 },
{ "book": 24, "chapter": 2, "verse_count": 37 },
{ "book": 24, "chapter": 3, "verse_count": 25 },
{ "book": 24, "chapter": 4, "verse_count": 31 },
{ "book": 24, "chapter": 5, "verse_count": 31 },
{ "book": 24, "chapter": 6, "verse_count": 30 },
{ "book": 24, "chapter": 7, "verse_count": 34 },
{ "book": 24, "chapter": 8, "verse_count": 22 },
{ "book": 24, "chapter": 9, "verse_count": 26 },
{ "book": 24, "chapter": 10, "verse_count": 25 },
{ "book": 24, "chapter": 11, "verse_count": 23 },
{ "book": 24, "chapter": 12, "verse_count": 17 },
{ "book": 24, "chapter": 13, "verse_count": 27 },
{ "book": 24, "chapter": 14, "verse_count": 22 },
{ "book": 24, "chapter": 15, "verse_count": 21 },
{ "book": 24, "chapter": 16, "verse_count": 21 },
{ "book": 24, "chapter": 17, "verse_count": 27 },
{ "book": 24, "chapter": 18, "verse_count": 23 },
{ "book": 24, "chapter": 19, "verse_count": 15 },
{ "book": 24, "chapter": 20, "verse_count": 18 },
{ "book": 24, "chapter": 21, "verse_count": 14 },
{ "book": 24, "chapter": 22, "verse_count": 30 },
{ "book": 24, "chapter": 23, "verse_count": 40 },
{ "book": 24, "chapter": 24, "verse_count": 10 },
{ "book": 24, "chapter": 25, "verse_count": 38 },
{ "book": 24, "chapter": 26, "verse_count": 24 },
{ "book": 24, "chapter": 27, "verse_count": 22 },
{ "book": 24, "chapter": 28, "verse_count": 17 },
{ "book": 24, "chapter": 29, "verse_count": 32 },
{ "book": 24, "chapter": 30, "verse_count": 24 },
{ "book": 24, "chapter": 31, "verse_count": 40 },
{ "book": 24, "chapter": 32, "verse_count": 44 },
{ "book": 24, "chapter": 33, "verse_count": 26 },
{ "book": 24, "chapter": 34, "verse_count": 22 },
{ "book": 24, "chapter": 35, "verse_count": 19 },
{ "book": 24, "chapter": 36, "verse_count": 32 },
{ "book": 24, "chapter": 37, "verse_count": 21 },
{ "book": 24, "chapter": 38, "verse_count": 28 },
{ "book": 24, "chapter": 39, "verse_count": 18 },
{ "book": 24, "chapter": 40, "verse_count": 16 },
{ "book": 24, "chapter": 41, "verse_count": 18 },
{ "book": 24, "chapter": 42, "verse_count": 22 },
{ "book": 24, "chapter": 43, "verse_count": 13 },
{ "book": 24, "chapter": 44, "verse_count": 30 },
{ "book": 24, "chapter": 45, "verse_count": 5 },
{ "book": 24, "chapter": 46, "verse_count": 28 },
{ "book": 24, "chapter": 47, "verse_count": 7 },
{ "book": 24, "chapter": 48, "verse_count": 47 },
{ "book": 24, "chapter": 49, "verse_count": 39 },
{ "book": 24, "chapter": 50, "verse_count": 46 },
{ "book": 24, "chapter": 51, "verse_count": 64 },
{ "book": 24, "chapter": 52, "verse_count": 34 },
{ "book": 25, "chapter": 1, "verse_count": 22 },
{ "book": 25, "chapter": 2, "verse_count": 22 },
{ "book": 25, "chapter": 3, "verse_count": 66 },
{ "book": 25, "chapter": 4, "verse_count": 22 },
{ "book": 25, "chapter": 5, "verse_count": 22 },
{ "book": 26, "chapter": 1, "verse_count": 28 },
{ "book": 26, "chapter": 2, "verse_count": 10 },
{ "book": 26, "chapter": 3, "verse_count": 27 },
{ "book": 26, "chapter": 4, "verse_count": 17 },
{ "book": 26, "chapter": 5, "verse_count": 17 },
{ "book": 26, "chapter": 6, "verse_count": 14 },
{ "book": 26, "chapter": 7, "verse_count": 27 },
{ "book": 26, "chapter": 8, "verse_count": 18 },
{ "book": 26, "chapter": 9, "verse_count": 11 },
{ "book": 26, "chapter": 10, "verse_count": 22 },
{ "book": 26, "chapter": 11, "verse_count": 25 },
{ "book": 26, "chapter": 12, "verse_count": 28 },
{ "book": 26, "chapter": 13, "verse_count": 23 },
{ "book": 26, "chapter": 14, "verse_count": 23 },
{ "book": 26, "chapter": 15, "verse_count": 8 },
{ "book": 26, "chapter": 16, "verse_count": 63 },
{ "book": 26, "chapter": 17, "verse_count": 24 },
{ "book": 26, "chapter": 18, "verse_count": 32 },
{ "book": 26, "chapter": 19, "verse_count": 14 },
{ "book": 26, "chapter": 20, "verse_count": 49 },
{ "book": 26, "chapter": 21, "verse_count": 32 },
{ "book": 26, "chapter": 22, "verse_count": 31 },
{ "book": 26, "chapter": 23, "verse_count": 49 },
{ "book": 26, "chapter": 24, "verse_count": 27 },
{ "book": 26, "chapter": 25, "verse_count": 17 },
{ "book": 26, "chapter": 26, "verse_count": 21 },
{ "book": 26, "chapter": 27, "verse_count": 36 },
{ "book": 26, "chapter": 28, "verse_count": 26 },
{ "book": 26, "chapter": 29, "verse_count": 21 },
{ "book": 26, "chapter": 30, "verse_count": 26 },
{ "book": 26, "chapter": 31, "verse_count": 18 },
{ "book": 26, "chapter": 32, "verse_count": 32 },
{ "book": 26, "chapter": 33, "verse_count": 33 },
{ "book": 26, "chapter": 34, "verse_count": 31 },
{ "book": 26, "chapter": 35, "verse_count": 15 },
{ "book": 26, "chapter": 36, "verse_count": 38 },
{ "book": 26, "chapter": 37, "verse_count": 28 },
{ "book": 26, "chapter": 38, "verse_count": 23 },
{ "book": 26, "chapter": 39, "verse_count": 29 },
{ "book": 26, "chapter": 40, "verse_count": 49 },
{ "book": 26, "chapter": 41, "verse_count": 26 },
{ "book": 26, "chapter": 42, "verse_count": 20 },
{ "book": 26, "chapter": 43, "verse_count": 27 },
{ "book": 26, "chapter": 44, "verse_count": 31 },
{ "book": 26, "chapter": 45, "verse_count": 25 },
{ "book": 26, "chapter": 46, "verse_count": 24 },
{ "book": 26, "chapter": 47, "verse_count": 23 },
{ "book": 26, "chapter": 48, "verse_count": 35 },
{ "book": 27, "chapter": 1, "verse_count": 21 },
{ "book": 27, "chapter": 2, "verse_count": 49 },
{ "book": 27, "chapter": 3, "verse_count": 30 },
{ "book": 27, "chapter": 4, "verse_count": 37 },
{ "book": 27, "chapter": 5, "verse_count": 31 },
{ "book": 27, "chapter": 6, "verse_count": 28 },
{ "book": 27, "chapter": 7, "verse_count": 28 },
{ "book": 27, "chapter": 8, "verse_count": 27 },
{ "book": 27, "chapter": 9, "verse_count": 27 },
{ "book": 27, "chapter": 10, "verse_count": 21 },
{ "book": 27, "chapter": 11, "verse_count": 45 },
{ "book": 27, "chapter": 12, "verse_count": 13 },
{ "book": 28, "chapter": 1, "verse_count": 11 },
{ "book": 28, "chapter": 2, "verse_count": 23 },
{ "book": 28, "chapter": 3, "verse_count": 5 },
{ "book": 28, "chapter": 4, "verse_count": 19 },
{ "book": 28, "chapter": 5, "verse_count": 15 },
{ "book": 28, "chapter": 6, "verse_count": 11 },
{ "book": 28, "chapter": 7, "verse_count": 16 },
{ "book": 28, "chapter": 8, "verse_count": 14 },
{ "book": 28, "chapter": 9, "verse_count": 17 },
{ "book": 28, "chapter": 10, "verse_count": 15 },
{ "book": 28, "chapter": 11, "verse_count": 12 },
{ "book": 28, "chapter": 12, "verse_count": 14 },
{ "book": 28, "chapter": 13, "verse_count": 16 },
{ "book": 28, "chapter": 14, "verse_count": 9 },
{ "book": 29, "chapter": 1, "verse_count": 20 },
{ "book": 29, "chapter": 2, "verse_count": 32 },
{ "book": 29, "chapter": 3, "verse_count": 21 },
{ "book": 30, "chapter": 1, "verse_count": 15 },
{ "book": 30, "chapter": 2, "verse_count": 16 },
{ "book": 30, "chapter": 3, "verse_count": 15 },
{ "book": 30, "chapter": 4, "verse_count": 13 },
{ "book": 30, "chapter": 5, "verse_count": 27 },
{ "book": 30, "chapter": 6, "verse_count": 14 },
{ "book": 30, "chapter": 7, "verse_count": 17 },
{ "book": 30, "chapter": 8, "verse_count": 14 },
{ "book": 30, "chapter": 9, "verse_count": 15 },
{ "book": 31, "chapter": 1, "verse_count": 21 },
{ "book": 32, "chapter": 1, "verse_count": 17 },
{ "book": 32, "chapter": 2, "verse_count": 10 },
{ "book": 32, "chapter": 3, "verse_count": 10 },
{ "book": 32, "chapter": 4, "verse_count": 11 },
{ "book": 33, "chapter": 1, "verse_count": 16 },
{ "book": 33, "chapter": 2, "verse_count": 13 },
{ "book": 33, "chapter": 3, "verse_count": 12 },
{ "book": 33, "chapter": 4, "verse_count": 13 },
{ "book": 33, "chapter": 5, "verse_count": 15 },
{ "book": 33, "chapter": 6, "verse_count": 16 },
{ "book": 33, "chapter": 7, "verse_count": 20 },
{ "book": 34, "chapter": 1, "verse_count": 15 },
{ "book": 34, "chapter": 2, "verse_count": 13 },
{ "book": 34, "chapter": 3, "verse_count": 19 },
{ "book": 35, "chapter": 1, "verse_count": 17 },
{ "book": 35, "chapter": 2, "verse_count": 20 },
{ "book": 35, "chapter": 3, "verse_count": 19 },
{ "book": 36, "chapter": 1, "verse_count": 18 },
{ "book": 36, "chapter": 2, "verse_count": 15 },
{ "book": 36, "chapter": 3, "verse_count": 20 },
{ "book": 37, "chapter": 1, "verse_count": 15 },
{ "book": 37, "chapter": 2, "verse_count": 23 },
{ "book": 38, "chapter": 1, "verse_count": 21 },
{ "book": 38, "chapter": 2, "verse_count": 13 },
{ "book": 38, "chapter": 3, "verse_count": 10 },
{ "book": 38, "chapter": 4, "verse_count": 14 },
{ "book": 38, "chapter": 5, "verse_count": 11 },
{ "book": 38, "chapter": 6, "verse_count": 15 },
{ "book": 38, "chapter": 7, "verse_count": 14 },
{ "book": 38, "chapter": 8, "verse_count": 23 },
{ "book": 38, "chapter": 9, "verse_count": 17 },
{ "book": 38, "chapter": 10, "verse_count": 12 },
{ "book": 38, "chapter": 11, "verse_count": 17 },
{ "book": 38, "chapter": 12, "verse_count": 14 },
{ "book": 38, "chapter": 13, "verse_count": 9 },
{ "book": 38, "chapter": 14, "verse_count": 21 },
{ "book": 39, "chapter": 1, "verse_count": 14 },
{ "book": 39, "chapter": 2, "verse_count": 17 },
{ "book": 39, "chapter": 3, "verse_count": 18 },
{ "book": 39, "chapter": 4, "verse_count": 6 },
{ "book": 40, "chapter": 1, "verse_count": 25 },
{ "book": 40, "chapter": 2, "verse_count": 23 },
{ "book": 40, "chapter": 3, "verse_count": 17 },
{ "book": 40, "chapter": 4, "verse_count": 25 },
{ "book": 40, "chapter": 5, "verse_count": 48 },
{ "book": 40, "chapter": 6, "verse_count": 34 },
{ "book": 40, "chapter": 7, "verse_count": 29 },
{ "book": 40, "chapter": 8, "verse_count": 34 },
{ "book": 40, "chapter": 9, "verse_count": 38 },
{ "book": 40, "chapter": 10, "verse_count": 42 },
{ "book": 40, "chapter": 11, "verse_count": 30 },
{ "book": 40, "chapter": 12, "verse_count": 50 },
{ "book": 40, "chapter": 13, "verse_count": 58 },
{ "book": 40, "chapter": 14, "verse_count": 36 },
{ "book": 40, "chapter": 15, "verse_count": 39 },
{ "book": 40, "chapter": 16, "verse_count": 28 },
{ "book": 40, "chapter": 17, "verse_count": 27 },
{ "book": 40, "chapter": 18, "verse_count": 35 },
{ "book": 40, "chapter": 19, "verse_count": 30 },
{ "book": 40, "chapter": 20, "verse_count": 34 },
{ "book": 40, "chapter": 21, "verse_count": 46 },
{ "book": 40, "chapter": 22, "verse_count": 46 },
{ "book": 40, "chapter": 23, "verse_count": 39 },
{ "book": 40, "chapter": 24, "verse_count": 51 },
{ "book": 40, "chapter": 25, "verse_count": 46 },
{ "book": 40, "chapter": 26, "verse_count": 75 },
{ "book": 40, "chapter": 27, "verse_count": 66 },
{ "book": 40, "chapter": 28, "verse_count": 20 },
{ "book": 41, "chapter": 1, "verse_count": 45 },
{ "book": 41, "chapter": 2, "verse_count": 28 },
{ "book": 41, "chapter": 3, "verse_count": 35 },
{ "book": 41, "chapter": 4, "verse_count": 41 },
{ "book": 41, "chapter": 5, "verse_count": 43 },
{ "book": 41, "chapter": 6, "verse_count": 56 },
{ "book": 41, "chapter": 7, "verse_count": 37 },
{ "book": 41, "chapter": 8, "verse_count": 38 },
{ "book": 41, "chapter": 9, "verse_count": 50 },
{ "book": 41, "chapter": 10, "verse_count": 52 },
{ "book": 41, "chapter": 11, "verse_count": 33 },
{ "book": 41, "chapter": 12, "verse_count": 44 },
{ "book": 41, "chapter": 13, "verse_count": 37 },
{ "book": 41, "chapter": 14, "verse_count": 72 },
{ "book": 41, "chapter": 15, "verse_count": 47 },
{ "book": 41, "chapter": 16, "verse_count": 20 },
{ "book": 42, "chapter": 1, "verse_count": 80 },
{ "book": 42, "chapter": 2, "verse_count": 52 },
{ "book": 42, "chapter": 3, "verse_count": 38 },
{ "book": 42, "chapter": 4, "verse_count": 44 },
{ "book": 42, "chapter": 5, "verse_count": 39 },
{ "book": 42, "chapter": 6, "verse_count": 49 },
{ "book": 42, "chapter": 7, "verse_count": 50 },
{ "book": 42, "chapter": 8, "verse_count": 56 },
{ "book": 42, "chapter": 9, "verse_count": 62 },
{ "book": 42, "chapter": 10, "verse_count": 42 },
{ "book": 42, "chapter": 11, "verse_count": 54 },
{ "book": 42, "chapter": 12, "verse_count": 59 },
{ "book": 42, "chapter": 13, "verse_count": 35 },
{ "book": 42, "chapter": 14, "verse_count": 35 },
{ "book": 42, "chapter": 15, "verse_count": 32 },
{ "book": 42, "chapter": 16, "verse_count": 31 },
{ "book": 42, "chapter": 17, "verse_count": 37 },
{ "book": 42, "chapter": 18, "verse_count": 43 },
{ "book": 42, "chapter": 19, "verse_count": 48 },
{ "book": 42, "chapter": 20, "verse_count": 47 },
{ "book": 42, "chapter": 21, "verse_count": 38 },
{ "book": 42, "chapter": 22, "verse_count": 71 },
{ "book": 42, "chapter": 23, "verse_count": 56 },
{ "book": 42, "chapter": 24, "verse_count": 53 },
{ "book": 43, "chapter": 1, "verse_count": 51 },
{ "book": 43, "chapter": 2, "verse_count": 25 },
{ "book": 43, "chapter": 3, "verse_count": 36 },
{ "book": 43, "chapter": 4, "verse_count": 54 },
{ "book": 43, "chapter": 5, "verse_count": 47 },
{ "book": 43, "chapter": 6, "verse_count": 71 },
{ "book": 43, "chapter": 7, "verse_count": 53 },
{ "book": 43, "chapter": 8, "verse_count": 59 },
{ "book": 43, "chapter": 9, "verse_count": 41 },
{ "book": 43, "chapter": 10, "verse_count": 42 },
{ "book": 43, "chapter": 11, "verse_count": 57 },
{ "book": 43, "chapter": 12, "verse_count": 50 },
{ "book": 43, "chapter": 13, "verse_count": 38 },
{ "book": 43, "chapter": 14, "verse_count": 31 },
{ "book": 43, "chapter": 15, "verse_count": 27 },
{ "book": 43, "chapter": 16, "verse_count": 33 },
{ "book": 43, "chapter": 17, "verse_count": 26 },
{ "book": 43, "chapter": 18, "verse_count": 40 },
{ "book": 43, "chapter": 19, "verse_count": 42 },
{ "book": 43, "chapter": 20, "verse_count": 31 },
{ "book": 43, "chapter": 21, "verse_count": 25 },
{ "book": 44, "chapter": 1, "verse_count": 26 },
{ "book": 44, "chapter": 2, "verse_count": 47 },
{ "book": 44, "chapter": 3, "verse_count": 26 },
{ "book": 44, "chapter": 4, "verse_count": 37 },
{ "book": 44, "chapter": 5, "verse_count": 42 },
{ "book": 44, "chapter": 6, "verse_count": 15 },
{ "book": 44, "chapter": 7, "verse_count": 60 },
{ "book": 44, "chapter": 8, "verse_count": 40 },
{ "book": 44, "chapter": 9, "verse_count": 43 },
{ "book": 44, "chapter": 10, "verse_count": 48 },
{ "book": 44, "chapter": 11, "verse_count": 30 },
{ "book": 44, "chapter": 12, "verse_count": 25 },
{ "book": 44, "chapter": 13, "verse_count": 52 },
{ "book": 44, "chapter": 14, "verse_count": 28 },
{ "book": 44, "chapter": 15, "verse_count": 41 },
{ "book": 44, "chapter": 16, "verse_count": 40 },
{ "book": 44, "chapter": 17, "verse_count": 34 },
{ "book": 44, "chapter": 18, "verse_count": 28 },
{ "book": 44, "chapter": 19, "verse_count": 41 },
{ "book": 44, "chapter": 20, "verse_count": 38 },
{ "book": 44, "chapter": 21, "verse_count": 40 },
{ "book": 44, "chapter": 22, "verse_count": 30 },
{ "book": 44, "chapter": 23, "verse_count": 35 },
{ "book": 44, "chapter": 24, "verse_count": 27 },
{ "book": 44, "chapter": 25, "verse_count": 27 },
{ "book": 44, "chapter": 26, "verse_count": 32 },
{ "book": 44, "chapter": 27, "verse_count": 44 },
{ "book": 44, "chapter": 28, "verse_count": 31 },
{ "book": 45, "chapter": 1, "verse_count": 32 },
{ "book": 45, "chapter": 2, "verse_count": 29 },
{ "book": 45, "chapter": 3, "verse_count": 31 },
{ "book": 45, "chapter": 4, "verse_count": 25 },
{ "book": 45, "chapter": 5, "verse_count": 21 },
{ "book": 45, "chapter": 6, "verse_count": 23 },
{ "book": 45, "chapter": 7, "verse_count": 25 },
{ "book": 45, "chapter": 8, "verse_count": 39 },
{ "book": 45, "chapter": 9, "verse_count": 33 },
{ "book": 45, "chapter": 10, "verse_count": 21 },
{ "book": 45, "chapter": 11, "verse_count": 36 },
{ "book": 45, "chapter": 12, "verse_count": 21 },
{ "book": 45, "chapter": 13, "verse_count": 14 },
{ "book": 45, "chapter": 14, "verse_count": 23 },
{ "book": 45, "chapter": 15, "verse_count": 33 },
{ "book": 45, "chapter": 16, "verse_count": 27 },
{ "book": 46, "chapter": 1, "verse_count": 31 },
{ "book": 46, "chapter": 2, "verse_count": 16 },
{ "book": 46, "chapter": 3, "verse_count": 23 },
{ "book": 46, "chapter": 4, "verse_count": 21 },
{ "book": 46, "chapter": 5, "verse_count": 13 },
{ "book": 46, "chapter": 6, "verse_count": 20 },
{ "book": 46, "chapter": 7, "verse_count": 40 },
{ "book": 46, "chapter": 8, "verse_count": 13 },
{ "book": 46, "chapter": 9, "verse_count": 27 },
{ "book": 46, "chapter": 10, "verse_count": 33 },
{ "book": 46, "chapter": 11, "verse_count": 34 },
{ "book": 46, "chapter": 12, "verse_count": 31 },
{ "book": 46, "chapter": 13, "verse_count": 13 },
{ "book": 46, "chapter": 14, "verse_count": 40 },
{ "book": 46, "chapter": 15, "verse_count": 58 },
{ "book": 46, "chapter": 16, "verse_count": 24 },
{ "book": 47, "chapter": 1, "verse_count": 24 },
{ "book": 47, "chapter": 2, "verse_count": 17 },
{ "book": 47, "chapter": 3, "verse_count": 18 },
{ "book": 47, "chapter": 4, "verse_count": 18 },
{ "book": 47, "chapter": 5, "verse_count": 21 },
{ "book": 47, "chapter": 6, "verse_count": 18 },
{ "book": 47, "chapter": 7, "verse_count": 16 },
{ "book": 47, "chapter": 8, "verse_count": 24 },
{ "book": 47, "chapter": 9, "verse_count": 15 },
{ "book": 47, "chapter": 10, "verse_count": 18 },
{ "book": 47, "chapter": 11, "verse_count": 33 },
{ "book": 47, "chapter": 12, "verse_count": 21 },
{ "book": 47, "chapter": 13, "verse_count": 14 },
{ "book": 48, "chapter": 1, "verse_count": 24 },
{ "book": 48, "chapter": 2, "verse_count": 21 },
{ "book": 48, "chapter": 3, "verse_count": 29 },
{ "book": 48, "chapter": 4, "verse_count": 31 },
{ "book": 48, "chapter": 5, "verse_count": 26 },
{ "book": 48, "chapter": 6, "verse_count": 18 },
{ "book": 49, "chapter": 1, "verse_count": 23 },
{ "book": 49, "chapter": 2, "verse_count": 22 },
{ "book": 49, "chapter": 3, "verse_count": 21 },
{ "book": 49, "chapter": 4, "verse_count": 32 },
{ "book": 49, "chapter": 5, "verse_count": 33 },
{ "book": 49, "chapter": 6, "verse_count": 24 },
{ "book": 50, "chapter": 1, "verse_count": 30 },
{ "book": 50, "chapter": 2, "verse_count": 30 },
{ "book": 50, "chapter": 3, "verse_count": 21 },
{ "book": 50, "chapter": 4, "verse_count": 23 },
{ "book": 51, "chapter": 1, "verse_count": 29 },
{ "book": 51, "chapter": 2, "verse_count": 23 },
{ "book": 51, "chapter": 3, "verse_count": 25 },
{ "book": 51, "chapter": 4, "verse_count": 18 },
{ "book": 52, "chapter": 1, "verse_count": 10 },
{ "book": 52, "chapter": 2, "verse_count": 20 },
{ "book": 52, "chapter": 3, "verse_count": 13 },
{ "book": 52, "chapter": 4, "verse_count": 18 },
{ "book": 52, "chapter": 5, "verse_count": 28 },
{ "book": 53, "chapter": 1, "verse_count": 12 },
{ "book": 53, "chapter": 2, "verse_count": 17 },
{ "book": 53, "chapter": 3, "verse_count": 18 },
{ "book": 54, "chapter": 1, "verse_count": 20 },
{ "book": 54, "chapter": 2, "verse_count": 15 },
{ "book": 54, "chapter": 3, "verse_count": 16 },
{ "book": 54, "chapter": 4, "verse_count": 16 },
{ "book": 54, "chapter": 5, "verse_count": 25 },
{ "book": 54, "chapter": 6, "verse_count": 21 },
{ "book": 55, "chapter": 1, "verse_count": 18 },
{ "book": 55, "chapter": 2, "verse_count": 26 },
{ "book": 55, "chapter": 3, "verse_count": 17 },
{ "book": 55, "chapter": 4, "verse_count": 22 },
{ "book": 56, "chapter": 1, "verse_count": 16 },
{ "book": 56, "chapter": 2, "verse_count": 15 },
{ "book": 56, "chapter": 3, "verse_count": 15 },
{ "book": 57, "chapter": 1, "verse_count": 25 },
{ "book": 58, "chapter": 1, "verse_count": 14 },
{ "book": 58, "chapter": 2, "verse_count": 18 },
{ "book": 58, "chapter": 3, "verse_count": 19 },
{ "book": 58, "chapter": 4, "verse_count": 16 },
{ "book": 58, "chapter": 5, "verse_count": 14 },
{ "book": 58, "chapter": 6, "verse_count": 20 },
{ "book": 58, "chapter": 7, "verse_count": 28 },
{ "book": 58, "chapter": 8, "verse_count": 13 },
{ "book": 58, "chapter": 9, "verse_count": 28 },
{ "book": 58, "chapter": 10, "verse_count": 39 },
{ "book": 58, "chapter": 11, "verse_count": 40 },
{ "book": 58, "chapter": 12, "verse_count": 29 },
{ "book": 58, "chapter": 13, "verse_count": 25 },
{ "book": 59, "chapter": 1, "verse_count": 27 },
{ "book": 59, "chapter": 2, "verse_count": 26 },
{ "book": 59, "chapter": 3, "verse_count": 18 },
{ "book": 59, "chapter": 4, "verse_count": 17 },
{ "book": 59, "chapter": 5, "verse_count": 20 },
{ "book": 60, "chapter": 1, "verse_count": 25 },
{ "book": 60, "chapter": 2, "verse_count": 25 },
{ "book": 60, "chapter": 3, "verse_count": 22 },
{ "book": 60, "chapter": 4, "verse_count": 19 },
{ "book": 60, "chapter": 5, "verse_count": 14 },
{ "book": 61, "chapter": 1, "verse_count": 21 },
{ "book": 61, "chapter": 2, "verse_count": 22 },
{ "book": 61, "chapter": 3, "verse_count": 18 },
{ "book": 62, "chapter": 1, "verse_count": 10 },
{ "book": 62, "chapter": 2, "verse_count": 29 },
{ "book": 62, "chapter": 3, "verse_count": 24 },
{ "book": 62, "chapter": 4, "verse_count": 21 },
{ "book": 62, "chapter": 5, "verse_count": 21 },
{ "book": 63, "chapter": 1, "verse_count": 13 },
{ "book": 64, "chapter": 1, "verse_count": 14 },
{ "book": 65, "chapter": 1, "verse_count": 25 },
{ "book": 66, "chapter": 1, "verse_count": 20 },
{ "book": 66, "chapter": 2, "verse_count": 29 },
{ "book": 66, "chapter": 3, "verse_count": 22 },
{ "book": 66, "chapter": 4, "verse_count": 11 },
{ "book": 66, "chapter": 5, "verse_count": 14 },
{ "book": 66, "chapter": 6, "verse_count": 17 },
{ "book": 66, "chapter": 7, "verse_count": 17 },
{ "book": 66, "chapter": 8, "verse_count": 13 },
{ "book": 66, "chapter": 9, "verse_count": 21 },
{ "book": 66, "chapter": 10, "verse_count": 11 },
{ "book": 66, "chapter": 11, "verse_count": 19 },
{ "book": 66, "chapter": 12, "verse_count": 17 },
{ "book": 66, "chapter": 13, "verse_count": 18 },
{ "book": 66, "chapter": 14, "verse_count": 20 },
{ "book": 66, "chapter": 15, "verse_count": 8 },
{ "book": 66, "chapter": 16, "verse_count": 21 },
{ "book": 66, "chapter": 17, "verse_count": 18 },
{ "book": 66, "chapter": 18, "verse_count": 24 },
{ "book": 66, "chapter": 19, "verse_count": 21 },
{ "book": 66, "chapter": 20, "verse_count": 15 },
{ "book": 66, "chapter": 21, "verse_count": 27 },
{ "book": 66, "chapter": 22, "verse_count": 21 }]


def make_verse_id(book, chapter, verse):
    """Create a verse ID string from book, chapter, and verse numbers (e.g., '1.1.1' for Genesis 1:1)"""
    return f"{book}.{chapter}.{verse}"


def get_verse_count_for_chapter(book, chapter):
    """Get verse count for a specific book and chapter"""
    for vc in verse_counts:
        if vc['book'] == book and vc['chapter'] == chapter:
            return vc['verse_count']
    return None


def expand_verse_range(start_book, start_chapter, start_verse, end_book, end_chapter, end_verse):
    """
    Expand a verse range into individual verses.
    Returns a list of (book, chapter, verse) tuples.
    """
    verses = []
    
    # Single verse
    if start_book == end_book and start_chapter == end_chapter and start_verse == end_verse:
        return [(start_book, start_chapter, start_verse)]
    
    # Same book, same chapter
    if start_book == end_book and start_chapter == end_chapter:
        for v in range(start_verse, end_verse + 1):
            verses.append((start_book, start_chapter, v))
        return verses
    
    # Same book, different chapters
    if start_book == end_book:
        # First chapter: start_verse to end of chapter
        verse_count = get_verse_count_for_chapter(start_book, start_chapter)
        if verse_count:
            for v in range(start_verse, verse_count + 1):
                verses.append((start_book, start_chapter, v))
        else:
            # No verse count data, just add the start verse
            verses.append((start_book, start_chapter, start_verse))
        
        # Middle chapters: all verses
        for ch in range(start_chapter + 1, end_chapter):
            verse_count = get_verse_count_for_chapter(start_book, ch)
            if verse_count:
                for v in range(1, verse_count + 1):
                    verses.append((start_book, ch, v))
        
        # Last chapter: 1 to end_verse
        for v in range(1, end_verse + 1):
            verses.append((end_book, end_chapter, v))
        
        return verses
    
    # Different books - more complex
    # First book, starting chapter to end of chapter
    verse_count = get_verse_count_for_chapter(start_book, start_chapter)
    if verse_count:
        for v in range(start_verse, verse_count + 1):
            verses.append((start_book, start_chapter, v))
    else:
        verses.append((start_book, start_chapter, start_verse))
    
    # First book, remaining chapters
    current_chapter = start_chapter + 1
    while True:
        verse_count = get_verse_count_for_chapter(start_book, current_chapter)
        if verse_count is None:
            break  # No more chapters in this book
        for v in range(1, verse_count + 1):
            verses.append((start_book, current_chapter, v))
        current_chapter += 1
    
    # Middle books: all chapters and verses
    for book in range(start_book + 1, end_book):
        current_chapter = 1
        while True:
            verse_count = get_verse_count_for_chapter(book, current_chapter)
            if verse_count is None:
                break  # No more chapters in this book
            for v in range(1, verse_count + 1):
                verses.append((book, current_chapter, v))
            current_chapter += 1
    
    # Last book, chapters before end_chapter
    for ch in range(1, end_chapter):
        verse_count = get_verse_count_for_chapter(end_book, ch)
        if verse_count:
            for v in range(1, verse_count + 1):
                verses.append((end_book, ch, v))
    
    # Last book, end chapter: 1 to end_verse
    for v in range(1, end_verse + 1):
        verses.append((end_book, end_chapter, v))
    
    return verses


def backup_database(db_path):
    """Create a backup of the database file"""
    backup_path = db_path.replace('.bdb', '_backup.bdb')
    shutil.copy2(db_path, backup_path)
    print(f"✓ Backup created: {backup_path}")
    return backup_path


def rename_old_tables(cursor):
    """Rename old tables to temporary names"""
    print("Renaming old tables to temporary names...")
    
    old_tables = ['verses', 'tags', 'notes', 'verse_tags', 'verse_notes', 'tag_notes', 'tag_tags']
    
    for table in old_tables:
        cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_temp")
        print(f"  Renamed {table} to {table}_temp")
    
    print("Old tables renamed")


def create_new_schema(cursor):
    """Create the new schema tables"""
    print("Creating new schema tables...")
    
    # Create verse table
    cursor.execute('''
        CREATE TABLE verse (
            verse_id TEXT PRIMARY KEY,
            book INTEGER NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL
        )
    ''')
    
    # Create verse_group table
    cursor.execute('''
        CREATE TABLE verse_group (
            verse_group_id INTEGER NOT NULL,
            verse_id TEXT NOT NULL,
            FOREIGN KEY (verse_id) REFERENCES verse(verse_id)
        )
    ''')
    
    # Create tag table
    cursor.execute('''
        CREATE TABLE tag (
            tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Create note table
    cursor.execute('''
        CREATE TABLE note (
            note_id INTEGER PRIMARY KEY AUTOINCREMENT,
            note TEXT NOT NULL
        )
    ''')
    
    # Create verse_group_tag junction table
    cursor.execute('''
        CREATE TABLE verse_group_tag (
            verse_group_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            FOREIGN KEY (verse_group_id) REFERENCES verse_group(verse_group_id),
            FOREIGN KEY (tag_id) REFERENCES tag(tag_id),
            PRIMARY KEY (verse_group_id, tag_id)
        )
    ''')
    
    # Create verse_group_note junction table
    cursor.execute('''
        CREATE TABLE verse_group_note (
            verse_group_id INTEGER NOT NULL,
            note_id INTEGER NOT NULL,
            FOREIGN KEY (verse_group_id) REFERENCES verse_group(verse_group_id),
            FOREIGN KEY (note_id) REFERENCES note(note_id),
            PRIMARY KEY (verse_group_id, note_id)
        )
    ''')
    
    # Create tag_note junction table
    cursor.execute('''
        CREATE TABLE tag_note (
            tag_id INTEGER NOT NULL,
            note_id INTEGER NOT NULL,
            FOREIGN KEY (tag_id) REFERENCES tag(tag_id),
            FOREIGN KEY (note_id) REFERENCES note(note_id),
            PRIMARY KEY (tag_id, note_id)
        )
    ''')
    
    # Create tag_tag junction table
    cursor.execute('''
        CREATE TABLE tag_tag (
            tag_1_id INTEGER NOT NULL,
            tag_2_id INTEGER NOT NULL,
            FOREIGN KEY (tag_1_id) REFERENCES tag(tag_id),
            FOREIGN KEY (tag_2_id) REFERENCES tag(tag_id),
            PRIMARY KEY (tag_1_id, tag_2_id)
        )
    ''')
    
    print("✓ New schema tables created")

def migrate_data(cursor):
    """Migrate all data from old schema to new schema"""
    print("\n" + "=" * 60)
    print("MIGRATING DATA")
    print("=" * 60)
    
    # Mapping dictionaries
    old_to_new_tag_map = {}
    old_to_new_note_map = {}
    old_verse_to_group_map = {}
    
    # 1. Migrate tags
    print("\n1. Migrating tags...")
    cursor.execute("SELECT id, tag FROM tags_temp")
    old_tags = cursor.fetchall()
    
    for old_id, tag_text in old_tags:
        cursor.execute("INSERT OR IGNORE INTO tag (tag) VALUES (?)", (tag_text,))
        cursor.execute("SELECT tag_id FROM tag WHERE tag = ?", (tag_text,))
        new_id = cursor.fetchone()[0]
        old_to_new_tag_map[old_id] = new_id
    
    print(f"   ✓ Migrated {len(old_tags)} tags")
    
    # 2. Migrate notes
    print("\n2. Migrating notes...")
    cursor.execute("SELECT id, note FROM notes_temp")
    old_notes = cursor.fetchall()
    
    for old_id, note_text in old_notes:
        cursor.execute("INSERT INTO note (note) VALUES (?)", (note_text,))
        new_id = cursor.lastrowid
        old_to_new_note_map[old_id] = new_id
    
    print(f"   ✓ Migrated {len(old_notes)} notes")
    
    # 3. Migrate verses (create verse_groups)
    print("\n3. Migrating verses...")
    cursor.execute("SELECT id, start_book, start_chapter, start_verse, end_book, end_chapter, end_verse FROM verses_temp")
    old_verses = cursor.fetchall()
    
    verse_group_counter = 1
    total_individual_verses = 0
    
    for old_verse_id, sb, sc, sv, eb, ec, ev in old_verses:
        # Create a verse_group for this verse range
        verse_group_id = verse_group_counter
        verse_group_counter += 1
        old_verse_to_group_map[old_verse_id] = verse_group_id
        
        # Expand verse range into individual verses
        all_verses = expand_verse_range(sb, sc, sv, eb, ec, ev)
        total_individual_verses += len(all_verses)
        
        for book, chapter, verse in all_verses:
            verse_id = make_verse_id(book, chapter, verse)
            
            # Insert into verse table (ignore if already exists)
            cursor.execute('''
                INSERT OR IGNORE INTO verse (verse_id, book, chapter, verse)
                VALUES (?, ?, ?, ?)
            ''', (verse_id, book, chapter, verse))
            
            # Insert into verse_group table
            cursor.execute('''
                INSERT INTO verse_group (verse_group_id, verse_id)
                VALUES (?, ?)
            ''', (verse_group_id, verse_id))
    
    print(f"   ✓ Migrated {len(old_verses)} verse ranges into {verse_group_counter - 1} verse groups")
    print(f"   ✓ Total individual verses: {total_individual_verses}")
    
    # 4. Migrate verse-tag relationships
    print("\n4. Migrating verse-tag relationships...")
    cursor.execute("SELECT verse_id, tag_id FROM verse_tags_temp")
    verse_tags = cursor.fetchall()
    
    migrated_count = 0
    skipped_count = 0
    skipped_details = []
    
    for old_verse_id, old_tag_id in verse_tags:
        verse_group_id = old_verse_to_group_map.get(old_verse_id)
        new_tag_id = old_to_new_tag_map.get(old_tag_id)
        
        if verse_group_id and new_tag_id:
            cursor.execute('''
                INSERT OR IGNORE INTO verse_group_tag (verse_group_id, tag_id)
                VALUES (?, ?)
            ''', (verse_group_id, new_tag_id))
            migrated_count += 1
        else:
            skipped_count += 1
            # Get verse reference
            cursor.execute("SELECT start_book, start_chapter, start_verse, end_book, end_chapter, end_verse FROM verses_temp WHERE id = ?", (old_verse_id,))
            verse_info = cursor.fetchone()
            verse_ref = f"{verse_info[0]}:{verse_info[1]}:{verse_info[2]}" if verse_info else f"ID:{old_verse_id}"
            if verse_info and verse_info[0:3] != verse_info[3:6]:
                verse_ref += f"-{verse_info[3]}:{verse_info[4]}:{verse_info[5]}"
            
            # Get tag text
            cursor.execute("SELECT tag FROM tags_temp WHERE id = ?", (old_tag_id,))
            tag_info = cursor.fetchone()
            tag_text = tag_info[0] if tag_info else f"ID:{old_tag_id}"
            
            reason = []
            if not verse_group_id:
                reason.append("verse not found")
            if not new_tag_id:
                reason.append("tag not found")
            
            skipped_details.append((verse_ref, tag_text, ", ".join(reason)))
    
    print(f"   ✓ Migrated {migrated_count} of {len(verse_tags)} verse-tag relationships")
    if skipped_count > 0:
        print(f"\n   ⚠ WARNING: Skipped {skipped_count} verse-tag relationships:")
        for verse_ref, tag_text, reason in skipped_details:
            print(f"      - Tag '{tag_text}' on verse {verse_ref} ({reason})")
        print()
    
    # 5. Migrate verse-note relationships
    print("\n5. Migrating verse-note relationships...")
    cursor.execute("SELECT verse_id, note_id FROM verse_notes_temp")
    verse_notes = cursor.fetchall()
    
    migrated_count = 0
    skipped_count = 0
    skipped_details = []
    
    for old_verse_id, old_note_id in verse_notes:
        verse_group_id = old_verse_to_group_map.get(old_verse_id)
        new_note_id = old_to_new_note_map.get(old_note_id)
        
        if verse_group_id and new_note_id:
            cursor.execute('''
                INSERT OR IGNORE INTO verse_group_note (verse_group_id, note_id)
                VALUES (?, ?)
            ''', (verse_group_id, new_note_id))
            migrated_count += 1
        else:
            skipped_count += 1
            # Get verse reference
            cursor.execute("SELECT start_book, start_chapter, start_verse, end_book, end_chapter, end_verse FROM verses_temp WHERE id = ?", (old_verse_id,))
            verse_info = cursor.fetchone()
            verse_ref = f"{verse_info[0]}:{verse_info[1]}:{verse_info[2]}" if verse_info else f"ID:{old_verse_id}"
            if verse_info and verse_info[0:3] != verse_info[3:6]:
                verse_ref += f"-{verse_info[3]}:{verse_info[4]}:{verse_info[5]}"
            
            # Get note text (truncated)
            cursor.execute("SELECT note FROM notes_temp WHERE id = ?", (old_note_id,))
            note_info = cursor.fetchone()
            note_text = note_info[0] if note_info else f"ID:{old_note_id}"

            reason = []
            if not verse_group_id:
                reason.append("verse not found")
            if not new_note_id:
                reason.append("note not found")
            
            skipped_details.append((verse_ref, note_text, ", ".join(reason)))
    
    print(f"   ✓ Migrated {migrated_count} of {len(verse_notes)} verse-note relationships")
    if skipped_count > 0:
        print(f"\n   ⚠ WARNING: Skipped {skipped_count} verse-note relationships:")
        for verse_ref, note_text, reason in skipped_details:
            print(f"      - Note '{note_text}' on verse {verse_ref} ({reason})")
        print()
    
    # 6. Migrate tag-note relationships
    print("\n6. Migrating tag-note relationships...")
    cursor.execute("SELECT tag_id, note_id FROM tag_notes_temp")
    tag_notes = cursor.fetchall()
    
    migrated_count = 0
    skipped_count = 0
    skipped_details = []
    
    for old_tag_id, old_note_id in tag_notes:
        new_tag_id = old_to_new_tag_map.get(old_tag_id)
        new_note_id = old_to_new_note_map.get(old_note_id)
        
        if new_tag_id and new_note_id:
            cursor.execute('''
                INSERT OR IGNORE INTO tag_note (tag_id, note_id)
                VALUES (?, ?)
            ''', (new_tag_id, new_note_id))
            migrated_count += 1
        else:
            skipped_count += 1
            # Get tag text
            cursor.execute("SELECT tag FROM tags_temp WHERE id = ?", (old_tag_id,))
            tag_info = cursor.fetchone()
            tag_text = tag_info[0] if tag_info else f"ID:{old_tag_id}"
            
            # Get note text (truncated)
            cursor.execute("SELECT note FROM notes_temp WHERE id = ?", (old_note_id,))
            note_info = cursor.fetchone()
            note_text = note_info[0] if note_info else f"ID:{old_note_id}"
            
            reason = []
            if not new_tag_id:
                reason.append("tag not found")
            if not new_note_id:
                reason.append("note not found")
            
            skipped_details.append((tag_text, note_text, ", ".join(reason)))
    
    print(f"   ✓ Migrated {migrated_count} of {len(tag_notes)} tag-note relationships")
    if skipped_count > 0:
        print(f"\n   ⚠ WARNING: Skipped {skipped_count} tag-note relationships:")
        for tag_text, note_text, reason in skipped_details:
            print(f"      - Tag '{tag_text}' linked to note '{note_text}' ({reason})")
        print()
    
    # 7. Migrate tag-tag relationships
    print("\n7. Migrating tag-tag relationships...")
    cursor.execute("SELECT tag1_id, tag2_id FROM tag_tags_temp")
    tag_tags = cursor.fetchall()
    
    migrated_count = 0
    skipped_count = 0
    skipped_details = []
    
    for old_tag_1_id, old_tag_2_id in tag_tags:
        new_tag_1_id = old_to_new_tag_map.get(old_tag_1_id)
        new_tag_2_id = old_to_new_tag_map.get(old_tag_2_id)
        
        if new_tag_1_id and new_tag_2_id:
            cursor.execute('''
                INSERT OR IGNORE INTO tag_tag (tag_1_id, tag_2_id)
                VALUES (?, ?)
            ''', (new_tag_1_id, new_tag_2_id))
            migrated_count += 1
        else:
            skipped_count += 1
            # Get tag texts
            cursor.execute("SELECT tag FROM tags_temp WHERE id = ?", (old_tag_1_id,))
            tag1_info = cursor.fetchone()
            tag1_text = tag1_info[0] if tag1_info else f"ID:{old_tag_1_id}"
            
            cursor.execute("SELECT tag FROM tags_temp WHERE id = ?", (old_tag_2_id,))
            tag2_info = cursor.fetchone()
            tag2_text = tag2_info[0] if tag2_info else f"ID:{old_tag_2_id}"
            
            reason = []
            if not new_tag_1_id:
                reason.append("first tag not found")
            if not new_tag_2_id:
                reason.append("second tag not found")
            
            skipped_details.append((tag1_text, tag2_text, ", ".join(reason)))
    
    print(f"   ✓ Migrated {migrated_count} of {len(tag_tags)} tag-tag relationships")
    if skipped_count > 0:
        print(f"\n   ⚠ WARNING: Skipped {skipped_count} tag-tag relationships:")
        for tag1_text, tag2_text, reason in skipped_details:
            print(f"      - Tag '{tag1_text}' linked to tag '{tag2_text}' ({reason})")
        print()
    
    print("\n✓ Data migration completed")


def drop_temp_tables(cursor):
    """Drop temporary old tables"""
    print("\nDropping temporary old tables...")
    
    temp_tables = ['verses_temp', 'tags_temp', 'notes_temp', 'verse_tags_temp', 
                   'verse_notes_temp', 'tag_notes_temp', 'tag_tags_temp']
    
    for table in temp_tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"  Dropped table: {table}")
    
    print("✓ Temporary tables dropped")

def migrate_database(db_path, create_backup=True):
    """
    Main migration function.
    Migrates a Bible Tagger database from version 0 to version 1.
    
    Args:
        db_path: Path to the database file
        create_backup: Whether to create a backup (default True)
    
    Returns:
        True if migration successful, False otherwise
    """
    print("\n" + "=" * 60)
    print("Bible Tagger Database Migration: Version 0 -> 1")
    print("=" * 60)
    print(f"Database: {db_path}\n")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"✗ Error: Database file not found: {db_path}")
        return False
    
    # Create backup if requested
    backup_path = None
    if create_backup:
        try:
            backup_path = backup_database(db_path)
        except Exception as e:
            print(f"✗ Error creating backup: {e}")
            return False
    else:
        print("⚠ Skipping backup (--no-backup specified)")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current version
        cursor.execute("PRAGMA user_version")
        current_version = cursor.fetchone()[0]
        
        if current_version != 0:
            print(f"✗ Error: Database version is {current_version}, expected 0")
            print("  This migration script only works for version 0 databases")
            conn.close()
            return False
        
        # Check for old schema tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        required_old_tables = ['verses', 'tags', 'notes', 'verse_tags', 'verse_notes', 'tag_notes', 'tag_tags']
        missing_tables = [t for t in required_old_tables if t not in tables]
        
        if missing_tables:
            print(f"✗ Error: Missing required old schema tables: {', '.join(missing_tables)}")
            print("  This may not be a valid version 0 Bible Tagger database")
            conn.close()
            return False
        
        print("✓ Database validated (version 0 schema)")
        
        # Step 1: Rename old tables to temporary names
        print("\n" + "=" * 60)
        print("STEP 1: RENAME OLD TABLES")
        print("=" * 60)
        rename_old_tables(cursor)
        conn.commit()
        
        # Step 2: Create new schema
        print("\n" + "=" * 60)
        print("STEP 2: CREATE NEW SCHEMA")
        print("=" * 60)
        create_new_schema(cursor)
        conn.commit()
        
        # Step 3: Migrate data
        print("\n" + "=" * 60)
        print("STEP 3: MIGRATE DATA")
        print("=" * 60)
        migrate_data(cursor)
        conn.commit()
        
        # Step 4: Drop temporary tables
        print("\n" + "=" * 60)
        print("STEP 4: DROP TEMPORARY TABLES")
        print("=" * 60)
        drop_temp_tables(cursor)
        conn.commit()
        
        # Step 5: Update database version
        print("\n" + "=" * 60)
        print("STEP 5: UPDATE DATABASE VERSION")
        print("=" * 60)
        cursor.execute("PRAGMA user_version = 1")
        conn.commit()
        print("✓ Database version updated to 1")
        
        # Success!
        print("\n" + "=" * 60)
        print("✓ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        if backup_path:
            print(f"\nBackup location: {backup_path}")
        print(f"Migrated database: {db_path}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Rollback and close connection
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        
        # Restore from backup if we created one
        if backup_path and os.path.exists(backup_path):
            print(f"\nRestoring from backup...")
            try:
                shutil.copy2(backup_path, db_path)
                print(f"✓ Database restored from backup")
            except Exception as restore_error:
                print(f"✗ Error restoring backup: {restore_error}")
                print(f"  Manual restore needed from: {backup_path}")
        
        return False


def main():
    """Main entry point for the migration script"""
    parser = argparse.ArgumentParser(
        description='Migrate Bible Tagger database from version 0 to version 1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python 0-to-1.py mydb.bdb
  python 0-to-1.py mydb.bdb --no-backup
        '''
    )
    
    parser.add_argument('database', 
                        help='Path to the .bdb database file to migrate')
    parser.add_argument('--no-backup', 
                        action='store_true',
                        help='Skip creating a backup of the database')
    
    args = parser.parse_args()
    
    # Run migration
    success = migrate_database(args.database, create_backup=not args.no_backup)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
