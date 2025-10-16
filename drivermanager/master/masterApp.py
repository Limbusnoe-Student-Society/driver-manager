import tkinter as tk
from tkinter import filedialog, messagebox
import os
import asyncio
import threading
import serverConfig as cfg
from concurrent.futures import ThreadPoolExecutor
import json
try:
    import requests
except ImportError:
    requests = None

class FileManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Файловый менеджер")
        self.root.geometry("700x550")
        
        self.current_path = tk.StringVar()
        self.current_path.set(os.getcwd())
        self.host = tk.StringVar()
        self.port = tk.StringVar()
        self.set_default_connection()
        self.file_vars = {}
        self.executor = ThreadPoolExecutor(max_workers=1)
        
        self.setup_ui()
        self.update_file_list()
        
    def setup_ui(self):
        path_frame = tk.Frame(self.root)
        path_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(path_frame, text="Текущая папка:").grid(row=0, column=0, sticky="w")
        tk.Entry(path_frame, textvariable=self.current_path, width=50).grid(row=0, column=1, padx=5)
        tk.Button(path_frame, text="Обзор", command=self.browse_folder).grid(row=0, column=2)
        tk.Button(path_frame, text="Обновить", command=self.update_file_list).grid(row=0, column=3, padx=5)

        list_frame = tk.Frame(self.root)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(list_frame, text="Файлы в папке:").pack(anchor=tk.W)

        button_frame = tk.Frame(list_frame)
        button_frame.pack(fill=tk.X, pady=5)

        tk.Button(button_frame, text="Выбрать все", command=self.select_all).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(button_frame, text="Снять выделение", command=self.deselect_all).pack(side=tk.LEFT)

        self.canvas = tk.Canvas(list_frame)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.file_frame = self.scrollable_frame

        connection_frame = tk.Frame(self.root)
        connection_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(connection_frame, text="Хост:").grid(row=0, column=0, sticky="w")
        tk.Entry(connection_frame, textvariable=self.host, width=20).grid(row=0, column=1, padx=5, sticky="w")
        
        tk.Label(connection_frame, text="Порт:").grid(row=0, column=2, sticky="w", padx=(20, 0))
        tk.Entry(connection_frame, textvariable=self.port, width=10).grid(row=0, column=3, padx=5, sticky="w")
        
        tk.Button(connection_frame, text="По умолчанию", command=self.set_default_connection).grid(row=0, column=4, padx=(20, 0))
        tk.Button(
            self.root, 
            text="Отправить запрос", 
            command=self.send_http_request_sync,
            bg="green", 
            pady=10
        ).pack(fill=tk.X, padx=10, pady=10)

    def set_default_connection(self):
        self.host.set(cfg.HOST)
        self.port.set(str(cfg.HTTP_PORT))    

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.current_path.set(folder)
            self.update_file_list()

    def update_file_list(self):
        for widget in self.file_frame.winfo_children():
            widget.destroy()
        
        self.file_vars.clear()
        
        path = self.current_path.get()
        if not path or not os.path.exists(path):
            tk.Label(self.file_frame, text="Папка не существует!", fg="red").pack(anchor=tk.W)
            return
        
        try:
            files_and_dirs = os.listdir(path)
            files = [f for f in files_and_dirs if os.path.isfile(os.path.join(path, f))]
            
            if not files:
                tk.Label(self.file_frame, text="Папка пуста", fg="gray").pack(anchor=tk.W)
                return
            
            for file in sorted(files):
                var = tk.BooleanVar()
                self.file_vars[file] = var
                
                chk = tk.Checkbutton(self.file_frame, text=file, variable=var, anchor="w")
                chk.pack(fill=tk.X, pady=1)
                
        except Exception as e:
            tk.Label(self.file_frame, text=f"Ошибка: {str(e)}", fg="red").pack(anchor=tk.W)

    def select_all(self):
        for var in self.file_vars.values():
            var.set(True)

    def deselect_all(self):
        for var in self.file_vars.values():
            var.set(False)

    def get_selected_files_with_paths(self):
        selected_files = []
        current_path = self.current_path.get()
        
        for filename, var in self.file_vars.items():
            if var.get():
                full_path = os.path.join(current_path, filename)
                selected_files.append(f"{current_path}\\{filename}")
        return selected_files

    def get_server_url(self):
        host = self.host.get().strip()
        port = self.port.get().strip()
        return f"http://{host}:{port}/install-drivers"

    def send_http_request_sync(self):
        if requests is None:
            messagebox.showerror("Ошибка", "Библиотека requests не установлена")
            return
            
        if not self.host.get().strip() or not self.port.get().strip():
            messagebox.showerror("Ошибка", "Укажите хост и порт")
            return
            
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._send_http_request())
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_async)
        thread.daemon = True
        thread.start()

    async def _send_http_request(self):
        try:
            selected_files = self.get_selected_files_with_paths()
            request_body = {
                "files": selected_files
            }
            print(request_body)
            
            server_url = self.get_server_url()
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor, 
                lambda: requests.post(
                    server_url,
                    json=request_body,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            )
            
            self.root.after(0, lambda: messagebox.showinfo(
                "HTTP Ответ", 
                f"Статус: {response.status_code}\nТекст: {response.text}"
            ))
        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", "Не удалось подключиться к серверу"))
        except requests.exceptions.Timeout:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", "Таймаут подключения к серверу"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка при отправке запроса: {str(e)}"))

def main():
    root = tk.Tk()
    app = FileManagerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()