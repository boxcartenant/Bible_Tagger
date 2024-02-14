import tkinter as tk
from tkinter import ttk
from tkinter import Misc
import bibledb_Lib as bibledb
from tkinter.font import Font

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


class SecondaryWindow:
    def __init__(self, master, callback, dbdata = None):
        self.master = master
        self.callback = callback
        self.dbdata = dbdata
        
        #Handy variables here...
        self.canvasFont = Font(size = 10)
        self.italicFont = Font(size = 10, slant = 'italic')
        self.boldFont = Font(size = 10, weight = 'bold')
        self.sortmode_text = "Sorting Alphabetically"
        self.sortmode = "alphabet" #toggles between "alphabet" and "usage"
        self.colormode_text = "Toggle Colors"
        self.colormode = "plain" #toggles: "plain", "redblue", "purpleyellow"
        

        # Set up the secondary window
        self.top_window = tk.Toplevel(master)
        self.top_window.title("DB Info")
        self.top_window.geometry("500x500")

        #I am accustomed to dealing with paned windows
        self.this_window = ttk.PanedWindow(self.top_window, orient="horizontal")
        self.this_window.pack(fill="both", expand=True)

        #this frame represents a single pane on the window;
        #I don't know if I'm going to have several panes or not,
        #...but if I will, then this is where I should split them.
        self.myFrame = ttk.Frame(self.this_window)

        #this frame is configured for the top left cell of the grid,
        #and to span the whole area in that cell
        #right now there's only one cell, so it takes the whole window
        self.myFrame.grid(row=0, column=0, sticky="nsew")
        self.myFrame.grid_rowconfigure(0, weight=1)
        self.myFrame.grid_columnconfigure(0, weight=1)
        
        #add the canvas to the frame
        self.canvas = tk.Canvas(self.myFrame)
        #the frame also has a grid inside it. Put the canvas on the top left cell.
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        #whenever the window resizes, I want the canvas scroll area to refresh
        self.canvas.bind("<Configure>", lambda e: self.display_attributes())

        #create vertical and horizontal scrollbars
        v_scrollbar = tk.Scrollbar(self.myFrame, orient="vertical", command=self.canvas.yview)
        h_scrollbar = tk.Scrollbar(self.myFrame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Configure scrollbar position on the grid
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        #add the frame to the window
        self.this_window.add(self.myFrame)

        #configure the scroll region to make the canvas scrollable
        canvas_width = self.canvas.winfo_reqwidth()
        canvas_height = self.canvas.winfo_reqheight()
        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

        #finish rendering the window before showing attributes, so that the dimensions will be accurate
        self.top_window.update_idletasks()

        #go ahead and display contents
        self.display_attributes()

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

    def display_attributes(self, dbstuff = None):
        x_offset = 5
        y_offset = 3
        textelbowroom = 10
        textlinegap = 2
        textlineheight = Font.metrics(self.canvasFont)["linespace"]
        boldlineheight = Font.metrics(self.boldFont)["linespace"]
        italiclineheight = Font.metrics(self.italicFont)["linespace"]
        right_x_offset = 30
        panelWidth = self.top_window.winfo_width() - right_x_offset

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
            checklist = bibledb.get_tag_list(self.dbdata)
            tags = [{"tag":b["tag"]} for b in checklist]

            #group tags by synonyms
            
            syngroups = []
            synonymlist = []
            for tag in checklist:
                #add the current tag to a list of synonyms
                synonymlist.append(tag["tag"])
                #get all the synonyms for that tag
                synonyms = bibledb.get_db_stuff(self.dbdata,"tag","tag",tag["tag"])
                for synonym in synonyms:
                    if synonym != tag:
                        #add each synonym to the synonym list
                        synonymlist.append(synonym["tag"])
                        #remove it from the checklist
                        checklist.remove(synonym)
                #add the synonymlist to the list of synonym groups
                syngroups.append({"tags":synonymlist})
                synonymlist = []
                #checklist.remove(tag)#this line causes the for loop to skip indices.

            syngroups_lo = 9223372036854775807
            syngroups_hi = 0
            #count the unique verses for the synonym group
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

            if self.sortmode == "alphabet":
                sorted_tags = sorted(tags, key=lambda x: x["tag"])
                sorted_syngroups = [(syngroups.index(lst), lst["tags"].index(dct["tag"])) for dct in sorted_tags for lst in syngroups if dct["tag"] in lst["tags"]]
            elif self.sortmode == "usage":
                #We are only using syngroups for display, so no need to sort tags here.
                #sorted_tags = sorted(tags, key=lambda x: x["verses"], reverse = True) #reverse to put the most-used tags on top
                sorted_syngroups = sorted(syngroups, key=lambda x: x["verses"], reverse = True)
            tagnum = 0
            for s in sorted_syngroups:
                if self.sortmode == "alphabet":
                    tags = [syngroups[s[0]]["tags"][s[1]]]
                    verses = syngroups[s[0]]["verses"]
                elif self.sortmode == "usage":
                    tags = s["tags"]
                    verses = s["verses"]

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
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


    #TO DO:
    #Fix tag click callback
    #update button text to reflect current color/sorting selections
                
        # Example button that calls the callback function in the main window
        #self.button = tk.Button(self.secondary_window, text="Call Main Window Callback", command=self.callback)
        #self.button.pack()
