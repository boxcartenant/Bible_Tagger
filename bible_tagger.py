import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import bibledb_lib
from tkinter.font import Font
from tkinter import simpledialog
from tkinter import messagebox
from bibledb_manager import DBManager
from bibledb_manager import TagInputDialog, combineVRefs
import os
import sys
import configparser
import argparse

textlinegap = 2
textelbowroom = 6 #that's "elbow room" for left and right spacing
bible_data = {}

config_filename = "config.cfg"
cfg = None

open_db_file = None
current_bible_json = None


def wrapText(text, width, font):
    line = ''
        
    lines = []
    for word in text.split(' '):
        linewidth = font.measure(line + " " + word)
        if linewidth < width:
            line += " " + word
        else:
            lines.append(line)
            line = word
    if line != '':
        lines.append(line)
    return lines


class BibleTaggerApp:
    def __init__(self, master, cli_args):
        self.master = master
        global bible_data, cfg

        jsonpath = cli_args.json_path if cli_args.json_path else cfg.get('DEFAULT', 'json_path', fallback=None)
        bdbpath = cli_args.db_path    if cli_args.db_path   else cfg.get('DEFAULT', 'bdb_path',  fallback=None)
        initial_window_size = cfg.get('INTERNAL', 'window_size', fallback="1000x600")

        self.master.geometry(initial_window_size)

        self.paned_window = ttk.PanedWindow(self.master, orient="horizontal")
        self.paned_window.pack(fill="both", expand=True)

        # Initialize DB Manager with callbacks for buttons that will be in it
        # Note: navigation_tree is created after this, so we'll update callbacks later
        self.db_manager = DBManager(
            self.master, 
            self.db_explorer_callback, 
            open_db_file,
            load_bible_callback=None,  # Will be set after navigation_tree is created
            load_db_callback=lambda: self.load_db(),
            save_db_as_callback=lambda: self.save_db_as(),
            backup_db_callback=lambda: self.backup_db(),
            new_db_callback=lambda: self.new_db(),
            merge_dbs_callback=lambda: self.merge_dbs()
        )

        self.navigation_tree = NavigationTree(self)
        self.scripture_panel = ScripturePanel(self)
        self.tagger_panel = TaggerPanel(self)
        
        # Now that navigation_tree is created, set the load_bible callback
        self.db_manager.load_bible_callback = lambda: self.navigation_tree.load_bible()

        self.history = History()

        self.paned_window.bind("<B1-Motion>", self.on_sash_drag)
        self.paned_window.bind("<ButtonRelease-1>", self.on_sash_release)
        self.paned_window.bind("<Configure>", lambda event : self.tagger_panel.display_attributes(None))

        # Bind window resize event to save geometry
        self.resize_after_id = None
        self.sash_after_id = None
        self.master.bind("<Configure>", self.on_window_resize)

        # Load and apply saved sash positions after window is ready
        # Default sash positions: left panel ~250px, right panel ~250px from right
        try:
            right_sash = cfg.getint('INTERNAL', 'sash_position', fallback=500)
        except:
            right_sash = 500
        self.master.after(100, lambda: self.restore_sash_position(right_sash))
        self.master.after(110, lambda: self.tagger_panel.display_attributes(None))

        #fixing the scrollbar behavior
        self.active_panel = None
        self.master.bind("<MouseWheel>", self.scroll_active_panel)
        self.scripture_panel.canvas.bind("<Enter>", self.set_active_panel)
        self.scripture_panel.canvas.bind("<Leave>", self.clear_active_panel)
        self.tagger_panel.canvas.bind("<Enter>", self.set_active_panel)
        self.tagger_panel.canvas.bind("<Leave>", self.clear_active_panel)
        #self.tagger_panel.canvas_frame.bind("<MouseWheel>", self.scroll_active_panel)

        # Try to load Bible JSON file
        bible_loaded = False
        if jsonpath:
            try:
                self.navigation_tree.load_json(jsonpath)
                bible_loaded = True
            except Exception as e:
                print("Failed to load JSON file from config:", e)
                jsonpath = None
        
        # If no Bible JSON loaded, prompt user to select one
        if not bible_loaded:
            response = messagebox.askyesno(
                "No Bible Loaded",
                "No Bible JSON file is currently loaded.\n\n"
                "Would you like to select a Bible JSON file now?\n\n"
                "(You can also load one later using the 'Load Bible' button)",
                icon='question'
            )
            
            if response:
                file_path = filedialog.askopenfilename(
                    parent=self.master,
                    title="Select Bible JSON File",
                    defaultextension=".json",
                    filetypes=[("JSON Bibles", "*.json"), ("All files", "*.*")]
                )
                
                if file_path and file_path[-5:] == '.json':
                    try:
                        self.navigation_tree.load_json(file_path)
                        bible_loaded = True
                        # Save message depends on use_last_bible setting
                        if not cfg.getboolean('DEFAULT', 'use_last_bible', fallback=False):
                            print(f"Bible JSON loaded: {file_path}")
                    except Exception as e:
                        messagebox.showerror(
                            "Error Loading Bible",
                            f"Failed to load Bible JSON file:\n{str(e)}"
                        )
                        print(f"Error loading Bible JSON: {e}")
                else:
                    print("Invalid or no file selected. You can load a Bible later using the 'Load Bible' button.")
            else:
                print("No Bible loaded. You can load one later using the 'Load Bible' button.")


        # Check if bdb file exists, if not create it with proper tables
            if bdbpath and not os.path.exists(bdbpath):
                print(f"BDB file not found at {bdbpath}. Creating new database...")
                # Create directory if it doesn't exist
                bdb_dir = os.path.dirname(bdbpath)
                if bdb_dir and not os.path.exists(bdb_dir):
                    os.makedirs(bdb_dir)
                # Create empty file and initialize database tables
                with open(bdbpath, 'w') as f:
                    f.write("")
                bibledb_lib.makeDB(bdbpath)
                print(f"Created new database at {bdbpath}")

        try:
            # Auto-migrate database if needed
            if bdbpath and os.path.exists(bdbpath):
                current_version = bibledb_lib.get_database_version(bdbpath)
                target_version = bibledb_lib.CURRENT_DATABASE_VERSION
                
                if current_version != target_version:
                    # Show dialog asking if user wants to migrate
                    message = (
                        f"Database Version Mismatch\n\n"
                        f"Current database version: {current_version}\n"
                        f"Required version: {target_version}\n\n"
                        f"The database needs to be migrated to work with this version of Bible Tagger.\n"
                        f"A backup will be created automatically.\n\n"
                        f"Would you like to migrate the database now?"
                    )
                    
                    user_choice = messagebox.askyesno(
                        "Database Migration Required",
                        message,
                        icon='warning'
                    )
                    
                    if user_choice:
                        # User chose to migrate
                        print(f"\nMigrating database from version {current_version} to {target_version}...")
                        success, backup_path = migrate_db(bdbpath, interactive=False)
                        
                        if success:
                            # Show success dialog
                            success_msg = (
                                f"Database successfully migrated!\n\n"
                                f"New version: {target_version}\n"
                            )
                            if backup_path and os.path.exists(backup_path):
                                success_msg += f"\nBackup saved at:\n{backup_path}"
                            
                            messagebox.showinfo("Migration Successful", success_msg)
                            print(f"✓ Database successfully migrated to version {target_version}")
                            if backup_path:
                                print(f"✓ Backup saved at: {backup_path}")
                        else:
                            # Show failure dialog
                            error_msg = (
                                f"Database migration failed!\n\n"
                                f"Please check the console for error details.\n"
                            )
                            if backup_path and os.path.exists(backup_path):
                                error_msg += f"\nYour original database was backed up to:\n{backup_path}"
                            
                            messagebox.showerror("Migration Failed", error_msg)
                            print(f"✗ Migration failed")
                            
                            # Let user choose a different database
                            bdbpath = None
                    else:
                        # User chose not to migrate, show file dialog
                        messagebox.showinfo(
                            "Load Different Database",
                            "Please select a database file to open."
                        )
                        bdbpath = None
            
            if bdbpath:
                self.load_bdb(bdbpath, True)
            else:
                # If no valid database, show load dialog
                if not self.load_db(on_startup=True):
                    # User cancelled database selection on startup, exit
                    print("No database selected. Exiting...")
                    self.master.destroy()
                    sys.exit(0)
        except Exception as e:
            print("Failed to load BDB file from config:", e)
            bdbpath = None

    ##### DB LOAD SAVE
    def load_bdb(self, file_path, no_verse = False):
        # Store the open file in a global variable
        
        global open_db_file, config_filename, cfg
        open_db_file = file_path
        # Update DB Manager label if it exists
        if hasattr(self, 'db_manager'):
            self.db_manager.update_db_label(file_path)
        if not no_verse:
            # item = "verseClick" if a verse was clicked
            # data = {"verse": the verse text, "ref": the verse reference}
            try:
                self.tagger_panel.display_attributes(item = "verseClick", data={"verse":"", "ref": "Deuteronomy 4:2"})
            except:
                pass
        else:
            self.tagger_panel.display_attributes()
        self.cause_canvas_to_refresh()
        self.update_tree_colors()

        if cfg.getboolean('DEFAULT', 'use_last_db', fallback=False):
            cfg['DEFAULT']['bdb_path'] = file_path
            with open(config_filename, 'w') as configfile:
                cfg.write(configfile)
        
    def load_db(self, on_startup=False):
        # Implement your logic to open the browse window and load the database
        # on_startup: if True and user cancels, return False to signal app should exit
        # Use DB Manager window as parent if it's open
        parent = self.db_manager.top_window if hasattr(self.db_manager, 'top_window') and self.db_manager.top_window else self.master
        file_path = filedialog.askopenfilename(parent=parent, defaultextension=".bdb", filetypes=[("Sqlite Bible Files", "*.bdb"), ("All files", "*.*")])
        if file_path:
            if file_path[-4:] == ".bdb":
                # Check database version
                current_version = bibledb_lib.get_database_version(file_path)
                target_version = bibledb_lib.CURRENT_DATABASE_VERSION
                
                if current_version != target_version:
                    # Show dialog asking if user wants to migrate
                    message = (
                        f"Database Version Mismatch\n\n"
                        f"Selected database version: {current_version}\n"
                        f"Required version: {target_version}\n\n"
                        f"The database needs to be migrated to work with this version of Bible Tagger.\n"
                        f"A backup will be created automatically.\n\n"
                        f"Would you like to migrate the database now?"
                    )
                    
                    user_choice = messagebox.askyesno(
                        "Database Migration Required",
                        message,
                        icon='warning',
                        parent=parent
                    )
                    
                    if user_choice:
                        # User chose to migrate
                        print(f"\nMigrating database from version {current_version} to {target_version}...")
                        success, backup_path = migrate_db(file_path, interactive=False)
                        
                        if success:
                            # Show success dialog
                            success_msg = (
                                f"Database successfully migrated!\n\n"
                                f"New version: {target_version}\n"
                            )
                            if backup_path and os.path.exists(backup_path):
                                success_msg += f"\nBackup saved at:\n{backup_path}"
                            
                            messagebox.showinfo("Migration Successful", success_msg, parent=parent)
                            print(f"✓ Database successfully migrated to version {target_version}")
                            if backup_path:
                                print(f"✓ Backup saved at: {backup_path}")
                            
                            # Load the migrated database
                            print(f"Loaded DB: {file_path}")
                            self.load_bdb(file_path)
                        else:
                            # Show failure dialog
                            error_msg = (
                                f"Database migration failed!\n\n"
                                f"Please check the console for error details.\n"
                            )
                            if backup_path and os.path.exists(backup_path):
                                error_msg += f"\nYour original database was backed up to:\n{backup_path}"
                            
                            messagebox.showerror("Migration Failed", error_msg, parent=parent)
                            print(f"✗ Migration failed")
                            # Don't load the database, stay with current
                    else:
                        # User chose not to migrate, stay with current database
                        print("Migration cancelled by user. Keeping current database.")
                else:
                    # Version matches, load normally
                    print(f"Loaded DB: {file_path}")
                    self.load_bdb(file_path)
                return True
            else:
                print("I'm not opening that. It's gotta be a SQLITE database file with the extension \".bdb\"")
                return False
        else:
            # User cancelled file selection
            return not on_startup  # If on startup, signal that startup should abort, else keep running

    def new_db(self):
        global open_db_file

        # Use DB Manager window as parent if it's open
        parent = self.db_manager.top_window if hasattr(self.db_manager, 'top_window') and self.db_manager.top_window else self.master
        file_path = filedialog.asksaveasfilename(parent=parent, defaultextension=".bdb", filetypes=[("Sqlite Bible Files", "*.bdb"), ("All files", "*.*")])

        if file_path:
            with open(file_path, 'w') as f:
                f.write("")
                bibledb_lib.makeDB(file_path)
            self.load_bdb(file_path)
    
    def backup_db(self):
        """Create a backup of the current database without switching to it"""
        global open_db_file

        # Use DB Manager window as parent if it's open
        parent = self.db_manager.top_window if hasattr(self.db_manager, 'top_window') and self.db_manager.top_window else self.master

        if open_db_file is None:
            messagebox.showwarning("No Database", "No database is currently loaded to backup.", parent=parent)
            return None

        file_path = filedialog.asksaveasfilename(
            parent=parent,
            defaultextension=".bdb", 
            filetypes=[("Sqlite Bible Files", "*.bdb"), ("All files", "*.*")],
            initialfile=os.path.basename(open_db_file).replace('.bdb', '_backup.bdb')
        )

        if file_path:
            try:
                bibledb_lib.copy_db(open_db_file, file_path)
                print(f"Database backed up to: {file_path}")
                return file_path
            except Exception as e:
                messagebox.showerror("Backup Failed", f"Failed to create backup:\n{str(e)}", parent=parent)
                return None
        return None
    
    def save_db_as(self):
        global open_db_file

        # Use DB Manager window as parent if it's open
        parent = self.db_manager.top_window if hasattr(self.db_manager, 'top_window') and self.db_manager.top_window else self.master
        file_path = filedialog.asksaveasfilename(parent=parent, defaultextension=".bdb", filetypes=[("Sqlite Bible Files", "*.bdb"), ("All files", "*.*")])

        if file_path:
            if open_db_file is None:
                with open(file_path, 'w') as f:
                    f.write("")
                    bibledb_lib.makeDB(file_path)
            else:
                bibledb_lib.copy_db(open_db_file, file_path)
            # Load the new database file (switch to it)
            self.load_bdb(file_path)
            print(f"Database saved as: {file_path}")
    
    def merge_dbs(self):
        # merges a second database into current database
        # Use DB Manager window as parent if it's open
        parent = self.db_manager.top_window if hasattr(self.db_manager, 'top_window') and self.db_manager.top_window else self.master
        file_path = filedialog.askopenfilename(parent=parent, defaultextension=".bdb", filetypes=[("Sqlite Bible Files", "*.bdb"), ("All files", "*.*")])
        if file_path:
            if file_path == open_db_file:
                print("You can't merge a database into itself!")
            elif not os.path.exists(file_path):
                print("That file doesn't exist!")
            elif file_path[-4:] == ".bdb":
                bibledb_lib.merge_dbs(open_db_file, file_path)
                self.cause_canvas_to_refresh()
                self.update_tree_colors()
            else:
                print("I'm not opening that. It's gotta be a SQLITE database file with the extension \".bdb\"")

    def set_active_panel(self, event):
        # Set the active panel to the widget under the mouse
        self.active_panel = event.widget
        #print("active_panel",self.active_panel)

    def clear_active_panel(self, event):
        # Clear the active panel when the mouse leaves
        self.active_panel = None

    def on_window_resize(self, event):
        # Only handle resize events for the main window, not child widgets
        if event.widget == self.master:
            # Cancel any pending save to avoid saving on every pixel change
            if self.resize_after_id:
                self.master.after_cancel(self.resize_after_id)
            # Schedule a save after 500ms of no resizing
            self.resize_after_id = self.master.after(500, self.save_window_size)

    def save_window_size(self):
        global cfg, config_filename
        # Get current window geometry
        geometry = self.master.geometry()
        
        # Update config
        cfg.set('INTERNAL', 'window_size', geometry)
        
        # Save to file
        with open(config_filename, 'w') as configfile:
            cfg.write(configfile)
        
        self.resize_after_id = None

    def scroll_active_panel(self, event):
        # Only scroll the active panel
        #print("scrolling active_panel",self.active_panel)
        if self.active_panel:
            first, last = self.active_panel.yview()  # Get scrollbar position
            if event.delta > 0 and first <= 0:  # Trying to scroll up but already at the top
                return  # Do nothing
            if event.delta < 0 and last >= 1:  # Trying to scroll down but already at the bottom
                return
            self.active_panel.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_sash_drag(self, event):
        # If the moved sash is near the treeview sash (left), ignore
        # if the moved sash is near the options panel (right), update the options panel
        if self.paned_window.sashpos(1) - 10 < event.x < self.paned_window.sashpos(1) + 10:
            self.canvas_callback(None, None)
        #in both cases, we need to update the canvas where the verses are (middle)
        self.scripture_panel.display_chapter()
        self.tagger_panel.display_attributes()

        #To Do: account for situations where the user puts the sashes together.

    def on_sash_release(self, event):
        # Save sash positions after mouse button is released
        if self.sash_after_id:
            self.master.after_cancel(self.sash_after_id)
        self.sash_after_id = self.master.after(500, self.save_sash_position)

    def restore_sash_position(self, right_sash):
        try:
            self.paned_window.sashpos(1, right_sash)
        except:
            pass  # Ignore errors if positions are invalid

    def save_sash_position(self):
        global cfg, config_filename
        try:
            right_sash = self.paned_window.sashpos(1)
            
            # Update config
            cfg.set('INTERNAL', 'sash_position', str(right_sash))
            
            # Save to file
            with open(config_filename, 'w') as configfile:
                cfg.write(configfile)
            
            self.sash_after_id = None
        except:
            pass  # Ignore errors during save

    def update_tree_colors(self):
        #do a sql query to find out what chapters have notes or tags
        marked_chapters = bibledb_lib.find_note_tag_chapters(open_db_file)
        #recolor all the chapters that have content
        self.navigation_tree.recolor(marked_chapters)

    def tree_callback(self, item, data, reset_scrollbar):
        # handle canvas-related actions caused by tree interactions here
        # You can call the CanvasView methods to update the canvas
        # For example, self.scripture_panel.display_attributes(attributes)
        self.scripture_panel.display_chapter(item, data, reset_scrollbar)
        #self.scripture_panel.reset_scrollregion(item)

    def canvas_callback(self, item, data, shift_key = False):
        # item is either "verseClick" or "tagClick", depending on what was clicked.
        # data is like {"verse":"in the beginning...", "ref": "Genesis 1:1"}
        
        # handle tree-related actions caused by canvas interactions here
        self.tagger_panel.display_attributes(item, data, shift_key)
        self.tagger_panel.reset_scrollregion(item)
        1;

    def cause_canvas_to_refresh(self):
        self.scripture_panel.display_chapter()
    
    def options_callback(self, data, scrollreset = False):
        #this is used when you are looking at tag xref data and you click a verse associated with the tag.
        #causes the tree and canvas to navigate to the verse you clicked.
        #data = (startverse, endverse)
        start = bibledb_lib.parseVerseReference(data[0])
        end = bibledb_lib.parseVerseReference(data[1])

        checkbook = self.scripture_panel.selected_start_b #capture this, so we won't reset the canvas view if we're not moving chapters.
        
        self.scripture_panel.selected_start_b = bibledb_lib.book_proper_names[start['sb']]
        self.scripture_panel.selected_end_b = bibledb_lib.book_proper_names[end['eb']]
        self.scripture_panel.selected_start_c = start['sc']
        self.scripture_panel.selected_end_c = end['ec']
        self.scripture_panel.selected_start_v = start['sv']
        self.scripture_panel.selected_end_v = end['ev']

        #navigate to the first verse in the range
        navtreedata = "/"+bibledb_lib.book_proper_names[start['sb']]+"/Ch "+start['sc']
        
        #if not scrollreset:
            #Sometimes if you are clicking a verse in tag data for a chapter you already have open, you'll already be looking at that verse
            # and have scrolled to a place you want. In that case, maybe you don't want it to reset....
            #scrollreset = checkbook != self.scripture_panel.selected_start_b
        #self.navigation_tree.select_item(navtreedata, scrollreset)
        self.navigation_tree.select_item(navtreedata, True) #changed this to "true" so it will always jump to the selected verse.
        
        self.tagger_panel.display_attributes("verseClick", {"verse": "This part of the code was never implemented", "ref": combineVRefs(data[0],data[1])}, False)
        self.tagger_panel.reset_scrollregion(None)
        #self.scripture_panel.display_chapter(reset_scrollbar = True)
        #self.scripture_panel.reset_scrollregion()
        
    def db_explorer_callback(self, clickdata = None, item = "tagClick"):
        #this function will either focus a tag or a verse, depending on what was clicked in the secondary window
        if item == "tagClick":
            data = {'ref':clickdata, 'id':None}
            self.tagger_panel.display_attributes(item, data)
        else: #"verseClick"
            #Scrollreset is True so that, if we're clicking back and forth between verses in the same chapter, it will just go ahead and highlight them.
            self.options_callback(clickdata, True)
        self.master.focus_force()

