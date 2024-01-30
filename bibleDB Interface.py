import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import bibledb_Lib
from tkinter.font import Font
from tkinter import Misc
from tkinter import simpledialog
from tkinter import messagebox

textlinegap = 2
windowsize = "1000x600"
textelbowroom = 10 #that's "elbow room" for left and right spacing
bible_data = {}

open_db_file = None


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
    lines.append(line)
    return lines

def combineVRefs(vref1, vref2):
    #get the verse reference and store in self.current_data['ref']
    #start book and chapter
    bookparts = vref1.split(":")[0].split(" ")
    bA = ""
    i = 0
    while i < len(bookparts)-1:
       bA += bookparts[i] + " "
       i+= 1
    bA = bA.strip()
    cA = vref1.split(":")[0].split(" ")[i]
    bookparts = vref2.split(":")[0].split(" ")
    #end book and chapter
    bB = ""
    i = 0
    while i < len(bookparts)-1:
       bB += bookparts[i] + " "
       i+= 1
    bB = bB.strip()
    cB = vref2.split(":")[0].split(" ")[i]
    #start and end verses
    vA = vref1.split(":")[1]
    vB = vref2.split(":")[1]
    if bA != bB: #different book
        if bibledb_Lib.book_proper_names.index(bA) < bibledb_Lib.book_proper_names.index(bB):
            return(bA+" "+cA + ":" + vA + " - " + bB + " " +cB + ":" + vB)
        else:
            return(bB+" "+cB + ":" + vB + " - " + bA + " " +cA + ":" + vA)
    elif cA != cB: #same book, different chapter
        if int(cA) < int(cB):
            return(bA+" "+cA + ":" + vA + "-" + cB + ":" + vB)
        else:
            return(bA+" "+cB + ":" + vB + "-" + cA + ":" + vA)
    elif vA != vB: #same book, same chapter, different verse
        if int(vA) < int(vB):
            return(bA+" "+cA + ":" + vA + "-" + vB)
        else:
            return(bA+" "+cB + ":" + vB + "-" + vA)
    else: #same book, same chapter, same verse
        return vref1
    

class MainWindow:
    def __init__(self, master):
        self.master = master
        global bible_data, windowsize

        self.master.geometry(windowsize)

        self.paned_window = ttk.PanedWindow(self.master, orient="horizontal")
        self.paned_window.pack(fill="both", expand=True)

        self.navigation_tree = NavigationTree(self.master, self.paned_window, self.tree_callback)
        self.canvas_view = CanvasView(self.master, self.paned_window, self.canvas_callback)
        self.options_panel = OptionsPanel(self.master, self.paned_window, self.options_callback, self.cause_canvas_to_refresh)

        self.paned_window.bind("<B1-Motion>", self.on_sash_drag)
        self.paned_window.bind("<Configure>", lambda event : self.options_panel.display_attributes(None))
        
    def on_sash_drag(self,event):
        # If the moved sash is near the treeview sash (left), update the tree view
        if self.paned_window.sashpos(0) - 10 < event.x < self.paned_window.sashpos(0) + 10:
            new_sash_position = event.x
            self.navigation_tree.tree_frame.columnconfigure(0, weight=1)
            self.navigation_tree.tree_frame.configure(width=new_sash_position)
            self.navigation_tree.tree.column("#0", width=new_sash_position)
        #elif the moved sash is near the options panel (right), update the options panel
        elif self.paned_window.sashpos(1) - 10 < event.x < self.paned_window.sashpos(1) + 10:
            self.canvas_view.canvas_callback(None, None)
        #in both cases, we need to update the canvas where the verses are (middle)
        self.canvas_view.display_chapter()
        self.options_panel.display_attributes()

        #To Do: account for situations where the user puts the sashes together.

    def tree_callback(self, item, data, reset_scrollbar):
        # handle canvas-related actions caused by tree interactions here
        # You can call the CanvasView methods to update the canvas
        # For example, self.canvas_view.display_attributes(attributes)
        self.canvas_view.display_chapter(item, data, reset_scrollbar)
        self.canvas_view.reset_scrollregion(item)
        

    def canvas_callback(self, item, data, shift_key = False):
        # item is either "verseClick" or "tagClick", depending on what was clicked.
        # data is like {"verse":"in the beginning...", "ref": "Genesis 1:1"}
        
        # handle tree-related actions caused by canvas interactions here
        self.options_panel.display_attributes(item, data, shift_key)
        self.options_panel.reset_scrollregion(item)
        1;

    def cause_canvas_to_refresh(self):
        self.canvas_view.display_chapter()
    
    def options_callback(self, data):
        #this is used when you are looking at tag xref data and you click a verse associated with the tag.
        #causes the tree and canvas to navigate to the verse you clicked.
        #data = (startverse, endverse)
        start = bibledb_Lib.parseVerseReference(data[0])
        end = bibledb_Lib.parseVerseReference(data[1])

        

        #we don't yet support verse ranges that span books
        self.canvas_view.selected_start_b = bibledb_Lib.book_proper_names[start['sb']]
        self.canvas_view.selected_end_b = bibledb_Lib.book_proper_names[end['eb']]
        self.canvas_view.selected_start_c = start['sc']
        self.canvas_view.selected_end_c = end['ec']
        self.canvas_view.selected_start_v = start['sv']
        self.canvas_view.selected_end_v = end['ev']

        #navigate to the first verse in the range
        navtreedata = "/"+bibledb_Lib.book_proper_names[start['sb']]+"/Ch "+start['sc']
        self.navigation_tree.select_item(navtreedata)
        
        self.options_panel.display_attributes("verseClick", {"verse": "This part of the code was never implemented", "ref": combineVRefs(data[0],data[1])}, False)
        self.options_panel.reset_scrollregion(None)
        #self.canvas_view.display_chapter(reset_scrollbar = True)
        #self.canvas_view.reset_scrollregion()
        
        1;

