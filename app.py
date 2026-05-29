import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading

from parser_nfe import parse_nfe, format_currency, importar_pasta_xml
from db_nfe import salvar_nfe, listar_nfe, carregar_nfe, excluir_nfe


class NFeViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Visualizador de Nota Fiscal Eletrônica (NF-e)")
        self.root.geometry("1100x720")
        self.root.minsize(950, 620)

        self.setup_styles()
        self.current_data = None
        self.current_source = None  # "file" or "db"

        self.create_widgets()

    # ─────────────────────────────────────────────────────────────
    # STYLES
    # ─────────────────────────────────────────────────────────────
    def setup_styles(self):
        self.style = ttk.Style()
        if os.name == "nt":
            try:
                self.style.theme_use("vista")
            except Exception:
                pass

        self.bg_color      = "#f8f9fa"
        self.primary_color = "#0f4c81"
        self.accent_color  = "#2e7d32"
        self.danger_color  = "#c62828"
        self.card_bg       = "#ffffff"
        self.text_color    = "#212529"
        self.muted_text    = "#6c757d"
        self.font_family   = "Segoe UI"

        self.style.configure(".", font=(self.font_family, 10))
        self.style.configure("TLabel", foreground=self.text_color)

        self.style.configure("Header.TFrame",      background=self.primary_color)
        self.style.configure("Toolbar.TFrame",     background="#e3ecf7")
        self.style.configure("HeaderTitle.TLabel", font=(self.font_family, 16, "bold"),
                             foreground="#ffffff",  background=self.primary_color)
        self.style.configure("HeaderSub.TLabel",   font=(self.font_family, 9, "italic"),
                             foreground="#c8d8ec",  background=self.primary_color)

        self.style.configure("TNotebook",          background=self.bg_color, padding=5)
        self.style.configure("TNotebook.Tab",      font=(self.font_family, 10, "bold"), padding=(10, 6))
        self.style.configure("Treeview.Heading",   font=(self.font_family, 9, "bold"), foreground="#333333")
        self.style.configure("Treeview",           font=(self.font_family, 9), rowheight=25)
        self.style.configure("Status.TFrame",      background="#dce3ec")
        self.style.configure("Status.TLabel",      background="#dce3ec", font=(self.font_family, 9))

        # Toolbar button styles
        self.style.configure("Btn1.TButton", font=(self.font_family, 9, "bold"))
        self.style.configure("Btn2.TButton", font=(self.font_family, 9, "bold"))
        self.style.configure("Btn3.TButton", font=(self.font_family, 9, "bold"))
        self.style.configure("Btn4.TButton", font=(self.font_family, 9, "bold"))

    # ─────────────────────────────────────────────────────────────
    # WIDGETS
    # ─────────────────────────────────────────────────────────────
    def create_widgets(self):
        # ── Header ───────────────────────────────────────────────
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(15, 12))
        header.pack(fill=tk.X, side=tk.TOP)

        ttk.Label(header, text="Visualizador de NF-e  •  Veículos", style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(header, text="Importe XMLs em lote, abra notas individuais ou consulte o banco de dados",
                  style="HeaderSub.TLabel").pack(anchor="w", pady=(2, 0))

        # ── Toolbar with 4 buttons ────────────────────────────────
        toolbar = ttk.Frame(self.root, style="Toolbar.TFrame", padding=(10, 6))
        toolbar.pack(fill=tk.X)

        btn_cfg = [
            ("📥  Importar Pasta XML",    self.btn_importar_pasta,   "Btn1.TButton",
             "Varre a pasta 'xml/', importa veículos para o banco e move os arquivos para xml/processados"),
            ("📁  Abrir Arquivo XML",     self.btn_abrir_arquivo,    "Btn2.TButton",
             "Abre um arquivo .xml para visualização"),
            ("💾  Salvar Nota Atual",     self.btn_salvar_atual,     "Btn3.TButton",
             "Salva a nota visualizada no banco de dados (somente veículos)"),
            ("🔍  Notas Salvas no Banco", self.btn_listar_banco,     "Btn4.TButton",
             "Consulta, filtra e carrega notas salvas no banco de dados"),
        ]

        for i, (label, cmd, style_name, tooltip) in enumerate(btn_cfg):
            btn = ttk.Button(toolbar, text=label, style=style_name, command=cmd)
            btn.pack(side=tk.LEFT, padx=(0 if i == 0 else 8, 0))
            self._add_tooltip(btn, tooltip)

        # Separator
        ttk.Separator(self.root, orient="horizontal").pack(fill=tk.X)

        # ── Main content area ────────────────────────────────────
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.empty_label = ttk.Label(
            self.main_frame,
            text="Nenhuma nota carregada.\n\nUse os botões acima para importar ou abrir uma Nota Fiscal Eletrônica.",
            font=(self.font_family, 12),
            justify=tk.CENTER,
            foreground=self.muted_text
        )
        self.empty_label.pack(expand=True)

        # ── Notebook (hidden until data loaded) ──────────────────
        self.notebook = ttk.Notebook(self.main_frame)
        self.tab_resumo       = ttk.Frame(self.notebook, padding=15)
        self.tab_emitente     = ttk.Frame(self.notebook, padding=15)
        self.tab_destinatario = ttk.Frame(self.notebook, padding=15)
        self.tab_itens        = ttk.Frame(self.notebook, padding=15)
        self.tab_valores      = ttk.Frame(self.notebook, padding=15)
        self.tab_adicional    = ttk.Frame(self.notebook, padding=15)

        self.notebook.add(self.tab_resumo,       text="📄 Identificação / Resumo")
        self.notebook.add(self.tab_emitente,     text="🏭 Emitente")
        self.notebook.add(self.tab_destinatario, text="👤 Destinatário")
        self.notebook.add(self.tab_itens,        text="🛒 Itens / Produtos")
        self.notebook.add(self.tab_valores,      text="💰 Valores e Impostos")
        self.notebook.add(self.tab_adicional,    text="💬 Informações Adicionais")

        # ── Status bar ───────────────────────────────────────────
        self.status_frame = ttk.Frame(self.root, style="Status.TFrame", padding=(10, 4))
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_lbl = ttk.Label(self.status_frame, text="Pronto.", style="Status.TLabel")
        self.status_lbl.pack(side=tk.LEFT)
        self.source_lbl = ttk.Label(self.status_frame, text="", style="Status.TLabel",
                                    foreground=self.primary_color, font=(self.font_family, 9, "bold"))
        self.source_lbl.pack(side=tk.RIGHT)

    # ─────────────────────────────────────────────────────────────
    # TOOLTIP HELPER
    # ─────────────────────────────────────────────────────────────
    def _add_tooltip(self, widget, text):
        tip = None

        def enter(e):
            nonlocal tip
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{x}+{y}")
            lbl = tk.Label(tip, text=text, background="#fffde7", foreground="#333",
                           font=(self.font_family, 8), relief="solid", borderwidth=1, padx=6, pady=4)
            lbl.pack()

        def leave(e):
            nonlocal tip
            if tip:
                tip.destroy()
                tip = None

        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    # ─────────────────────────────────────────────────────────────
    # BUTTON 1 – Importar Pasta XML
    # ─────────────────────────────────────────────────────────────
    def btn_importar_pasta(self):
        """Scans xml/ folder in a background thread and shows a live-log dialog."""
        pasta = "xml"
        if not os.path.isdir(pasta):
            messagebox.showerror("Pasta não encontrada",
                                 f"A pasta '{pasta}' não foi encontrada no diretório atual.\n"
                                 "Crie a pasta 'xml' e coloque os arquivos .xml nela.")
            return

        # Build the progress dialog
        dlg = tk.Toplevel(self.root)
        dlg.title("Importando XMLs da pasta xml/")
        dlg.geometry("680x420")
        dlg.resizable(True, True)
        dlg.transient(self.root)
        dlg.grab_set()

        header_frm = ttk.Frame(dlg, style="Header.TFrame", padding=10)
        header_frm.pack(fill=tk.X)
        ttk.Label(header_frm, text="📥  Importação em Lote",
                  font=(self.font_family, 13, "bold"), foreground="#fff",
                  background=self.primary_color).pack(anchor="w")
        ttk.Label(header_frm, text="Varrendo pasta xml/, importando veículos e movendo arquivos para xml/processados",
                  font=(self.font_family, 9, "italic"), foreground="#c8d8ec",
                  background=self.primary_color).pack(anchor="w", pady=(2, 0))

        log_frame = ttk.Frame(dlg, padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(log_frame)
        log_text = tk.Text(log_frame, wrap=tk.WORD, font=(self.font_family, 9),
                           bg="#1e1e2e", fg="#cdd6f4", insertbackground="#cdd6f4",
                           bd=0, state=tk.DISABLED, yscrollcommand=sb.set)
        sb.config(command=log_text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Color tags for log
        log_text.tag_configure("ok",   foreground="#a6e3a1")
        log_text.tag_configure("warn", foreground="#f9e2af")
        log_text.tag_configure("err",  foreground="#f38ba8")
        log_text.tag_configure("info", foreground="#89dceb")

        btn_frame = ttk.Frame(dlg, padding=(10, 6))
        btn_frame.pack(fill=tk.X)
        self._summary_label = ttk.Label(btn_frame, text="Aguardando...", foreground=self.muted_text,
                                        font=(self.font_family, 9))
        self._summary_label.pack(side=tk.LEFT)
        btn_close = ttk.Button(btn_frame, text="Fechar", state=tk.DISABLED,
                               command=dlg.destroy)
        btn_close.pack(side=tk.RIGHT)

        def append_log(msg, tag="info"):
            log_text.config(state=tk.NORMAL)
            if "✅" in msg:
                tag = "ok"
            elif "⚠️" in msg:
                tag = "warn"
            elif "❌" in msg:
                tag = "err"
            log_text.insert(tk.END, msg + "\n", tag)
            log_text.see(tk.END)
            log_text.config(state=tk.DISABLED)

        def run_import():
            result = importar_pasta_xml(pasta_base=pasta, callback_progresso=lambda m: dlg.after(0, append_log, m))
            def on_done():
                summary = (f"Total: {result['total']} | "
                           f"✅ Importadas: {result['importadas']} | "
                           f"⚠️  Ignoradas: {result['ignoradas']} | "
                           f"❌ Erros: {result['erros']}")
                self._summary_label.config(text=summary, foreground=self.text_color)
                btn_close.config(state=tk.NORMAL)
                self.status_lbl.config(text=f"Importação concluída. {summary}")
            dlg.after(0, on_done)

        thread = threading.Thread(target=run_import, daemon=True)
        thread.start()

    # ─────────────────────────────────────────────────────────────
    # BUTTON 2 – Abrir Arquivo XML
    # ─────────────────────────────────────────────────────────────
    def btn_abrir_arquivo(self):
        file_path = filedialog.askopenfilename(
            title="Selecionar XML de NF-e",
            filetypes=[("Arquivos XML", "*.xml"), ("Todos os Arquivos", "*.*")]
        )
        if not file_path:
            return
        try:
            data = parse_nfe(file_path)
            self.current_data   = data
            self.current_source = "file"
            self.display_data()
            self.status_lbl.config(text=f"Arquivo carregado: {os.path.basename(file_path)}")
            self.source_lbl.config(text="📁 Origem: Arquivo XML")
        except Exception as e:
            messagebox.showerror("Erro de Leitura", f"Não foi possível processar o XML:\n{str(e)}")

    # ─────────────────────────────────────────────────────────────
    # BUTTON 3 – Salvar Nota Atual
    # ─────────────────────────────────────────────────────────────
    def btn_salvar_atual(self):
        if not self.current_data:
            messagebox.showwarning("Sem dados", "Nenhuma nota está carregada para salvar.\n"
                                               "Abra um arquivo XML primeiro.")
            return

        sucesso, msg = salvar_nfe(self.current_data)
        if sucesso:
            messagebox.showinfo("Salvo com Sucesso ✅", msg)
            self.status_lbl.config(text="Nota salva no banco de dados.")
        else:
            messagebox.showwarning("Não foi possível salvar", msg)

    # ─────────────────────────────────────────────────────────────
    # BUTTON 4 – Listar Notas no Banco
    # ─────────────────────────────────────────────────────────────
    def btn_listar_banco(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Notas Fiscais de Veículos – Banco de Dados")
        dlg.geometry("950x560")
        dlg.minsize(800, 400)
        dlg.transient(self.root)
        dlg.grab_set()

        # Header
        hdr = ttk.Frame(dlg, style="Header.TFrame", padding=10)
        hdr.pack(fill=tk.X)
        ttk.Label(hdr, text="🔍  Notas Salvas no Banco de Dados",
                  font=(self.font_family, 13, "bold"), foreground="#fff",
                  background=self.primary_color).pack(anchor="w")
        ttk.Label(hdr, text="Consulte, filtre e carregue notas fiscais de veículos salvas anteriormente",
                  font=(self.font_family, 9, "italic"), foreground="#c8d8ec",
                  background=self.primary_color).pack(anchor="w", pady=(2, 0))

        # Search bar
        search_frm = ttk.Frame(dlg, padding=(10, 8))
        search_frm.pack(fill=tk.X)
        ttk.Label(search_frm, text="🔎 Buscar:", font=(self.font_family, 10, "bold")).pack(side=tk.LEFT)
        self._search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frm, textvariable=self._search_var, width=40,
                                 font=(self.font_family, 10))
        search_entry.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(search_frm, text="(número, chassi, emitente ou destinatário)",
                  foreground=self.muted_text, font=(self.font_family, 9)).pack(side=tk.LEFT, padx=8)
        ttk.Button(search_frm, text="Limpar", command=lambda: self._search_var.set("")).pack(side=tk.LEFT)

        # Treeview
        tree_frm = ttk.Frame(dlg, padding=(10, 0))
        tree_frm.pack(fill=tk.BOTH, expand=True)

        cols = ("numero", "serie", "data", "emitente", "destinatario", "chassi", "valor")
        sb_y = ttk.Scrollbar(tree_frm, orient=tk.VERTICAL)
        sb_x = ttk.Scrollbar(tree_frm, orient=tk.HORIZONTAL)

        tree = ttk.Treeview(tree_frm, columns=cols, show="headings",
                            yscrollcommand=sb_y.set, xscrollcommand=sb_x.set,
                            selectmode="browse")
        sb_y.config(command=tree.yview)
        sb_x.config(command=tree.xview)

        tree.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        tree_frm.rowconfigure(0, weight=1)
        tree_frm.columnconfigure(0, weight=1)

        headers = {"numero": "Nº NF", "serie": "Série", "data": "Data Emissão",
                   "emitente": "Emitente", "destinatario": "Destinatário",
                   "chassi": "Chassi", "valor": "Valor Total"}
        widths  = {"numero": 80, "serie": 50, "data": 130, "emitente": 220,
                   "destinatario": 220, "chassi": 160, "valor": 110}
        anchors = {"numero": "center", "serie": "center", "data": "center",
                   "emitente": "w", "destinatario": "w", "chassi": "center", "valor": "e"}

        for c in cols:
            tree.heading(c, text=headers[c])
            tree.column(c, width=widths[c], anchor=anchors[c])

        # Populate from DB
        self._db_chave_map = {}

        def load_rows(busca=None):
            tree.delete(*tree.get_children())
            self._db_chave_map.clear()
            rows = listar_nfe(busca if busca else None)
            for row in rows:
                iid = tree.insert("", "end", values=(
                    row["numero"], row["serie"], row["data_emissao"],
                    row["emitente_nome"], row["destinatario_nome"],
                    row["chassi"], row["valor_total"]
                ))
                self._db_chave_map[iid] = row["chave"]
            lbl_count.config(text=f"{len(rows)} nota(s) encontrada(s).")

        # Delayed search on typing
        def on_search_change(*_):
            term = self._search_var.get().strip()
            load_rows(term if term else None)

        self._search_var.trace_add("write", on_search_change)

        # Bottom action bar
        action_frm = ttk.Frame(dlg, padding=(10, 8))
        action_frm.pack(fill=tk.X)
        lbl_count = ttk.Label(action_frm, text="", foreground=self.muted_text,
                              font=(self.font_family, 9))
        lbl_count.pack(side=tk.LEFT)

        def carregar_selecionada():
            sel = tree.focus()
            if not sel:
                messagebox.showwarning("Nenhuma seleção", "Selecione uma nota para carregar.", parent=dlg)
                return
            chave = self._db_chave_map.get(sel)
            data = carregar_nfe(chave)
            if data:
                self.current_data   = data
                self.current_source = "db"
                self.display_data()
                nf = data["ide"]["nNF"]
                self.status_lbl.config(text=f"Nota NF-{nf} carregada do banco de dados.")
                self.source_lbl.config(text="🗄️ Origem: Banco de Dados")
                dlg.destroy()
            else:
                messagebox.showerror("Erro", "Não foi possível carregar a nota do banco.", parent=dlg)

        def excluir_selecionada():
            sel = tree.focus()
            if not sel:
                messagebox.showwarning("Nenhuma seleção", "Selecione uma nota para excluir.", parent=dlg)
                return
            chave = self._db_chave_map.get(sel)
            vals  = tree.item(sel, "values")
            conf = messagebox.askyesno(
                "Confirmar Exclusão",
                f"Deseja realmente excluir a nota NF-{vals[0]} (Chassi: {vals[5]})?\n"
                "Esta operação não pode ser desfeita.",
                parent=dlg
            )
            if conf:
                excluir_nfe(chave)
                load_rows(self._search_var.get().strip() or None)
                self.status_lbl.config(text=f"Nota NF-{vals[0]} excluída do banco.")

        ttk.Button(action_frm, text="📋  Carregar Nota Selecionada",
                   command=carregar_selecionada).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(action_frm, text="🗑️  Excluir Nota Selecionada",
                   command=excluir_selecionada).pack(side=tk.RIGHT)

        # Double-click also loads
        tree.bind("<Double-1>", lambda e: carregar_selecionada())

        # Initial load
        load_rows()

    # ─────────────────────────────────────────────────────────────
    # DATA DISPLAY
    # ─────────────────────────────────────────────────────────────
    def display_data(self):
        self.empty_label.pack_forget()
        self.notebook.pack(fill=tk.BOTH, expand=True)

        for tab in (self.tab_resumo, self.tab_emitente, self.tab_destinatario,
                    self.tab_itens, self.tab_valores, self.tab_adicional):
            for child in tab.winfo_children():
                child.destroy()

        self.populate_resumo()
        self.populate_emitente()
        self.populate_destinatario()
        self.populate_itens()
        self.populate_valores()
        self.populate_adicional()

    # ─────────────────────────────────────────────────────────────
    # SHARED UI HELPERS
    # ─────────────────────────────────────────────────────────────
    def create_card_frame(self, parent, title):
        return ttk.LabelFrame(parent, text=title, padding=12)

    def add_field(self, parent, label, value, row, column, columnspan=1,
                  sticky="w", is_copyable=False):
        lbl = ttk.Label(parent, text=label, font=(self.font_family, 9, "bold"),
                        foreground=self.muted_text)
        lbl.grid(row=row * 2, column=column, columnspan=columnspan,
                 sticky="w", padx=5, pady=(4, 0))

        if is_copyable:
            entry = tk.Entry(parent, font=(self.font_family, 10), bg="#f1f3f5",
                             fg=self.text_color, bd=0, highlightthickness=0)
            entry.insert(0, value)
            entry.config(state="readonly")
            entry.grid(row=row * 2 + 1, column=column, columnspan=columnspan,
                       sticky="ew", padx=5, pady=(0, 6))
        else:
            val_lbl = ttk.Label(parent, text=value, font=(self.font_family, 10))
            val_lbl.grid(row=row * 2 + 1, column=column, columnspan=columnspan,
                         sticky=sticky, padx=5, pady=(0, 6))

    def _scrolled_text(self, parent, content):
        """Creates a read-only scrolled Text widget and packs it into parent."""
        frm = ttk.Frame(parent)
        frm.pack(fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(frm)
        ta = tk.Text(frm, wrap=tk.WORD, font=(self.font_family, 10),
                     bg="#f8f9fa", fg=self.text_color, bd=0,
                     yscrollcommand=sb.set)
        sb.config(command=ta.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        ta.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ta.insert(tk.END, content)
        ta.config(state=tk.DISABLED)

    # ─────────────────────────────────────────────────────────────
    # TAB: RESUMO
    # ─────────────────────────────────────────────────────────────
    def populate_resumo(self):
        ide = self.current_data["ide"]
        self.tab_resumo.columnconfigure(0, weight=1)

        card = self.create_card_frame(self.tab_resumo, "Informações Básicas da NF-e")
        card.pack(fill=tk.BOTH, expand=True)
        for i in range(4):
            card.columnconfigure(i, weight=1)

        self.add_field(card, "Número da NF-e", ide["nNF"], 0, 0, is_copyable=True)
        self.add_field(card, "Série", ide["serie"], 0, 1)
        self.add_field(card, "Data e Hora de Emissão", ide["dhEmi"], 0, 2)
        self.add_field(card, "Tipo de Operação", ide["tpNF"], 0, 3)
        self.add_field(card, "Natureza da Operação", ide["natOp"], 1, 0, columnspan=2)
        self.add_field(card, "Modelo do Documento", ide["mod"], 1, 2)
        self.add_field(card, "Chave de Acesso (44 dígitos)", ide["chave"], 2, 0,
                       columnspan=4, is_copyable=True)

    # ─────────────────────────────────────────────────────────────
    # TAB: EMITENTE
    # ─────────────────────────────────────────────────────────────
    def populate_emitente(self):
        emit = self.current_data["emit"]
        if not emit:
            ttk.Label(self.tab_emitente, text="Dados do Emitente não disponíveis.",
                      font=(self.font_family, 11)).pack()
            return

        self.tab_emitente.columnconfigure(0, weight=1)

        card_basic = self.create_card_frame(self.tab_emitente, "Identificação do Emitente")
        card_basic.pack(fill=tk.X, pady=(0, 10))
        for i in range(3):
            card_basic.columnconfigure(i, weight=1)

        self.add_field(card_basic, "Razão Social / Nome", emit["xNome"], 0, 0, columnspan=2)
        self.add_field(card_basic, "Nome Fantasia", emit["xFant"] or "-", 0, 2)

        cnpj_val   = emit["CNPJ"] or emit["CPF"]
        cnpj_label = "CNPJ" if emit["CNPJ"] else "CPF"
        self.add_field(card_basic, cnpj_label, cnpj_val, 1, 0, is_copyable=True)
        self.add_field(card_basic, "Inscrição Estadual", emit["IE"] or "Isento / Não informado",
                       1, 1, is_copyable=True)

        card_addr = self.create_card_frame(self.tab_emitente, "Endereço")
        card_addr.pack(fill=tk.BOTH, expand=True)
        for i in range(4):
            card_addr.columnconfigure(i, weight=1)

        self.add_field(card_addr, "Logradouro", emit["logradouro"], 0, 0, columnspan=2)
        self.add_field(card_addr, "Número", emit["numero"], 0, 2)
        self.add_field(card_addr, "Complemento", emit["complemento"] or "-", 0, 3)
        self.add_field(card_addr, "Bairro", emit["bairro"], 1, 0)
        self.add_field(card_addr, "Município", emit["municipio"], 1, 1)
        self.add_field(card_addr, "UF", emit["uf"], 1, 2)
        self.add_field(card_addr, "CEP", emit["cep"], 1, 3, is_copyable=True)
        self.add_field(card_addr, "Telefone", emit["telefone"] or "Não informado", 2, 0)

    # ─────────────────────────────────────────────────────────────
    # TAB: DESTINATÁRIO
    # ─────────────────────────────────────────────────────────────
    def populate_destinatario(self):
        dest = self.current_data["dest"]
        if not dest:
            card = self.create_card_frame(self.tab_destinatario, "Identificação do Destinatário")
            card.pack(fill=tk.BOTH, expand=True)
            ttk.Label(card, text="Nota emitida sem identificação de destinatário (Consumidor Final).",
                      font=(self.font_family, 10, "italic")).pack(pady=20)
            return

        self.tab_destinatario.columnconfigure(0, weight=1)

        card_basic = self.create_card_frame(self.tab_destinatario, "Identificação do Destinatário")
        card_basic.pack(fill=tk.X, pady=(0, 10))
        for i in range(3):
            card_basic.columnconfigure(i, weight=1)

        self.add_field(card_basic, "Nome / Razão Social", dest["xNome"], 0, 0, columnspan=2)
        cnpj_val   = dest["CNPJ"] or dest["CPF"]
        cnpj_label = "CNPJ" if dest["CNPJ"] else "CPF"
        self.add_field(card_basic, cnpj_label, cnpj_val, 0, 2, is_copyable=True)
        self.add_field(card_basic, "Inscrição Estadual", dest["IE"] or "Não informado / Isento",
                       1, 0, is_copyable=True)

        card_addr = self.create_card_frame(self.tab_destinatario, "Endereço")
        card_addr.pack(fill=tk.BOTH, expand=True)
        for i in range(4):
            card_addr.columnconfigure(i, weight=1)

        self.add_field(card_addr, "Logradouro", dest["logradouro"], 0, 0, columnspan=2)
        self.add_field(card_addr, "Número", dest["numero"], 0, 2)
        self.add_field(card_addr, "Complemento", dest["complemento"] or "-", 0, 3)
        self.add_field(card_addr, "Bairro", dest["bairro"], 1, 0)
        self.add_field(card_addr, "Município", dest["municipio"], 1, 1)
        self.add_field(card_addr, "UF", dest["uf"], 1, 2)
        self.add_field(card_addr, "CEP", dest["cep"], 1, 3, is_copyable=True)
        self.add_field(card_addr, "Telefone", dest["telefone"] or "Não informado", 2, 0)

    # ─────────────────────────────────────────────────────────────
    # TAB: ITENS / PRODUTOS
    # ─────────────────────────────────────────────────────────────
    def populate_itens(self):
        products = self.current_data["products"]

        container = ttk.Frame(self.tab_itens)
        container.pack(fill=tk.BOTH, expand=True)

        columns = ("item", "codigo", "descricao", "ncm", "cfop", "unidade", "qtd", "v_unitario", "v_total")
        sb_y = ttk.Scrollbar(container, orient=tk.VERTICAL)
        sb_x = ttk.Scrollbar(container, orient=tk.HORIZONTAL)

        self.tree = ttk.Treeview(container, columns=columns, show="headings",
                                 yscrollcommand=sb_y.set, xscrollcommand=sb_x.set,
                                 selectmode="browse")
        sb_y.config(command=self.tree.yview)
        sb_x.config(command=self.tree.xview)

        self.tree.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.on_item_double_click)

        headers = {"item": "Item", "codigo": "Código",
                   "descricao": "Descrição do Produto / Serviço",
                   "ncm": "NCM", "cfop": "CFOP", "unidade": "Unid.",
                   "qtd": "Qtd", "v_unitario": "V. Unitário", "v_total": "V. Total"}
        widths   = {"item": 40, "codigo": 100, "descricao": 360, "ncm": 80,
                    "cfop": 60, "unidade": 50, "qtd": 70, "v_unitario": 100, "v_total": 110}
        anchors  = {"item": "center", "codigo": "w", "descricao": "w",
                    "ncm": "center", "cfop": "center", "unidade": "center",
                    "qtd": "e", "v_unitario": "e", "v_total": "e"}

        for col in columns:
            self.tree.heading(col, text=headers[col],
                              command=lambda c=col: self.sort_tree_column(c, False))
            self.tree.column(col, width=widths[col], minwidth=widths[col] - 20,
                             anchor=anchors[col])

        for item in products:
            def fmt_cur(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            def fmt_qty(v): return f"{v:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")

            self.tree.insert("", "end", values=(
                item["nItem"], item["cProd"], item["xProd"],
                item["ncm"], item["cfop"], item["uCom"],
                fmt_qty(item["qCom"]), fmt_cur(item["vUnCom"]), fmt_cur(item["vProd"])
            ))

        ttk.Label(self.tab_itens,
                  text="💡 Dica: Clique duplo em um produto para ver detalhes completos (veículo, impostos, adicionais). "
                       "Clique nos cabeçalhos para ordenar.",
                  font=(self.font_family, 9, "italic"), foreground=self.muted_text
                  ).pack(anchor="w", pady=(8, 0))

    def sort_tree_column(self, col, reverse):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]

        def key(v):
            clean = v.replace("R$", "").replace(".", "").replace(",", ".").strip()
            try:   return float(clean)
            except Exception: pass
            try:   return int(v)
            except Exception: return v.lower()

        items.sort(key=lambda t: key(t[0]), reverse=reverse)
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self.sort_tree_column(col, not reverse))

    # ─────────────────────────────────────────────────────────────
    # ITEM DOUBLE-CLICK POPUP (with inner notebook)
    # ─────────────────────────────────────────────────────────────
    def on_item_double_click(self, event):
        sel = self.tree.focus()
        if not sel:
            return
        values  = self.tree.item(sel, "values")
        item_no = values[0]

        orig_item = next((p for p in self.current_data["products"]
                          if str(p["nItem"]) == str(item_no)), None)
        if not orig_item:
            return

        popup = tk.Toplevel(self.root)
        popup.title(f"Detalhes – Item #{item_no} | {orig_item['cProd']}")
        popup.geometry("660x560")
        popup.minsize(600, 480)
        popup.transient(self.root)
        popup.grab_set()

        p_hdr = ttk.Frame(popup, style="Header.TFrame", padding=10)
        p_hdr.pack(fill=tk.X)
        ttk.Label(p_hdr, text=f"Item #{item_no}: {orig_item['xProd']}",
                  font=(self.font_family, 11, "bold"), foreground="#ffffff",
                  background=self.primary_color, wraplength=620).pack(anchor="w")

        p_content = ttk.Frame(popup, padding=10)
        p_content.pack(fill=tk.BOTH, expand=True)

        nb = ttk.Notebook(p_content)
        nb.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # ── Tab: Dados Gerais e Valores ──────────────────────────
        t_geral = ttk.Frame(nb, padding=10)
        nb.add(t_geral, text="📋 Dados Gerais e Valores")
        t_geral.columnconfigure(0, weight=1)

        c_prod = self.create_card_frame(t_geral, "Especificações Técnicas")
        c_prod.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for i in range(3): c_prod.columnconfigure(i, weight=1)

        self.add_field(c_prod, "Código Interno",    orig_item["cProd"], 0, 0)
        self.add_field(c_prod, "NCM",               orig_item["ncm"],   0, 1)
        self.add_field(c_prod, "CFOP",              orig_item["cfop"],  0, 2)
        self.add_field(c_prod, "Unidade Comercial", orig_item["uCom"],  1, 0)
        def fqty(v): return f"{v:,.4f}".replace(",","X").replace(".",",").replace("X",".")
        self.add_field(c_prod, "Quantidade", fqty(orig_item["qCom"]), 1, 1)
        self.add_field(c_prod, "Valor Unitário", format_currency(orig_item["vUnCom"]), 1, 2)

        c_val = self.create_card_frame(t_geral, "Composição de Valores")
        c_val.grid(row=1, column=0, sticky="ew")
        for i in range(3): c_val.columnconfigure(i, weight=1)

        self.add_field(c_val, "Valor Bruto",  format_currency(orig_item["vProd"]),  0, 0)
        self.add_field(c_val, "Desconto (-)", format_currency(orig_item["vDesc"]),  0, 1)
        self.add_field(c_val, "Frete (+)",    format_currency(orig_item["vFrete"]), 0, 2)
        self.add_field(c_val, "Seguro (+)",   format_currency(orig_item["vSeg"]),   1, 0)
        self.add_field(c_val, "Outros (+)",   format_currency(orig_item["vOutro"]), 1, 1)

        v_liq = (orig_item["vProd"] - orig_item["vDesc"]
                 + orig_item["vFrete"] + orig_item["vSeg"] + orig_item["vOutro"])
        ttk.Label(c_val, text="Valor Líquido do Item",
                  font=(self.font_family, 9, "bold"), foreground=self.accent_color
                  ).grid(row=4, column=2, sticky="w", padx=5, pady=(4, 0))
        ttk.Label(c_val, text=format_currency(v_liq),
                  font=(self.font_family, 13, "bold"), foreground=self.accent_color
                  ).grid(row=5, column=2, sticky="w", padx=5, pady=(0, 6))

        # ── Tab: infAdProd ───────────────────────────────────────
        if orig_item.get("infAdProd"):
            t_adic = ttk.Frame(nb, padding=10)
            nb.add(t_adic, text="💬 Descrição / Adicionais")
            self._scrolled_text(t_adic, orig_item["infAdProd"])

        # ── Tab: veicProd ────────────────────────────────────────
        veic = orig_item.get("veicProd")
        if veic:
            t_veic = ttk.Frame(nb, padding=10)
            nb.add(t_veic, text="🚗 Dados do Veículo")
            t_veic.columnconfigure(0, weight=1)

            c_veic = self.create_card_frame(t_veic, "Informações Específicas do Veículo")
            c_veic.pack(fill=tk.BOTH, expand=True)
            for i in range(3): c_veic.columnconfigure(i, weight=1)

            comb_map = {"01": "Álcool", "02": "Gasolina", "03": "Diesel",
                        "16": "Gás Natural", "17": "Líquido", "18": "Elétrico"}
            cond_map = {"1": "Acabado", "2": "Inacabado", "3": "Semiacabado"}
            op_map   = {"1": "Venda Concessionária", "2": "Faturamento Direto",
                        "3": "Venda Direta", "0": "Outros"}

            def fw(v, d="-"): return v if v else d
            def fp(v):
                try:    return f"{float(v):,.3f}".replace(",","X").replace(".",",").replace("X",".") + " kg"
                except: return v or "-"

            self.add_field(c_veic, "Chassi",       veic["chassi"], 0, 0, is_copyable=True)
            self.add_field(c_veic, "Nº do Motor",  veic["nMotor"], 0, 1, is_copyable=True)
            self.add_field(c_veic, "Cor", f"{fw(veic['xCor'])} (Cód: {fw(veic['cCor'])})", 0, 2)

            self.add_field(c_veic, "Ano Fab. / Mod.", f"{fw(veic['anoFab'])} / {fw(veic['anoMod'])}", 1, 0)
            self.add_field(c_veic, "Potência (CV)",   fw(veic["pot"]),   1, 1)
            self.add_field(c_veic, "Cilindradas",     fw(veic["cilin"]), 1, 2)

            self.add_field(c_veic, "Peso Líquido",  fp(veic["pesoL"]), 2, 0)
            self.add_field(c_veic, "Peso Bruto",    fp(veic["pesoB"]), 2, 1)
            self.add_field(c_veic, "Combustível",   comb_map.get(veic["tpComb"], fw(veic["tpComb"])), 2, 2)

            self.add_field(c_veic, "Série",              fw(veic["nSerie"]), 3, 0)
            self.add_field(c_veic, "CMT (Cap. Máx. Tração)", fw(veic["CMT"]), 3, 1)
            self.add_field(c_veic, "Dist. Entre Eixos", fw(veic["dist"]),  3, 2)

            self.add_field(c_veic, "Condição",           cond_map.get(veic["condVeic"], fw(veic["condVeic"])), 4, 0)
            self.add_field(c_veic, "Cód. Modelo (RENAVAM)", fw(veic["cMod"]), 4, 1, is_copyable=True)
            self.add_field(c_veic, "Tipo de Operação",   op_map.get(veic["tpOp"], fw(veic["tpOp"])), 4, 2)

        ttk.Button(popup, text="Fechar", command=popup.destroy).pack(pady=(0, 10))

    # ─────────────────────────────────────────────────────────────
    # TAB: VALORES E IMPOSTOS
    # ─────────────────────────────────────────────────────────────
    def populate_valores(self):
        total = self.current_data["total"]
        self.tab_valores.columnconfigure(0, weight=1)

        mc = ttk.Frame(self.tab_valores)
        mc.pack(fill=tk.BOTH, expand=True)
        mc.columnconfigure(0, weight=1)
        mc.columnconfigure(1, weight=1)

        # Left: Composição Financeira
        c_fin = self.create_card_frame(mc, "Composição Financeira da NF-e")
        c_fin.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        for i in range(2): c_fin.columnconfigure(i, weight=1)

        self.add_field(c_fin, "Total dos Produtos / Serviços", total["vProd"],  0, 0)
        self.add_field(c_fin, "Desconto (-)",                  total["vDesc"],  0, 1)
        self.add_field(c_fin, "Valor do Frete (+)",            total["vFrete"], 1, 0)
        self.add_field(c_fin, "Valor do Seguro (+)",           total["vSeg"],   1, 1)
        self.add_field(c_fin, "Outras Despesas (+)",           total["vOutro"], 2, 0)

        ttk.Separator(c_fin, orient="horizontal").grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(c_fin, text="VALOR TOTAL DA NF (vNF)",
                  font=(self.font_family, 11, "bold"), foreground=self.accent_color
                  ).grid(row=7, column=0, columnspan=2, sticky="w", padx=5)
        ttk.Label(c_fin, text=total["vNF"],
                  font=(self.font_family, 20, "bold"), foreground=self.accent_color
                  ).grid(row=8, column=0, columnspan=2, sticky="w", padx=5)

        # Right: Impostos
        c_tax = self.create_card_frame(mc, "Resumo de Tributos e Impostos")
        c_tax.grid(row=0, column=1, sticky="nsew")
        for i in range(2): c_tax.columnconfigure(i, weight=1)

        self.add_field(c_tax, "Base de Cálculo do ICMS",           total["vBC"],     0, 0)
        self.add_field(c_tax, "Valor Total do ICMS",               total["vICMS"],   0, 1)
        self.add_field(c_tax, "Base de Cálculo ICMS ST",           total["vBCST"],   1, 0)
        self.add_field(c_tax, "Valor ICMS Substituição (ST)",      total["vST"],     1, 1)
        self.add_field(c_tax, "Valor Total do IPI",                total["vIPI"],    2, 0)
        self.add_field(c_tax, "Valor Total do PIS",                total["vPIS"],    2, 1)
        self.add_field(c_tax, "Valor Total da COFINS",             total["vCOFINS"], 3, 0)
        self.add_field(c_tax, "Imposto de Importação (II)",        total["vII"],     3, 1)

    # ─────────────────────────────────────────────────────────────
    # TAB: INFORMAÇÕES ADICIONAIS
    # ─────────────────────────────────────────────────────────────
    def populate_adicional(self):
        inf = self.current_data.get("infAdic", {})
        self.tab_adicional.columnconfigure(0, weight=1)
        self.tab_adicional.rowconfigure(0, weight=1)
        self.tab_adicional.rowconfigure(1, weight=1)

        has_content = False

        if inf.get("infCpl"):
            has_content = True
            c_cpl = self.create_card_frame(
                self.tab_adicional, "Informações Complementares (Interesse do Contribuinte)")
            c_cpl.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
            self._scrolled_text(c_cpl, inf["infCpl"])

        if inf.get("infAdFisco"):
            has_content = True
            c_fisco = self.create_card_frame(
                self.tab_adicional, "Informações de Interesse do Fisco")
            c_fisco.grid(row=1, column=0, sticky="nsew")
            self._scrolled_text(c_fisco, inf["infAdFisco"])

        if not has_content:
            ttk.Label(self.tab_adicional,
                      text="Nenhuma informação adicional ou complementar encontrada.",
                      font=(self.font_family, 10, "italic")).pack(pady=20)


# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = NFeViewerApp(root)
    root.mainloop()