class History:
    def __init__(self):
        # Navigation history system
        self.navigation_history = []  # List of (item, data) tuples
        self.navigation_index = -1    # Current position in history (-1 = no history)

    def add_or_replace_state(self, item, data):
        # Truncate forward history if we're not at the end
        if self.navigation_index < len(self.navigation_history) - 1:
            self.navigation_history = self.navigation_history[:self.navigation_index + 1]

        # Check for duplicate before adding
        if self.navigation_index >= 0:
            hist_item, hist_data = self.navigation_history[self.navigation_index]
            if hist_item != item or hist_data != data:
                # Add new entry (normal behavior)
                self.navigation_history.append((item, data))
                self.navigation_index += 1
        else:
            self.navigation_history.append((item, data))
            self.navigation_index += 1

    def can_go_back(self):
        """Check if we can navigate backward in history"""
        # Allow going back even from index 0 to -1 (no verse loaded state)
        return self.navigation_index >= 0
    
    def can_go_forward(self):
        """Check if we can navigate forward in history"""
        # Can go forward if we have history and we're not at the end
        # This includes going from -1 (no verse) to 0 (first verse)
        return len(self.navigation_history) > 0 and self.navigation_index < len(self.navigation_history) - 1

    def go_back(self):
        """Navigate backward in history"""
        if self.can_go_back():
            self.navigation_index -= 1
            # If we're now at -1, return None (no verse loaded state)
            if self.navigation_index < 0:
                return None, None
            prev_item, prev_data = self.navigation_history[self.navigation_index]
            return prev_item, prev_data
        return None, None
    
    def go_forward(self):
        """Navigate forward in history"""
        if self.can_go_forward():
            self.navigation_index += 1
            next_item, next_data = self.navigation_history[self.navigation_index]
            return next_item, next_data
        return None, None

