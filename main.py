import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)


class SchedulerApp:

    def __init__(self, root):

        self.root = root
        self.root.title("Planificador de CPU Ultra-Dinámico")
        self.root.geometry("1200x900")

        self.processes = []
        self.ax = None
        self.canvas = None

        # INTERFAZ PRINCIPAL

        main_frame = ttk.Frame(root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ctrl_frame = ttk.LabelFrame(
            main_frame,
            text=" Configuración de Simulación ",
            padding=10
        )
        ctrl_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            ctrl_frame,
            text="📂 Cargar CSV",
            command=self.load_csv
        ).pack(side=tk.LEFT, padx=10)

        self.algo_var = tk.StringVar(value="FCFS")

        ttk.OptionMenu(
            ctrl_frame,
            self.algo_var,
            "FCFS",
            "FCFS",
            "SPN",
            "SRT",
            "RR"
        ).pack(side=tk.LEFT, padx=5)

        # Campo para el Quantum (Solo para RR)
        ttk.Label(ctrl_frame, text="Quantum:").pack(side=tk.LEFT, padx=5)
        self.quantum_var = tk.StringVar(value="2")
        ttk.Entry(ctrl_frame, textvariable=self.quantum_var, width=5).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            ctrl_frame,
            text="▶️ Iniciar",
            command=self.run_scheduler
        ).pack(side=tk.LEFT, padx=20)

        info_lbl = ttk.Label(
            ctrl_frame,
            text="Touchpad / Rueda Mouse: Zoom Natural",
            font=('Segoe UI', 9, 'italic')
        )
        info_lbl.pack(side=tk.RIGHT)

        # TABLA

        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.X, pady=10)

        columns = (
            "ID",
            "Llegada",
            "Ejecucion",
            "Inicio",
            "Fin",
            "Retorno",
            "Espera"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=8
        )

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")

        scroll_y = ttk.Scrollbar(
            table_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview
        )

        self.tree.configure(yscroll=scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # MÉTRICAS

        self.lbl_averages = ttk.Label(
            main_frame,
            text="Cargue datos para ver métricas",
            font=('Segoe UI', 10, 'bold')
        )
        self.lbl_averages.pack(pady=5)

        # CONTENEDOR GANTT

        self.graph_container = ttk.LabelFrame(
            main_frame,
            text=" Diagrama de Gantt Interactivo ",
            padding=10
        )
        self.graph_container.pack(fill=tk.BOTH, expand=True, pady=10)

    # ─── CARGAR CSV ────────────────────────────────────────────────────────────

    def load_csv(self):

        file_path = filedialog.askopenfilename(
            filetypes=[("Archivos CSV", "*.csv")]
        )

        if not file_path:
            return

        try:
            df = pd.read_csv(file_path)
            df.columns = df.columns.str.strip().str.lower()

            required = ['id', 'llegada', 'ejecucion']
            for col in required:
                if col not in df.columns:
                    raise Exception(f"Falta columna requerida: {col}")

            self.processes = df.to_dict('records')

            messagebox.showinfo(
                "Éxito",
                f"{len(self.processes)} procesos cargados."
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar el archivo:\n{e}"
            )

    # ─── PLANIFICADOR ──────────────────────────────────────────────────────────

    def run_scheduler(self):

        if not self.processes:
            return

        algorithm = self.algo_var.get()
        try:
            quantum = int(self.quantum_var.get())
        except Exception:
            quantum = 1

        # Preparar procesos
        processes_pool = sorted(
            [p.copy() for p in self.processes],
            key=lambda x: x['llegada']
        )
        for p in processes_pool:
            p['restante'] = p['ejecucion']
            p['inicio_real'] = None

        ready_queue = []
        finished = []
        gantt_log = []   # micro-bloques de 1 unidad

        current_time = 0
        current_p = None
        q_counter = 0

        # Simulación tick a tick
        while processes_pool or ready_queue or current_p:

            # 1. Mover procesos que llegaron al tiempo actual a la Ready Queue
            while processes_pool and processes_pool[0]['llegada'] <= current_time:
                ready_queue.append(processes_pool.pop(0))

            # 2. Lógica de Expulsión
            if current_p:
                if algorithm == "SRT":
                    if ready_queue:
                        ready_queue.sort(key=lambda x: x['restante'])
                        if ready_queue[0]['restante'] < current_p['restante']:
                            ready_queue.append(current_p)
                            current_p = None

                elif algorithm == "RR":
                    if q_counter >= quantum:
                        ready_queue.append(current_p)
                        current_p = None

            # 3. Selección de proceso si la CPU está libre
            if not current_p and ready_queue:
                if algorithm == "SPN":
                    ready_queue.sort(key=lambda x: x['ejecucion'])
                elif algorithm == "SRT":
                    ready_queue.sort(key=lambda x: x['restante'])
                elif algorithm == "FCFS":
                    ready_queue.sort(key=lambda x: x['llegada'])
                # RR: no se reordena (FIFO)

                current_p = ready_queue.pop(0)
                if current_p['inicio_real'] is None:
                    current_p['inicio_real'] = current_time
                q_counter = 0

            # 4. Ejecutar 1 tick
            if current_p:
                gantt_log.append({
                    'id': current_p['id'],
                    'inicio': current_time,
                    'dur': 1
                })
                current_p['restante'] -= 1
                current_time += 1
                q_counter += 1

                if current_p['restante'] == 0:
                    current_p['fin'] = current_time
                    current_p['retorno'] = current_p['fin'] - current_p['llegada']
                    current_p['espera'] = current_p['retorno'] - current_p['ejecucion']
                    finished.append(current_p)
                    current_p = None

            else:
                # CPU ociosa: saltar al siguiente proceso que llegue
                if processes_pool:
                    current_time = processes_pool[0]['llegada']
                elif not ready_queue:
                    break          # no hay nada más que hacer
                else:
                    break          # salvaguarda ante estado inconsistente

        self.update_ui(finished, gantt_log)

    # ─── FUSIONAR BLOQUES CONSECUTIVOS DEL MISMO PROCESO ─────────────────────
    # FIX: evita dibujar un rectángulo por cada unidad de tiempo;
    #       bloques contiguos del mismo proceso se unen en uno solo.

    def merge_gantt_blocks(self, gantt_log):
        if not gantt_log:
            return []

        merged = []
        current = gantt_log[0].copy()

        for block in gantt_log[1:]:
            mismo_proceso = block['id'] == current['id']
            contiguo = block['inicio'] == current['inicio'] + current['dur']

            if mismo_proceso and contiguo:
                current['dur'] += block['dur']
            else:
                merged.append(current)
                current = block.copy()

        merged.append(current)
        return merged

    # ─── ACTUALIZAR UI ─────────────────────────────────────────────────────────

    def update_ui(self, results, gantt_log):

        for item in self.tree.get_children():
            self.tree.delete(item)

        total_retorno = 0
        total_espera = 0

        results.sort(key=lambda x: x['id'])

        for p in results:
            self.tree.insert(
                "", "end",
                values=(
                    p['id'],
                    p['llegada'],
                    p['ejecucion'],
                    p['inicio_real'],
                    p['fin'],
                    p['retorno'],
                    p['espera']
                )
            )
            total_retorno += p['retorno']
            total_espera += p['espera']

        promedio_r = total_retorno / len(results)
        promedio_e = total_espera / len(results)

        self.lbl_averages.config(
            text=(
                f"MÉTRICAS  →  "
                f"Retorno Promedio: {promedio_r:.2f}   |   "
                f"Espera Promedio: {promedio_e:.2f}"
            )
        )

        self.draw_interactive_gantt(results, gantt_log)

    # ─── GANTT ─────────────────────────────────────────────────────────────────

    def draw_interactive_gantt(self, results, gantt_log):

        for widget in self.graph_container.winfo_children():
            widget.destroy()

        # FIX: fusionar bloques antes de dibujar
        gantt_log = self.merge_gantt_blocks(gantt_log)

        ids_unicos = sorted(list(set(p['id'] for p in results)))
        y_map = {
            id_proc: len(ids_unicos) - i
            for i, id_proc in enumerate(ids_unicos)
        }

        fig_height = min(max(5, len(ids_unicos) * 0.8), 12)

        fig, self.ax = plt.subplots(
            figsize=(15, fig_height),
            facecolor='#f5f5f5'
        )

        colors = cm.get_cmap('tab20', len(ids_unicos))

        # Dibujar bloques fusionados
        for block in gantt_log:
            idx = ids_unicos.index(block['id'])
            y = y_map[block['id']]

            self.ax.broken_barh(
                [(block['inicio'], block['dur'])],
                (y - 0.35, 0.7),
                facecolors=colors(idx),
                edgecolor='black',
                linewidth=0.8
            )

            # FIX: etiqueta centrada en cada bloque
            self.ax.text(
                block['inicio'] + block['dur'] / 2,
                y,
                str(block['id']),
                ha='center',
                va='center',
                fontsize=7,
                fontweight='bold',
                color='white'
            )

        # CONFIGURACIÓN DE EJES

        self.ax.set_title(
            f"Diagrama de Gantt — {self.algo_var.get()}",
            fontsize=13,
            fontweight='bold'
        )
        self.ax.set_xlabel("Tiempo")
        self.ax.set_ylabel("Procesos")

        self.ax.set_yticks(list(y_map.values()))
        self.ax.set_yticklabels(list(y_map.keys()), fontsize=9)

        max_time = max(b['inicio'] + b['dur'] for b in gantt_log) if gantt_log else 10

        # FIX: ticks enteros en el eje X para lectura clara del tiempo
        self.ax.set_xticks(range(0, max_time + 2))
        self.ax.set_xlim(0, max_time + 1)
        self.ax.set_ylim(0.5, len(ids_unicos) + 1)

        self.ax.grid(True, axis='x', linestyle='--', alpha=0.4)

        fig.tight_layout()

        # CANVAS

        self.canvas = FigureCanvasTkAgg(fig, master=self.graph_container)
        self.canvas.draw()
        self.canvas.mpl_connect('scroll_event', self.on_zoom)

        toolbar = NavigationToolbar2Tk(self.canvas, self.graph_container)
        toolbar.update()

        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ─── ZOOM ──────────────────────────────────────────────────────────────────

    def on_zoom(self, event):

        if event.inaxes != self.ax:
            return

        base_scale = 1.15
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()

        xdata = event.xdata
        ydata = event.ydata

        scale_factor = 1 / base_scale if event.button == 'up' else base_scale

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        self.ax.set_xlim([
            xdata - new_width * (1 - relx),
            xdata + new_width * relx
        ])

        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
        self.ax.set_ylim([
            ydata - new_height * (1 - rely),
            ydata + new_height * rely
        ])

        self.canvas.draw_idle()


if __name__ == "__main__":
    root = tk.Tk()
    app = SchedulerApp(root)
    root.mainloop()