class NavigationTree:
    def __init__(self, master, paned_window, tree_callback, weight=1):
        self.master = master
        global data_model
        self.paned_window = paned_window
        self.tree_item_data = {}
        self.treeFont = Font()
        self.tree_callback = tree_callback
        
        # Create a frame for the button and tree
        self.tree_frame = ttk.Frame(self.paned_window)
        self.tree_frame.grid(row=0, column=0, sticky="nsew")
        self.tree_frame.grid_rowconfigure(1, weight=1) #tree stretches to bottom of window

        # Create a button for opening the file dialog
        self.open_button = tk.Button(self.tree_frame, text="Open Bible json File", command=self.open_file_dialog)
        self.open_button.grid(row=0, column=0, sticky="nsew") #button to open new files

        # Create a tree view
        self.tree = ttk.Treeview(self.tree_frame, show='tree')
        self.tree.grid(row=1, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.paned_window.add(self.tree_frame)
        self.tree.bind("<ButtonRelease-1>", self.on_tree_item_click)
        
    def populate_tree(self, data, parent_id):
        for key, value in data.items():
            item_id = self.tree.insert(parent_id, 'end', text=key, iid=parent_id+"/"+key)
            self.tree_item_data[item_id] = value  # Store the associated data
            i = 0
            while i < len(value):
                chapter_id = self.tree.insert(item_id, 'end', text="Ch "+str(i+1), iid=item_id+"/Ch "+str(i+1))
                self.tree_item_data[chapter_id] = value[i]  # Store the associated data
                #TO DO: Remove the above line (self.tree_item_data[chapter_id] = value[i]) if not used
                i += 1

    def select_item(self, item_path):
        path_elements = item_path.split("/")
        current_item = ""

        for element in path_elements:
            current_item += element
            self.tree.item(current_item, open=True)  # Expand the parent item
            current_item += "/"
        
        # Select the final item
        self.tree.selection_set(current_item[:-1])
        self.on_tree_item_click()
        
    def on_tree_item_click(self, event=None):
        try:
            item_id = self.tree.selection()[0]
            children = self.tree.get_children(item_id)
                
            self.tree.column("#0", stretch=False)
            self.tree.update_idletasks()

            #adjust width of tree to accommodate width of selected item
            text_width = self.treeFont.measure(self.tree.item(item_id, 'text').strip())
            tab_width = self.tree.bbox(item_id, column="#0")[0]  # Get the width of the last column
            content_width = text_width+tab_width
            #print(self.tree.bbox(item_id, column="#0"))
            #print(str(text_width) + ", " + str(tab_width) + ", " + str(self.tree.winfo_width()))
            #print(self.tree.item(item_id, 'text'))
            #print(Font().actual())

            if content_width > self.tree.winfo_width():
                self.tree.column("#0", width=content_width)  # Adjust the column width
            else:
                self.tree.column("#0", width=self.tree.winfo_width())  # Set the width to the visible width

            #get the data associated with that item and pass it to the canvas for display
            item_data = self.tree_item_data.get(item_id)
            #print("sending..." + str(attributes))
            # Use the callback in the NavigationTree class to handle the canvas update
            reset_scrollbar = True
            self.tree_callback(item_id, item_data, reset_scrollbar)
        except IndexError:
            #clicking white space on the list throws this error. Just don't update the item.
            pass 

    
    def open_file_dialog(self):
        global data_model
        file_path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON Bibles", "*.json"), ("All files", "*.*")])
        if file_path and file_path[-5:] == '.json':
            print(f"Selected file: {file_path}")
            with open(file_path, 'r') as file:
                content = file.read()
            data_model = bibledb_Lib.getBibleData(content)
            #print("dumping output from open_file_dialog")
            #print(data_model)
            self.populate_tree(data_model, '')
        else:
            print("Invalid file! It's gotta be a json file. Funny thing about this: you could use this program to make notes about any kind of JSON data which is organized in a way similar to a supported Bible JSON file.")
            

class CanvasView:
    def __init__(self, master, paned_window, canvas_callback):
        self.canvas_callback = canvas_callback
        self.master = master
        global data_model, open_db_file
        self.paned_window = paned_window
        self.canvasFont = Font(size = 10)
        self.italicFont = Font(size = 10, slant = 'italic')
        self.boldFont = Font(size = 10, weight = 'bold')
        self.italicunderlineFont = Font(size=10, slant='italic', underline=True)


        self.canvas_frame = ttk.Frame(self.paned_window)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        # Create a canvas inside a canvas frame
        self.canvas = tk.Canvas(self.canvas_frame)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.canvas.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Create vertical and horizontal scrollbars
        v_scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        h_scrollbar = tk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)

        # Configure canvas to use scrollbars
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Add scrollbars to the canvas frame
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.scrollbar_width = v_scrollbar.winfo_reqwidth()

        self.selected_start_v = -1
        self.selected_end_v = -1
        self.selected_start_c = -1
        self.selected_end_c = -1
        self.selected_start_b = ""
        self.selected_end_b = ""

        self.paned_window.add(self.canvas_frame)

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
        self.canvas_callback("verseClick", {"verse": item_id, "ref": scopename}, event.state & (1<<0))
        
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
        bb = bibledb_Lib.getBookIndex(bookname)
        sb = bibledb_Lib.getBookIndex(self.selected_start_b)
        eb = bibledb_Lib.getBookIndex(self.selected_end_b)
        #print(vv)
        #print(cc)
        if event.state & (1<<0):
            #print("shift key pressed")
            #shift key is pressed
            #set selected chapters in order
            if bb > sb:
                self.selected_end_b = bibledb_Lib.book_proper_names[bb]
                eb = bb
                self.selected_end_c = cc
                self.selected_end_v = vv
            elif bb < sb:
                self.selected_end_b = bibledb_Lib.book_proper_names[sb]
                eb = sb
                self.selected_start_b = bibledb_Lib.book_proper_names[bb]
                sb = bb
                self.selected_end_c = self.selected_start_c
                self.selected_start_c = cc
                self.selected_end_v = self.selected_start_v
                self.selected_start_v = vv
            else: #same book
                self.selected_start_b = bibledb_Lib.book_proper_names[bb]
                sb = bb
                self.selected_end_b = bibledb_Lib.book_proper_names[bb]
                eb = bb
            if sb == eb:
                if cc > self.selected_start_c:
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
            self.selected_start_b = bibledb_Lib.book_proper_names[bb]
            self.selected_end_b = bibledb_Lib.book_proper_names[bb]
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
        
        item_hierarchy = item.split('/')
        if len(item_hierarchy) > 2:
            #print(item)
            #print(item_hierarchy)
            #print(self.selected_start_b)
            #print(self.selected_end_b)
            thisbook = item.split('/')[-2]
            thischapter = item.split(' ')[-1]

            #we're going to draw vertical lines left of the verses to indicate which verses have notes and tags.
            #get the tagged and noted verse rows
            notestags = bibledb_Lib.find_note_tag_verses(open_db_file, thisbook, thischapter)
            #move the verses over to make room for the lines. One pixel for each unique verse ID.
            id_lines = len(notestags)*2
            if id_lines > 0:
                x_offset += id_lines

            #show the chapter header 
            self.canvas.create_text(x_offset, y_offset, text=str(thisbook)+" Chapter "+str(thischapter), anchor=tk.W, font = self.boldFont)
            y_offset += boldlineheight + textlinegap*2
            
            verse_area_width = self.paned_window.sashpos(1) - self.paned_window.sashpos(0) - self.scrollbar_width - textelbowroom*2
            v = 1
            c = int(item_hierarchy[-1].replace("Ch ",""))
            b = int(bibledb_Lib.getBookIndex(item_hierarchy[-2]))
            sv = int(self.selected_start_v)
            ev = int(self.selected_end_v)
            sc = int(self.selected_start_c)
            ec = int(self.selected_end_c)
            sb = int(bibledb_Lib.getBookIndex(self.selected_start_b))
            eb = int(bibledb_Lib.getBookIndex(self.selected_end_b))

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

                
                vtop = y_offset - textlinegap
                
                verseRef = str(item).replace("/Ch "," ").replace("/","")+":"+str(v)
                #print(verseRef)
                lineNotPrinted = True
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
                color = "purple"
                lx = x_offset - id_lines
                if t == "tag": #blue if just a tag
                    color = "blue"
                elif t == "note": #orange if just a note
                    color = "orange4"
                for verse in verse_heights:
                    v = verse['v']
                    if ((sb == b and sc == c and sv <= v) or\
                        (sb == b and sc < c) or\
                        (sb < b)) and\
                       ((eb == b and ec == c and ev >= v) or\
                        (eb == b and ec > c) or\
                        (eb > b)):
                        self.canvas.create_line(lx, verse['top'], lx, verse['bot'], fill=color, width=1)
                id_lines -= 2
                        
        #print(item_hierarchy)
        #print(data)

        # Configure the scroll region to make the canvas scrollable
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if(reset_scrollbar):
            self.canvas.xview_moveto(0)
            self.canvas.yview_moveto(0)
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

        tk.Label(master, text="Enter text:").grid(row=0, column=0, padx=10, pady=10)

        self.text_input = tk.Text(master, height=5, width=30)
        self.text_input.grid(row=1, column=0, padx=10, pady=10)
        self.text_input.insert(tk.END, self.initial_value)

        # Bind the Return/Enter key to the custom function
        self.master.bind("<Return>", self.on_enter_key)

        return self.text_input  # Focus on the text input initially

    def on_enter_key(self, event):
        # Insert a newline character when the Enter key is pressed
        self.text_input.insert(tk.END, "\n")
    def buttonbox(self):
        box = tk.Frame(self)

        w = tk.Button(box, text="OK", width=10, command=self.ok)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)

        box.pack()

    def apply(self):
        self.result = self.text_input.get("1.0", tk.END).strip()