class NavigationTree:
    #leftmost panel on the main window
    def __init__(self, bta, weight=1):
        global bible_data
        self.bta = bta
        self.tree_item_data = {}
        self.treeFont = Font()
        self.marked_chapters = []

        # Create a frame for the tree
        self.tree_frame = ttk.Frame(self.bta.paned_window)
        self.tree_frame.grid(row=0, column=0, sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1) #tree stretches to bottom of window

        # Create a tree view
        self.tree = ttk.Treeview(self.tree_frame, show='tree')
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Create a frame for DB Manager button below the tree
        self.db_buttons_frame = ttk.Frame(self.tree_frame)
        self.db_buttons_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5, padx=2)
        self.db_buttons_frame.grid_columnconfigure(0, weight=1)
        
        # Create single Open DB Manager button
        self.open_db_manager_button = tk.Button(self.db_buttons_frame, text="Open DB Manager", 
                                                command=lambda: self.bta.db_manager.show(self.bta.db_explorer_callback, open_db_file))
        self.open_db_manager_button.grid(row=0, column=0, sticky="ew")
        
        self.bta.paned_window.add(self.tree_frame)
        self.tree.bind("<ButtonRelease-1>", self.on_tree_item_click)
        self.tree.bind("<KeyRelease-Up>", self.on_tree_item_click)
        self.tree.bind("<KeyRelease-Down>", self.on_tree_item_click)
        self.tree.bind("<KeyRelease-Left>", self.on_tree_item_click)
        self.tree.bind("<KeyRelease-Right>", self.on_tree_item_click)

    def populate_tree(self, data, parent_id):
        for key, value in data.items():
            item_id = self.tree.insert(parent_id, 'end', text=key, iid=parent_id+"/"+key)
            self.tree_item_data[item_id] = value  # Store the associated data
            i = 0
            while i < len(value):
                tagID = item_id+"/Ch "+str(i+1)
                chapter_id = self.tree.insert(item_id, 'end', text="Ch "+str(i+1), iid=tagID, tags=(tagID,))
                #print(tagID)
                self.tree_item_data[chapter_id] = value[i]  # Store the associated data
                #TO DO: Remove the above line (self.tree_item_data[chapter_id] = value[i]) if not used
                i += 1

    def recolor(self, marked_chapters):
        # Configure tag colors first
        self.tree.tag_configure("blue_book", foreground='blue')
        self.tree.tag_configure("black_book", foreground='black')
        
        # Determine which chapters changed
        blue_chapters = list(set(marked_chapters) - set(self.marked_chapters))
        black_chapters = list(set(self.marked_chapters) - set(marked_chapters))
        
        # Color changed chapters
        for chapter in blue_chapters:
            self.tree.tag_configure(chapter, foreground='blue')
        for chapter in black_chapters:
            self.tree.tag_configure(chapter, foreground='black')
        
        # Update book colors based on ALL currently marked chapters
        all_marked_books = {self.tree.parent(chapter) for chapter in marked_chapters}
        all_books = {self.tree.parent(item) for item in self.tree.get_children() 
                     for item in self.tree.get_children(item)}
        unmarked_books = all_books - all_marked_books
        
        for book in all_marked_books:
            if book:  # Check book exists
                self.tree.item(book, tags=("blue_book",))
        for book in unmarked_books:
            if book:  # Check book exists
                self.tree.item(book, tags=("black_book",))
        
        self.marked_chapters = marked_chapters
        self.tree.update_idletasks()

    def select_item(self, item_path, reset_scroll_region = True):
        path_elements = item_path.split("/")
        current_item = ""

        for element in path_elements:
            current_item += element
            self.tree.item(current_item, open=True)  # Expand the parent item
            current_item += "/"
        
        # Select the final item
        self.tree.selection_set(current_item[:-1])
        self.on_tree_item_click(reset_scroll_region)
        
    def on_tree_item_click(self, reset_scroll_region=True, event=None):
        #select and show chapters when clicked
        #print(reset_scroll_region)
        #print(event)
        try: 
            item_id = self.tree.selection()[0]
            children = self.tree.get_children(item_id)
                
            #self.tree.column("#0", stretch=False)
            self.tree.update_idletasks()

            #adjust width of tree to accommodate width of selected item
            #this is a carry over from a tree I used for another program...
            #text_width = self.treeFont.measure(self.tree.item(item_id, 'text').strip())
            #tab_width = self.tree.bbox(item_id, column="#0")[0]  # Get the width of the last column
            #content_width = text_width+tab_width
            #print(self.tree.bbox(item_id, column="#0"))
            #print(str(text_width) + ", " + str(tab_width) + ", " + str(self.tree.winfo_width()))
            #print(self.tree.item(item_id, 'text'))
            #print(Font().actual())

            #if content_width > self.tree.winfo_width():
            #    self.tree.column("#0", width=content_width)  # Adjust the column width
            #else:
            #    self.tree.column("#0", width=self.tree.winfo_width())  # Set the width to the visible width

            #get the data associated with that item and pass it to the canvas for display
            item_data = self.tree_item_data.get(item_id)
            #print("sending..." + str(attributes))
            # Use the callback in the NavigationTree class to handle the canvas update
            self.bta.tree_callback(item_id, item_data, reset_scroll_region)
        except IndexError:
            print("failed in on_tree_item_click")
            #clicking white space on the list throws this error. Just don't update the item.
            pass 

    def load_json(self, bible_file_path):
        global bible_data, cfg, config_filename, current_bible_json
        current_bible_json = bible_file_path
        with open(bible_file_path, 'r', encoding='utf-8') as file:
            bible_file_content = file.read()
            bible_data = bibledb_lib.getBibleData(bible_file_content)
        #print("dumping output from open_file_dialog")
        #print(bible_data)
        
        # Clear existing tree items before loading new Bible
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_data.clear()
        
        self.populate_tree(bible_data, '')
        self.bta.cause_canvas_to_refresh()
        self.bta.update_tree_colors()
        
        # Save Bible path to config if use_last_bible is enabled
        if cfg.getboolean('DEFAULT', 'use_last_bible', fallback=False):
            cfg['DEFAULT']['json_path'] = bible_file_path
            with open(config_filename, 'w') as configfile:
                cfg.write(configfile)
        
        # Update DB Manager Bible label if it exists and pass the bible path
        if hasattr(self.bta, 'db_manager'):
            self.bta.db_manager.update_bible_label(bible_file_path)
    
    def load_bible(self):
        #button to open a Bible file
        global bible_data
        # Use DB Manager window as parent if it's open
        parent = self.bta.db_manager.top_window if hasattr(self.bta.db_manager, 'top_window') and self.bta.db_manager.top_window else self.bta.master
        file_path = filedialog.askopenfilename(parent=parent, defaultextension=".json", filetypes=[("JSON Bibles", "*.json"), ("All files", "*.*")])
        if file_path and file_path[-5:] == '.json':
            #print(f"Selected file: {file_path}")
            self.load_json(file_path)
        else:
            print("Invalid file! It's gotta be a json file. Funny thing about this: you could use this program to make notes about any kind of JSON data which is organized in a way similar to a supported Bible JSON file.")

