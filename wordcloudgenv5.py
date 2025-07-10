import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from ttkthemes import ThemedTk
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import threading
import json
import os

# --- Custom Rounded Button Widget ---
class RoundedButton(tk.Canvas):
    """A custom rounded button widget that is theme-aware and can be disabled."""
    def __init__(self, parent, text, command, **kwargs):
        self.radius = kwargs.pop("radius", 10)
        padding = kwargs.pop("padding", 10)
        font = kwargs.pop("font", ("Segoe UI", 11, "bold"))
        
        temp_label = tk.Label(parent, text=text, font=font, padx=padding, pady=padding)
        width = temp_label.winfo_reqwidth()
        height = temp_label.winfo_reqheight()
        temp_label.destroy()

        super().__init__(parent, width=width, height=height, borderwidth=0, highlightthickness=0, **kwargs)

        self.command = command
        self.text = text
        self.font = font
        self.disabled = False
        
        self.fg = "white"
        self.bg_color = "#4CAF50"
        self.hover_color = "#5a9a5d"
        self.pressed_color = "#3e8e41"
        self.disabled_color = "#a0a0a0"

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def draw(self, color=None):
        if self.winfo_width() <= 1 or self.winfo_height() <= 1:
            self.after(10, self.draw)
            return

        self.delete("all")
        
        current_color = self.bg_color
        if self.disabled:
            current_color = self.disabled_color
        elif color:
            current_color = color
        
        x1, y1, x2, y2 = 0, 0, self.winfo_width(), self.winfo_height()
        r = self.radius

        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]

        self.create_polygon(points, fill=current_color, smooth=True)
        self.create_text(x2 / 2, y2 / 2, text=self.text, font=self.font, fill=self.fg)

    def _on_enter(self, event):
        if not self.disabled: self.draw(self.hover_color)
    def _on_leave(self, event):
        if not self.disabled: self.draw()
    def _on_press(self, event):
        if not self.disabled: self.draw(self.pressed_color)
    def _on_release(self, event):
        if not self.disabled:
            self.draw(self.hover_color)
            if self.command: self.command()
            
    def configure_colors(self, fg, bg, hover, pressed, disabled, parent_bg):
        self.fg, self.bg_color, self.hover_color, self.pressed_color, self.disabled_color = fg, bg, hover, pressed, disabled
        self.config(bg=parent_bg)
        self.draw()

    def disable(self):
        self.disabled = True
        self.draw()
    def enable(self):
        self.disabled = False
        self.draw()