class OptionsPanel:
    def __init__(self, master, paned_window, options_callback, cause_canvas_to_refresh):
        self.options_callback = options_callback
        self.cause_canvas_to_refresh = cause_canvas_to_refresh
        self.master = master
        global data_model, open_db_file
        self.paned_window = paned_window
        self.canvasFont = Font(size = 10)
        self.italicFont = Font(size = 10, slant = 'italic')
        self.boldFont = Font(size = 10, weight = 'bold')
        self.current_data = None
        self.current_item = None
        
        global open_db_file


        self.canvas_frame = ttk.Frame(self.paned_window)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        # Create a canvas inside a canvas frame
        self.canvas = tk.Canvas(self.canvas_frame)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.canvas.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Create vertical and horizontal scrollbars
        v_scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        h_scrollbar = tk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)

        # Configure canvas to use scrollbars
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Add scrollbars to the canvas frame
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.paned_window.add(self.canvas_frame)
        self.note_area_text = "Click to add notes."
        self.verse_xref_list = []
        
        # Configure the scroll region to make the canvas scrollable
        canvas_width = self.canvas.winfo_reqwidth()
        canvas_height = self.canvas.winfo_reqheight()
        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

    def reset_scrollregion(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("ALL"))
        
    def display_attributes(self, item = None, data = None, shift_key = False):
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
        if item == None:
            item = self.current_item
        else:
            self.current_item = item
            
        #get the verse reference and store in self.current_data['ref']
        if data != None and self.current_item == "verseClick":
            if shift_key and "-" not in self.current_data['ref']:
                self.current_data['ref'] = combineVRefs(self.current_data['ref'], data['ref'])
            else:
                self.current_data = data
        elif data != None:
            self.current_data = data
        else:
            data = self.current_data

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
        panelWidth = self.master.winfo_width() - self.paned_window.sashpos(1) - right_x_offset
        note_area_height = 300 #The height of the "notes" text entry area

        #add stuff to the canvas

        #type_to_get is sent to various functions to tell them what kind of data they're supposed to fetch.
        if self.current_item == "verseClick":
            title_text = "=== Verse Data ==="
            type_to_get = "verse"
        elif self.current_item == "tagClick":
            title_text = "=== Tag Data ==="
            type_to_get = "tag"
        else:
            title_text = "Make a Selection"
            
        self.canvas.create_text(x_offset, y_offset, text=title_text, anchor=tk.W, font=self.boldFont)
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
            #Check the DB to find out if there are notes for the selected verse
            # (here we are assuming that we're showing a verse. Later we need to add support for showing tag data)
            # For now, we're only showing index 0, the first row of the results, because idk if I'm going to permit more rows than that to exist.
            note_query_result = bibledb_Lib.get_db_stuff(open_db_file, "note", type_to_get, self.current_data["ref"])
                
            if len(note_query_result) > 0:
                self.note_area_text = note_query_result[0]['note']
            else:
                self.note_area_text = None
            
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
            
            self.canvas.tag_bind('notepad_area', '<Button-1>', lambda event, reference=self.current_data['ref'], reftype = type_to_get: self.edit_note_text(event, reference, reftype))

            y_offset += note_area_height + 10

            # LIST OF TAGS ##---- DONE

            #Check the DB for tags for the selected verse
            # (here we are assuming that we're showing a verse. Later we need to add support for showing tag data)
            self.tags_list = bibledb_Lib.get_db_stuff(open_db_file, "tag", type_to_get, self.current_data["ref"])

            xb_width = self.canvasFont.measure(" x ")
            tagx = 0

            checklist = self.tags_list
            synonymlist = []
            
            #get all synonymous tags
            for tag in checklist:
                synonyms = bibledb_Lib.get_db_stuff(open_db_file,"tag","tag",tag['tag'])
                for synonym in synonyms:
                    if synonym not in self.tags_list and synonym['tag'] != self.current_data["ref"]:
                        #synonyms won't have a delete button on the display, so we group them in the list in order to make it clear what they are.
                        index = self.tags_list.index(tag)
                        self.tags_list.insert(index+1,synonym)
                        synonymlist.append(synonym)

            
            #show the tags list
            for tag in self.tags_list:
                tagname = tag['tag']
                tag_width =  self.canvasFont.measure(tagname) + 2*textelbowroom

                #wrap tag list
                if tag_width + xb_width + tagx + x_offset + right_x_offset > panelWidth:
                    tagx = 0
                    y_offset += textlineheight + textlinegap*3

                #tag delete "X" button.
                #only do this if this is not a synonym
                if tag not in synonymlist:
                    tag_delete_binder = "delete_" + str(tag['id'])
                    self.canvas.create_rectangle(x_offset+tagx, y_offset, x_offset+tagx+xb_width, y_offset+textlineheight+textlinegap*2, fill='coral1', tags=tag_delete_binder)
                    self.canvas.create_text(x_offset+tagx, y_offset+textlinegap, text=" X", anchor=tk.NW, font=self.canvasFont, tags=tag_delete_binder)
                    self.canvas.tag_bind(tag_delete_binder, '<Button-1>', lambda event, verse=self.current_data['ref'], mytag=tag['tag'], reftype = type_to_get: self.delete_tag(event, verse, mytag, reftype))
                    tagx += xb_width
                #actual tag display
                tag_display_binder = "display_" + str(tag['id'])
                self.canvas.create_rectangle(x_offset+tagx, y_offset, x_offset+tagx+tag_width, y_offset+textlineheight+textlinegap*2, fill='azure', tags=tag_display_binder)
                self.canvas.create_text(x_offset+tagx, y_offset+textlinegap, text=" " + tag['tag'], anchor=tk.NW, font=self.canvasFont, tags=tag_display_binder)
                #button event to show tag details in this panel...
                self.canvas.tag_bind(tag_display_binder, '<Button-1>', lambda event, item="tagClick", data = {'ref':tagname, 'id':tag['id']} : self.display_attributes(item, data))
                tagx += tag_width

            y_offset += textlineheight + textlinegap*3 + 10

            # CREATE TAG BUTTON ##---- DONE
            # Create a button rectangle.
            buttonText = "Create Tag"
            button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.create_tag_button_rect = self.canvas.create_rectangle(x_offset, y_offset, x_offset + button_width, y_offset + textlineheight + 2*textelbowroom, fill='azure', tags='create_tag_button')
            self.canvas.create_text(x_offset+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags = 'create_tag_button')#button text for open db
            self.canvas.tag_bind('create_tag_button', '<Button-1>', lambda event, verse=self.current_data['ref'], reftype = type_to_get: self.create_tag(event, verse, reftype))

            y_offset += 10 + textlineheight + 2*textelbowroom
    
            # VERSE LIST ##---- DONE
            #the verse list only appears when looking at tags.
            if self.current_item == "tagClick":
                verses = bibledb_Lib.get_db_stuff(open_db_file, "verse", "tag", self.current_data["ref"])

                #in the case of a tag, all associated tags are synonyms.
                for syntag in self.tags_list:
                    more_verses = bibledb_Lib.get_db_stuff(open_db_file, "verse", "tag", syntag['tag'])
                    for another_verse in more_verses:
                        if another_verse not in verses:
                            verses.append(another_verse)

                
                try:
                    # If the user makes a DB using a version of the Bible that has the apocrypha, and then tries to pull notes about Revelation from that DB while he has a protestant Bible loaded...
                    #    then the reference to bibledb_Lib.book_proper_names[] will throw an index out of range error.
                    #    I am making this tool primarily for myself to use, and I don't include the apocrypha in my Bible, so I don't plan to fix this.
                    self.verse_xref_list = [(bibledb_Lib.book_proper_names[x["start_book"]]+" "+str(x["start_chapter"])+":"+str(x["start_verse"]), bibledb_Lib.book_proper_names[x["end_book"]]+" "+str(x["end_chapter"])+":"+str(x["end_verse"])) for x in verses]
                except:
                    self.verse_xref_list = []
                    print("Failed to get the verse references for that tag. This error might occur if your DB was made with a version of the Bible that had different books from the version you're currently using. For example, if the DB was made including the apocrypha, but your current Bible doesn't have it.")
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

        if self.current_data is not None:
        ##### DB LOAD SAVE BUTTONS
            buttonText = "Load DB"
            button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.canvas.create_rectangle(x_offset, y_offset, x_offset+button_width,y_offset + textlineheight + 2*textelbowroom, fill='snow', tags='load_db_button')
            self.canvas.create_text(x_offset+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags='load_db_button')
            self.canvas.tag_bind('load_db_button', '<Button-1>', self.load_db)

            y_offset += 10 + textlineheight + 2*textelbowroom
    
            buttonText = "Save or Make New DB"
            button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.canvas.create_rectangle(x_offset, y_offset, x_offset+button_width,y_offset + textlineheight + 2*textelbowroom, fill='snow', tags='save_db_button')
            self.canvas.create_text(x_offset+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags='save_db_button')
            self.canvas.tag_bind('save_db_button', '<Button-1>', self.saveas_db)

            y_offset += 10 + textlineheight + 2*textelbowroom
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def tag_verse_click(self, event, payload):
        #payload = (startverse, endverse)
        self.options_callback(payload)
        
    def delete_tag(self, event, verse, tag, reftype):
        answer = messagebox.askyesno("Really delete?", "Do you want to remove tag \""+str(tag)+"\"?")
        if answer:
            if reftype == "verse":
                bibledb_Lib.delete_verse_tag(open_db_file, verse, tag)
            elif reftype == "tag":
                #in this case, "verse" is just another tag.
                bibledb_Lib.delete_tag_tag(open_db_file, verse, tag)
            self.display_attributes()
            self.cause_canvas_to_refresh()
        else:
            print("Tag deletion canceled")

    def create_tag(self, event, verse, reftype):
        tag = simpledialog.askstring("Add Tag", "Enter Tag:", initialvalue="")
        #print("Do the tag creation logic here")
        if tag is not None:
            if reftype == "verse":
                bibledb_Lib.add_verse_tag(open_db_file, verse, tag)
            elif reftype == "tag":
                #in this case, "verse" is just another tag.
                bibledb_Lib.add_tag_tag(open_db_file, verse, tag)
            self.display_attributes()
            self.cause_canvas_to_refresh()
        else:
            print("Tag creation cancelled")
    
    def edit_note_text(self, event, reference, reftype):
        #print(type(self.note_area_text),self.note_area_text)
        current_text = self.note_area_text
        if current_text == None:
            current_text = ""
        MultiLineInputDialog.initial_value = current_text
        dialog = MultiLineInputDialog(self.master, "Edit Notes")
        new_text = dialog.result
        #print(new_text)
        if new_text is not None and new_text != "":
            self.note_area_text = new_text
            if reftype == "verse":
                bibledb_Lib.add_verse_note(open_db_file, reference, new_text)
            elif reftype == "tag":
                bibledb_Lib.add_tag_note(open_db_file, reference, new_text)
            self.display_attributes()
            self.cause_canvas_to_refresh()
        elif new_text == "":
            answer = messagebox.askyesno("Really delete?", "Do you want to delete this note?")
            if answer:
                if reftype == "verse":
                    bibledb_Lib.delete_verse_note(open_db_file, reference)
                elif reftype == "tag":
                    bibledb_Lib.delete_tag_note(open_db_file, reference)
                self.display_attributes()
                self.cause_canvas_to_refresh()
    
    ##### DB LOAD SAVE
    def load_db(self, event):
        print("trying to load a db")
        # Implement your logic to open the browse window and load the database
        file_path = filedialog.askopenfilename(defaultextension=".bdb", filetypes=[("Sqlite Bible Files", "*.bdb"), ("All files", "*.*")])
        if file_path:
            if file_path[-4:] == ".bdb":
                # Store the open file in a global variable
                global open_db_file
                open_db_file = file_path
                print(f"Loaded DB: {file_path}")
                self.display_attributes()
                self.cause_canvas_to_refresh()
            else:
                print("I'm not opening that. It's gotta be a SQLITE database file with the extension \".bdb\"")

    def saveas_db(self, event):
        file_path = filedialog.asksaveasfilename(defaultextension=".bdb", filetypes=[("Sqlite Bible Files", "*.bdb"), ("All files", "*.*")])

        if file_path:
            with open(file_path, 'w') as file:
                # Create the file if it doesn't exist
                file.write("")
            bibledb_Lib.makeDB(file_path)
            global open_db_file
            open_db_file = file_path
            self.display_attributes()
            self.cause_canvas_to_refresh()
            print(f"Selected or created file: {file_path}")

if __name__ == "__main__":
    
    root = tk.Tk()
    root.title("Bible Notes!")
    
    #Monkey Add a circle method to canvas
    def _create_circle(self, x, y, r, **kwargs):
        return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
    tk.Canvas.create_circle = _create_circle
    
    
    main_window = MainWindow(root)
    #main_window = MainWindow(root, data_model)

    root.mainloop()