class ScripturePanel:
    def __init__(self, bta):
        global bible_data, open_db_file
        self.bta = bta
        self.canvasFont = Font(size = 10)
        self.italicFont = Font(size = 10, slant = 'italic')
        self.boldFont = Font(size = 10, weight = 'bold')
        self.italicunderlineFont = Font(size=10, slant='italic', underline=True)

        self.canvas_frame = ttk.Frame(self.bta.paned_window)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        # Create a canvas inside a canvas frame
        self.canvas = tk.Canvas(self.canvas_frame)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.canvas.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Create vertical and horizontal scrollbars
        self.v_scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.h_scrollbar = tk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)

        # Configure canvas to use scrollbars
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Add scrollbars to the canvas frame
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.scrollbar_width = self.v_scrollbar.winfo_reqwidth()

        self.selected_start_v = -1
        self.selected_end_v = -1
        self.selected_start_c = -1
        self.selected_end_c = -1
        self.selected_start_b = ""
        self.selected_end_b = ""

        self.bta.paned_window.add(self.canvas_frame)

        # Draw on the canvas (e.g., lines, rectangles, text, images)
        #self.canvas.create_line(50, 50, 200, 50, fill="blue", width=2)
        #self.canvas.create_rectangle(100, 100, 250, 200, fill="red")
        self.canvas.create_text(90, 125, text="Bible Data Viewer!", fill="green", font = self.canvasFont)
        
        # Configure the scroll region to make the canvas scrollable
        canvas_width = self.canvas.winfo_reqwidth()
        canvas_height = self.canvas.winfo_reqheight()
        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
        self.current_item = "/"
        self.current_data = "/"
            
        
    def on_text_click(self, event, item_id, scopename, vv):
        #item_id is the text of the selected verse
        #scopename is the formatted verse name (e.g. "exodus 3:2")
        #vv is the verse number that was clicked. (e.g. 2)
        
        # Get the text associated with the clicked object
        #------Send tag data to the second window for cross referencing
        self.bta.canvas_callback("verseClick", {"verse": item_id, "ref": scopename}, event.state & (1<<0))
        
        #print("ID:"+ str(item_id), "\nSCOPE:"+str(scopename), "\nVV:"+str(vv))
        splitscope = scopename.split(" ")
        cc = int(splitscope[-1].split(":")[0])
        bookname = ''
        #print(splitscope)
        if len(splitscope) > 2:
            i = 0
            while i < (len(splitscope)-1):
                bookname += splitscope[i] + " "
                i += 1
            bookname = bookname.strip()
        else:
            bookname = splitscope[0]
        #print(bookname)
        bb = bibledb_lib.getBookIndex(bookname)
        sb = bibledb_lib.getBookIndex(self.selected_start_b)
        eb = bibledb_lib.getBookIndex(self.selected_end_b)
        #print(vv)
        #print(cc)
        if event.state & (1<<0):
            #shift key is pressed
            #if a range is already selected, just go back to the first verse in it
            self.selected_end_b = self.selected_start_b
            self.selected_end_c = self.selected_start_c
            self.selected_end_v = self.selected_start_v
            eb = sb
            
            #set selected chapters in order
            if bb > sb:
                self.selected_end_b = bibledb_lib.book_proper_names[bb]
                eb = bb
                self.selected_end_c = cc
                self.selected_end_v = vv
            elif bb < sb:
                self.selected_end_b = bibledb_lib.book_proper_names[sb]
                eb = sb
                self.selected_start_b = bibledb_lib.book_proper_names[bb]
                sb = bb
                self.selected_end_c = self.selected_start_c
                self.selected_start_c = cc
                self.selected_end_v = self.selected_start_v
                self.selected_start_v = vv
            else: #same book
                self.selected_start_b = bibledb_lib.book_proper_names[bb]
                sb = bb
                self.selected_end_b = bibledb_lib.book_proper_names[bb]
                eb = bb
            if sb == eb:
                if int(cc) > int(self.selected_start_c):
                    #print("new chapter is greater than old chapter")
                    self.selected_end_c = cc
                    self.selected_end_v = vv
                elif cc < self.selected_start_c:
                    self.selected_end_c = self.selected_start_c
                    self.selected_start_c = cc
                    self.selected_end_v = self.selected_start_v
                    self.selected_start_v = vv
                else:#same chapter
                    self.selected_end_c = cc
                    self.selected_start_c = cc
            #if the chapter hasn't changed, just do the verses:
                if self.selected_end_c == self.selected_start_c:
                    if vv > self.selected_start_v:
                        self.selected_end_v = vv
                    else:
                        self.selected_end_v = self.selected_start_v
                        self.selected_start_v = vv
        else:
            self.selected_start_b = bibledb_lib.book_proper_names[bb]
            self.selected_end_b = bibledb_lib.book_proper_names[bb]
            self.selected_start_v = vv
            self.selected_end_v = vv
            self.selected_start_c = cc
            self.selected_end_c = cc
        self.display_chapter()
        #self.display_chapter()
        #print(f"Text clicked: {clicked_text}")
        #print(f"Scope: {scopename}")
        
    def reset_scrollregion(self, event = None):
        self.canvas.configure(scrollregion=self.canvas.bbox("ALL"))
    
    def display_chapter(self, item = None, data = None, reset_scrollbar = False):
        #items are like, "/Genesis/Ch 1"
        #data is a list of verse text:
        # ['In the beginning God created the heavens and the earth. ',
        #  'And the earth was waste and void; and darkness was upon the face of the deep...',...]
        if item != None and data != None:
            self.current_item = item
            self.current_data = data
        else:
            item = self.current_item
            data = self.current_data
        #print(item)
        self.canvas.delete("all")
        y_offset = 40  # Initial Y offset
        x_offset = 5 #initial x offset...
        rung_number = 0
        Label_offset = -25
        textlineheight = Font.metrics(self.canvasFont)["linespace"]
        boldlineheight = Font.metrics(self.boldFont)["linespace"]
        global textlinegap, fbdCircleDiam, textelbowroom
        selected_y_offset = None
        item_hierarchy = item.split('/')
        #print(item_hierarchy)
        if len(item_hierarchy) > 2:
            #print(item)
            #print(item_hierarchy)
            #print(self.selected_start_b)
            #print(self.selected_end_b)
            thisbook = item.split('/')[-2]
            thischapter = item.split(' ')[-1]

            #we're going to draw vertical lines left of the verses to indicate which verses have notes and tags.
            #get the tagged and noted verse rows
            notestags = bibledb_lib.find_note_tag_verses(open_db_file, thisbook, thischapter)
            #move the verses over to make room for the lines. Two pixels for each unique verse ID.
            id_lines = len(notestags)*2
            if id_lines > 0:
                x_offset += id_lines

            #show the chapter header 
            self.canvas.create_text(x_offset, y_offset, text=str(thisbook)+" Chapter "+str(thischapter), anchor=tk.W, font = self.boldFont)
            y_offset += boldlineheight + textlinegap*2
            
            verse_area_width = self.bta.paned_window.sashpos(1) - self.bta.paned_window.sashpos(0) - self.scrollbar_width - textelbowroom*2
            v = 1
            c = int(item_hierarchy[-1].replace("Ch ",""))
            b = int(bibledb_lib.getBookIndex(item_hierarchy[-2]))
            sv = int(self.selected_start_v)
            ev = int(self.selected_end_v)
            sc = int(self.selected_start_c)
            ec = int(self.selected_end_c)
            sb = int(bibledb_lib.getBookIndex(self.selected_start_b))
            eb = int(bibledb_lib.getBookIndex(self.selected_end_b))

            #print("book:",sb, b, eb,"\nchapter:",sc,c,ec,"\nverse:",sv, v, ev)
            verse_heights = []

            for verse in data:
                textColor = "black"
                #if the current verse is in the user-selected range, highlight it.
                if ((sb == b and sc == c and sv <= v) or\
                    (sb == b and sc < c) or\
                    (sb < b)) and\
                   ((eb == b and ec == c and ev >= v) or\
                    (eb == b and ec > c) or\
                    (eb > b)):
                    textColor = "maroon"
                    #record the y-offset of the first selected verse so we can navigate to it later.
                    if selected_y_offset is None:
                        selected_y_offset = y_offset - textlinegap - boldlineheight*2
                        if selected_y_offset < 0:
                            selected_y_offset = 0

                
                vtop = y_offset - textlinegap
                
                verseRef = str(item).replace("/Ch "," ").replace("/","")+":"+str(v)
                #print(verseRef)
                #Print the verse number in italics
                text_object = self.canvas.create_text(x_offset, y_offset, text=str(v), anchor=tk.NW, fill = textColor, font = self.italicFont)
                self.canvas.tag_bind(text_object, '<Button-1>', lambda event, item_id=text_object, vref=verseRef, verse=verse, vnum = v: self.on_text_click(event, verse, vref, vnum))
                v_offset = self.italicFont.measure(str(v)) + textelbowroom + x_offset #offset for the verse, to the right of the verse number.
                # print the verse; wrap to the size of the middle column
                for line in wrapText(verse, verse_area_width - v_offset, self.canvasFont):
                    text_object = self.canvas.create_text(v_offset, y_offset, text=line, anchor=tk.NW, fill = textColor, font = self.canvasFont)
                    self.canvas.tag_bind(text_object, '<Button-1>', lambda event, item_id=text_object, vref=verseRef, verse=verse, vnum = v: self.on_text_click(event, verse, vref, vnum))
                    y_offset += textlineheight + textlinegap

                vbot = y_offset - textlinegap

                #keep track of the top and bottom coord for each verse, to mark which ones have notes and tags.
                verse_heights.append({'v':v,'top':vtop,'bot':vbot})
                
                v += 1

            #draw lines next to every verse that has a note or a tag associated with it.
            for row in notestags:
                sb = row['start_book']
                sc = row['start_chapter']
                eb = row['end_book']
                ec = row['end_chapter']
                sv = row['start_verse']
                ev = row['end_verse']
                t = row['type']
                #purple if there's both a note and a tag.
                color = "maroon"
                lx = x_offset - id_lines
                if t == "tag": #blue if just a tag
                    color = "blue"
                elif t == "note": #orange if just a note
                    color = "orange2"

                #capture the top and bottom verse in a group which spans multiple chapters
                lowest_v = 999999
                highest_v = -5
                low_vh = None
                high_vh = None
                for verse in verse_heights:
                    v = verse['v']
                    if ((sb == b and sc == c and sv <= v) or\
                        (sb == b and sc < c) or\
                        (sb < b)) and\
                       ((eb == b and ec == c and ev >= v) or\
                        (eb == b and ec > c) or\
                        (eb > b)):
                        if v < lowest_v:
                            lowest_v = v
                            low_vh = verse
                        if v > highest_v:
                            highest_v = v
                            high_vh = verse
                        self.canvas.create_line(lx, verse['top'], lx, verse['bot'], fill=color, width=1)
                if ec > c or eb > b or sc < c or sb < b:
                    #if this group spans multiple chapters, give it a little hat and a little shoe to indicate it.
                    self.canvas.create_line(lx, high_vh['bot'], lx+2, high_vh['bot'], fill=color, width=5)
                    self.canvas.create_line(lx, low_vh['top'], lx+2, low_vh['top'], fill=color, width=5)
                id_lines -= 2
                        
        #print(item_hierarchy)
        #print(data)

        # Configure the scroll region to make the canvas scrollable
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        #if we're navigating to a new chapter, start at the top.
        if(reset_scrollbar):
            #if there is a verse selected in this chapter, go ahead and scroll to it.
            if selected_y_offset is not None:
                canvas_height = self.canvas.winfo_height()
                scroll_target = selected_y_offset/self.canvas.bbox("all")[3] #scroll percentage
                self.canvas.yview_moveto(scroll_target)
            else:
                #tbh I'm not sure when this part of the if-statement will ever be called anymore.
                self.canvas.yview_moveto(0)
            self.canvas.xview_moveto(0)
        #canvas_width = self.canvas.winfo_reqwidth()
        #canvas_height = self.canvas.winfo_reqheight()
        #print("width, height", canvas_width, canvas_height)
        #print("x_offset, y_offset", x_offset, y_offset)
        #try: #this will work if x_offset is set, which is the case when we are drawing ladders.
        #    self.canvas.config(scrollregion=(0, 0, x_offset, y_offset+40))
        #except:
        #    self.canvas.config(scrollregion=(0, 0, canvas_width, y_offset+40))