class WordCloudApp(ThemedTk):
    """A modern GUI application for generating word clouds."""
    def __init__(self):
        super().__init__()
        self.title("Word Cloud Generator")
        self.geometry("650x700")

        self.settings_path = os.path.join(os.path.expanduser("~"), ".wordcloud_app_settings.json")
        settings = self._load_settings()

        self.update_idletasks()
        x_coordinate = int((self.winfo_screenwidth() / 2) - (self.winfo_width() / 2))
        y_coordinate = int((self.winfo_screenheight() / 2) - (self.winfo_height() / 2))
        self.geometry(f"+{x_coordinate}+{y_coordinate}")

        self.set_theme("arc")
        self.font_style = ("Segoe UI", 10)
        self.font_style_bold = ("Segoe UI", 11, "bold")
        
        self.light_theme = {
            "bg": "#f0f0f0", "fg": "#000000", "text_bg": "#ffffff", "text_fg": "#000000", "status_bg": "#e0e0e0",
            "button_fg": "#ffffff", "button_bg": "#4CAF50", "button_hover": "#5cb85c", "button_pressed": "#3e8e41", "button_disabled": "#d0d0d0"
        }
        self.dark_theme = {
            "bg": "#2e2e2e", "fg": "#d0d0d0", "text_bg": "#3c3c3c", "text_fg": "#d0d0d0", "status_bg": "#3c3c3c",
            "button_fg": "#ffffff", "button_bg": "#4f4f4f", "button_hover": "#6a6a6a", "button_pressed": "#2c2c2c", "button_disabled": "#202020"
        }
        
        self.input_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        
        self.default_exclusion_words = [
            "author", "post", "content", "reddit", "score", "url", "subreddit", "title", "Steam", "Comment", "https", "Comments", "u", "account",
            "comments", "csgomarketforum", "SteamScams", "scam", "trade", "support", "png","game","csgo", "redd", "got", "skin","item","S",
            "will","items","one","someone","know","scammed","guy","people"
        ]
        
        self.initial_exclusion_list = settings.get("exclusion_list", "\n".join(self.default_exclusion_words))
        is_dark_mode = settings.get("dark_mode", False)
        self.active_theme = self.dark_theme if is_dark_mode else self.light_theme

        self.create_widgets()

        if is_dark_mode:
            self.dark_mode_switch.invoke()
        else:
            self.apply_theme()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def create_widgets(self):
        self.main_frame = ttk.Frame(self, padding="15 15 15 15")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20), anchor="n")
        self.header_label = ttk.Label(header_frame, text="Word Cloud Generator", font=("Segoe UI", 16, "bold"))
        self.header_label.pack(side=tk.LEFT)
        self.dark_mode_switch = ttk.Checkbutton(header_frame, text="Dark Mode", style="Switch.TCheckbutton", command=self.toggle_theme)
        self.dark_mode_switch.pack(side=tk.RIGHT)

        self.file_container = tk.Frame(self.main_frame)
        self.file_container.pack(fill=tk.X, pady=(0, 10))
        self.file_title_label = tk.Label(self.file_container, text="1. Select Files", anchor='w', font=self.font_style)
        self.file_title_label.pack(fill=tk.X, pady=(0, 2))
        
        self.file_border = tk.Frame(self.file_container)
        self.file_border.pack(fill=tk.BOTH, expand=True)
        
        self.file_content_frame = tk.Frame(self.file_border)
        self.file_content_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        self.input_button = RoundedButton(self.file_content_frame, text="Select Input .txt File", command=self.select_input_file, font=self.font_style_bold)
        self.input_button.pack(pady=5)
        self.input_path_label = ttk.Label(self.file_content_frame, text="No input file selected.", style="Muted.TLabel", wraplength=550)
        self.input_path_label.pack(fill=tk.X, pady=(0, 5))

        self.output_button = RoundedButton(self.file_content_frame, text="Set Output Image Path", command=self.set_output_file, font=self.font_style_bold)
        self.output_button.pack(pady=5)
        self.output_path_label = ttk.Label(self.file_content_frame, text="No output path set.", style="Muted.TLabel", wraplength=550)
        self.output_path_label.pack(fill=tk.X)

        self.exclusion_container = tk.Frame(self.main_frame)
        self.exclusion_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.exclusion_header_frame = tk.Frame(self.exclusion_container)
        self.exclusion_header_frame.pack(fill=tk.X, pady=(0, 2))

        self.exclusion_title_label = tk.Label(self.exclusion_header_frame, text="2. Edit Exclusion List (one per line)", anchor='w', font=self.font_style)
        self.exclusion_title_label.pack(side=tk.LEFT)
        
        # --- NEW: Frame to hold the new buttons ---
        self.exclusion_button_frame = tk.Frame(self.exclusion_header_frame)
        self.exclusion_button_frame.pack(side=tk.RIGHT)

        self.import_button = RoundedButton(self.exclusion_button_frame, text="Import", command=self.import_exclusion_list, font=self.font_style, padding=5, radius=5)
        self.import_button.pack(side=tk.LEFT, padx=(0, 5))

        # --- NEW: "Clear List" button ---
        self.clear_button = RoundedButton(self.exclusion_button_frame, text="Clear", command=self.clear_exclusion_list, font=self.font_style, padding=5, radius=5)
        self.clear_button.pack(side=tk.LEFT)

        self.exclusion_border = tk.Frame(self.exclusion_container)
        self.exclusion_border.pack(fill=tk.BOTH, expand=True)

        self.exclusion_text = scrolledtext.ScrolledText(self.exclusion_border, wrap=tk.WORD, height=10, width=50, relief=tk.FLAT, font=self.font_style, borderwidth=0, highlightthickness=0)
        self.exclusion_text.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.exclusion_text.insert(tk.INSERT, self.initial_exclusion_list)

        self.generate_button = RoundedButton(self.main_frame, text="3. Generate Word Cloud", command=self.start_generation_thread, font=self.font_style_bold)
        self.generate_button.pack(pady=10)
        self.generate_button.disable()
        
        self.status_label = ttk.Label(self, text="Ready", relief=tk.SUNKEN, anchor='w', padding=5)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM)

    def toggle_theme(self):
        self.active_theme = self.dark_theme if self.dark_mode_switch.instate(['selected']) else self.light_theme
        self.apply_theme()

    def apply_theme(self):
        theme = self.active_theme
        self.configure(bg=theme["bg"])
        
        style = ttk.Style()
        style.configure(".", background=theme["bg"], foreground=theme["fg"], font=self.font_style)
        style.configure("TFrame", background=theme["bg"])
        style.configure("Muted.TLabel", foreground="#888" if theme == self.light_theme else "#9e9e9e", background=theme["text_bg"])
        self.header_label.configure(style="TLabel")
        
        style.map("Switch.TCheckbutton",
            background=[('active', theme["bg"])],
            foreground=[('!disabled', theme["fg"])]
        )

        self.file_container.configure(bg=theme["bg"])
        self.file_title_label.configure(bg=theme["bg"], fg=theme["fg"])
        self.file_border.configure(bg=theme["fg"])
        self.file_content_frame.configure(bg=theme["text_bg"])

        self.exclusion_container.configure(bg=theme["bg"])
        self.exclusion_header_frame.configure(bg=theme["bg"])
        self.exclusion_title_label.configure(bg=theme["bg"], fg=theme["fg"])
        self.exclusion_border.configure(bg=theme["fg"])
        self.exclusion_button_frame.configure(bg=theme["bg"]) # Configure new frame
        self.exclusion_text.configure(
            background=theme["text_bg"], foreground=theme["text_fg"],
            insertbackground=theme["fg"], selectbackground=theme["button_bg"]
        )
        self.status_label.configure(background=theme["status_bg"], foreground=theme["fg"])

        for btn, parent_bg_key in [(self.input_button, "text_bg"), 
                                  (self.output_button, "text_bg"), 
                                  (self.generate_button, "bg"),
                                  (self.import_button, "bg"),
                                  (self.clear_button, "bg")]: # Add new button to theme logic
            btn.configure_colors(fg=theme["button_fg"], bg=theme["button_bg"], hover=theme["button_hover"], 
                                 pressed=theme["button_pressed"], disabled=theme["button_disabled"], parent_bg=theme[parent_bg_key])

    def _update_generate_button_state(self):
        if self.input_file_path.get() and self.output_file_path.get():
            self.generate_button.enable()
        else:
            self.generate_button.disable()

    def select_input_file(self):
        path = filedialog.askopenfilename(title="Select input .txt file", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        if path:
            self.input_file_path.set(path)
            self.input_path_label.config(text=f"Input: {path}")
            self._update_generate_button_state()

    def set_output_file(self):
        path = filedialog.asksaveasfilename(title="Save Word Cloud As...", defaultextension=".png", filetypes=(("PNG Image", "*.png"), ("All files", "*.*")))
        if path:
            self.output_file_path.set(path)
            self.output_path_label.config(text=f"Output: {path}")
            self._update_generate_button_state()

    def import_exclusion_list(self):
        path = filedialog.askopenfilename(title="Select exclusion list .txt file", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        if not path:
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as file:
                new_words = file.read()
            
            current_text = self.exclusion_text.get("1.0", tk.END).strip()
            if current_text:
                self.exclusion_text.insert(tk.END, f"\n{new_words}")
            else:
                self.exclusion_text.insert(tk.END, new_words)
            
            messagebox.showinfo("Success", "Exclusion list imported successfully.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to import file: {e}")

    # --- NEW: Method to clear the exclusion list ---
    def clear_exclusion_list(self):
        """Clears all text from the exclusion list text box."""
        self.exclusion_text.delete("1.0", tk.END)

    def _load_settings(self):
        try:
            with open(self.settings_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_settings(self):
        settings = {
            "dark_mode": self.dark_mode_switch.instate(['selected']),
            "exclusion_list": self.exclusion_text.get("1.0", tk.END).strip()
        }
        with open(self.settings_path, 'w') as f:
            json.dump(settings, f, indent=4)

    def _on_closing(self):
        self._save_settings()
        self.destroy()

    def start_generation_thread(self):
        self.status_label.config(text="Status: Processing...")
        self.generate_button.disable()
        thread = threading.Thread(target=self._threaded_generate, daemon=True)
        thread.start()

    def _threaded_generate(self):
        try:
            output_path = self.generate_word_cloud()
            result = {"status": "success", "path": output_path}
        except Exception as e:
            result = {"status": "error", "message": str(e)}
        self.after(0, self.on_generation_complete, result)

    def on_generation_complete(self, result):
        if result["status"] == "success":
            self.status_label.config(text=f"Status: Success! Saved to {result['path']}")
            messagebox.showinfo("Success", f"Word cloud saved successfully to:\n{result['path']}")
        else:
            self.status_label.config(text=f"Status: Error - {result['message']}")
            messagebox.showerror("Error", f"An unexpected error occurred: {result['message']}")
        self._update_generate_button_state()

    def generate_word_cloud(self):
        input_path = self.input_file_path.get()
        output_path = self.output_file_path.get()
        
        with open(input_path, 'r', encoding='utf-8') as file:
            text = file.read()

        custom_exclusion_list = [word.strip().lower() for word in self.exclusion_text.get("1.0", tk.END).split("\n") if word.strip()]
        
        stopwords = set(STOPWORDS)
        stopwords.update(custom_exclusion_list)

        wordcloud = WordCloud(stopwords=stopwords, background_color="white", width=1600, height=800, max_words=200, collocations=False).generate(text)

        fig = plt.figure(figsize=(20, 10))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis("off")
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        return output_path

if __name__ == "__main__":
    app = WordCloudApp()
    app.mainloop()
