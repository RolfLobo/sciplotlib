from rich.progress import Progress, TimeElapsedColumn, TimeRemainingColumn, TextColumn, BarColumn
from rich.progress import track
import typer
import ttkbootstrap as ttk
from ttkbootstrap import Style
import tkinter as tk
from tkinter import filedialog
import sys
import pdb
import numpy as np
import os
import io
import pickle
from pathlib import Path

# Matplotlib
import matplotlib.pyplot as plt
import matplotlib.cbook as cbook
import matplotlib.image as mpimg

# Sciplotlib
import sciplotlib.style as splstyle
from sciplotlib.compose import (
    cm_to_px, PAPER_DIMENSIONS,
    copy_axes_content, load_panel_content,
    parse_layout_file, render_panels_to_figure,
)

# For saving
import json
import yaml

class ResizablePanel:
    def __init__(self, canvas, x, y, w, h, label="A",
                 grid_rows=6, grid_cols=4, paper_bbox=None):
        self.canvas = canvas
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.paper_bbox = paper_bbox  # [x0, y0, x1, y1]
        self.rect = canvas.create_rectangle(x, y, x + w, y + h, fill="lightgray")

        # Figure lettering
        self.label_id = canvas.create_text(x + 6, y + 6, text=label, anchor="nw", font=("Helvetica", 12, "bold"))
        self.label_text = label
        # self.rect, self.label_id = self._draw_panel()

        self.drag_data = {"x": 0, "y": 0}
        self._bind_events()

        self.edge_margin = 6
        self.active_edge = None
        self.dragging = False

        # CONTEXT MENU (WHEN YOU RIGHT CLICK)
        self.menu = tk.Menu(canvas, tearoff=0)


        # ASSIGN FILE TO FIGURE PANEL
        self.menu.add_command(label="Assign file", command=self.assign_file)
        self.file_label_id = None

    def _draw_panel(self):
        rect = self.canvas.create_rectangle(self.x0, self.y0, self.x1, self.y1, fill="lightgray")
        label_id = self.canvas.create_text(self.x0 + 6, self.y0 + 6, text=self.label_text,
                                           anchor="nw", font=("Helvetica", 12, "bold"))
        return rect, label_id

    def snap_to_grid(self, x, y):
        if not self.paper_bbox:
            return x, y  # fallback: no snapping

        x0, y0, x1, y1 = self.paper_bbox
        w = x1 - x0
        h = y1 - y0

        cell_w = w / self.grid_cols
        cell_h = h / self.grid_rows

        col = round((x - x0) / cell_w)
        row = round((y - y0) / cell_h)

        return x0 + col * cell_w, y0 + row * cell_h

    def _bind_events(self):
        self.canvas.tag_bind(self.rect, "<ButtonPress-1>", self.on_press)
        self.canvas.tag_bind(self.rect, "<B1-Motion>", self.on_drag)

        if sys.platform == 'darwin':
            right_click_button_number = 2
        else:
            right_click_button_number = 3

        # Bind right-click  to open context menu
        self.canvas.tag_bind(self.rect, "<Button-%.f>" % right_click_button_number, self.show_context_menu)
        self.canvas.tag_bind(self.label_id, "<Button-%.f>" % right_click_button_number, self.show_context_menu)

        # Detect cursor change
        self.canvas.tag_bind(self.rect, "<Motion>", self.on_motion)

        # Bind button release
        self.canvas.tag_bind(self.rect, "<ButtonRelease-1>", self.on_release)
        self.canvas.tag_bind(self.label_id, "<ButtonRelease-1>", self.on_release)

    def _detect_edge(self, x, y):
        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        m = self.edge_margin

        near_left = abs(x - x0) < m
        near_right = abs(x - x1) < m
        near_top = abs(y - y0) < m
        near_bottom = abs(y - y1) < m

        # Corner priority
        if near_left and near_top:
            return "top-left"
        elif near_right and near_top:
            return "top-right"
        elif near_left and near_bottom:
            return "bottom-left"
        elif near_right and near_bottom:
            return "bottom-right"
        elif near_left:
            return "left"
        elif near_right:
            return "right"
        elif near_top:
            return "top"
        elif near_bottom:
            return "bottom"
        else:
            return None

    def _get_cursor(self, edge):
        return {
            "top": "sb_v_double_arrow",
            "bottom": "sb_v_double_arrow",
            "left": "sb_h_double_arrow",
            "right": "sb_h_double_arrow",
            "top-left": "top_left_corner",
            "top-right": "top_right_corner",
            "bottom-left": "bottom_left_corner",
            "bottom-right": "bottom_right_corner"
        }.get(edge, "arrow")

    def on_motion(self, event):
        edge = self._detect_edge(event.x, event.y)
        cursor = self._get_cursor(edge)
        self.canvas.config(cursor=cursor)

    def on_press(self, event):
        # Dragging the rectangle
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

        # Resizing the rectangle
        self.active_edge = self._detect_edge(event.x, event.y)
        if self.active_edge is None:
            self.dragging = True

    def on_drag(self, event):
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]


        min_size = 30
        x0, y0, x1, y1 = self.canvas.coords(self.rect)

        if self.active_edge:

            if self.active_edge == "left":
                x0 = min(x1 - min_size, x0 + dx)
            elif self.active_edge == "right":
                x1 = max(x0 + min_size, x1 + dx)
            elif self.active_edge == "top":
                y0 = min(y1 - min_size, y0 + dy)
            elif self.active_edge == "bottom":
                y1 = max(y0 + min_size, y1 + dy)
            elif self.active_edge == "top-left":
                x0 = min(x1 - min_size, x0 + dx)
                y0 = min(y1 - min_size, y0 + dy)
            elif self.active_edge == "top-right":
                x1 = max(x0 + min_size, x1 + dx)
                y0 = min(y1 - min_size, y0 + dy)
            elif self.active_edge == "bottom-left":
                x0 = min(x1 - min_size, x0 + dx)
                y1 = max(y0 + min_size, y1 + dy)
            elif self.active_edge == "bottom-right":
                x1 = max(x0 + min_size, x1 + dx)
                y1 = max(y0 + min_size, y1 + dy)

            self.canvas.coords(self.rect, x0, y0, x1, y1)
            self.canvas.coords(self.label_id, x0 + 6, y0 + 6)
            if self.file_label_id:
                cx = (x0 + x1) / 2
                cy = (y0 + y1) / 2
                self.canvas.coords(self.file_label_id, cx, cy)

        elif self.dragging:
            self.canvas.move(self.rect, dx, dy)
            self.canvas.move(self.label_id, dx, dy)
            if self.file_label_id:
                self.canvas.move(self.file_label_id, dx, dy)

        # Original arbitrary coordinates
        # self.canvas.coords(self.rect, x0, y0, x1, y1)


        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_release(self, event):
        x0, y0, x1, y1 = self.canvas.coords(self.rect)

        # Snap both corners
        x0, y0 = self.snap_to_grid(x0, y0)
        x1, y1 = self.snap_to_grid(x1, y1)

        self.canvas.coords(self.rect, x0, y0, x1, y1)
        self.canvas.coords(self.label_id, x0 + 6, y0 + 6)
        if self.file_label_id:
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            self.canvas.coords(self.file_label_id, cx, cy)

        self.active_edge = None
        self.dragging = False

    def on_resize_press(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_resize_drag(self, event):
        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        self.canvas.coords(self.label_id, x0 + 6, y0 + 6)  # move the lettering as well with resize
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        # self.canvas.coords(self.rect, x0, y0, x1 + dx, y1 + dy)

        # Snap corners to grid
        x0, y0 = self.snap_to_grid(x0, y0)
        x1, y1 = self.snap_to_grid(x1, y1)

        # Update rectangle
        self.canvas.coords(self.rect, x0, y0, x1, y1)

        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

        # Update file label position
        if self.file_label_id:
            x0, y0, x1, y1 = self.canvas.coords(self.rect)
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            self.canvas.coords(self.file_label_id, cx, cy)

    def get_bbox(self):
        return self.canvas.coords(self.rect)  # [x0, y0, x1, y1]

    def show_context_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def assign_file(self):
        filetypes = [("Image files", "*.jpg *.jpeg *.png *.svg"),
                     ("Pickle files", "*.pkl"),
                     ("All files", "*.*")]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            self.display_file_path(filepath)

    def display_file_path(self, filepath):
        # Save internally if needed
        self.filepath = filepath

        # Get current bounding box
        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2

        if self.file_label_id:
            self.canvas.delete(self.file_label_id)

        self.file_label_id = self.canvas.create_text(
            cx, cy, text=filepath, anchor="center", font=("Helvetica", 9), width=x1 - x0 - 20
        )


class FigureLayoutApp(ttk.Window):
    def __init__(self, PAPER_WIDTH_CM, PAPER_HEIGHT_CM, dpi):
        super().__init__(themename='lumen')
        self.title("Figure Layout GUI")
        self.geometry("1300x1300")

        # Quite app when window is closed
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.dpi = dpi 

        # Initial figure size 
        self.paper_width_cm = 0
        self.paper_height_cm = 0


        # Grid layout
        self.grid_rows_var = tk.IntVar(value=20)
        self.grid_cols_var = tk.IntVar(value=10)

        # Internal copies to update logic
        self.grid_rows = self.grid_rows_var.get()
        self.grid_cols = self.grid_cols_var.get()

        ############################## Layout Frames ##############################
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True)

        # Left side: Canvas
        self.canvas = tk.Canvas(main_frame, bg="white", width=800, height=1300)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Make sure grid expands canvas but not control panel
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        ### MAKE RIGHT PANEL ####
        # Right side: Vertical stack of control panels
        right_column_frame = ttk.Frame(main_frame)
        right_column_frame.grid(row=0, column=1, sticky="n", padx=(30, 50), pady=50)

        # Right side: Control Panel : Layout Controls
        control_panel = ttk.LabelFrame(right_column_frame, text="Layout controls", padding=10)
        control_panel.pack(fill="x", pady=(0, 30))
        # control_panel.grid(row=0, column=1, sticky="n", padx=100, pady=50)

        # Add buttons to control panel
        self.add_button = ttk.Button(control_panel, text="Add Panel", command=self.add_panel)
        self.add_button.pack(pady=(0, 10), fill="x")

        self.save_button = ttk.Button(control_panel, text="Save Layout", command=self.save_layout)
        self.save_button.pack(pady=(0, 10), fill="x")

        self.load_button = ttk.Button(control_panel, text="Load Layout", command=self.load_layout)
        self.load_button.pack(pady=(0, 10), fill="x")

        self.make_button = ttk.Button(control_panel, text="Make Figures", command=self.make_figures)
        self.make_button.pack(pady=(10, 0), fill="x")

        # --- SAVE FIGURE CONTROLS ---
        save_frame = ttk.LabelFrame(control_panel, text="Save Options", padding=5)
        save_frame.pack(fill='x', pady=(15, 0))

        ttk.Label(save_frame, text="Save Path").pack(anchor="w")

        path_entry_frame = ttk.Frame(save_frame)
        path_entry_frame.pack(fill='x', expand=True)

        self.save_path_var = tk.StringVar()
        # Set the default path to ~/composed_layout
        default_save_path = Path.home() / "composed_layout"
        self.save_path_var.set(str(default_save_path))

        save_entry = ttk.Entry(path_entry_frame, textvariable=self.save_path_var)
        save_entry.pack(side='left', fill='x', expand=True)

        browse_button = ttk.Button(path_entry_frame, text="...", command=self._browse_save_path, width=3)
        browse_button.pack(side='right', padx=(5, 0))

        # Grid customisation
        ttk.Label(control_panel, text="Grid Rows").pack(anchor="w")
        ttk.Entry(control_panel, textvariable=self.grid_rows_var).pack(fill="x", pady=(0, 10))

        ttk.Label(control_panel, text="Grid Columns").pack(anchor="w")
        ttk.Entry(control_panel, textvariable=self.grid_cols_var).pack(fill="x", pady=(0, 10))

        ttk.Button(control_panel, text="Update Grid", command=self.update_grid).pack(pady=(10, 0), fill="x")

        # Paper Size Controls
        ttk.Separator(control_panel, orient='horizontal').pack(fill='x', pady=10)

        ttk.Label(control_panel, text="Paper Size").pack(anchor="w")
        self.paper_size_var = tk.StringVar(value='a4')
        paper_sizes = ['a4', 'a4_half_portrait', 'a0_portrait', 'a0_landscape', '16:9_monitor', 'custom']
        self.paper_size_combo = ttk.Combobox(control_panel, textvariable=self.paper_size_var, values=paper_sizes)
        self.paper_size_combo.pack(fill="x", pady=(0, 10))
        self.paper_size_combo.bind("<<ComboboxSelected>>", self._on_paper_size_change)

        # Frame for custom size entries
        self.custom_size_frame = ttk.Frame(control_panel)
        self.custom_size_frame.pack(fill='x')

        ttk.Label(self.custom_size_frame, text="Width (cm)").grid(row=0, column=0, sticky='w')
        self.custom_width_var = tk.DoubleVar(value=21.0)
        ttk.Entry(self.custom_size_frame, textvariable=self.custom_width_var).grid(row=0, column=1, padx=5)

        ttk.Label(self.custom_size_frame, text="Height (cm)").grid(row=1, column=0, sticky='w')
        self.custom_height_var = tk.DoubleVar(value=29.7)
        ttk.Entry(self.custom_size_frame, textvariable=self.custom_height_var).grid(row=1, column=1, padx=5)
        
        # Add a button to apply the new paper size
        self.update_paper_button = ttk.Button(control_panel, text="Update Paper Size", command=self.update_paper_size)
        self.update_paper_button.pack(pady=(10, 0), fill="x")


        # Right side: Control Panel : Style controls
        style_panel = ttk.LabelFrame(right_column_frame, text="Style", padding=10)
        style_panel.pack(fill="x")
        # style_panel.grid(row=1, column=1, sticky="n", padx=100, pady=50)

        # 1. Stylesheet Dropdown
        ttk.Label(style_panel, text="Stylesheet").pack(anchor="w")
        self.stylesheet_var = tk.StringVar(value="default")
        ttk.Combobox(style_panel, textvariable=self.stylesheet_var, values=["default", "modern",
                                                                            "nature-reviews", "economist"]).pack(
            fill="x", pady=(0, 10))

        # 2. Font Dropdown
        ttk.Label(style_panel, text="Font").pack(anchor="w")
        self.font_var = tk.StringVar(value="Helvetica")
        ttk.Combobox(style_panel, textvariable=self.font_var, values=["Helvetica", "Computer Modern Sans Serif", "Comic Sans MS"]).pack(
            fill="x", pady=(0, 10))

        # 3. Font Size (float entry)
        ttk.Label(style_panel, text="Font size").pack(anchor="w")
        self.font_size_var = tk.DoubleVar(value=11.0)
        ttk.Entry(style_panel, textvariable=self.font_size_var).pack(fill="x", pady=(0, 10))

        # 4. Tick mark font size
        ttk.Label(style_panel, text="Tick mark font size").pack(anchor="w")
        self.tick_font_size_var = tk.DoubleVar(value=9.0)
        ttk.Entry(style_panel, textvariable=self.tick_font_size_var).pack(fill="x")

        # 5. Capital or small letters
        self.use_capital_letters_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(style_panel, text="Use Capital Letters", variable=self.use_capital_letters_var,
                        command=self._update_panel_labels).pack(anchor="w", pady=(0, 10))

        ########################### MAKE THE PAPER PAGE ######################################
        self.panels = []  # set empty panels for now 
        # Create an empty rectangle first
        self.paper_rect = self.canvas.create_rectangle(0, 0, 0, 0, fill="white", outline="black", width=2)

        # Set the initial state and draw the paper
        self.update_paper_size()
        self._on_paper_size_change()

        """
        paper_width_px = cm_to_px(PAPER_WIDTH_CM, dpi)
        paper_height_px = cm_to_px(PAPER_HEIGHT_CM, dpi)

        # Offset to center the paper rectangle in the canvas
        offset_x = 50
        offset_y = 50
        self.paper_rect = self.canvas.create_rectangle(
            offset_x,
            offset_y,
            offset_x + paper_width_px,
            offset_y + paper_height_px,
            fill="white",
            outline="black",
            width=2
        )

        # Draw grid layout
        self.draw_grid((offset_x, offset_y, offset_x + paper_width_px, offset_y + paper_height_px),
                       self.grid_rows, self.grid_cols)
        """


    """
    def add_panel(self):
        label = chr(ord('A') + len(self.panels))  # A, B, C, ...
        panel = ResizablePanel(self.canvas, 50, 50, 200, 150, label=label)
        self.panels.append(panel)
    """

    """
    def add_panel(self):
        label = chr(ord('A') + len(self.panels))  # A, B, C, ...

        row, col = 0, 0
        rowspan, colspan = 2, 2  # Default size

        panel = GridPanel(
            self.canvas, self.paper_rect, self.grid_rows, self.grid_cols,
            row, col, rowspan, colspan, label=label
        )
        self.panels.append(panel)
    """

    def add_panel(self):

        # Determine the base character ('A' or 'a') from the checkbutton state
        if self.use_capital_letters_var.get():
            base_char = 'A'
        else:
            base_char = 'a'

        label = chr(ord(base_char) + len(self.panels))
        x0, y0, x1, y1 = self.canvas.coords(self.paper_rect)
        panel = ResizablePanel(self.canvas, x0 + 50, y0 + 50, 200, 150,
                               label=label,
                               grid_rows=self.grid_rows,
                               grid_cols=self.grid_cols,
                               paper_bbox=self.canvas.coords(self.paper_rect))
        self.panels.append(panel)

    def _update_panel_labels(self):
        """Updates the lettering case for all existing panels."""
        if self.use_capital_letters_var.get():
            base_char = 'A'
        else:
            base_char = 'a'

        for i, panel in enumerate(self.panels):
            new_label = chr(ord(base_char) + i)
            # Update the panel's internal text property
            panel.label_text = new_label
            # Update the text displayed on the canvas
            self.canvas.itemconfig(panel.label_id, text=new_label)

    def _bbox_to_grid_coords(self, bbox):
        paper_x0, paper_y0, paper_x1, paper_y1 = self.canvas.coords(self.paper_rect)
        paper_w = paper_x1 - paper_x0
        paper_h = paper_y1 - paper_y0
        grid_rows = self.grid_rows_var.get()
        grid_cols = self.grid_cols_var.get()

        x0, y0, x1, y1 = bbox
        col0 = int(round((x0 - paper_x0) / paper_w * grid_cols))
        row0 = int(round((y0 - paper_y0) / paper_h * grid_rows))
        col1 = int(round((x1 - paper_x0) / paper_w * grid_cols))
        row1 = int(round((y1 - paper_y0) / paper_h * grid_rows))

        return row0, col0, row1 - row0, col1 - col0

    def _grid_coords_to_bbox(self, row, col, rowspan, colspan):
        paper_x0, paper_y0, paper_x1, paper_y1 = self.canvas.coords(self.paper_rect)
        paper_w = paper_x1 - paper_x0
        paper_h = paper_y1 - paper_y0
        grid_rows = self.grid_rows_var.get()
        grid_cols = self.grid_cols_var.get()

        cell_w = paper_w / grid_cols
        cell_h = paper_h / grid_rows

        x0 = paper_x0 + col * cell_w
        y0 = paper_y0 + row * cell_h
        x1 = x0 + colspan * cell_w
        y1 = y0 + rowspan * cell_h

        return [x0, y0, x1, y1]

    def save_layout(self):
        """Gathers the current layout state and saves it to a JSON or YAML file."""
        filepath = filedialog.asksaveasfilename(
            title="Save Layout File",
            defaultextension=".yaml",
            filetypes=[("YAML Files", "*.yaml *.yml"), ("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        suffix = Path(filepath).suffix.lower()
        try:
            if suffix in ('.yaml', '.yml'):
                self._save_yaml(filepath)
            else:
                self._save_json(filepath)
            print(f"Layout saved successfully to {filepath}")
        except Exception as e:
            print(f"Error saving layout: {e}")

    def _save_json(self, filepath):
        layout_data = {
            'grid_settings': {
                'rows': self.grid_rows_var.get(),
                'cols': self.grid_cols_var.get()
            },
            'paper_settings': {
                'size_name': self.paper_size_var.get(),
                'custom_width_cm': self.custom_width_var.get(),
                'custom_height_cm': self.custom_height_var.get()
            },
            'panels': []
        }

        for panel in self.panels:
            panel_info = {
                'label': panel.label_text,
                'bbox': panel.get_bbox(),
                'filepath': getattr(panel, 'filepath', None)
            }
            layout_data['panels'].append(panel_info)

        with open(filepath, 'w') as f:
            json.dump(layout_data, f, indent=4)

    def _save_yaml(self, filepath):
        panels_data = []
        for panel in self.panels:
            row, col, rowspan, colspan = self._bbox_to_grid_coords(panel.get_bbox())
            panel_info = {
                'label': panel.label_text,
                'row': row,
                'col': col,
                'rowspan': rowspan,
                'colspan': colspan,
            }
            fp = getattr(panel, 'filepath', None)
            if fp:
                panel_info['file'] = fp
            panels_data.append(panel_info)

        layout_data = {
            'paper': {
                'size': self.paper_size_var.get(),
                'width_cm': float(self.custom_width_var.get()),
                'height_cm': float(self.custom_height_var.get()),
            },
            'grid': {
                'rows': self.grid_rows_var.get(),
                'cols': self.grid_cols_var.get(),
            },
            'style': {
                'stylesheet': self.stylesheet_var.get(),
                'font': self.font_var.get(),
                'font_size': float(self.font_size_var.get()),
                'tick_font_size': float(self.tick_font_size_var.get()),
            },
            'panels': panels_data,
        }

        with open(filepath, 'w') as f:
            yaml.dump(layout_data, f, default_flow_style=False, sort_keys=False)

    def load_layout(self):
        """Loads a layout state from a JSON or YAML file."""
        filepath = filedialog.askopenfilename(
            title="Open Layout File",
            filetypes=[("Layout Files", "*.yaml *.yml *.json"), ("YAML Files", "*.yaml *.yml"),
                       ("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        suffix = Path(filepath).suffix.lower()
        try:
            if suffix in ('.yaml', '.yml'):
                self._load_yaml(filepath)
            else:
                self._load_json(filepath)
            print(f"Layout loaded successfully from {filepath}")
        except Exception as e:
            print(f"Error loading layout: {e}")

    def _clear_panels(self):
        for panel in self.panels:
            self.canvas.delete(panel.rect)
            self.canvas.delete(panel.label_id)
            if panel.file_label_id:
                self.canvas.delete(panel.file_label_id)
        self.panels.clear()

    def _load_json(self, filepath):
        with open(filepath, 'r') as f:
            layout_data = json.load(f)

        self._clear_panels()

        self.grid_rows_var.set(layout_data['grid_settings']['rows'])
        self.grid_cols_var.set(layout_data['grid_settings']['cols'])
        self.paper_size_var.set(layout_data['paper_settings']['size_name'])
        self.custom_width_var.set(layout_data['paper_settings']['custom_width_cm'])
        self.custom_height_var.set(layout_data['paper_settings']['custom_height_cm'])
        self.update_paper_size()

        for panel_info in layout_data['panels']:
            bbox = panel_info['bbox']
            x0, y0, x1, y1 = bbox
            w, h = x1 - x0, y1 - y0

            panel = ResizablePanel(self.canvas, x0, y0, w, h,
                                   label=panel_info['label'],
                                   grid_rows=self.grid_rows,
                                   grid_cols=self.grid_cols,
                                   paper_bbox=self.canvas.coords(self.paper_rect))

            if panel_info.get('filepath'):
                panel.display_file_path(panel_info['filepath'])

            self.panels.append(panel)

    def _load_yaml(self, filepath):
        with open(filepath, 'r') as f:
            layout_data = yaml.safe_load(f)

        self._clear_panels()

        paper = layout_data.get('paper', {})
        grid = layout_data.get('grid', {})
        style = layout_data.get('style', {})

        self.grid_rows_var.set(grid.get('rows', 20))
        self.grid_cols_var.set(grid.get('cols', 10))
        self.paper_size_var.set(paper.get('size', 'a4'))
        self.custom_width_var.set(paper.get('width_cm', 21.0))
        self.custom_height_var.set(paper.get('height_cm', 29.7))
        self.update_paper_size()

        if style:
            self.stylesheet_var.set(style.get('stylesheet', 'default'))
            self.font_var.set(style.get('font', 'Helvetica'))
            self.font_size_var.set(style.get('font_size', 11.0))
            self.tick_font_size_var.set(style.get('tick_font_size', 9.0))

        for panel_info in layout_data.get('panels', []):
            row = panel_info.get('row', 0)
            col = panel_info.get('col', 0)
            rowspan = panel_info.get('rowspan', 2)
            colspan = panel_info.get('colspan', 2)

            bbox = self._grid_coords_to_bbox(row, col, rowspan, colspan)
            x0, y0, x1, y1 = bbox
            w, h = x1 - x0, y1 - y0

            label = panel_info.get('label', chr(ord('A') + len(self.panels)))
            panel = ResizablePanel(self.canvas, x0, y0, w, h,
                                   label=label,
                                   grid_rows=self.grid_rows,
                                   grid_cols=self.grid_cols,
                                   paper_bbox=self.canvas.coords(self.paper_rect))

            fp = panel_info.get('file')
            if fp:
                panel.display_file_path(fp)

            self.panels.append(panel)


    def _browse_save_path(self):
        """Opens a file dialog to choose a save location and base filename."""
        initial_path = Path(self.save_path_var.get())

        filepath = filedialog.asksaveasfilename(
            initialdir=initial_path.parent,
            initialfile=initial_path.stem,
            title="Choose save location and base filename",
            filetypes=[("PDF file", "*.pdf"), ("SVG file", "*.svg"), ("All files", "*.*")]
        )

        if filepath:
            # We strip any extension the user provides, as we'll be adding .pdf and .svg ourselves
            p = Path(filepath)
            self.save_path_var.set(str(p.with_suffix('')))

    def draw_grid(self, paper_coords, nrows, ncols):
        x0, y0, x1, y1 = paper_coords
        paper_width = x1 - x0
        paper_height = y1 - y0

        col_width = paper_width / ncols
        row_height = paper_height / nrows

        # Draw vertical lines
        for i in range(1, ncols):
            x = x0 + i * col_width
            self.canvas.create_line(x, y0, x, y1, fill="lightgray", dash=(2, 2), tags="grid")

        # Draw horizontal lines
        for j in range(1, nrows):
            y = y0 + j * row_height
            self.canvas.create_line(x0, y, x1, y, fill="lightgray", dash=(2, 2), tags="grid")

    def update_grid(self):
        try:
            rows = self.grid_rows_var.get()
            cols = self.grid_cols_var.get()

            if rows < 1 or cols < 1:
                raise ValueError

            self.grid_rows = rows
            self.grid_cols = cols

            # Clear previous grid lines
            self.canvas.delete("grid")

            # Redraw grid on paper rectangle
            self.draw_grid(self.canvas.coords(self.paper_rect), self.grid_rows, self.grid_cols)

            # Optionally: update existing panels to snap to the new grid
            for panel in self.panels:
                 # 1. Update the panel's internal knowledge of the grid
                panel.nrows = self.grid_rows
                panel.ncols = self.grid_cols
                panel.paper_bbox = self.canvas.coords(self.paper_rect)

                # 2. Get current position and calculate the new snapped position
                x0, y0, x1, y1 = panel.get_bbox()
                nx0, ny0 = panel.snap_to_grid(x0, y0)
                nx1, ny1 = panel.snap_to_grid(x1, y1)

                # 3. Move the existing panel items to the new snapped coordinates
                panel.canvas.coords(panel.rect, nx0, ny0, nx1, ny1)
                panel.canvas.coords(panel.label_id, nx0 + 6, ny0 + 6)
                if panel.file_label_id:
                    cx = (nx0 + nx1) / 2
                    cy = (ny0 + ny1) / 2
                    panel.canvas.coords(panel.file_label_id, cx, cy)
                
                # panel.canvas.delete(panel.rect)
                # panel.canvas.delete(panel.label_id)
                # panel.rect, panel.label_id = panel._draw_panel()
                # panel._bind_events()

        except Exception as e:
            print("Invalid grid dimensions:", e)
    
    def _on_paper_size_change(self, event=None):
        """Enables or disables the custom size entry fields based on dropdown selection."""
        if self.paper_size_var.get() == 'custom':
            for child in self.custom_size_frame.winfo_children():
                child.configure(state='normal')
        else:
            for child in self.custom_size_frame.winfo_children():
                child.configure(state='disabled')

    def update_paper_size(self):
        """Resizes the paper rectangle on the canvas based on the selected size."""
        selection = self.paper_size_var.get()

        if selection == 'custom':
            paper_width_cm = self.custom_width_var.get()
            paper_height_cm = self.custom_height_var.get()
        else:
            paper_width_cm, paper_height_cm = PAPER_DIMENSIONS[selection]
            self.custom_width_var.set(paper_width_cm)
            self.custom_height_var.set(paper_height_cm)
        
        # Store the true dimensions for the final figure export
        self.paper_width_cm = paper_width_cm
        self.paper_height_cm = paper_height_cm

        # --- SCALING LOGIC ---
        # 1. Calculate the paper's true pixel size
        true_width_px = cm_to_px(self.paper_width_cm, self.dpi)
        true_height_px = cm_to_px(self.paper_height_cm, self.dpi)

        # 2. Define the available drawing area on the canvas
        offset_x = 50
        offset_y = 50
        canvas_area_w = self.canvas.winfo_width() - (2 * offset_x)
        canvas_area_h = self.canvas.winfo_height() - (2 * offset_y)
        
        if canvas_area_w <= 1: # Fallback if canvas not drawn yet
            canvas_area_w = 800 - (2 * offset_x)
            canvas_area_h = 1300 - (2 * offset_y)
        
        # 3. Calculate the scale factor to fit the paper in the area
        scale = 1.0
        if true_width_px > canvas_area_w or true_height_px > canvas_area_h:
            scale_w = canvas_area_w / true_width_px
            scale_h = canvas_area_h / true_height_px
            scale = min(scale_w, scale_h)

        # 4. Calculate the scaled display size
        display_width_px = true_width_px * scale
        display_height_px = true_height_px * scale
        
        # 5. Resize the paper rectangle on the canvas using the display size
        self.canvas.coords(
            self.paper_rect,
            offset_x,
            offset_y,
            offset_x + display_width_px,
            offset_y + display_height_px
        )

        # Update the grid to match the new size
        self.update_grid()
        
        # Also update the paper_bbox for all existing panels
        for panel in self.panels:
            panel.paper_bbox = self.canvas.coords(self.paper_rect)


    def make_figures(self):

        # Use the stored true dimensions (in inches) for the final figure, not the canvas preview size.
        fig_width_in = self.paper_width_cm / 2.54
        fig_height_in = self.paper_height_cm / 2.54

        output_dpi = 300

        style_name = self.stylesheet_var.get()
        selected_font = self.font_var.get()  # Get the font from the dropdown
        rc_params = {
            'pdf.fonttype': 42,
            'font.family': selected_font
        }

        with plt.style.context(splstyle.get_style(style_name)):
            with plt.rc_context(rc=rc_params):
                fig = plt.figure(figsize=(fig_width_in, fig_height_in), dpi=output_dpi)

                # Use GridSpec for layout
                from matplotlib.gridspec import GridSpec

                grid_rows = self.grid_rows_var.get()
                grid_cols = self.grid_cols_var.get()
                gs = GridSpec(grid_rows, grid_cols, figure=fig)

                # Get paper bounding box
                paper_x0, paper_y0, paper_x1, paper_y1 = self.canvas.coords(self.paper_rect)
                paper_w = paper_x1 - paper_x0
                paper_h = paper_y1 - paper_y0

                for panel in self.panels:
                    x0, y0, x1, y1 = panel.get_bbox()
                    rel_x0 = (x0 - paper_x0) / paper_w
                    rel_y0 = (y0 - paper_y0) / paper_h
                    rel_x1 = (x1 - paper_x0) / paper_w
                    rel_y1 = (y1 - paper_y0) / paper_h

                    # Convert relative coords into grid rows/cols
                    col0 = int(round(rel_x0 * grid_cols))
                    row0 = int(round(rel_y0 * grid_rows))
                    col1 = int(round(rel_x1 * grid_cols))
                    row1 = int(round(rel_y1 * grid_rows))

                    # Clamp to bounds
                    col0, col1 = sorted([max(0, min(col0, grid_cols - 1)), max(0, min(col1, grid_cols))])
                    row0, row1 = sorted([max(0, min(row0, grid_rows - 1)), max(0, min(row1, grid_rows))])

                    if col0 == col1:
                        col1 += 1
                    if row0 == row1:
                        row1 += 1

                    subfig_ax = fig.add_subplot(gs[row0:row1, col0:col1])

                    # Add sub figure lettering
                    subfig_ax.text(-0.1, 1.05, panel.label_text, transform=subfig_ax.transAxes,
                                   fontsize=14, fontweight='bold', va='bottom', ha='right')

                    subfig_ax.set_xticks([])
                    subfig_ax.set_yticks([])

                    filepath = getattr(panel, "filepath", None)
                    if filepath:
                        load_panel_content(subfig_ax, filepath, fig)
                    else:
                        subfig_ax.set_facecolor("#f0f0f0")
                        subfig_ax.text(0.5, 0.5, "Empty", ha="center", va="center")

                fig.suptitle("Composed Layout", fontsize=14)
                fig.tight_layout()
                # fig.show()

                # --- SAVE THE FIGURE ---
                save_path_str = self.save_path_var.get()
                if save_path_str:
                    try:
                        p = Path(save_path_str)
                        # Ensure the parent directory exists
                        p.parent.mkdir(parents=True, exist_ok=True)

                        # Define paths for both file types
                        pdf_path = p.with_suffix('.pdf')
                        svg_path = p.with_suffix('.svg')

                        # Save as PDF and SVG
                        fig.savefig(pdf_path)
                        fig.savefig(svg_path, transparent=True)

                        print(f"Figure saved successfully to:\n  {pdf_path}\n  {svg_path}")

                    except Exception as e:
                        print(f"Error saving figure: {e}")

app = typer.Typer()


@app.command()
def make_layout(paper_size='a4', dpi: int = 96):

    if paper_size == 'a4':
        PAPER_WIDTH_CM = 21
        PAPER_HEIGHT_CM = 29.7

    # style = Style(theme='lumen')
    # ctk.set_appearance_mode("System")
    figureApp = FigureLayoutApp(PAPER_WIDTH_CM, PAPER_HEIGHT_CM, dpi)
    figureApp.mainloop()

@app.command()
def make_example_figures(save_folder=None):

    # Example figure 1 : scatter plot
    fig, ax = plt.subplots()
    x_vals = np.random.normal(0, 2, 100)
    y_vals = np.random.normal(0, 1, 100)

    ax.scatter(x_vals, y_vals)

    save_name = 'example_scatter.pkl'
    if save_folder is not None:
        save_path = os.path.join(save_folder, save_name)
    else:
        save_path = save_name

    with open(save_path, 'wb') as f:  # should be 'wb' rather than 'w'
        pickle.dump(fig, f)

    # also save as png
    fig.savefig(save_path[0:-4])

    # Example figure 2 : imshow
    fig, ax = plt.subplots()
    with cbook.get_sample_data('grace_hopper.jpg') as image_file:
        image = plt.imread(image_file)

    ax.imshow(image)
    ax.set_xticks([])
    ax.set_yticks([])

    save_name = 'example_image.pkl'
    if save_folder is not None:
        save_path = os.path.join(save_folder, save_name)
    else:
        save_path = save_name

    with open(save_path, 'wb') as f:  # should be 'wb' rather than 'w'
        pickle.dump(fig, f)

    # also save as png
    fig.savefig(save_path[0:-4])

    # Example figure 3: subplots of two things
    fig, axs = plt.subplots(1, 2)

    # bar plot
    fruits = ['apple', 'blueberry', 'cherry', 'orange']
    counts = [40, 100, 30, 55]
    bar_labels = ['red', 'blue', '_red', 'orange']
    bar_colors = ['tab:red', 'tab:blue', 'tab:red', 'tab:orange']

    axs[0].bar(fruits, counts, label=bar_labels, color=bar_colors)

    # line plot
    x = np.linspace(0, 10, 1000)
    axs[1].plot(x, np.sin(x))

    save_name = 'example_subplots.pkl'
    if save_folder is not None:
        save_path = os.path.join(save_folder, save_name)
    else:
        save_path = save_name

    with open(save_path, 'wb') as f:  # should be 'wb' rather than 'w'
        pickle.dump(fig, f)

    # also save as png
    fig.savefig(save_path[0:-4])


@app.command()
def render(layout_file: str, output: str = None, dpi: int = 300):
    """Render a layout file (YAML or JSON) directly to PDF/SVG without the GUI."""
    parsed = parse_layout_file(layout_file)

    fig_w_in = parsed['paper_w_cm'] / 2.54
    fig_h_in = parsed['paper_h_cm'] / 2.54

    if output is None:
        output = str(Path(layout_file).with_suffix(''))
    output = str(Path(output).with_suffix(''))

    style_info = parsed['style']
    style_name = style_info.get('stylesheet', 'default')
    selected_font = style_info.get('font', 'Helvetica')
    font_size = style_info.get('font_size', 11.0)

    rc_params = {
        'pdf.fonttype': 42,
        'font.family': selected_font,
        'font.size': font_size,
    }

    with plt.style.context(splstyle.get_style(style_name)):
        with plt.rc_context(rc=rc_params):
            fig = plt.figure(figsize=(fig_w_in, fig_h_in), dpi=dpi)
            render_panels_to_figure(parsed['panels'], parsed['grid_rows'],
                                     parsed['grid_cols'], fig)
            fig.tight_layout()

            p = Path(output)
            p.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(p.with_suffix('.pdf'))
            fig.savefig(p.with_suffix('.svg'), transparent=True)
            print(f"Figure rendered to:\n  {p.with_suffix('.pdf')}\n  {p.with_suffix('.svg')}")


class GridPanel:
    def __init__(self, canvas, paper_rect_id, nrows, ncols, row, col, rowspan, colspan, label="A"):
        self.canvas = canvas
        self.nrows = nrows
        self.ncols = ncols
        self.row = row
        self.col = col
        self.rowspan = rowspan
        self.colspan = colspan
        self.label = label
        self.filepath = None

        # Convert to pixel coordinates
        self.paper_bbox = self.canvas.coords(paper_rect_id)
        self.rect, self.label_id = self._draw_panel()

        # Draffing of the grid panel
        self.canvas.tag_bind(self.rect, "<ButtonPress-1>", self.on_press)
        self.canvas.tag_bind(self.rect, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.label_id, "<ButtonPress-1>", self.on_press)
        self.canvas.tag_bind(self.label_id, "<B1-Motion>", self.on_drag)
        self.drag_data = {"x": 0, "y": 0}

        self.canvas.tag_bind(self.rect, "<ButtonRelease-1>", self.on_release)
        self.canvas.tag_bind(self.label_id, "<ButtonRelease-1>", self.on_release)

    def _draw_panel(self):
        x0, y0, x1, y1 = self.paper_bbox
        w = (x1 - x0) / self.ncols
        h = (y1 - y0) / self.nrows

        px0 = x0 + self.col * w
        py0 = y0 + self.row * h
        px1 = px0 + self.colspan * w
        py1 = py0 + self.rowspan * h

        rect_id = self.canvas.create_rectangle(px0, py0, px1, py1, fill="lightgray")
        label_id = self.canvas.create_text(px0 + 6, py0 + 6, anchor="nw", text=self.label, font=("Helvetica", 12, "bold"))
        return rect_id, label_id

    def get_gridspec_slice(self):
        return slice(self.row, self.row + self.rowspan), slice(self.col, self.col + self.colspan)

    def on_press(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_drag(self, event):
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]

        # Move rectangle visually
        self.canvas.move(self.rect, dx, dy)
        self.canvas.move(self.label_id, dx, dy)

        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_release(self, event):
        # Snap to grid
        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        grid_x0, grid_y0, _, _ = self.paper_bbox
        w = (self.paper_bbox[2] - grid_x0) / self.ncols
        h = (self.paper_bbox[3] - grid_y0) / self.nrows

        # New grid coordinates (from snapped top-left)
        col = int((x0 - grid_x0 + w / 2) // w)
        row = int((y0 - grid_y0 + h / 2) // h)

        # Keep within bounds
        col = max(0, min(self.ncols - self.colspan, col))
        row = max(0, min(self.nrows - self.rowspan, row))

        self.row = row
        self.col = col

        # Redraw panel
        self.canvas.delete(self.rect)
        self.canvas.delete(self.label_id)
        self.rect, self.label_id = self._draw_panel()
        self._bind_events()

    def _bind_events(self):
        self.canvas.tag_bind(self.rect, "<ButtonPress-1>", self.on_press)
        self.canvas.tag_bind(self.rect, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.rect, "<ButtonRelease-1>", self.on_release)

        self.canvas.tag_bind(self.label_id, "<ButtonPress-1>", self.on_press)
        self.canvas.tag_bind(self.label_id, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.label_id, "<ButtonRelease-1>", self.on_release)


@app.command()
def main():

    logger.info('Running layout')

    # TODO: ask the user which process to run : make_layout


if __name__ == "__main__":
    app()