class MultiLineInputDialog(simpledialog.Dialog):

    initial_value = ""

    def body(self, master):
        self.result = None

        # Set the initial size of the dialog window (width x height)
        self.geometry("400x300")  # Initial size

        tk.Label(master, text="Enter text:").grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Create a frame to hold the Text widget and scrollbar
        self.text_frame = tk.Frame(master)
        self.text_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # Make sure the grid resizes with the window
        master.grid_rowconfigure(1, weight=1)
        master.grid_columnconfigure(0, weight=1)
        self.text_frame.grid_rowconfigure(0, weight=1)
        self.text_frame.grid_columnconfigure(0, weight=1)

        # Define a fixed-width font (Courier) for consistent line height and width
        self.text_font = Font(size=10)

        # Create the text input and scrollbar
        self.text_input = tk.Text(self.text_frame, height=5, width=30, wrap=tk.WORD, font=self.text_font)
        self.text_input.grid(row=0, column=0, sticky="nsew")

        scrollbar = tk.Scrollbar(self.text_frame, command=self.text_input.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_input.config(yscrollcommand=scrollbar.set)

        self.text_input.insert(tk.END, self.initial_value)

        # Bind the Return/Enter key to the custom function
        self.text_input.bind("<Return>", self.on_enter_key)

        # Allow resizing of the window
        self.resizable(True, True)

        # Bind the <Configure> event to dynamically adjust the text widget size
        self.bind("<Configure>", self.on_resize)

        return self.text_input  # Focus on the text input initially

    def on_resize(self, event):
        if event.widget == self:
            # Adjust the width and height based on font metrics
            char_width = self.text_font.measure("0")  # Width of a character "0"
            line_height = self.text_font.metrics("linespace")  # Height of a line
            new_width = int(self.winfo_width() / char_width)  # Adjust width by character width

            #The -120 here is intended to make room for the buttons at the bottom.
            new_height = int((self.winfo_height()-120) / line_height) # Adjust height by line height
            
            self.text_input.config(width=new_width, height=new_height)

    def on_enter_key(self, event):
        # Insert a newline character when the Enter key is pressed
        self.text_input.insert(tk.INSERT, "\n")
        return "break"  # Prevent the default behavior of closing the dialog

    def buttonbox(self):
        box = tk.Frame(self)

        w = tk.Button(box, text="OK", width=10, command=self.ok)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)

        box.pack()

    def apply(self):
        self.result = self.text_input.get("1.0", tk.END).strip()

