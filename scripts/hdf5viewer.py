from tkinter import Tk,Toplevel,Listbox,Entry,Frame,Label,StringVar,Button,StringVar,filedialog,Scrollbar,Frame,END,CENTER,W,BOTTOM,TOP,BOTH,Toplevel,X,Menu
from tkinter import colorchooser
from tkinter.ttk import Treeview
import h5py
import matplotlib
from matplotlib.colors import Colormap
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
import sys
import os

class ColormapChooser(Toplevel):
    def __init__(self,master,cmap=None):
        Toplevel.__init__(self,master)
        # update title
        self.title("Choose a colormap")
        # create frame
        frm = Frame(self)
        # create listbox
        self.clist = Listbox(frm)
        # bind double click
        self.clist.bind('<Button-1>',self.cmapSelect)
        # get all colormaps
        for ci,(kk,_) in enumerate(filter(lambda x : isinstance(x[1],Colormap),vars(matplotlib.cm).items())):
            self.clist.insert(ci,kk)
        # scrollbar
        scroll = Scrollbar(frm,orient='vertical')
        scroll.config(command=self.clist.yview)
        # currently selected colormap
        # if nothing is given, get matplotlib default
        if cmap == None:
            self.curr_cmap = getattr(matplotlib.cm,matplotlib.rcParams['image.cmap'])
        else:
            # if user specifies a string
            if type(cmap) == str:
                # attempt to get index of colormap from list
                # if it fails, reverts to default
                try:
                    idx = self.self.clist.get(0,END).index(cmap)
                    self.self.clist.select(idx)
                    self.curr_cmap = getattr(matplotlib.cm,self.self.clist.get(0,END)[idx])
                except ValueError:
                    self.curr_cmap = getattr(matplotlib.cm,matplotlib.rcParams['image.cmap'])
            # if the user passs a Colormap directly, store that
            elif isinstance(cmap,Colormap):
                self.curr_cmap = cmap
            # if it's something else
            # print error message and set current colormap to None
            else:
                print(f"Unsupported colormap value {cmap}!",file=sys.stderr)
                self.curr_cmap = None
        # add buttons
        btt_frm = Frame(self)
        select_btt = Button(btt_frm,text="Select",command=self.enter_handler)
        cancel_btt = Button(btt_frm,text="Cancel",command=self.cancel_handler)

        # keyboard handlers for if the button is currently selected
        select_btt.bind('<KeyPress-Return>', func=self.enter_handler)
        cancel_btt.bind('<KeyPress-Return>', func=self.cancel_handler)
        ## pack
        self.clist.grid(row=0,column=0,sticky='nswe')
        scroll.grid(row=0,column=1,sticky='ns')
        
        frm.grid(row=0,column=0,sticky='nswe')
        
        select_btt.grid(row=0,column=0,sticky='ew')
        cancel_btt.grid(row=0,column=1,sticky='ew')
        
        btt_frm.grid(row=1,column=0,columnspan=2,sticky='ew')
    # colormap listbox double click handler
    # gets colormap matching key and updates selected colormap
    def cmapSelect(self,event):
        selection = event.widget.curselection()
        if len(selection)==0:
            return
        print(event.widget.get(selection[0]))
        self.curr_cmap = getattr(matplotlib.cm,event.widget.get(selection[0]))

    def enter_handler(self):
        selection = self.clist.curselection()
        self.curr_cmap = self.clist.get(selection[0])
        self.destroy()

    def cancel_handler(self):
        self.curr_cmap = None
        self.destroy()

    def show(self):
        self.wm_deiconify()
        self.clist.focus_force()
        self.wait_window()
        return self.curr_cmap
        
