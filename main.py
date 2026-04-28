import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.cm as cm
import numpy as np

class SchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Planificador de CPU Ultra-Dinámico")
        self.root.geometry("1100x900")
        self.processes = []
        self.ax = None
        self.canvas = None

        # --- Interfaz Estilizada ---
        main_frame = ttk.Frame(root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ctrl_frame = ttk.LabelFrame(main_frame, text=" Configuración de Simulación ", padding="10")
        ctrl_frame.pack(fill=tk.X, pady=5)

        ttk.Button(ctrl_frame, text="📂 Cargar CSV", command=self.load_csv).pack(side=tk.LEFT, padx=10)
        self.algo_var = tk.StringVar(value="FCFS")
        ttk.OptionMenu(ctrl_frame, self.algo_var, "FCFS", "FCFS", "SPN").pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="▶️ Iniciar", command=self.run_scheduler).pack(side=tk.LEFT, padx=20)
        
        info_lbl = ttk.Label(ctrl_frame, text="Scroll: Zoom XY | Shift+Scroll: Pan X | Ctrl+Scroll: Pan Y", font=('Segoe UI', 9, 'italic'))
        info_lbl.pack(side=tk.RIGHT)

        # Tabla con Scroll
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.X, pady=10)
        columns = ("ID", "Llegada", "Ejecucion", "Inicio", "Fin", "Retorno", "Espera")
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=6)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        
        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.lbl_averages = ttk.Label(main_frame, text="Cargue datos para ver promedios", font=('Segoe UI', 10, 'bold'))
        self.lbl_averages.pack(pady=5)

        self.graph_container = ttk.LabelFrame(main_frame, text=" Diagrama de Gantt Interactivo (Zoom Inteligente) ", padding="10")
        self.graph_container.pack(fill=tk.BOTH, expand=True, pady=10)

    def load_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("Archivos CSV", "*.csv")])
        if file_path:
            try:
                df = pd.read_csv(file_path)
                df.columns = df.columns.str.strip().str.lower()
                self.processes = df.to_dict('records')
                messagebox.showinfo("Éxito", f"{len(self.processes)} procesos listos.")
            except Exception as e:
                messagebox.showerror("Error", f"Error en archivo: {e}")

    def run_scheduler(self):
        if not self.processes: return
        algo = self.algo_var.get()
        proc_list = [p.copy() for p in self.processes]
        proc_list.sort(key=lambda x: x['llegada'])
        ready_queue, finished, current_time = [], [], 0
        
        while proc_list or ready_queue:
            while proc_list and proc_list[0]['llegada'] <= current_time:
                ready_queue.append(proc_list.pop(0))
            if not ready_queue:
                if proc_list: current_time = proc_list[0]['llegada']; continue
                break
            if algo == "SPN": ready_queue.sort(key=lambda x: x['ejecucion'])
            p = ready_queue.pop(0)
            p['inicio'] = current_time
            p['fin'] = current_time + p['ejecucion']
            p['retorno'] = p['fin'] - p['llegada']
            p['espera'] = p['inicio'] - p['llegada']
            current_time = p['fin']
            finished.append(p)
        self.update_ui(finished)

    def update_ui(self, results):
        for i in self.tree.get_children(): self.tree.delete(i)
        tr, te = 0, 0
        for p in results:
            self.tree.insert("", "end", values=(p['id'], p['llegada'], p['ejecucion'], p['inicio'], p['fin'], p['retorno'], p['espera']))
            tr += p['retorno']; te += p['espera']
        self.lbl_averages.config(text=f"MÉTRICAS -> Retorno Promedio: {tr/len(results):.2f} | Espera Promedio: {te/len(results):.2f}")
        self.draw_interactive_gantt(results)

    def draw_interactive_gantt(self, results):
        for widget in self.graph_container.winfo_children(): widget.destroy()
        
        # Crear figura con fondo limpio
        fig, self.ax = plt.subplots(figsize=(10, 5), facecolor='#f0f0f0')
        results_sorted = sorted(results, key=lambda x: str(x['id']), reverse=True)
        self.ids = [str(p['id']) for p in results_sorted]
        colors = cm.get_cmap('coolwarm', len(self.ids))
        
        for i, p in enumerate(results_sorted):
            # Dibujar barras con recorte (clipping) activo por defecto en Matplotlib
            self.ax.broken_barh([(p['inicio'], p['ejecucion'])], (i - 0.35, 0.7), 
                               facecolors=colors(i), edgecolor='#333333', linewidth=1, alpha=0.9)
            
            # Texto dinámico: solo aparece si hay espacio
            self.ax.text(p['inicio'] + p['ejecucion']/2, i, str(p['id']), 
                        va='center', ha='center', color='black', fontsize=9, fontweight='bold', clip_on=True)

        # Configuración de Ejes
        self.ax.set_yticks(range(len(self.ids)))
        self.ax.set_yticklabels(self.ids, fontsize=8)
        self.ax.set_xlabel("Línea de Tiempo", fontsize=10, fontweight='bold')
        self.ax.set_ylabel("Procesos", fontsize=10, fontweight='bold')
        self.ax.grid(True, which='both', linestyle='--', alpha=0.4)
        
        # Límites iniciales para que no se vea vacío
        max_t = max(p['fin'] for p in results)
        self.ax.set_xlim(-1, max_t + 2)
        self.ax.set_ylim(-1, len(self.ids))

        self.canvas = FigureCanvasTkAgg(fig, master=self.graph_container)
        self.canvas.draw()
        
        # Conexión de eventos
        self.canvas.mpl_connect('scroll_event', self.on_scroll_dynamic)
        
        # Barra de herramientas estándar por si acaso
        toolbar = NavigationToolbar2Tk(self.canvas, self.graph_container)
        toolbar.update()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def on_scroll_dynamic(self, event):
        if event.inaxes != self.ax: return
        
        base_scale = 1.25
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        
        # --- Lógica de PAN (Desplazamiento) ---
        if event.key == 'shift': # Pan Horizontal
            dx = (cur_xlim[1] - cur_xlim[0]) * 0.15
            if event.button == 'up': self.ax.set_xlim([cur_xlim[0] - dx, cur_xlim[1] - dx])
            else: self.ax.set_xlim([cur_xlim[0] + dx, cur_xlim[1] + dx])
        elif event.key == 'control': # Pan Vertical
            dy = (cur_ylim[1] - cur_ylim[0]) * 0.15
            if event.button == 'up': self.ax.set_ylim([cur_ylim[0] + dy, cur_ylim[1] + dy])
            else: self.ax.set_ylim([cur_ylim[0] - dy, cur_ylim[1] - dy])
            
        # --- Lógica de ZOOM (Ambos Ejes) ---
        else:
            scale_factor = 1/base_scale if event.button == 'up' else base_scale
            
            # Zoom X
            new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
            rel_x = (cur_xlim[1] - event.xdata) / (cur_xlim[1] - cur_xlim[0])
            self.ax.set_xlim([event.xdata - new_width * (1 - rel_x), event.xdata + new_width * rel_x])
            
            # Zoom Y
            new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
            rel_y = (cur_ylim[1] - event.ydata) / (cur_ylim[1] - cur_ylim[0])
            self.ax.set_ylim([event.ydata - new_height * (1 - rel_y), event.ydata + new_height * rel_y])

        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = SchedulerApp(root)
    root.mainloop()