class TaggerPanel:
    def __init__(self, bta):
        global bible_data, open_db_file
        self.bta = bta
        self.canvasFont = Font(size = 10)
        self.italicFont = Font(size = 10, slant = 'italic')
        self.boldFont = Font(size = 10, weight = 'bold')
        self.current_data = None
        self.current_item = None

        global open_db_file

        self.canvas_frame = ttk.Frame(self.bta.paned_window)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        # Create a canvas inside a canvas frame
        self.canvas = tk.Canvas(self.canvas_frame)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.canvas.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Create vertical and horizontal scrollbars
        self.v_scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.h_scrollbar = tk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)

        # Configure canvas to use scrollbars
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Add scrollbars to the canvas frame
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.bta.paned_window.add(self.canvas_frame)
        self.note_area_text = "Click to add notes."
        self.verse_xref_list = []
        
        # Configure the scroll region to make the canvas scrollable
        canvas_width = self.canvas.winfo_reqwidth()
        canvas_height = self.canvas.winfo_reqheight()
        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

    def reset_scrollregion(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("ALL"))
        
    def display_attributes(self, item = None, data = None, shift_key = False):
        global bible_data
        #When showing VERSES:
        # item = "verseClick" if a verse was clicked.
        # data = {"verse": the verse text, "ref": the verse reference},
        # shift_key = event.state & (1<<0) #that is, the shift key was pressed if true
        
        #When showing TAGS:
        # item = "tagClick" if a tag was clicked.
        # data = {"ref": the tag name, "id": the tag id}
        # shift_key doesn't matter.

        #print(self.current_item)
        #keep track of what kind of thing we're currently showing.
        update_history = True
        from_history = False
        if item == "history":
            if data["direction"] == "backward":
                item, data = self.bta.history.go_back()
            elif data["direction"] == "forward":
                item, data = self.bta.history.go_forward()
            update_history = False
            from_history = True
        
        # Handle item: if from history and item is None, clear the current state
        # Otherwise, use current_item if item is None
        if item == None:
            if from_history:
                # Going back to "no verse loaded" state
                self.current_item = None
                self.current_data = None
            else:
                # Regular None call, use existing state
                item = self.current_item
        else:
            self.current_item = item 

        #get the verse reference and store in self.current_data['ref']
        if data != None and self.current_item == "verseClick":
            #self.current_data is None the first time a verse is clicked. '-' will be in it if multiple verses are currently selected.
            if (self.current_data is not None) and (shift_key and "-" not in self.current_data['ref']):
                # Shift-clicking from single verse: create new state with extended range
                self.current_data = {"verse": data.get('verse', ''), "ref": combineVRefs(self.current_data['ref'], data['ref'])}
            elif (self.current_data is not None) and (shift_key and "-" in self.current_data['ref']):
                # Shift-clicking from range: create new state extending from start of original range
                self.current_data = {"verse": data.get('verse', ''), "ref": combineVRefs(self.current_data['ref'].split('-')[0], data['ref'])}
            else:
                self.current_data = data
        elif data != None:
            self.current_data = data
        else:
            data = self.current_data
        
        # Add new state to navigation history using the History class
        # Only add to history if we have valid item and data (skip empty initialization calls)
        if update_history and self.current_item is not None and self.current_data is not None:
            self.bta.history.add_or_replace_state(self.current_item, self.current_data)

    
        #Clear the canvas
        self.canvas.delete("all")

        #Set some metrics
        y_offset = 40  # Initial Y offset
        x_offset = 5
        textlineheight = Font.metrics(self.canvasFont)["linespace"]
        boldlineheight = Font.metrics(self.boldFont)["linespace"]
        italiclineheight = Font.metrics(self.italicFont)["linespace"]
        global textlinegap, fbdCircleDiam, textelbowroom
        right_x_offset = 30 #to compensate for the scrollbar
        panelWidth = self.bta.master.winfo_width() - self.bta.paned_window.sashpos(1) - right_x_offset
        note_area_height = 500

        #add stuff to the canvas

        #type_to_get is sent to various functions to tell them what kind of data they're supposed to fetch.
        if self.current_item == "verseClick":
            title_text = "=== Verse Data ==="
            type_to_get = "verse"
        elif self.current_item == "tagClick":
            title_text = "=== Tag Data ==="
            type_to_get = "tag"
        else:
            type_to_get = None
            title_text = "Make a Selection"
            
        self.canvas.create_text(x_offset, y_offset, text=title_text, anchor=tk.W, font=self.boldFont)
        
        # Show navigation buttons (back and forward) - always visible, disabled when unavailable
        button_spacing = 5  # Space between buttons
        base_button_height = textlineheight + 2*textelbowroom
        button_height = int(base_button_height * 0.8)  # 80% height
        button_y_offset = y_offset + (base_button_height - button_height) // 2  # Center vertically
        
        # Forward button (rightmost)
        forward_button_text = "→"
        forward_base_width = self.canvasFont.measure(forward_button_text) + 2*textelbowroom
        forward_button_width = int(forward_base_width * 2.0)  # 200% width
        forward_button_x = panelWidth - 5 - forward_button_width
        
        # Determine if button should be enabled or disabled
        forward_enabled = self.bta.history.can_go_forward()
        forward_color = 'lightgreen' if forward_enabled else 'lightgray'
        forward_text_color = 'black' if forward_enabled else 'gray'
        
        self.canvas.create_rectangle(
            forward_button_x, button_y_offset, 
            forward_button_x + forward_button_width, button_y_offset + button_height, 
            fill=forward_color, tags='forward_button'
        )
        self.canvas.create_text(
            forward_button_x + forward_button_width // 2, button_y_offset + button_height // 2, 
            text=forward_button_text, font=self.canvasFont, fill=forward_text_color, tags='forward_button'
        )
        if forward_enabled:
            self.canvas.tag_bind('forward_button', '<Button-1>', self.go_forward)
        
        # Back button (to the left of forward button)
        back_button_text = "←"
        back_base_width = self.canvasFont.measure(back_button_text) + 2*textelbowroom
        back_button_width = int(back_base_width * 2.0)  # 200% width
        back_button_x = forward_button_x - button_spacing - back_button_width
        
        # Determine if button should be enabled or disabled
        back_enabled = self.bta.history.can_go_back()
        back_color = 'lightblue' if back_enabled else 'lightgray'
        back_text_color = 'black' if back_enabled else 'gray'
        
        self.canvas.create_rectangle(
            back_button_x, button_y_offset, 
            back_button_x + back_button_width, button_y_offset + button_height, 
            fill=back_color, tags='back_button'
        )
        self.canvas.create_text(
            back_button_x + back_button_width // 2, button_y_offset + button_height // 2, 
            text=back_button_text, font=self.canvasFont, fill=back_text_color, tags='back_button'
        )
        if back_enabled:
            self.canvas.tag_bind('back_button', '<Button-1>', self.go_back)
        
        y_offset += boldlineheight + textlinegap + 10
        
        ##### TITLE (the verse reference) ##---- DONE
        if self.current_data is not None:
            self.canvas.create_text(x_offset, y_offset, text=str(self.current_data['ref']), anchor=tk.W, font=self.boldFont)

        y_offset += boldlineheight + textlinegap*5 #*5 because it's a title. Have some gap! Golly!

        #If there's no db file, then we'll only show the buttons to load a db.
        
        if open_db_file is not None:
            #These are the functions for accessing the db:
            # def add_verse_tag(database_file, verse_ref, tag_name):
            # def add_verse_note(database_file, verse_ref, note):
            # def add_tag_note(database_file, tag_name, note):
            # def get_db_stuff(databas_file, x_type, y_type, y_value): #types must be in "verse", "tag", "note"
            
            # NOTES ##---- DONE
            SquareTop = y_offset
            y_offset += textlinegap
            noteTextHeight = 0
            #Check the DB to find out if there are notes for the selected verse or tag
            if type_to_get == "verse":
                # Get notes for verse groups that EXACTLY match the current reference
                self.note_area_text = bibledb_lib.get_note(open_db_file, self.current_data["ref"], bible_data)
            elif type_to_get == "tag":
                # Get note for this specific tag
                note_result = bibledb_lib.get_db_stuff(open_db_file, "note", "tag", self.current_data["ref"])
                self.note_area_text = note_result[0]['note'] if note_result and len(note_result) > 0 else None
            else:
                self.note_area_text = None

            #show the note area text
            if self.note_area_text is not None:
                text_to_render = []
                for paragraph in self.note_area_text.split('\n'):
                    for line in wrapText(paragraph, panelWidth - x_offset*2 - textlinegap*2, self.canvasFont):
                        text_to_render.append(line)
                        #self.canvas.tag_bind(text_object, '<Button-1>', self.edit_note_text)
                        noteTextHeight += textlineheight + textlinegap
                if note_area_height < noteTextHeight:
                    note_area_height = noteTextHeight
                note_area_rectangle = self.canvas.create_rectangle(5, y_offset, panelWidth - 5, y_offset + note_area_height, fill='floral white', tags='notepad_area')
                noteTextHeight = 0
                for line in text_to_render:
                    text_object = self.canvas.create_text(x_offset+textlinegap, y_offset+noteTextHeight, text=line, anchor=tk.NW, font = self.canvasFont, tags='notepad_area')
                    noteTextHeight += textlineheight + textlinegap
                #self.canvas.tag_bind('notepad_area', '<Button-1>', self.edit_note_text)
            else:
                note_area_rectangle = self.canvas.create_rectangle(5, y_offset, panelWidth - 5, y_offset + note_area_height, fill='floral white', tags='notepad_area')
                
                text_object = self.canvas.create_text(x_offset+textlinegap, y_offset+noteTextHeight, text="Click to add notes.", anchor=tk.NW, font = self.canvasFont, tags='notepad_area')
                #self.canvas.tag_bind(text_object, '<Button-1>', self.edit_note_text)
            
            if type_to_get:
                self.canvas.tag_bind('notepad_area', '<Button-1>', lambda event, reference=self.current_data['ref'], reftype = type_to_get: self.edit_note_text(event, reference, reftype))

            y_offset += note_area_height + 10

            # LIST OF TAGS ##---- DONE

            #Check the DB for tags for the selected verse or tag
            if type_to_get:
                self.tags_list = bibledb_lib.get_db_stuff(open_db_file, "tag", type_to_get, self.current_data["ref"])
            else:
                self.tags_list = []

            xb_width = self.canvasFont.measure(" x ")
            tagx = 0

            checklist = self.tags_list.copy() #copy so that we can modify the list while iterating through the unchanged version of it.
            synonymlist = []
            #print("checklist",checklist)
            
            #get all synonymous tags
            for tag in checklist:
                synonyms = bibledb_lib.get_db_stuff(open_db_file,"tag","tag",tag['tag'])
                while len(synonyms) > 0:
                #for synonym in synonyms:
                    synonym = synonyms.pop()
                    if synonym not in self.tags_list and synonym['tag'] != self.current_data["ref"]:
                        #synonyms won't have a delete button on the display, so we group them in the list in order to make it clear what they are.
                        index = self.tags_list.index(tag)
                        self.tags_list.insert(index+1,synonym)
                        synonymlist.append(synonym)
                        synonyms += bibledb_lib.get_db_stuff(open_db_file,"tag","tag",synonym['tag'])

            #show the tags list
            for tag in self.tags_list:
                tagname = tag['tag']
                tag_width =  self.canvasFont.measure(tagname) + 2*textelbowroom

                #wrap tag list
                if tag_width + xb_width + tagx+1 + x_offset + right_x_offset > panelWidth: #+1 for that thicker line between tags
                    tagx = 0
                    y_offset += textlineheight + textlinegap*3

                #tag delete "X" button.
                #only do this if this is not a synonym
                if tag not in synonymlist:
                    tag_delete_binder = "Delete_" + str(tag['tag_id'])
                    tagx += 1 #making a thicker line between tag groups
                    self.canvas.create_rectangle(x_offset+tagx, y_offset, x_offset+tagx+xb_width, y_offset+textlineheight+textlinegap*2, fill='coral1', tags=tag_delete_binder)
                    self.canvas.create_text(x_offset+tagx, y_offset+textlinegap, text=" X", anchor=tk.NW, font=self.canvasFont, tags=tag_delete_binder)
                    self.canvas.tag_bind(tag_delete_binder, '<Button-1>', lambda event, verse=self.current_data['ref'], mytag=tag['tag'], reftype = type_to_get: self.delete_tag(event, verse, mytag, reftype))
                    tagx += xb_width
                #actual tag display
                tag_display_binder = "Display_" + str(tag['tag_id'])
                self.canvas.create_rectangle(x_offset+tagx, y_offset, x_offset+tagx+tag_width, y_offset+textlineheight+textlinegap*2, fill='azure', tags=tag_display_binder)

                #if there's a note on this tag, put a little triangle on the corner of the tag's button
                if (len(bibledb_lib.get_db_stuff(open_db_file, "note", "tag", tagname)) > 0):
                    self.canvas.create_polygon( #triangle for tags with comments
                        x_offset + tagx + tag_width,  # x1: Upper-right corner x
                        y_offset,                     # y1: Upper-right corner y
                        x_offset + tagx + tag_width - 10,  # x2: 10 pixels left of upper-right corner x
                        y_offset,                     # y2: Same y as upper-right corner
                        x_offset + tagx + tag_width,  # x3: Upper-right corner x
                        y_offset + 10,                 # y3: 10 pixels down from upper-right corner y
                        fill='black',
                        outline='black',  # Optional: remove or change if you don't want an outline
                        tags=tag_display_binder
                    )
                self.canvas.create_text(x_offset+tagx, y_offset+textlinegap, text=" " + tag['tag'], anchor=tk.NW, font=self.canvasFont, tags=tag_display_binder)
                #button event to show tag details in this panel...
                self.canvas.tag_bind(tag_display_binder, '<Button-1>', lambda event, item="tagClick", data = {'ref':tagname, 'id':tag['tag_id']} : self.display_attributes(item, data))
                tagx += tag_width

            y_offset += textlineheight + textlinegap*3 + 10

            # CREATE TAG BUTTON ##---- DONE
            # Create a button rectangle.
            buttonText = "Add Tag"
            if type_to_get == "tag":
                buttonText = "Add Tag Synonym"
            if type_to_get:
                button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
                self.create_tag_button_rect = self.canvas.create_rectangle(x_offset, y_offset, x_offset + button_width, y_offset + textlineheight + 2*textelbowroom, fill='azure', tags='create_tag_button')
                self.canvas.create_text(x_offset+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags = 'create_tag_button')#button text for open db
                self.canvas.tag_bind('create_tag_button', '<Button-1>', lambda event, verse=self.current_data['ref'], reftype = type_to_get: self.create_tag(event, verse, reftype))

            y_offset += 10 + textlineheight + 2*textelbowroom

            # NOTES LIST ##---- Show notes from overlapping verse groups
            #only show notes when looking at verses (not tags)
            if self.current_item == "verseClick":
                overlapping_notes = bibledb_lib.get_overlapping_notes(open_db_file, self.current_data['ref'], bible_data)
                
                # Filter out the current reference from the list
                current_ref = self.current_data['ref']
                overlapping_notes = [note_ref for note_ref in overlapping_notes if note_ref != current_ref]
                
                if overlapping_notes:
                    # Title for notes section
                    self.canvas.create_text(x_offset, y_offset, text="Notes:", anchor=tk.W, font=self.canvasFont)
                    y_offset += textlineheight + textlinegap*2
                    
                    # Display each note as a button
                    notex = 0
                    for idx, note_ref in enumerate(overlapping_notes):
                        # note_ref is already a formatted string like "Exodus 1:1"
                        button_width = self.canvasFont.measure(note_ref) + 2*textelbowroom
                        
                        if button_width + notex + x_offset + right_x_offset > panelWidth:
                            notex = 0
                            y_offset += textlineheight + textlinegap*3
                        
                        note_tag = f"note_click_{idx}"
                        self.canvas.create_rectangle(x_offset+notex, y_offset, x_offset+notex+button_width, 
                                                     y_offset+textlineheight+textlinegap*2, fill='lightyellow', tags=note_tag)
                        self.canvas.create_text(x_offset+notex+textelbowroom, y_offset+textlinegap, 
                                               text=note_ref, anchor=tk.NW, font=self.canvasFont, tags=note_tag)
                        
                        # Bind click event to navigate to that verse
                        self.canvas.tag_bind(note_tag, '<Button-1>', 
                                           lambda event, ref=note_ref: 
                                           self.display_attributes("verseClick", {"ref": ref}))
                        notex += button_width
                    
                    y_offset += textlineheight + textlinegap*3 + 10
    
            # VERSE LIST ##---- DONE
            #the verse list only appears when looking at tags.
            if self.current_item == "tagClick":
                verses = bibledb_lib.get_db_stuff(open_db_file, "verse", "tag", self.current_data["ref"])

                #in the case of a tag, all associated tags are synonyms.
                for syntag in self.tags_list:
                    more_verses = bibledb_lib.get_db_stuff(open_db_file, "verse", "tag", syntag['tag'])
                    for another_verse in more_verses:
                        if another_verse not in verses:
                            verses.append(another_verse)

                
                #try:
                    # If the user makes a DB using a version of the Bible that has the apocrypha, and then tries to pull notes about Revelation from that DB while he has a protestant Bible loaded...
                    #    then the reference to bibledb_lib.book_proper_names[] will throw an index out of range error.
                    #    I am making this tool primarily for myself to use, and I don't include the apocrypha in my Bible, so I don't plan to fix this.
                verses.sort(key=lambda r: (r["start_book"], r["start_chapter"], r["start_verse"]))
                self.verse_xref_list = [(bibledb_lib.book_proper_names[x["start_book"]]+" "+str(x["start_chapter"])+":"+str(x["start_verse"]), bibledb_lib.book_proper_names[x["end_book"]]+" "+str(x["end_chapter"])+":"+str(x["end_verse"])) for x in verses]
                #except:
                    #self.verse_xref_list = []
                    #print("Failed to get the verse references for that tag. This error might occur if your DB was made with a version of the Bible that had different books from the version you're currently using. For example, if the DB was made including the apocrypha, but your current Bible doesn't have it.")
                tagx = 0
                for xverse in self.verse_xref_list:
                    itemText = combineVRefs(xverse[0],xverse[1])
                    button_width = self.canvasFont.measure(itemText) + 2*textelbowroom
                    if button_width + tagx + x_offset + right_x_offset > panelWidth:
                        tagx = 0
                        y_offset += textlineheight + textlinegap*3
                    clicktag = "verse_click_"+str(tagx)+"_"+str(y_offset)
                    self.canvas.create_rectangle(x_offset+tagx, y_offset, x_offset+tagx+button_width, y_offset+textlineheight+textlinegap*2, fill='azure', tags=clicktag)
                    self.canvas.create_text(x_offset+tagx+textelbowroom, y_offset+textlinegap, text=itemText, anchor=tk.NW, font = self.canvasFont, tags=clicktag)
                    self.canvas.tag_bind(clicktag, '<Button-1>', lambda event, payload=xverse: self.tag_verse_click(event, payload))
                    tagx += button_width
                y_offset += textlineheight + textlinegap*3 + 10

            # Configure the scroll region to make the canvas scrollable
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self.canvas.xview_moveto(0)
            self.canvas.yview_moveto(0)
        else:
            self.canvas.create_text(x_offset, y_offset, text="No DB Loaded", anchor=tk.W, font=self.canvasFont)
            y_offset += textlineheight + textlinegap*5 #*5 because it's a title. Have some gap! Golly!

        # DB buttons have been moved to NavigationTree (below the tree)
        
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    
    def go_back(self, _):
        """Navigate backward in history"""
        if self.bta.history.can_go_back():
            self.display_attributes("history", {"direction": "backward"}, False)
            self.reset_scrollregion(None)
    
    def go_forward(self, _):
        """Navigate forward in history"""
        if self.bta.history.can_go_forward():
            self.display_attributes("history", {"direction": "forward"}, False)
            self.reset_scrollregion(None)
    
    def tag_verse_click(self, event, payload):
        #payload = (startverse, endverse)
        self.bta.options_callback(payload)
        
    def delete_tag(self, event, verse, tag, reftype):
        answer = messagebox.askyesno("Really delete?", "Do you want to remove tag \""+str(tag)+"\"?")
        if answer:
            if reftype == "verse":
                bibledb_lib.delete_verse_tag(open_db_file, verse, tag)
            elif reftype == "tag":
                #in this case, "verse" is just another tag.
                bibledb_lib.delete_tag_tag(open_db_file, verse, tag)
            self.display_attributes()
            self.bta.cause_canvas_to_refresh()
            self.bta.update_tree_colors()
        else:
            print("Tag deletion canceled")

    def create_tag(self, event, verse, reftype):
        #tag = simpledialog.askstring("Add Tag", "Enter Tag:", initialvalue="") #OLD WAY -- no tag suggestions
        global open_db_file, bible_data
        tag = TagInputDialog(self.bta.master,open_db_file).selected_tag
        #print("the selected tag is:",tag,type(tag))
        #print("Do the tag creation logic here")
        if (tag is not None) and (tag != ""):
            if reftype == "verse":
                bibledb_lib.add_verse_tag(open_db_file, verse, tag, bible_data)
            elif reftype == "tag":
                #in this case, "verse" is just another tag.
                bibledb_lib.add_tag_tag(open_db_file, verse, tag)
            self.display_attributes()
            self.bta.cause_canvas_to_refresh()
            self.bta.update_tree_colors()
            #move the canvas to the bottom.
            #it's a little jumpy, but entirely critical when addint lots of tags to a page with very long notes.
            self.canvas.yview_moveto(1.0)
        else:
            pass
            #print("Tag creation cancelled")
    
    def edit_note_text(self, event, reference, reftype):
        #print(type(self.note_area_text),self.note_area_text)
        current_text = self.note_area_text
        if current_text == None:
            current_text = ""
        MultiLineInputDialog.initial_value = current_text
        dialog = MultiLineInputDialog(self.bta.master, "Edit Notes")
        new_text = dialog.result
        #print(new_text)
        if new_text is not None and new_text != "":
            global bible_data
            self.note_area_text = new_text
            if reftype == "verse":
                bibledb_lib.add_verse_note(open_db_file, reference, new_text, bible_data)
            elif reftype == "tag":
                bibledb_lib.add_tag_note(open_db_file, reference, new_text)
            self.display_attributes()
            self.bta.cause_canvas_to_refresh()
            self.bta.update_tree_colors()
        elif new_text == "":
            answer = messagebox.askyesno("Really delete?", "Do you want to delete this note?")
            if answer:
                if reftype == "verse":
                    bibledb_lib.delete_verse_note(open_db_file, reference)
                elif reftype == "tag":
                    bibledb_lib.delete_tag_note(open_db_file, reference)
                self.display_attributes()
                self.bta.cause_canvas_to_refresh()
                self.bta.update_tree_colors()



