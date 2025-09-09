import tkinter as tk
from tkinter import ttk
from tkinter import Misc
import bibledb_Lib as bibledb
from tkinter import simpledialog
from tkinter.font import Font
from openpyxl import Workbook
from tkinter import filedialog
import os

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
    try:
        vA = vref1.split(":")[1]
        vB = vref2.split(":")[1]
    except Exception as e:
        print("Error in combineVRefs(): ",e)
        print("vref1 =", vref1)
        print("vref2 =", vref2)
        return vref1
    if bA != bB: #different book
        if bibledb.book_proper_names.index(bA) < bibledb.book_proper_names.index(bB):
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

def bargraph_size(test, testmin, testmax, barmin=0, barmax=100):
    test_adjusted = test - testmin
    testmax_adjusted = testmax - testmin
    result = (test_adjusted * (barmax - barmin) / testmax_adjusted) + barmin
    if result < 3:
        result = 3
    return result

def color_gradient(length, min_length, max_length, type_selection):
    if type_selection == "redblue":
        # Red to Blue pastel gradient
        r = 255-int(bargraph_size(length, min_length, max_length, 0, 255))
        g = int(bargraph_size(length, min_length, max_length, 50, 180))
        b = int(bargraph_size(length, min_length, max_length, 0, 255))
    elif type_selection == "purpleyellow":
        # Purple to Yellow pastel gradient
        r = int(bargraph_size(length, min_length, max_length, 200, 255))
        g = 255-int(bargraph_size(length, min_length, max_length, 0, 255))
        b = int(bargraph_size(length, min_length, max_length, 0, 255))
    else:
        return 'azure'
    # Return color in hexadecimal format
    return f'#{r:02x}{g:02x}{b:02x}'


class TagInputDialog(simpledialog.Dialog):
    #inherits simpledialog to make a tag input dialog with a dropdown suggestion list
    def __init__(self, parent, dbdata, topselection = False, get_tags_like=bibledb.get_tags_like, thistitle="Add Tag", bookinputdialog=False):
        #if topselection is false, entering a new tagname will return the new tagname
        #if topselection is true, entering a new tagname will return the top item in the list box
        #get_tags_like is a callback to whatever function you intend to use to find similar tags. (maybe unnecessary for this to be an argument)
        self.topselection = topselection
        self.get_tags_like = get_tags_like
        self.selected_tag = None
        self.dbdata = dbdata
        self.bookinputdialog = bookinputdialog
        super().__init__(parent, title=thistitle)

    def body(self, master):
        # Entry for typing tag
        self.entry = tk.Entry(master)
        self.entry.grid(row=0, column=0, padx=10, pady=10)
        # Listbox to display tag suggestions
        self.listbox = tk.Listbox(master, height=5)
        self.listbox.grid(row=1, column=0, padx=10, pady=10)
        self.listbox.grid_remove()  # Initially hide the listbox
        # Bind entry events for filtering suggestions
        self.entry.bind("<KeyRelease>", self.update_suggestions)
        self.entry.bind("<Down>", self.focus_listbox)  # Bind down arrow key
        self.listbox.bind("<Double-1>", self.on_select)
        self.listbox.bind('<Button-1>', self.quick_select)
        self.listbox.bind("<Return>", self.on_select)  # Bind enter key in listbox
        return self.entry  # Focus on entry widget

    def update_suggestions(self, event):
        # Get the current input from the entry widget
        partial_tag = self.entry.get()

        # Clear the listbox
        self.listbox.delete(0, tk.END)
        if partial_tag.strip():
            # Get suggestions from the database
            matching_tags = self.get_tags_like(self.dbdata, partial_tag)
            if matching_tags:
                # Insert suggestions into the listbox
                for tag in matching_tags:
                    self.listbox.insert(tk.END, tag)

                # Show the listbox if there are matching tags
                self.listbox.grid()
            else:
                # Hide the listbox if no matches are found
                self.listbox.grid_remove()
        else:
            # Hide the listbox if the input is empty
            self.listbox.grid_remove()

    def focus_listbox(self, event):
        # If there are items in the listbox, select the first one and focus the listbox
        if self.listbox.size() > 0:
            self.listbox.selection_set(0)  # Select the first item
            self.listbox.activate(0)       # Make the first item active
            self.listbox.focus_set()       # Move focus to the listbox

    def quick_select(self, event):
        #print("quick select")
        index = self.listbox.nearest(event.y)
        if index >= 0:
            if self.bookinputdialog:
                selected_text = self.listbox.get(index)
            else:
                selected_text = self.listbox.get(index)[0]
            self.entry.delete(0,tk.END)
            self.entry.insert(0,selected_text)
    
    def on_select(self, event):
        #print("on select")
        # Get the selected tag from the listbox
        selected = self.listbox.curselection()
        if self.bookinputdialog and selected:
            self.selected_tag = self.listbox.get(selected[0])
            self.ok()
        elif selected:
            self.selected_tag = self.listbox.get(selected[0])[0]
            self.ok()  # Close the dialog

    def apply(self):
        #print("apply")
        selected = None
        # Get the final tag value (from entry or listbox)
        if self.topselection and self.listbox.size() > 0:
            # Check if there are no highlighted items
            has_selected_items = any(self.listbox.selection_includes(i) for i in range(self.listbox.size()))
            
            # Check if there are no items identical to the string from self.entry.get()
            search_string = self.entry.get()
            #print(search_string, [self.listbox.get(i) for i in range(self.listbox.size())])
            #if self.bookinputdialog:
            #    matching_index = next((i for i in range(self.listbox.size()) if self.listbox.get(i) == search_string), None)
            #else:
            matching_index = next((i for i in range(self.listbox.size()) if self.listbox.get(i)[0] == search_string), None)
    
            # If no highlighted items and no matching items, select the first item
            if not has_selected_items:
                if matching_index is not None:
                    #print("found!")
                    # If an identical item is found, select it
                    self.listbox.selection_set(matching_index)
                    self.listbox.activate(matching_index)  # Make the matching item active
                else:
                    # If no matches, select the first item
                    self.listbox.selection_set(0)  # Select the first item
                    self.listbox.activate(0)       # Make the first item active
                self.listbox.focus_set()       # Move focus to the listbox
                selected = self.listbox.curselection()
        if selected and self.bookinputdialog:
            self.selected_tag = self.listbox.get(selected[0])
        elif selected:
            self.selected_tag = self.listbox.get(selected[0])[0]
        elif not self.selected_tag:
            self.selected_tag = self.entry.get()   

######################Secondary Window is the window and the bargraph column. The filter view is instantiated here.