class DataViewer:
    ''' DataViewer
        ======================
        David Miller, 2020
        The University of Sheffield 2020

        Wrapper GUI for a Matplotlib Figure showing the data given on creation. Called by HDF5Viewer when the user
        double clicks on a dataset.

        This GUI is designed a means of performing basic inspections of data stored in HDF5 files. If users want to
        perform something intensive or particular custom, they are advised to do so elsewhere.

        On creation, the DataViewer opens up the file specified by filename and accesses the dataset specified by the
        path dataName. It then decides how to plot the data based on the number of dimensions in the dataset. The used
        plots are as follows using their respective default options:

        |No. dims | Plots    |
        |---------|----------|
        |   1     | Line     |
        |   2     | Contourf |
        |   3     | Contourf |

        In the case of three dimensions, a scrollbar is added on top of the plot and provides a means for the user
        to select which 2D slice of the 3D dataset to show.

        The scrollbar only supports drag operations.

        Any higher dimensional data is ignored.

        The title above the Figure displays the name of the dataset and which index, if any is being displayed.

        Methods
        -------------------------
        on_key_press(event):
            Handler for key presses used on the Matploblib canvas

        scroll_data(self,*args):
            Handler for changing which slice of a 3D dataset is displayed. A new data index is chosen based on where
            the scrollbar cursor is dragged to. The index is calculated by multiplying the scrollbar positon [0,1] by
            the number of frames in the dataset and then converted to an integer.
            Updates the title and canvas on exit. Sets the scrollbar position to where the user left it.
            
            Currently this only has support for clicking and dragging the scrollbar cursor. Other operations are
            ignored.
    '''
    # using filename and name of dataset
    # create a figure and display the data
    def __init__(self,master,dataName,filename):
        self.master = master
        # save creation options
        self.dataName = dataName
        self.filename = filename
        # set title
        self.master.title("Data Viewer")
        # current colormap, default
        self.curr_cmap = getattr(matplotlib.cm,matplotlib.rcParams['image.cmap'])
        # currnt line color
        self.curr_lcol = matplotlib.rcParams['axes.prop_cycle'].by_key()['color'][0]
        ## menu bar for customisation
        # root menu
        menu = Menu(master)
        # options menu
        optsmenu = Menu(menu,tearoff=0)
        # label for graph
        self.title = StringVar()
        self.title.set(f'Displaying {dataName}')
        self.graph_title = Label(master,textvariable=self.title)
        self.graph_title.pack(side=TOP,pady=10,padx=10)
        # create figure
        self.fig = Figure(figsize=(5,5),dpi=100)
        self.axes = self.fig.add_subplot(111)
        # get data from dataset and plot data
        with h5py.File(filename,mode='r') as f:
            self.data_shape = f[dataName].shape
            # if the data is 1D, plot as line
            if len(self.data_shape)==1:
                self.axes.plot(f[dataName][()],self.curr_lcol)
                optsmenu.add_command(label="Set color",command=self.set_color)
            # if data is 2D, plot as filled contour
            elif len(self.data_shape)==2:
                self.axes.contourf(f[dataName][()],cmap=self.curr_cmap)
                optsmenu.add_command(label="Set colormap",command=self.set_colormap)
            # if data is 3D plot as contourf, but also add a scrollbar for navigation
            elif len(self.data_shape)==3:
                optsmenu.add_command(label="Set colormap",command=self.set_colormap)
                # create scroll bar for viewing different slices
                self.plot_scroll=Scrollbar(master,orient="horizontal",command=self.scroll_data)
                # add too gui
                self.plot_scroll.pack(side=TOP,fill=BOTH,expand=True)
                # plot first slice of data
                self.axes.contourf(f[dataName][:,:,0],cmap=self.curr_cmap)
                # create index for current depth index
                self.depth_index = 0
                self.title.set(f"Displaying {dataName} [{self.depth_index}]")
        # add to root menu
        menu.add_cascade(label="Options",menu=optsmenu)
        self.master.config(menu=menu)
        # create canvas to render figure
        self.fig_canvas = FigureCanvasTkAgg(self.fig,self.master)
        # update result
        self.fig_canvas.draw()
        # update canvas to set position and expansion options
        self.fig_canvas.get_tk_widget().pack(side=TOP,fill=BOTH,expand=True)

        ## add matplotlib toolbar
        self.fig_toolbar = NavigationToolbar2Tk(self.fig_canvas,self.master)
        self.fig_toolbar.update()
        # add to gui. always one row below the canvas
        self.fig_canvas._tkcanvas.pack(side=TOP,fill=BOTH,expand=True)
        ## add key press handlers
        self.fig_canvas.mpl_connect("key_press_event",self.on_key_press)
        # ensure elements are expandable in grid
        num_cols,num_rows = master.grid_size()
        for c in range(num_cols):
            master.columnconfigure(c,weight=1)
        for r in range(num_rows):
            master.rowconfigure(r,weight=1)
        # finish any idle tasks and set the minimum size of the window to cur
        master.update_idletasks()
        master.after_idle(lambda: master.minsize(master.winfo_width(), master.winfo_height()))
        
    # handler for matplotlib keypress events
    def on_key_press(event):
        key_press_handler(event,self.fig_canvas,self.fig_toolbar)

    # handler for using the scrollbar to view slices of data
    def scroll_data(self,*args):
        #print(args)
        # if the user has dragged the scrollbar
        if args[0] == "moveto":
            # args is only one element in this case and is a number between 0 and 1
            # 0 is left most position and 1 is right most position
            # the data index is calculated as this number times depth and converted to integer
            self.depth_index = int(float(args[1])*self.data_shape[2])
            # if index exceeds dataset limits
            # correct it
            if self.depth_index>=self.data_shape[-1]:
                self.depth_index = self.data_shape[-1]-1
            # set the scrollbar position to where the user dragged it to
            self.plot_scroll.set(float(args[1]),(self.depth_index+1)/self.data_shape[2])
            # reopen file
            with h5py.File(self.filename,mode='r') as f:
                self.axes.contourf(f[self.dataName][:,:,self.depth_index],cmap=self.curr_cmap)
            # update canvas
            self.fig_canvas.draw()
            # update title
            self.title.set(f"Displaying {self.dataName} [{self.depth_index}]")

    def set_colormap(self):
        ch = ColormapChooser(self.master).show()
        if ch:
            self.curr_cmap = ch
            self.scroll_data("moveto",str(self.plot_scroll.get()[0]))

    def update_line(self):
        # remove first line from plot
        self.axes.lines.pop(0)
        with h5py.File(self.filename,mode='r') as f:
            self.axes.plot(f[self.dataName][()],self.curr_lcol)
        # update canvas
        self.fig_canvas.draw()

    def set_color(self):
        col = colorchooser.askcolor()
        if col[1]:
            self.curr_lcol = col[1]
            self.update_line()
        