def migrate_db(db_path, interactive=True):
    """
    Migrate a database to the current version.
    
    Args:
        db_path: Path to the database file to migrate
        interactive: If True, prompt user for confirmation. If False, migrate automatically.
    
    Returns:
        tuple: (success: bool, backup_path: str or None)
               success is True if migration successful or not needed, False otherwise
               backup_path is the path to the backup file created, or None if no backup
    """
    if not os.path.exists(db_path):
        print(f"✗ Error: Database file not found: {db_path}")
        return False, None
    
    # Check current database version
    current_version = bibledb_lib.get_database_version(db_path)
    target_version = bibledb_lib.CURRENT_DATABASE_VERSION

    if current_version == target_version:
        if interactive:
            print(f"Database is already at version {target_version}")
        return True, None

    if current_version > target_version:
        print(f"Error: Database version ({current_version}) is newer than expected ({target_version})")
        print("This may happen if you're using an older version of Bible Tagger")
        return False, None

    # Find migration path
    migration_dir = "db_migration"
    if not os.path.exists(migration_dir):
        print(f"Error: Migration directory not found: {migration_dir}")
        return False, None

    if interactive:
        print(f"Database: {db_path}")
        print(f"Current version: {current_version}")
        print(f"Target version: {target_version}")

    # Build migration chain
    migration_chain = []
    current = current_version

    while current < target_version:
        next_version = current + 1
        migration_file = os.path.join(migration_dir, f"{current}-to-{next_version}.py")
        
        if not os.path.exists(migration_file):
            print(f"Error: Missing migration script: {migration_file}")
            print(f"Cannot migrate from version {current} to {next_version}")
            return False, None

        migration_chain.append((current, next_version, migration_file))
        current = next_version

    # Display migration plan
    if interactive:
        print(f"\nMigration plan:")
        for from_ver, to_ver, script in migration_chain:
            print(f"  {from_ver} → {to_ver}: {script}")

        print(f"\nThis will migrate the database through {len(migration_chain)} step(s)")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled")
            return False, None

    # Calculate backup path
    base_path = os.path.splitext(db_path)[0]
    backup_path = f"{base_path}_backup.bdb"

    # Execute migrations
    for index, (from_ver, to_ver, script) in enumerate(migration_chain):
        if interactive:
            print(f"\n{'='*60}")
            print(f"Executing migration: {from_ver} → {to_ver}")
            print(f"{'='*60}")

        # Import and run the migration script
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"migration_{from_ver}_to_{to_ver}", script)
        migration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)

        # Call the migrate_database function from the migration script
        # Only create backup for the first migration in the chain
        if hasattr(migration_module, 'migrate_database'):
            create_backup = (index == 0)  # Only backup on first migration
            success = migration_module.migrate_database(db_path, create_backup=create_backup)
            if not success:
                print(f"\nMigration failed at step {from_ver} → {to_ver}")
                return False, backup_path if index == 0 and os.path.exists(backup_path) else None
        else:
            print(f"Error: Migration script {script} does not have migrate_database function")
            return False, None
    
    if interactive:
        print(f"\n{'='*60}")
        print(f"All migrations completed successfully!")
        print(f"{'='*60}")
        print(f"Database is now at version {target_version}")
    
    return True, backup_path


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Bible Tagger")

    # Add optional arguments for the main GUI mode
    parser.add_argument("--db", dest="db_path", help="Path to database file (overrides config)")
    parser.add_argument("--json", dest="json_path", help="Path to Bible JSON file (overrides config)")

    subparsers = parser.add_subparsers(dest="command", required=False)

    # migrate
    migrate_parser = subparsers.add_parser("migrate", help="Migrate old database")
    migrate_parser.add_argument("old_db", nargs='?', help="Path to old database to migrate (defaults to database in config)")

    # config
    config_parser = subparsers.add_parser("config", help="Manage configuration files")
    config_sub = config_parser.add_subparsers(dest="action")
    config_sub.add_parser("new", help="Create new configuration file")
    config_sub.add_parser("update", help="Update current configuration file with options from newest template")
    config_sub.add_parser("validate", help="Validate current configuration file")

    # scrape
    scrape_parser = subparsers.add_parser("scrape", help="Scrape bible translation for use with Bible Tagger")
    scrape_parser.add_argument("version", help="Version to scrape")

    args = parser.parse_args()

    template_filename = f'template.{config_filename}'

    def create_config():
        with open(template_filename, 'r') as template_file:
            template_content = template_file.read()
        with open(config_filename, 'w') as config_file:
            config_file.write(template_content)

    def update_config():
        """Update config file with missing options from template"""
        if not os.path.exists(config_filename):
            print(f"Config file not found: {config_filename}")
            print("Creating new config file...")
            create_config()
            return
        
        # Read existing config and template
        existing_config = configparser.ConfigParser()
        existing_config.read(config_filename)
        
        template_config = configparser.ConfigParser()
        template_config.read(f'template.{config_filename}')
        
        updated = False
        # Add missing sections and options from template
        for section in template_config.sections():
            if not existing_config.has_section(section):
                existing_config.add_section(section)
                print(f"Added missing section: [{section}]")
                updated = True
            
            for option in template_config.options(section):
                if not existing_config.has_option(section, option):
                    value = template_config.get(section, option)
                    existing_config.set(section, option, value)
                    print(f"Added missing option: {option} in [{section}]")
                    updated = True
        
        # Also check DEFAULT section
        for option in template_config.defaults():
            if option not in existing_config.defaults():
                value = template_config.get('DEFAULT', option)
                existing_config.set('DEFAULT', option, value)
                print(f"Added missing option: {option} in [DEFAULT]")
                updated = True
        
        if updated:
            with open(config_filename, 'w') as config_file:
                existing_config.write(config_file)
            print(f"Config file updated")
        else:
            print(f"Config file is up to date")
    
    def validate_config():
        """Validate config file against template for missing or malformed options"""
        if not os.path.exists(config_filename):
            print(f"Config file not found: {config_filename}")
            print("Run 'python bible_tagger.py config new' to create one")
            return False
        
        if not os.path.exists(template_filename):
            print(f"Template file not found: {template_filename}")
            print("Cannot validate without template")
            return False
        
        # Read config file
        cfg_check = configparser.ConfigParser()
        try:
            cfg_check.read(config_filename)
        except Exception as e:
            print(f"Error reading config file: {e}")
            return False
        
        # Read template file
        template_config = configparser.ConfigParser()
        try:
            template_config.read(template_filename)
        except Exception as e:
            print(f"Error reading template file: {e}")
            return False

        valid = True
        
        # Check for missing sections (excluding DEFAULT which is implicit)
        for section in template_config.sections():
            if not cfg_check.has_section(section):
                print(f"Missing section: [{section}]")
                valid = False
        
        # Check for missing options in each section
        for section in template_config.sections():
            if cfg_check.has_section(section):
                for option in template_config.options(section):
                    if not cfg_check.has_option(section, option):
                        print(f"Missing option in [{section}]: {option}")
                        valid = False
        
        # Check DEFAULT section options
        for option in template_config.defaults():
            if option not in cfg_check.defaults():
                print(f"Missing option in [DEFAULT]: {option}")
                valid = False
        
        # Validate boolean values (use_last_db, use_last_bible)
        if cfg_check.has_option('DEFAULT', 'use_last_db'):
            try:
                use_last_db = cfg_check.get('DEFAULT', 'use_last_db')
                if use_last_db.strip() and use_last_db.lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                    print(f"Invalid boolean value for use_last_db: '{use_last_db}'")
                    print("   Expected: true, false, yes, no, 1, or 0")
                    valid = False
            except Exception as e:
                print(f"Error validating use_last_db: {e}")
                valid = False
        
        if cfg_check.has_option('DEFAULT', 'use_last_bible'):
            try:
                use_last_bible = cfg_check.get('DEFAULT', 'use_last_bible')
                if use_last_bible.strip() and use_last_bible.lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                    print(f"Invalid boolean value for use_last_bible: '{use_last_bible}'")
                    print("   Expected: true, false, yes, no, 1, or 0")
                    valid = False
            except Exception as e:
                print(f"Error validating use_last_bible: {e}")
                valid = False
        
        # Check file paths if specified (warnings only, not errors)
        json_path = cfg_check.get('DEFAULT', 'json_path', fallback=None)
        if json_path and json_path.strip() and json_path not in ['#', '# relative or absolute path']:
            if not os.path.exists(json_path):
                print(f"Info: JSON file not found: {json_path}")
                print("   (This is just a warning - you can set it later)")
        
        bdb_path = cfg_check.get('DEFAULT', 'bdb_path', fallback=None)
        if bdb_path and bdb_path.strip() and bdb_path not in ['./MyDB.bdb', '# relative or absolute path']:
            if not os.path.exists(bdb_path):
                print(f"Info: BDB file not found: {bdb_path}")
                print("   (This is just a warning - file will be created when needed)")
        
        if valid:
            print(f"Config file is valid")
        else:
            print(f"\nConfig file has issues")
            print("Run 'python bible_tagger.py config update' to fix missing options")
        
        return valid

    if args.command == "config":
        if args.action == "new":
            if os.path.exists(config_filename):
                response = input(f"Error: Config file already exists: {config_filename}")
            else:
                create_config()
                print(f"Config file created: {config_filename}")
        elif args.action == "update":
            update_config()
        elif args.action == "validate":
            validate_config()

    if not os.path.exists(config_filename):
        create_config()

    if args.command is None:
        cfg = configparser.ConfigParser()
        cfg.read(config_filename)

        root = tk.Tk()
        root.title("Bible Tagger")
        root.iconbitmap("./bibletaggericon.ico")

        bta = BibleTaggerApp(root, args)

        root.mainloop()
    elif args.command == "migrate":
        # Determine which database to migrate
        if hasattr(args, 'old_db') and args.old_db:
            db_to_migrate = args.old_db
        else:
            # Use database from config file
            cfg_temp = configparser.ConfigParser()
            cfg_temp.read(config_filename)
            db_to_migrate = cfg_temp.get('DEFAULT', 'bdb_path', fallback=None)
            
            if not db_to_migrate:
                print("Error: No database specified and no database found in config file")
                print("Usage: python bible_tagger.py migrate <database_path>")
                sys.exit(1)
        
        # Use the refactored migrate_db function
        success, _ = migrate_db(db_to_migrate, interactive=True)
        sys.exit(0 if success else 1)
    elif args.command == "scrape":
        print(f"Scraping Bible version: {args.version}")
        print("\nScraping not yet implemented.")
        print("\nThis feature will allow you to scrape Bible translations from online sources")
        print("and convert them to JSON format for use with Bible Tagger.")
        print("\nFor now, you can use the SWORD-to-JSON converter in the project folder.")
        sys.exit(1)

