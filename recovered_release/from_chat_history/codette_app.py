"""
Recovered from a ChatGPT history export (history_2025-*.json) in the archives.
The source existed only inside the conversation transcript, never as a file.
"""

import tkinter as tk
from tkinter import messagebox

class CodetteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Codette Chatbot")

        self.input_field = tk.Entry(self)
        self.input_field.pack(fill='x', padx=5, pady=5)
        self.input_field.bind('<Return>', lambda event: self.handle_ask())

        self.ask_button = tk.Button(self, text="Ask", command=self.handle_ask)
        self.ask_button.pack(side='top', padx=5, pady=5)

        self.clear_button = tk.Button(self, text="Clear", command=self.clear_all)
        self.clear_button.pack(side='top', padx=5, pady=5)
        
        self.output_box = tk.Text(self, height=20, width=70, state='normal')
        self.output_box.pack(fill='both', expand=True, padx=5, pady=5)

        self.scrollbar = tk.Scrollbar(self, command=self.output_box.yview)
        self.output_box.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side='right', fill='y')

    def handle_ask(self):
        user_query = self.input_field.get().strip()
        if not user_query:
            messagebox.showwarning("Input Required", "Please enter your question.")
            return
        
        # TEMP: Dummy response until we connect to AI backend logic.
        codette_reply = f"[Pretend answer] You asked: '{user_query}'"
        
        self.output_box.insert(tk.END, f"User: {user_query}\nCodette: {codette_reply}\n\n")
        self.out_box_yview_bottom()
        self.input_field.delete(0, tk.END)  # Clear input after asking

    def out_box_yview_bottom(self):
        ''' Scroll output box to bottom '''
        self.output_box.yview_moveto(1.0)

    def clear_all(self):
        self.input_field.delete(0, tk.END)
        self.output_box.delete('1.0', tk.END)

if __name__ == "__main__":
    app = CodetteApp()
    app.mainloop()
