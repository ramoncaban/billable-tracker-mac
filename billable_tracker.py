import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
from datetime import datetime
import json
import os
import sys
from pathlib import Path
import csv

def get_data_file():
    if getattr(sys, 'frozen', False):
        data_dir = Path.home() / ".billable_tracker"
        data_dir.mkdir(exist_ok=True)
        return str(data_dir / "billable_tracker_data.json")
    else:
        return "billable_tracker_data.json"

class TimeTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Billable Hours Tracker")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.current_client = None
        self.timer_running = False
        self.start_time = None
        self.after_id = None

        self.data_file = get_data_file()
        self.sessions = {}

        self.setup_ui()
        self.load_sessions()

    def setup_ui(self):
        bg_color = "#2B2B2B"
        fg_color = "white"

        self.left_frame = tk.Frame(self.root)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.client_listbox = tk.Listbox(self.left_frame, height=15, width=20)
        self.client_listbox.pack()
        self.client_listbox.bind("<<ListboxSelect>>", self.on_client_select)

        self.add_client_button = tk.Button(self.left_frame, text="Add Client", command=self.add_client)
        self.add_client_button.pack(pady=5)

        self.remove_client_button = tk.Button(self.left_frame, text="Remove Client", command=self.remove_client)
        self.remove_client_button.pack(pady=5)

        self.reset_history_button = tk.Button(self.left_frame, text="Reset History", command=self.reset_history)
        self.reset_history_button.pack(pady=5)

        self.right_frame = tk.Frame(self.root)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.client_label = tk.Label(self.right_frame, text="No client selected", font=("Helvetica", 14))
        self.client_label.pack(pady=(0, 10))

        self.timer_label = tk.Label(self.right_frame, text="00:00:00", font=("Helvetica", 24))
        self.timer_label.pack(pady=10)

        self.start_stop_button = tk.Button(self.right_frame, text="Start", width=10, command=self.toggle_timer)
        self.start_stop_button.pack(pady=5)

        self.history_label = tk.Label(self.right_frame, text="Session History:", font=("Helvetica", 12))
        self.history_label.pack(pady=(20, 0))

        self.history_text = tk.Text(self.right_frame, height=10, width=50)
        self.history_text.pack(pady=(5, 0))

        self.save_button = tk.Button(self.right_frame, text="Save History to File", command=self.save_history_manual)
        self.save_button.pack(pady=5)

        self.export_all_button = tk.Button(self.right_frame, text="Export All Clients to CSV", command=self.export_all_to_csv)
        self.export_all_button.pack(pady=5)

        self.root.configure(bg=bg_color)
        self.left_frame.configure(bg=bg_color)
        self.right_frame.configure(bg=bg_color)
        self.client_listbox.configure(bg=bg_color, fg=fg_color, selectbackground="#555555", selectforeground="white")
        self.client_label.configure(bg=bg_color, fg=fg_color)
        self.timer_label.configure(bg=bg_color, fg=fg_color)
        self.history_label.configure(bg=bg_color, fg=fg_color)
        self.history_text.configure(bg=bg_color, fg=fg_color, insertbackground=fg_color)

        for btn in [self.add_client_button, self.remove_client_button, self.reset_history_button,
                    self.start_stop_button, self.save_button, self.export_all_button]:
            btn.configure(bg="white", fg="black", activebackground="#DDDDDD", activeforeground="black")

    def load_sessions(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r") as f:
                    self.sessions = json.load(f)
                for client in self.sessions.keys():
                    self.client_listbox.insert(tk.END, client)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load session data: {e}")
                self.sessions = {}
        else:
            self.sessions = {}

    def save_sessions(self):
        try:
            with open(self.data_file, "w") as f:
                json.dump(self.sessions, f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save session data: {e}")

    def add_client(self):
        client_name = simpledialog.askstring("Add Client", "Enter client name:")
        if client_name:
            if client_name in self.sessions:
                messagebox.showerror("Error", "Client already exists!")
            else:
                self.sessions[client_name] = []
                self.client_listbox.insert(tk.END, client_name)
                self.save_sessions()

    def remove_client(self):
        selection = self.client_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a client to remove.")
            return

        client_to_remove = self.client_listbox.get(selection[0])
        answer = messagebox.askyesno("Confirm Removal", f"Are you sure you want to remove '{client_to_remove}'?")
        if answer:
            if client_to_remove in self.sessions:
                del self.sessions[client_to_remove]
            self.client_listbox.delete(selection[0])
            if self.current_client == client_to_remove:
                self.current_client = None
                self.client_label.config(text="No client selected")
                self.history_text.delete("1.0", tk.END)
            self.save_sessions()

    def reset_history(self):
        if self.current_client:
            answer = messagebox.askyesno("Reset History", f"Are you sure you want to reset history for '{self.current_client}'?")
            if answer:
                self.sessions[self.current_client] = []
                self.update_history_text()
                self.save_sessions()
        else:
            messagebox.showerror("Error", "No client selected.")

    def on_client_select(self, event):
        selection = self.client_listbox.curselection()
        if selection:
            selected_client = self.client_listbox.get(selection[0])
            if self.timer_running:
                answer = messagebox.askyesno("Switch Client", "A timer is running. Stop current timer and switch to selected client?")
                if answer:
                    self.stop_timer()
                else:
                    if self.current_client:
                        idx = list(self.client_listbox.get(0, tk.END)).index(self.current_client)
                        self.client_listbox.selection_clear(0, tk.END)
                        self.client_listbox.selection_set(idx)
                    return
            self.current_client = selected_client
            self.client_label.config(text=f"Current Client: {self.current_client}")
            self.update_history_text()

    def toggle_timer(self):
        if self.current_client is None:
            messagebox.showerror("Error", "Please select a client first.")
            return

        if not self.timer_running:
            self.start_timer()
            self.start_stop_button.config(text="Stop")
        else:
            self.stop_timer()
            self.start_stop_button.config(text="Start")

    def start_timer(self):
        self.start_time = datetime.now()
        self.timer_running = True
        self.update_timer()

    def update_timer(self):
        if self.timer_running:
            now = datetime.now()
            elapsed = now - self.start_time
            self.timer_label.config(text=str(elapsed).split(".")[0])
            self.after_id = self.root.after(1000, self.update_timer)

    def stop_timer(self):
        if self.timer_running:
            self.timer_running = False
            if self.after_id:
                self.root.after_cancel(self.after_id)
            end_time = datetime.now()
            duration = end_time - self.start_time
            session_record = [
                self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time.strftime("%Y-%m-%d %H:%M:%S"),
                str(duration).split(".")[0]
            ]
            if self.current_client:
                self.sessions[self.current_client].append(session_record)
                self.save_sessions()
            self.timer_label.config(text="00:00:00")
            self.start_time = None
            self.update_history_text()

    def update_history_text(self):
        self.history_text.delete("1.0", tk.END)
        if self.current_client and self.sessions.get(self.current_client):
            history = self.sessions[self.current_client]
            for idx, record in enumerate(history, 1):
                self.history_text.insert(tk.END, f"{idx}. Start: {record[0]}, End: {record[1]}, Duration: {record[2]}\n")

    def save_history_manual(self):
        if self.current_client:
            file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
            if file_path:
                try:
                    with open(file_path, "w") as f:
                        f.write(f"Session History for {self.current_client}\n")
                        history = self.sessions[self.current_client]
                        for idx, record in enumerate(history, 1):
                            f.write(f"{idx}. Start: {record[0]}, End: {record[1]}, Duration: {record[2]}\n")
                    messagebox.showinfo("Saved", f"History saved to {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save history: {e}")
        else:
            messagebox.showerror("Error", "No client selected.")

    def export_all_to_csv(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if file_path:
            try:
                with open(file_path, "w", newline="") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Client", "Start Time", "End Time", "Duration"])
                    for client, records in self.sessions.items():
                        for record in records:
                            writer.writerow([client, *record])
                messagebox.showinfo("Exported", f"All session data saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export CSV: {e}")

    def on_close(self):
        if self.timer_running:
            messagebox.showwarning("Timer Running", "You must stop the timer before closing the application.")
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TimeTrackerApp(root)
    root.mainloop()