class SecondaryWindow:
    def __init__(self, master, callback, dbdata = None):
        self.master = master
        self.callback = callback #used for clicking a tag and setting it as the current tag in the main window
        self.dbdata = dbdata #info about the currend db that's open
        
        #Handy variables here...
        self.canvasFont = Font(size = 10)
        self.italicFont = Font(size = 10, slant = 'italic')
        self.boldFont = Font(size = 10, weight = 'bold')
        self.sortmode_text = "Sorting Alphabetically"
        self.sortmode = "alphabet" #toggles between "alphabet" and "usage"
        self.colormode_text = "Toggle Colors"
        self.colormode = "plain" #toggles: "plain", "redblue", "purpleyellow"
        self.export_tags_this_time = False
        self.export_tags_path = "./"
        self.all_tags_list = [] # this variable contains the tags sorted by usage. It is used by right_hand_frame to export tag/note/verses 

        # Set up the secondary window
        self.top_window = tk.Toplevel(master)
        self.top_window.title("DB Info")
        self.top_window.geometry("800x500")
        self.reload_id = None
        self.reload_id2 = None

        #I am accustomed to dealing with paned windows
        self.this_window = ttk.PanedWindow(self.top_window, orient="horizontal")
        self.this_window.pack(fill="both", expand=True)

        #Left-hand pane
        self.myFrame = ttk.Frame(self.this_window)
        self.myFrame.grid(row=0, column=0, sticky="nsew")
        self.myFrame.grid_rowconfigure(0, weight=1)
        self.myFrame.grid_columnconfigure(0, weight=1)
        
        #add the canvas to the frame
        self.canvas = tk.Canvas(self.myFrame)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        #create vertical and horizontal scrollbars
        v_scrollbar = tk.Scrollbar(self.myFrame, orient="vertical", command=self.canvas.yview)
        h_scrollbar = tk.Scrollbar(self.myFrame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Configure scrollbar position on the grid
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        #add the frame to the window
        self.this_window.add(self.myFrame)

        #add another frame to the right-hand side of the window. We're using two columns now, baby!
        self.rightFrame = RightHandFrame(self.master, self.this_window, self.callback, self.dbdata, self)
        self.rightFrame.grid(row=0, column=1, sticky="nsew")
        self.this_window.add(self.rightFrame)

        #configure the scroll region to make the canvas scrollable
        canvas_width = self.canvas.winfo_reqwidth()
        canvas_height = self.canvas.winfo_reqheight()
        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

        #whenever the window resizes, I want the canvas scroll area to refresh
        self.canvas.bind("<Configure>", self.on_resize)

        #finish rendering the window before showing attributes, so that the dimensions will be accurate
        self.top_window.update_idletasks()
        
        #sash drag for resizing the panels
        self.this_window.bind("<B1-Motion>", self.on_sash_drag)
        self.this_window.bind("<Configure>", self.window_resize)

        #go ahead and display contents
        self.display_attributes()

        self.active_panel = None
        self.top_window.bind("<MouseWheel>", self.scroll_active_panel)
        self.canvas.bind("<Enter>", self.set_active_panel)
        self.canvas.bind("<Leave>", self.clear_active_panel)
        self.rightFrame.canvas.bind("<Enter>", self.set_active_panel)
        self.rightFrame.canvas.bind("<Leave>", self.clear_active_panel)

    def set_active_panel(self, event):
        # Set the active panel to the widget under the mouse
        self.active_panel = event.widget
        #print("active_panel",self.active_panel)

    def clear_active_panel(self, event):
        # Clear the active panel when the mouse leaves
        self.active_panel = None

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

    def on_resize(self, event):
        #this is for instances where the bargraph canvas is resized.

        #reloading is resource intensive for this window, so we don't want to do for every new window size.
        # Cancel any existing timer
        if self.reload_id is not None:
            self.canvas.after_cancel(self.reload_id)

        # Set a new timer to reload attributes after 300 ms of inactivity
        self.reload_id = self.canvas.after(300, self.display_attributes)

    def window_resize(self, event):
        # Resizing the window doesn't move the sash, but only results in resizing the right-hand frame.
        self.rightFrame.display_attributes(canvas_width = self.this_window.winfo_width() - self.this_window.sashpos(0))
    
    def on_sash_drag(self,event):
        # If the moved sash is near the treeview sash (left), update the tree view
        if self.this_window.sashpos(0) - 10 < event.x < self.this_window.sashpos(0) + 10:
            new_sash_position = event.x
            self.myFrame.columnconfigure(0, weight=1)
            self.myFrame.configure(width=new_sash_position)
            #update the canvas
            self.rightFrame.display_attributes(canvas_width = self.this_window.winfo_width() - new_sash_position)
            self.on_resize(event)
            #self.rightFrame.display_attributes(canvas_width = self.this_window.winfo_width() - new_sash_position)
    
    def on_tag_click(self, event, item_id):
        self.callback(item_id)
        #here is where we will callback to the main window to show tag data

    #I know string compares are heavy, but this is a light application overall at the moment.
    def on_sortmode_click(self, event):
        #this is for a button to toggle between...
        # a) sorting tags in alphabetical order (every tag gets a line, synonyms are shown multiple times)
        # b) sorting tags according to usage (synonym groups get just one line)
        if self.sortmode == "alphabet": #toggles between "alphabet" and "usage"
            self.sortmode = "usage"
            self.sortmode_text = "Sorting by usage"
        else:
            self.sortmode = "alphabet"
            self.sortmode_text = "Sorting Alphabetically"
        self.display_attributes()

    def on_colormode_click(self, event):
        #this is for a button to toggle between...
        # a) showing tags on a color gradient for usage (maybe a few options)
        # b) showing all tags in the same color
        if self.colormode == "plain":#toggles: "plain", "redblue", "purpleyellow"
            self.colormode = "redblue"
        elif self.colormode == "redblue":
            self.colormode = "purpleyellow"
        else:
            self.colormode = "plain"
        self.display_attributes()

    def on_exporttags_click(self, event):
        self.export_tags_this_time = True
        self.export_tags_path = filedialog.asksaveasfilename(defaultextension=".xls", filetypes=[("Excel", "*.xls"), ("All files", "*.*")])
        if self.export_tags_path:
            self.export_tags_this_time = True
        self.display_attributes()

    def display_attributes(self, dbstuff = None):
        #shows all the tags
        x_offset = 5
        y_offset = 3
        textelbowroom = 10
        textlinegap = 2
        textlineheight = Font.metrics(self.canvasFont)["linespace"]
        boldlineheight = Font.metrics(self.boldFont)["linespace"]
        italiclineheight = Font.metrics(self.italicFont)["linespace"]
        right_x_offset = 30
        panelWidth = self.this_window.sashpos(0) - right_x_offset

        #Clear the canvas
        self.canvas.delete("all")
        
        if dbstuff != None:
            self.dbdata = dbstuff
        else:
            dbstuff = self.dbdata

        if self.dbdata is None:
            self.canvas.create_text(10, 30, text="Select a verse to load a DB.", fill="green", font = self.canvasFont)
        else:
            #get all the tags
            checklist = [b['tag'] for b in bibledb.get_tag_list(self.dbdata)] #all the tags
            
            syngroups = []   #each indice is a list of synonymous tags
            synonymlist = [] #a group of synonymous tags to be added to syngroups
            checkedlist = [] #tags we've already dealt with. So we don't deal with them again.
            synonyms = []    #a working list of tags we're in the middle of finding synonyms for
            
            for tag in checklist:
                if tag not in checkedlist:
                    checkedlist.append(tag)
                    synonymlist.append(tag)
                    synonyms = [b['tag'] for b in bibledb.get_db_stuff(self.dbdata,"tag","tag",tag)]
                    while len(synonyms) > 0:
                        synonym = synonyms.pop()
                        if synonym not in checkedlist:
                            checkedlist.append(synonym)
                            synonymlist.append(synonym)
                            synonyms += [b['tag'] for b in bibledb.get_db_stuff(self.dbdata,"tag","tag",synonym)]
                    
                  #  #OLD Recursive way of getting syngroups
                  #  def recursivesynonyms(syno, thisgroup):
                  #      synonyms = [b['tag'] for b in bibledb.get_db_stuff(self.dbdata,"tag","tag",syno)]
                  #      for tag in synonyms:
                  #          if tag not in thisgroup:
                  #              thisgroup.append(tag)
                  #              thisgroup = recursivesynonyms(tag, thisgroup)
                  #      return thisgroup
                  #  
                  #  synonymlist = recursivesynonyms(tag, [tag])
                  #  
                  #  for s in synonymlist:
                  #      if s != tag:
                  #          checkedlist.append(s)
                  #      
                    syngroups.append({"tags":synonymlist})
                    synonymlist = []
                

            syngroups_lo = 9223372036854775807
            syngroups_hi = 0
            #count the unique verses for the synonym group
            #these low and high values are used to scale bargraph lengths and colors
            verses = []
            for i in range(len(syngroups)):
                for tag in syngroups[i]["tags"]:
                    checkverses = bibledb.get_db_stuff(self.dbdata, "verse", "tag", tag)
                    for verse in checkverses:
                        if verse not in verses:
                            verses.append(verse)
                syngroups[i]["verses"] = len(verses)
                if syngroups[i]["verses"] < syngroups_lo:
                    syngroups_lo = syngroups[i]["verses"]
                if syngroups[i]["verses"] > syngroups_hi:
                    syngroups_hi = syngroups[i]["verses"]
                verses = []
                                

            tags_lo = 9223372036854775807
            tags_hi = 0
            tags = [{"tag":b} for b in checklist]
            #count the verses for each tag
            for i in range(len(tags)):
                tags[i]["verses"] = len(bibledb.get_db_stuff(self.dbdata, "verse", "tag", tags[i]["tag"]))
                if tags[i]["verses"] < tags_lo:
                    tags_lo = tags[i]["verses"]
                if tags[i]["verses"] > tags_hi:
                    tags_hi = tags[i]["verses"]
            
            #show some statistics at the top
            #  qty of tags
            showtext = "total tag count: " +str(len(tags))
            self.canvas.create_text(x_offset+textelbowroom, y_offset+textelbowroom, text=showtext, anchor=tk.NW, font=self.canvasFont)
            y_offset += textlineheight + textlinegap
            #  qty of synonym groups
            showtext = "tag count after grouping synonyms: " +str(len(syngroups))
            self.canvas.create_text(x_offset+textelbowroom, y_offset+textelbowroom, text=showtext, anchor=tk.NW, font=self.canvasFont)
            y_offset += textelbowroom + textlineheight + textlinegap
            
            #show sorting buttons
            buttonText = self.sortmode_text #"Toggle Sorting"
            sort_button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.canvas.create_rectangle(x_offset, y_offset, x_offset+sort_button_width,y_offset + textlineheight + 2*textelbowroom, fill='snow', tags='on_sortmode_click')
            self.canvas.create_text(x_offset+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags='on_sortmode_click')
            self.canvas.tag_bind('on_sortmode_click', '<Button-1>', self.on_sortmode_click)

            

            buttonText = self.colormode_text #"Toggle Coloring"
            color_button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            color_x_offset = x_offset
            if x_offset + sort_button_width + textelbowroom*2 + color_button_width < panelWidth:
                color_x_offset += sort_button_width + textelbowroom*2
            else:
                y_offset += 10 + textlineheight + 2*textelbowroom
            self.canvas.create_rectangle(color_x_offset, y_offset, color_x_offset+color_button_width,y_offset + textlineheight + 2*textelbowroom, fill='snow', tags='on_colormode_click')
            self.canvas.create_text(color_x_offset+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags='on_colormode_click')
            self.canvas.tag_bind('on_colormode_click', '<Button-1>', self.on_colormode_click)

            buttonText = "Export List"
            export_button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            export_x_offset = color_x_offset
            if export_x_offset + textelbowroom*2 + color_button_width + export_button_width < panelWidth:
                export_x_offset += color_button_width + textelbowroom*2
            else:
                export_x_offset = x_offset
                y_offset += 10 + textlineheight + 2*textelbowroom
            self.canvas.create_rectangle(export_x_offset, y_offset, export_x_offset+export_button_width,y_offset + textlineheight + 2*textelbowroom, fill='snow', tags='on_exporttags_click')
            self.canvas.create_text(export_x_offset+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags='on_exporttags_click')
            self.canvas.tag_bind('on_exporttags_click', '<Button-1>', self.on_exporttags_click)

            y_offset += 10 + textlineheight + 2*textelbowroom
            
            #now we have...
            # tags -- ["tagname","tagname1","tagname2",...]
            # tagverses -- [versecount, versecount1, versecount2,...]
            # syngroups -- [{"tags":["tagname","tagname1","tagname2",...],"verses":integer_verse_count},...]
            
            # tags_hi -- the qty of references to the most used tag
            # tags_lo -- the qty of references to the least used tag
            # syngroups_hi -- the qty of references to the most used syngroup
            # syngroups_lo -- the qty of references to the least used syngroup
            #... the ranges for tags might be inaccurate in view of syngroups where another synonym has the references

            #self.sortmode_text = "sorting"#the button text
            #self.sortmode = "alphabet" #toggles between "alphabet" and "usage"
            #self.colormode_text = "color" #the button text
            #self.colormode = "plain" #toggles: "plain", "redblue", "purpleyellow"

            #prepare the workbook
            workbook = None
            sheet = None
            if self.export_tags_this_time:
                workbook = Workbook()
                sheet = workbook.active
                wbheader = ["Verse Count", "Tags..."]
                sheet.append(wbheader)
                
            if self.sortmode == "alphabet":
                sorted_tags = sorted(tags, key=lambda x: x["tag"])
                sorted_syngroups = [(syngroups.index(lst), lst["tags"].index(dct["tag"])) for dct in sorted_tags for lst in syngroups if dct["tag"] in lst["tags"]]
            elif self.sortmode == "usage":
                #We are only using syngroups for display, so no need to sort tags here.
                #sorted_tags = sorted(tags, key=lambda x: x["verses"], reverse = True) #reverse to put the most-used tags on top
                sorted_syngroups = sorted(syngroups, key=lambda x: x["verses"], reverse = True)
            tagnum = 0
            self.all_tags_list = [s["tags"] for s in sorted(syngroups, key=lambda x: x["verses"], reverse = True)]# this variable is used by right_hand_frame to export tag/note/verses 
            for s in sorted_syngroups:
                #print(s)
                if self.sortmode == "alphabet":
                    #in this case, s is a list of tuples, representing the index of the tag in syngroups.
                    tags = [syngroups[s[0]]["tags"][s[1]]]
                    verses = syngroups[s[0]]["verses"]
                elif self.sortmode == "usage":
                    #in this case, s is a dict, like {'tags': ['beard', 'hair', 'beards'], 'verses': 4}
                    tags = s["tags"]
                    verses = s["verses"]
                if self.export_tags_this_time:
                    sheet.append([verses]+tags)

                barcolor = color_gradient(verses, syngroups_lo, syngroups_hi, self.colormode)
                barlength = bargraph_size(verses, syngroups_lo, syngroups_hi, x_offset, panelWidth)
                
                
                #use the width of the window to determine how many times this tag list will wrap
                #   use that width to determine the needed height for this bar-graph rectangle

                linesize = textelbowroom
                barheight = textlineheight + textlinegap*2
                rendertags = [] #this will store, in rows, all the tags to be displayed on this bar
                tagline = []
                #first calculate the total height of this block of tags, for the bar graph bar height
                for tag in tags:
                    tagwidth = self.canvasFont.measure(tag)
                    if tagwidth + linesize + textelbowroom < panelWidth:
                        tagline.append(tag)
                        linesize += tagwidth + textelbowroom
                    else:
                        rendertags.append(tagline)
                        tagline = [tag]
                        barheight += textlineheight + textlinegap
                        linesize = tagwidth+textelbowroom
                if tagline != []:
                    rendertags.append(tagline)

                #render the bar, and then iterate through the tags and display them
                tag_binder = "GOTO_tag_"+str(tagnum) #the bar binds to the first tag in the group
                self.canvas.create_rectangle(x_offset, y_offset, x_offset+barlength, y_offset+barheight, fill=barcolor, tags=tag_binder)
                y_offset += textlinegap
                for tagline in rendertags:
                    tagx = textelbowroom
                    for i, tag in enumerate(tagline):
                        tag_binder = "GOTO_tag_"+str(tagnum)
                        self.canvas.create_text(x_offset+tagx, y_offset, text=tag, anchor=tk.NW, font=self.canvasFont, tags=tag_binder)
                        self.canvas.tag_bind(tag_binder, '<Button-1>', lambda event, item_id = tag : self.on_tag_click(event,item_id))
                        tagnum += 1
                        tagwidth = self.canvasFont.measure(tag)
                        tagx += tagwidth + textelbowroom
                        if i < len(tagline)-1:
                            self.canvas.create_line(tagx, y_offset-(textlinegap/2), tagx, y_offset+textlineheight+(textlinegap/2)+2, fill='black', width=2)
                            #the +2 in the second y coord above was just an asthetic tweak, and can be removed if you don't like it.
                            tagx += 2
                    y_offset += textlineheight + textlinegap
                y_offset += 10
        if self.export_tags_this_time:
            self.export_tags_this_time = False
            workbook.save(self.export_tags_path)
            print("Exported tags to: " + str(self.export_tags_path))
            self.export_tags_path = None
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

###########################################Right Hand Frame is the verse sorting area. Probably not a useful name for it, now that I think about it.

class RightHandFrame(ttk.Frame):
    def __init__(self, master, parent, callback = None, dbdata = None, left_frame = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvasFont = Font(size = 10)
        self.italicFont = Font(size = 10, slant = 'italic')
        self.boldFont = Font(size = 10, weight = 'bold')
        self.left_frame = left_frame
        
        self.callback = callback
        self.dbdata = dbdata
        
        # Configure grid inside this frame
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create a canvas inside the right-hand frame
        self.canvas = tk.Canvas(self)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.canvas.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Create vertical and horizontal scrollbars
        self.v_scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.h_scrollbar = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)

        # Configure canvas to use scrollbars
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Add scrollbars to the canvas frame
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Handy variables
        self.tags_list = []
        self.union = True #Show all of the verses for the selected tags
        self.intersection = False #Show only the verses shared by all selected tags
        self.symmetric_difference = False #Show only the verses that are unique to only one of the selected tags
        self.verse_xref_list = []
        self.selected_books = []
        self.comments_only = False #only show verses with comments
        self.shown_verses = [] #in case you want to do something with the verses that are currently visible
        

        # Configure the scroll region to make the canvas scrollable
        self.canvas_width = self.canvas.winfo_reqwidth()
        self.canvas_height = self.canvas.winfo_reqheight()
        self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        
        # the rest of the stuff
        self.display_attributes()
        
        #self.canvas.create_text(10, 10, anchor="nw", text="Right-hand canvas content")

    def get_books_like(self, dbdata, partial_book):
        result = [book for book in bibledb.book_proper_names if partial_book.lower().strip() in book.lower().strip()]
        return result
    
    def select_book(self, event):
        selected_book = TagInputDialog(self.master, self.dbdata, topselection = True, get_tags_like = self.get_books_like, thistitle = "Select Books", bookinputdialog = True).selected_tag
        if (selected_book is not None) and (selected_book != "") and (selected_book in bibledb.book_proper_names) and (selected_book not in self.selected_books):
            self.selected_books.append(selected_book)
            self.display_attributes()

    def delete_book(self, event, bookname):
        if bookname in self.selected_books:
            self.selected_books.remove(bookname)
            self.display_attributes()
        else:
            print("Tried removing a book that wasn't listed from the filter pane. Oh no!")

    def select_tag(self, event):
        #replace tagSelect() with the actual code for tag selection, to get the popup.
        selected_tag = TagInputDialog(self.master, self.dbdata, topselection = True).selected_tag
        if (selected_tag is not None) and (selected_tag != "") and bibledb.tag_exists(self.dbdata, selected_tag):
            selected_tag_synonyms = [b['tag'] for b in bibledb.get_db_stuff(self.dbdata,"tag","tag",selected_tag)]
            
            if selected_tag and (selected_tag not in self.tags_list) and all(item not in self.tags_list for item in selected_tag_synonyms):
                self.tags_list.append(selected_tag)
                self.display_attributes()
            
    def delete_tag(self, event, tagname):
        if tagname in self.tags_list:
            self.tags_list.remove(tagname)
            self.display_attributes()
        else:
            print("Tried removing a tag that wasn't listed from the filter pane. Oh no!")

    def on_tag_click(self, event, item_id):
        #this callback goes to the main window to show tag data
        self.callback(item_id)

    def on_verse_click(self, event, item_id):
        #this callback goes to the main window to show tag data
        self.callback(item_id, "verse")

    def toggle_union(self, event):
        if self.union:
            self.union = False
            self.intersection = True
        elif self.intersection:
            self.intersection = False
            self.symmetric_difference = True
        elif self.symmetric_difference:
            self.symmetric_difference = False
            self.union = True
        self.display_attributes()

    def toggle_comments_only(self, wasted_memory):
        self.comments_only = not self.comments_only
        self.display_attributes()

    def copy_verse_lists(self, event):
        #puts the currently visible verse list in the clipboard
        result = ""
        for verse in self.shown_verses:
            result += verse
        root = tk._default_root
        if root:
            root.clipboard_clear()
            root.clipboard_append(result)
            root.update()
        else:
            print("ERROR in bibledb_Manager.copy_verse_list(). No access to root.")

    def export_tags_and_synonyms(self, event):

        def get_verses_for_taglist(tags):
            result = []
            for synonym_group in tags:
                verses = []
                notes = []
                for tag in synonym_group:
                    this_note = bibledb.get_db_stuff(self.dbdata, "note", "tag", tag)
                    if this_note:
                        this_note = this_note[0]['note']
                        notes.append(this_note)
                    checkverses = bibledb.get_db_stuff(self.dbdata, "verse", "tag", tag)
                    for verse in checkverses:
                        if verse not in verses:
                            #print(verse)
                            verses.append(verse)
                #I don't know if these functions will work, but they're basically what's being done down below in display_verses
                verses.sort(key=lambda r: (r['start_book'], r['start_chapter'], r['start_verse']))#sort by start book first, then chapter, then verse, so all the verses appear in order
                verses = [bibledb.normalize_vref(q) for q in verses]
                result.append({"tags":synonym_group,"notes":notes, "verses":verses})
            return result
        
        #self.dbdata
        tagslist = self.left_frame.all_tags_list
        exportdata = get_verses_for_taglist(tagslist)
        contents = ""
        for item in exportdata:
            contents += '\n  //////TAGS://////\n'
            for tag in item['tags']:
                contents += tag + ", "
            contents += '\n  //////NOTES://////\n'
            for note in item['notes']:
                contents += note + '\n\n'
            contents += '\n  //////VERSES://////\n'
            for verse in item['verses']:
                contents += verse + ', '
            contents += "\n\n+=+=+=+=+=+=+=+=+=+=+=+=+=+=+\n\n"
                
        output_file = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt"), ("All files", "*.*")])
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(contents)
                    
    def export_verse_notes(self, event): ##################################################
        #self.dbdata
        verses = bibledb.get_all_verses_with_notes(self.dbdata)
        contents = ""
        for verse in verses:
            contents += verse['verse'] + '\n'
            contents += verse['note']
            contents += "\n\n+=+=+=+=+=+=+=+=+=+=+=+=+=+=+\n\n"
        output_file = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt"), ("All files", "*.*")])
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(contents)
        
    def export_tag_networks(self, event):
        folder = "tag networks"
        os.makedirs(folder, exist_ok=True)
        tagslist = self.left_frame.all_tags_list
        def get_verses_for_taglist(tags):
            result = []
            for synonym_group in tags:
                verses = []
                for tag in synonym_group:
                    checkverses = bibledb.get_db_stuff(self.dbdata, "verse", "tag", tag)
                    for verse in checkverses:
                        if verse not in verses:
                            verses.append(verse)
                verses.sort(key=lambda r: (r['start_book'], r['start_chapter'], r['start_verse']))
                verse_refs = [bibledb.normalize_vref(q) for q in verses]
                result.append({"tags":synonym_group, "verses":verse_refs})
            return result
        exportdata = get_verses_for_taglist(tagslist)
        for item in exportdata:
            primary_tag = item['tags'][0].replace("/", "_").replace("\\", "_")
            filename = os.path.join(folder, primary_tag + ".txt")
            cooccurring_tags = set()
            for vref in item['verses']:
                tags_on_verse = [t['tag'] for t in bibledb.get_db_stuff(self.dbdata, "tag", "verse", vref)]
                cooccurring_tags.update(tags_on_verse)
            contents = ", ".join(sorted(cooccurring_tags)) + "\n"
            contents += "----------\n"
            for vref in item['verses']:
                tags_on_verse = [t['tag'] for t in bibledb.get_db_stuff(self.dbdata, "tag", "verse", vref)]
                contents += vref + "\n"
                contents += ", ".join(tags_on_verse) + "\n\n"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(contents)
        tk.messagebox.showinfo("Information", "Exported files to folder, 'tag networks'!")

    def export_subtopic_breakdowns(self, event):
        folder = "subtopic breakdowns"
        os.makedirs(folder, exist_ok=True)
        tagslist = self.left_frame.all_tags_list
        for synonym_group in tagslist:
            verses = []
            for tag in synonym_group:
                checkverses = bibledb.get_db_stuff(self.dbdata, "verse", "tag", tag)
                for verse in checkverses:
                    if verse not in verses:
                        verses.append(verse)
            verses.sort(key=lambda r: (r['start_book'], r['start_chapter'], r['start_verse']))
            verse_refs = [bibledb.normalize_vref(q) for q in verses]
            verse_objs = verses
            verse_dict = dict(zip(verse_refs, verse_objs))
            verse_tags = {}
            for vref in verse_refs:
                tags = [t['tag'] for t in bibledb.get_db_stuff(self.dbdata, "tag", "verse", vref)]
                verse_tags[vref] = set(tags)
            co_tags = set()
            for tags in verse_tags.values():
                co_tags.update(tags)
            checklist = list(co_tags)
            sub_syngroups = []
            synonymlist = []
            checkedlist = []
            synonyms = []
            for tag in checklist:
                if tag not in checkedlist:
                    checkedlist.append(tag)
                    synonymlist.append(tag)
                    synonyms = [b['tag'] for b in bibledb.get_db_stuff(self.dbdata,"tag","tag",tag)]
                    while len(synonyms) > 0:
                        synonym = synonyms.pop()
                        if synonym not in checkedlist:
                            checkedlist.append(synonym)
                            synonymlist.append(synonym)
                            synonyms += [b['tag'] for b in bibledb.get_db_stuff(self.dbdata,"tag","tag",synonym)]
                    sub_syngroups.append(synonymlist)
                    synonymlist = []
            t_set = set(synonym_group)
            sub_syngroups = [sg for sg in sub_syngroups if set(sg) != t_set]
            sub_data = []
            for sub_sg in sub_syngroups:
                s_set = set(sub_sg)
                sub_verses = [v for v, vtags in verse_tags.items() if s_set & vtags]
                sub_data.append((len(sub_verses), sub_sg, sub_verses))
            sub_data.sort(key=lambda x: x[0], reverse=True)
            for _, _, sv in sub_data:
                sv.sort(key=lambda vr: (verse_dict[vr]['start_book'], verse_dict[vr]['start_chapter'], verse_dict[vr]['start_verse'], verse_dict[vr]['end_book'], verse_dict[vr]['end_chapter'], verse_dict[vr]['end_verse']))
            primary_tag = synonym_group[0].replace("/", "_").replace("\\", "_")
            filename = os.path.join(folder, primary_tag + ".txt")
            contents = ""
            for count, sg, sverses in sub_data:
                if count > 0:
                    contents += f"///// SUBTOPIC ({count} verses): " + ", ".join(sg) + "\n"
                    contents += ", ".join(sverses) + "\n\n"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(contents)
        tk.messagebox.showinfo("Information", "Exported files to folder, 'subtopic breakdowns'!")


    def export_single_topics(self, event):
        def get_verses_for_taglist(tags):
            result = []
            for synonym_group in tags:
                verses = []
                notes = []
                for tag in synonym_group:
                    this_note = bibledb.get_db_stuff(self.dbdata, "note", "tag", tag)
                    if this_note:
                        this_note = this_note[0]['note']
                        notes.append(this_note)
                    checkverses = bibledb.get_db_stuff(self.dbdata, "verse", "tag", tag)
                    for verse in checkverses:
                        if verse not in verses:
                            verses.append(verse)
                verses.sort(key=lambda r: (r['start_book'], r['start_chapter'], r['start_verse']))
                verses = [bibledb.normalize_vref(q) for q in verses]
                result.append({"tags":synonym_group,"notes":notes, "verses":verses})
            return result
        
        folder = "single topic exports"
        os.makedirs(folder, exist_ok=True)
        tagslist = self.left_frame.all_tags_list
        exportdata = get_verses_for_taglist(tagslist)
        for item in exportdata:
            primary_tag = item['tags'][0].replace("/", "_").replace("\\", "_")
            filename = os.path.join(folder, primary_tag + ".txt")
            contents = ""
            contents += '\n  //////TAGS://////\n'
            contents += ', '.join(item['tags']) + '\n'
            contents += '  //////NOTES://////\n'
            contents += '\n\n'.join(item['notes']) + '\n\n'
            contents += '  //////VERSES://////\n'
            contents += ', '.join(item['verses']) + '\n\n'
            contents += "+=+=+=+=+=+=+=+=+=+=+=+=+=+=+\n\n"
            contents += '  //////VERSE NOTES://////\n'
            for verse in item['verses']:
                vnotes = bibledb.get_db_stuff(self.dbdata, "note", "verse", verse)
                if vnotes:
                    contents += verse + '\n'
                    contents += vnotes[0]['note'] + '\n\n'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(contents)
        tk.messagebox.showinfo("Information", "Exported files to folder, 'single topic exports'!")


    def display_attributes(self, dbstuff = None, canvas_width = None):
        if canvas_width == None:
            canvas_width = self.canvas_width
        else:
            self.canvas_width = canvas_width
        y_offset = 40
        x_offset = 5
        textelbowroom = 10
        textlinegap = 2
        textlineheight = Font.metrics(self.canvasFont)["linespace"]
        boldlineheight = Font.metrics(self.boldFont)["linespace"]
        italiclineheight = Font.metrics(self.italicFont)["linespace"]
        right_x_offset = 30
        panelWidth = canvas_width - right_x_offset

        #Clear the canvas
        self.canvas.delete("all")

        #show a header?
        

        if dbstuff != None:
            self.dbdata = dbstuff
        else:
            dbstuff = self.dbdata

        #if there's no db file, then don't show anything.
        if self.dbdata is None:
            self.canvas.create_text(x_offset, y_offset, text="Go select a verse and load a db first.", fill="green", font = self.canvasFont)
        else:
            #some statistical data...
            showtext = "total verse count: " +str(len(self.verse_xref_list))
            versecount_text = self.canvas.create_text(x_offset+textelbowroom, y_offset+textelbowroom, text=showtext, anchor=tk.NW, font=self.canvasFont)
            y_offset += textlineheight + textlinegap*2 + textelbowroom*2
            
            # HEADER ##---- DONE
            if self.union:
                title_text = "=== UNION: Showing all verses for selected tags ==="
            elif self.intersection:
                title_text = "=== INTERSECTION: Showing verses shared by all selected tags ==="
            elif self.symmetric_difference:
                title_text = "=== SYMMETRIC DIFFERENCE: Showing verses unique to only one of the selected tags ==="
            self.canvas.create_text(x_offset, y_offset, text=title_text, anchor=tk.W, font=self.boldFont)
            y_offset += boldlineheight + textlinegap + 10

            # CREATE TAG BUTTON ##---- DONE
            buttonX = x_offset
            # Create all the option buttons

        #Export Buttons
            buttonText = "Export all Tag/Note/Verses"
            button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.export_tagversenote_button = self.canvas.create_rectangle(buttonX, y_offset, buttonX + button_width, y_offset + textlineheight + 2*textelbowroom, fill='snow', tags='export_tags_button')
            self.canvas.create_text(buttonX+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags = 'export_tags_button')#button text for open db
            self.canvas.tag_bind('export_tags_button', '<Button-1>', lambda event: self.export_tags_and_synonyms(event))
            buttonX += x_offset + button_width

            buttonText = "Export all Verse Notes"
            button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.export_versenote_button = self.canvas.create_rectangle(buttonX, y_offset, buttonX + button_width, y_offset + textlineheight + 2*textelbowroom, fill='snow', tags='export_verses_button')
            self.canvas.create_text(buttonX+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags = 'export_verses_button')#button text for open db
            self.canvas.tag_bind('export_verses_button', '<Button-1>', lambda event: self.export_verse_notes(event))
            buttonX += x_offset + button_width

            #new row
            y_offset += 10 + textlineheight + 2*textelbowroom
            buttonX = x_offset

            buttonText = "Export Single Topics"
            button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.export_single_button = self.canvas.create_rectangle(buttonX, y_offset, buttonX + button_width, y_offset + textlineheight + 2*textelbowroom, fill='snow', tags='export_single_button')
            self.canvas.create_text(buttonX+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags = 'export_single_button')#button text for open db
            self.canvas.tag_bind('export_single_button', '<Button-1>', lambda event: self.export_single_topics(event))
            buttonX += x_offset + button_width

            buttonText = "Export Tag Networks"
            button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.export_tagnet_button = self.canvas.create_rectangle(buttonX, y_offset, buttonX + button_width, y_offset + textlineheight + 2*textelbowroom, fill='snow', tags='export_tagnet_button')
            self.canvas.create_text(buttonX+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags = 'export_tagnet_button')
            self.canvas.tag_bind('export_tagnet_button', '<Button-1>', lambda event: self.export_tag_networks(event))
            buttonX += x_offset + button_width

            #new row
            y_offset += 10 + textlineheight + 2*textelbowroom
            buttonX = x_offset

            buttonText = "Export Subtopic Breakdowns"
            button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.export_subtopic_button = self.canvas.create_rectangle(buttonX, y_offset, buttonX + button_width, y_offset + textlineheight + 2*textelbowroom, fill='snow', tags='export_subtopic_button')
            self.canvas.create_text(buttonX+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags = 'export_subtopic_button')
            self.canvas.tag_bind('export_subtopic_button', '<Button-1>', lambda event: self.export_subtopic_breakdowns(event))
            buttonX += x_offset + button_width

            #new row
            y_offset += 10 + textlineheight + 2*textelbowroom
            buttonX = x_offset
            
        #Tag Sorting Buttons:
            buttonText = "Search Tag"
            button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.create_tag_button_rect = self.canvas.create_rectangle(buttonX, y_offset, buttonX + button_width, y_offset + textlineheight + 2*textelbowroom, fill='azure', tags='create_tag_button')
            self.canvas.create_text(buttonX+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags = 'create_tag_button')#button text for open db
            self.canvas.tag_bind('create_tag_button', '<Button-1>', lambda event: self.select_tag(event))
            buttonX += x_offset + button_width
            
            buttonText = "Select Books"
            button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.select_book_rect = self.canvas.create_rectangle(buttonX, y_offset, buttonX + button_width, y_offset + textlineheight + 2*textelbowroom, fill='azure', tags='select_book_button')
            self.canvas.create_text(buttonX+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags = 'select_book_button')#button text for open db
            self.canvas.tag_bind('select_book_button', '<Button-1>', lambda event: self.select_book(event))
            buttonX += x_offset + button_width

            buttonText = "Toggle Set Operation"
            button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.create_toggle_union_btn = self.canvas.create_rectangle(buttonX, y_offset, buttonX + button_width, y_offset + textlineheight + 2*textelbowroom, fill='snow', tags='toggle_union_button')
            self.canvas.create_text(buttonX+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags = 'toggle_union_button')#button text for open db
            self.canvas.tag_bind('toggle_union_button', '<Button-1>', lambda event: self.toggle_union(event))
            buttonX += x_offset + button_width

            #new row
            y_offset += 10 + textlineheight + 2*textelbowroom
            buttonX = x_offset

        #Additional Toolset:
            buttonText = "Copy These Verses"
            button_width = self.canvasFont.measure(buttonText) + 2*textelbowroom
            self.copy_this_verselist_button = self.canvas.create_rectangle(buttonX, y_offset, buttonX + button_width, y_offset + textlineheight + 2*textelbowroom, fill='snow', tags='copy_vlist_button')
            self.canvas.create_text(buttonX+textelbowroom, y_offset+textelbowroom, text=buttonText, anchor=tk.NW, font=self.canvasFont, tags = 'copy_vlist_button')#button text for open db
            self.canvas.tag_bind('copy_vlist_button', '<Button-1>', lambda event: self.copy_verse_lists(event))
            buttonX += x_offset + button_width

            # comments only checkbox -- the filtering feature associated with this is not written yet
            if self.comments_only:
                comments_checkbox_fill = "black"
            else:
                comments_checkbox_fill = "white"

            self.canvas.create_rectangle(buttonX, y_offset, buttonX+textlineheight, y_offset+textlineheight, outline="black", fill=comments_checkbox_fill)
            self.checkbox_id = self.canvas.create_rectangle(buttonX+textlineheight/4, y_offset+textlineheight/4, buttonX+(textlineheight*3/4), y_offset+(textlineheight*3/4), fill=comments_checkbox_fill)
            self.label_id = self.canvas.create_text(buttonX+textlineheight+textelbowroom, y_offset, text="Only show verses with comments", anchor=tk.NW)
            self.canvas.tag_bind(self.checkbox_id, "<Button-1>", self.toggle_comments_only)
            self.canvas.tag_bind(self.label_id, "<Button-1>", self.toggle_comments_only)

            #new row...
            y_offset += 10 + textlineheight + 2*textelbowroom
            buttonX = x_offset

            

            # LIST OF TAGS AND VERSES ##---- DONE
            #print("test 1")
            #delete tag button size...
            
            checklist = self.tags_list.copy() #in this case, the checklist is all strings, so no tag['tag'] or tag['id']
            synonymlist = [] #the list of tags that will actually be shown
            verses = []  # To hold the final set of verses

            if len(self.tags_list) > 0:
                grouped_verses = []  # To hold verse sets for each tag + synonyms group

                # Go through each selected tag in self.tags_list
                for tag in self.tags_list:
                    #prepare the verse set for this tag and its synonyms by getting the verses for this tag first.
                    verse_set = set()
                    #print("tag", tag)
                    vd = bibledb.get_db_stuff(self.dbdata, "verse", "tag", tag) #vd now has a list of all the verses as returned by get_db_stuff
                    vdcopy = vd.copy() #make a copy of verse data so we can parse it safely
                    #eliminate all verses that aren't in the selected books
                    if (len(self.selected_books) > 0):
                        for verse in vdcopy:
                            if (bibledb.book_proper_names[verse["start_book"]] not in bibledb.book_proper_names) and (bibledb.book_proper_names[verse["end_book"]] not in bibledb.book_proper_names):
                                vd.remove(verse)
                        vdcopy = vd.copy() #remake vdcopy for the next filter


                    #print("vd 1", vd)
                    #convert the verse data to a tuple of numbers to make it hashable for some list functions
                    verse_set.update(((m["start_book"],m["start_chapter"],m["start_verse"],m["end_book"],m["end_chapter"],m["end_verse"]) for m in vd))

                    # Get all synonyms for the current tag (including the tag itself)
                    synonyms = bibledb.get_db_stuff(self.dbdata, "tag", "tag", tag)
                    #for synonym in synonyms:
                    while len(synonyms) > 0:
                        synonym = synonyms.pop()
                        #make the synonymlist which will be used for the tags
                        if synonym['tag'] not in checklist:
                            #synonyms won't have a delete button on the display, so we group them in the list in order to make it clear what they are.
                            index = checklist.index(tag)
                            checklist.insert(index+1,synonym['tag'])
                            synonymlist.append(synonym['tag'])
                            synonyms += bibledb.get_db_stuff(self.dbdata, "tag", "tag", synonym['tag'])
                        # add the verses for every synonym
                        vd = bibledb.get_db_stuff(self.dbdata, "verse", "tag", synonym['tag'])
                        #print("vd 2", vd)
                        verse_set.update(((m["start_book"],m["start_chapter"],m["start_verse"],m["end_book"],m["end_chapter"],m["end_verse"]) for m in vd))

                    # Append the verse set (tag + its synonyms) to grouped_verses
                    grouped_verses.append(verse_set)

                # This next section is why I wanted the hashable tuples....
                # Union logic: collect all unique verses from all tag groups
                if self.union:
                    verses = set()
                    # making it a set will prevent duplicate entries
                    for verse_set in grouped_verses:
                        verses.update(verse_set)
                # Intersection logic: collect only verses present in all tag groups
                elif self.intersection:
                    verses = grouped_verses[0]  # Start with the first group of verses (this is a set, not a list)
                    for verse_set in grouped_verses[1:]:
                        verses = verses.intersection(verse_set)  # Keep only common verses
                # symmetric difference logic: show only verses which are present in only one of the tag groups
                elif self.symmetric_difference:
                    verses = grouped_verses[0]
                    for verse_set in grouped_verses[1:]:
                        verses = verses.symmetric_difference(verse_set)
                
                #both union and intersection converted verses to a set. Make it a list again.
                verses = list(verses)
                

            #SHOW THE BOOK FILTER LIST
            xb_width = self.canvasFont.measure(" x ")
            tagx = 0
            
            for book in self.selected_books:
                #print(book)
                book_width = self.canvasFont.measure(book) + 2*textelbowroom
                if book_width + xb_width + tagx+1 + x_offset + right_x_offset > panelWidth: #+1 for that thicker line between tags
                    tagx = 0
                    y_offset += textlineheight + textlinegap*3
                #every book gets an x
                book_delete_binder = "Delete_" + str(book)
                tagx += 1 #making a thicker line between tag groups
                self.canvas.create_rectangle(x_offset+tagx, y_offset, x_offset+tagx+xb_width, y_offset+textlineheight+textlinegap*2, fill='coral1', tags=book_delete_binder)
                self.canvas.create_text(x_offset+tagx, y_offset+textlinegap, text=" X", anchor=tk.NW, font=self.canvasFont, tags=book_delete_binder)
                
                tagx += xb_width
                #clicking the book deletes the book from the list
                self.canvas.create_rectangle(x_offset+tagx, y_offset, x_offset+tagx+book_width, y_offset+textlineheight+textlinegap*2, fill='azure', tags=book_delete_binder)
                self.canvas.create_text(x_offset+tagx, y_offset+textlinegap, text=" " + book, anchor=tk.NW, font=self.canvasFont, tags=book_delete_binder)
                
                self.canvas.tag_bind(book_delete_binder, '<Button-1>', lambda event, mytag=book: self.delete_book(event, book))
                tagx += book_width


            if len(self.selected_books) > 0:
                y_offset += textlineheight + textlinegap*3 + 10
            
            #SHOW THE TAGS LIST
            tagx = 0
            for tag in checklist:
                tag_width =  self.canvasFont.measure(tag) + 2*textelbowroom

                #wrap tag list
                if tag_width + xb_width + tagx+1 + x_offset + right_x_offset > panelWidth: #+1 for that thicker line between tags
                    tagx = 0
                    y_offset += textlineheight + textlinegap*3

                #tag delete "X" button.
                #only do this if this is not a synonym
                if tag not in synonymlist:
                    tag_delete_binder = "Delete_" + str(checklist.index(tag))
                    tagx += 1 #making a thicker line between tag groups
                    self.canvas.create_rectangle(x_offset+tagx, y_offset, x_offset+tagx+xb_width, y_offset+textlineheight+textlinegap*2, fill='coral1', tags=tag_delete_binder)
                    self.canvas.create_text(x_offset+tagx, y_offset+textlinegap, text=" X", anchor=tk.NW, font=self.canvasFont, tags=tag_delete_binder)
                    self.canvas.tag_bind(tag_delete_binder, '<Button-1>', lambda event, mytag=tag: self.delete_tag(event, mytag))
                    tagx += xb_width
                #actual tag display
                tag_display_binder = "Display_" + str(checklist.index(tag))
                self.canvas.create_rectangle(x_offset+tagx, y_offset, x_offset+tagx+tag_width, y_offset+textlineheight+textlinegap*2, fill='azure', tags=tag_display_binder)

                #if there's a note on this tag, put a little triangle on the corner of the tag's button
                if (len(bibledb.get_db_stuff(self.dbdata, "note", "tag", tag)) > 0):
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
                self.canvas.create_text(x_offset+tagx, y_offset+textlinegap, text=" " + tag, anchor=tk.NW, font=self.canvasFont, tags=tag_display_binder)
                #button event to show tag details in this panel...
                self.canvas.tag_bind(tag_display_binder, '<Button-1>', lambda event, item_id = tag : self.on_tag_click(event,item_id))
                tagx += tag_width

            y_offset += textlineheight + textlinegap*3 + 10

            # SHOW THE VERSE LIST
            
            try:
                # If the user makes a DB using a version of the Bible that has the apocrypha, and then tries to pull notes about Revelation from that DB while he has a protestant Bible loaded...
                #    then the reference to bibledb_Lib.book_proper_names[] will throw an index out of range error.
                #    I am making this tool primarily for myself to use, and I don't include the apocrypha in my Bible, so I don't plan to fix this.
                
                verses.sort(key=lambda r: (r[0], r[1], r[2]))#sort by start book first, then chapter, then verse, so all the verses appear in order
                self.verse_xref_list = [(bibledb.book_proper_names[q[0]]+" "+str(q[1])+":"+str(q[2]), bibledb.book_proper_names[q[3]]+" "+str(q[4])+":"+str(q[5])) for q in verses]
            except:
                self.verse_xref_list = []
                print("Failed to get the verse references for that tag. This error might occur if your DB was made with a version of the Bible that had different books from the version you're currently using. For example, if the DB was made including the apocrypha, but your current Bible doesn't have it.")
            self.canvas.itemconfigure(versecount_text, text = "total verse count: " +str(len(self.verse_xref_list)))
            tagx = 0
            self.shown_verses = []
            for xverse in self.verse_xref_list:
                itemText = combineVRefs(xverse[0],xverse[1])#this is the human readable verse reference
                #Check if we're filtering on verses with comments
                if self.comments_only and not (len(bibledb.get_db_stuff(self.dbdata, "note", "verse", itemText)) > 0):
                    continue #if we're filtering and no comment, then skip this iteration in the foor loop.
                #check if the verse should be book filtered
                if len(self.selected_books) > 0:
                    skipverse = True
                    for book in self.selected_books:
                        if book in itemText:
                            skipverse = False
                            break
                    if skipverse:
                        continue

                self.shown_verses.append(itemText + ", ")
                #draw the button and verse
                button_width = self.canvasFont.measure(itemText) + 2*textelbowroom
                if button_width + tagx + x_offset + right_x_offset > panelWidth:
                    tagx = 0
                    y_offset += textlineheight + textlinegap*3
                clicktag = "verse_click_"+str(tagx)+"_"+str(y_offset)
                self.canvas.create_rectangle(x_offset+tagx, y_offset, x_offset+tagx+button_width, y_offset+textlineheight+textlinegap*2, fill='azure', tags=clicktag)
                self.canvas.create_text(x_offset+tagx+textelbowroom, y_offset+textlinegap, text=itemText, anchor=tk.NW, font = self.canvasFont, tags=clicktag)
                self.canvas.tag_bind(clicktag, '<Button-1>', lambda event, payload=xverse: self.on_verse_click(event, payload))
                tagx += button_width
            #print("test 3")
            y_offset += textlineheight + textlinegap*3 + 10
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))