class HDF5Viewer:
    ''' HD5Viewer
        ======================
        David Miller, 2020
        The University of Sheffield 2020
        
        Presents a graphical means for users to view and inspect the contents of a HDF5 file.
        
        The user points the GUI to a HDF5 file by clicking on the 'Open' button, travelling to a folder and either
        double clicking on a file or selecting a file and clicking the 'Open' button.

        Once the file is selected, the user clicks the 'Scan' button which opens the file in read-only mode in
        a context manager and iterates through the file. The GUI populates a treeview in the GUI with the names of
        objects, their type, shape and data type (datasets only) in a way that mirrows the structures of the file.
        If the type column describes the type of object inside the HDF5 file. If the object is a Group, the contents
        under the shape column represents the number of items stored one level under it. If the object is a Dataset,
        the shape represents the shape of the array stored in the dataset. The data type column is only updated for
        datasets and is the type of data stored in the dataset.

        This class keeps control of the specified file for the minimum amount of time only accessing it for the
        duration of scan_file.

        If the user double clicks on a dataset, a DataViewer GUI is opened in another window. This attempts to display
        the dataset, choosing the appropriate plots based on the shape of the dataset.

        Methods:
        --------------------------
        open_file(self):
            Opens a file dialog for the user to select the HDF5 file they want to inspect.
            
        explore_group(self,item,parent):
            Iterates through the objects stored under item and updates the treeview with the information it finds
            under the node/leaft with the ID parent. If it finds a Group while iterating, explore_group is called
            with the newly discovered Group passed as the item to explore and the parent node to update under.
            Used in scan_file.

        scan_file(self):
            Attempts to open the file specified by the user. If a file path has yet to be specified it returns.
            If it's successful in opening the file, it iterates through its contents updating the treeview with the=
            information it finds. It uses the function explore_group to iterate through Groups it finds under root.
    '''
        
    def __init__(self,master):
        self.master = master
        # set title of image
        master.title("HDF5 File Viewer")

        ## initialize internal variables used
        # set current file as blank
        self.curr_file = "/"
        self.status = StringVar()
        
        ## initialize widgets
        # status label indicating progress or errors
        self.status_label = Label(master,textvariable=self.status)
        self.status.set("Waiting for filename...")
        # button to scan target HDF5 file
        self.scan_button = Button(master,text="Scan File",command=self.scan_file,padx=2)
        # button to chose hdf5 file
        self.openfile_button = Button(master,text="Open File",command=self.open_file,padx=2)
        # box to display current filename
        self.name_display = Entry(master,text="Current filename")
        ## setup tree headings
        # tree view for file layout
        self.file_tree = Treeview(master,columns=("htype","shape","dtype"),show="tree")
        # add double click handler
        # <Double-1> double left click handler
        self.file_tree.bind("<Double-1>",self.create_viewer)
        # dimensions of the columns
        self.file_tree.column("htype",width=200,anchor=CENTER)
        self.file_tree.column("shape",width=200,anchor=CENTER)
        self.file_tree.column("dtype",width=200,anchor=CENTER)
        # text to display in headings
        self.file_tree.heading("htype",text="Item Type")
        self.file_tree.heading("shape",text="Shape")
        self.file_tree.heading("dtype",text="Data Type")
        self.file_tree['show']='headings'
        
        ## add scrollbar for treeview
        # define scrollbar and set the action associated with moving the scrollbar to changing
        # the yview of the tree
        self.tree_scroll=Scrollbar(master,orient="vertical",command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=self.tree_scroll)
        
        # set grid layout for widgets using grid
        self.status_label.grid(columnspan=3,row=0)
        self.file_tree.grid(column=0,row=2,columnspan=3,sticky='nswe')
        self.scan_button.grid(column=0,row=1,sticky='we',padx=10)
        self.openfile_button.grid(column=1,row=1,sticky='we',padx=10)
        self.name_display.grid(column=2,row=1,sticky='we',padx=10)
        self.tree_scroll.grid(column=3,row=2,sticky='ns')
        # set weight parameters for control how the elements are resized when the user changes the window size
        master.columnconfigure(0,weight=1)
        master.columnconfigure(1,weight=1)
        master.columnconfigure(2,weight=1)
        master.columnconfigure(3,weight=1)
        master.rowconfigure(0,weight=1)
        master.rowconfigure(1,weight=1)
        master.rowconfigure(2,weight=1)
        master.rowconfigure(3,weight=1)
        # finish any idle tasks and set the minimum size of the window to cur
        master.update_idletasks()
        master.after_idle(lambda: master.minsize(master.winfo_width(), master.winfo_height()))
        
    # function for the user to select the HDF5 file to explore
    # opens file dialog for user to explore
    def open_file(self):
        self.status.set("Waiting for user to select file...")
        # open dialog to search for hdf5 file
        self.curr_file = filedialog.askopenfilename(initialdir=os.path.dirname(self.curr_file),title="Select HDF5 file to inspect",filetypes=[("HDF5 files","*.hdf5")])
        self.name_display.delete(0,END)
        self.name_display.insert(0,self.curr_file)
        try:
            with open(self.curr_file,'r') as file:
                self.status.set("Successfully opened target file")
        except OSError as err:
            self.status.set(err)
            
    # function to explore HDF5 group and update tree
    # if it finds another HDF5 group it calls the functions to explore that group
    def explore_group(self,item,parent):
        self.status.set(f"Exploring {item.name}")
        #print("Exploring {}...".format(item.name))
        # iterate through items
        for v in item.values():
            #print(v.name,str(type(v)))
            # if it's a dataset, update shape entry with shape of dataset
            if isinstance(v,h5py.Dataset):
                self.file_tree.insert(parent,'end',text=v.name,values=(str(type(v)),str(v.shape),str(v.dtype)),open=True)
                self.file_tree['show']='tree headings'
            # if it's a group, call function to investiage it passing last group as parent to add new nodes to
            elif isinstance(v,h5py.Group):
                pkn = self.file_tree.insert(parent,'end',text=v.name,values=(str(type(v)),f"{(len(v.keys()),)}"),open=True)
                self.explore_group(v,pkn)           
    # explores target hdf5 file and displays the the keys of each entry
    # it the entry is a group, then it calls explore_group to explore further
    def scan_file(self):
        # if target file is set
        if self.curr_file != "/":
            # clear tree
            self.file_tree.delete(*self.file_tree.get_children())
            # open file in read mode and iterate through values
            with h5py.File(self.curr_file,'r') as file:
                for v in file.values():
                    # if it's a dataset, update shape entry with shape of dataset
                    if isinstance(v,h5py.Dataset):
                        self.file_tree.insert('','end',text=v.name,values=(str(type(v)),str(v.shape),str(v.dtype)),open=True)
                    # if it's a group, call function to investiage it
                    elif isinstance(v,h5py.Group):
                        pkn = self.file_tree.insert('','end',text=v.name,values=(str(type(v)),f"{(len(v.keys()),)}"),open=True)
                        self.explore_group(v,pkn)
            # update tree display
            self.file_tree['show']='tree headings'
            self.status.set(f"Finished scanning .../{self.curr_file[self.curr_file.rfind('/')+1:]}")
            # finish idle tasks and set minimum window size to final window size
            self.master.update_idletasks()
            self.master.after_idle(lambda: self.master.minsize(self.master.winfo_width(), self.master.winfo_height()))
        else:
            self.status.set("No fime set!")
    def create_viewer(self,event):
        if self.curr_file != "/":
            # get the item selected
            iid = self.file_tree.identify('item',event.x,event.y)
            # get the values of the item to check if a dataset or group was selected
            if 'Dataset' in self.file_tree.item(iid,"values")[0]:
                self.status.set(f"Creating view for {self.file_tree.item(iid,'text')}")
                # create new child window
                t = Toplevel()
                # initialize window inside new child window
                self.data_viewer = DataViewer(t,self.file_tree.item(iid,"text"),self.curr_file)

if __name__ == "__main__":         
    root = Tk()
    view = HDF5Viewer(root)
    root.mainloop()

        
