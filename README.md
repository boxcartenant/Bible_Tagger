This is a Bible annotating program. It loads a JSON bible of your choice, (I programmed this around the output of SWORD-to-JSON. A copy of that is included in here), and lets you load/save/create a SQLite database with the following tables:

verses(id, start_verse, end_verse), tags(id, tag), notes(id, note), verse_tags(verse_id, tag_id), verse_notes(verse_id, note_id), tag_notes(tag_id, note_id), tag_tags(tag_id, tag_id).

It's written in Python with TKinter, with a 3-column interface:
- The left column is a tree for navigating books and chapters.
- The middle column shows the text for one chapter, with little lines to show what verses have been annotated or tagged. You can click a verse (or shift-click to select multiple verses).
- The right column shows the selected verse(s), any notes you've written about that verse range, and a list of tags associated with the verse.

The columns are resizable (there's an invisible "sash" between each column that you can drag left and right).

If you click a tag, it'll show all the verses associated with that tag, and let you associate that tag with synonymous tags, just in case you make a mistake.
(e.g. maybe you made a tag called "eros" and another tag called "romance" and you want them to actually be the same category).

