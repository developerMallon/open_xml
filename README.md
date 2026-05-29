# 📑 Visualizador de Nota Fiscal Eletrônica (NF-e) – Veículos

Aplicação desktop moderna em Python para visualizar, importar em lote e gerenciar Notas Fiscais Eletrônicas de veículos com banco de dados SQLite embutido.

---

## ✨ Funcionalidades

| Botão | Função |
|---|---|
| 📥 **Importar Pasta XML** | Varre a pasta `xml/`, importa NFs de **veículos** para o banco, move os arquivos para `xml/processados/` |
| 📁 **Abrir Arquivo XML** | Abre qualquer `.xml` de NF-e para visualização imediata (sem salvar) |
| 💾 **Salvar Nota Atual** | Salva a nota atualmente exibida no banco SQLite (apenas veículos, sem duplicatas) |
| 🔍 **Notas Salvas no Banco** | Abre painel de consulta com busca ao vivo, carregamento e exclusão de notas |

### Destaques
- **Zero dependências externas** – usa apenas bibliotecas nativas do Python 3 (`tkinter`, `xml.etree`, `sqlite3`, `json`, `threading`).
- **Importação em lote com log ao vivo** – dialog com terminal colorido mostrando o progresso em tempo real, em thread separada para não travar a UI.
- **Banco de dados SQLite híbrido** – colunas indexadas para busca rápida + JSON documental completo para reconstrução fiel de todos os dados.
- **Verificação de chassi** – somente NFs com tag `<veicProd>/<chassi>` são importadas para o banco.
- **Prevenção de duplicatas por chave de acesso** – re-importar os mesmos XMLs é seguro.
- **Movimentação automática** – após o processamento (sucesso, ignorado ou erro), o arquivo `.xml` é movido para `xml/processados/` com tratamento de conflito de nomes.
- **Interface de consulta** – busca por número, chassi, emitente ou destinatário; duplo clique ou botão para carregar; botão de exclusão com confirmação.

---

## 🛠️ Requisitos

- **Python 3.8+** instalado.
- Nenhum `pip install` necessário.

---

## 🚀 Como Executar

```powershell
python app.py
```

Ou duplo clique no arquivo `app.py`.

---

## 📂 Estrutura de Arquivos

```text
open_xml/
├── app.py               # Interface gráfica (GUI) – ponto de entrada
├── parser_nfe.py        # Parser XML + função de importação em lote
├── db_nfe.py            # Módulo SQLite (CRUD + init)
├── nfe_database.db      # Banco de dados (criado automaticamente)
├── README.md
└── xml/                 # Coloque aqui os XMLs a importar
    └── processados/     # XMLs movidos após processamento
```

---

## 💡 Fluxo de Uso Típico

1. Copie os arquivos `.xml` de NF-e para a pasta `xml/`.
2. Execute `python app.py`.
3. Clique em **📥 Importar Pasta XML** — acompanhe o log em tempo real.
4. Os XMLs de veículos serão salvos no banco; os arquivos movidos para `xml/processados/`.
5. Clique em **🔍 Notas Salvas no Banco** para pesquisar e carregar qualquer nota importada.
6. Para notas abertas individualmente com **📁 Abrir Arquivo XML**, use **💾 Salvar Nota Atual** para adicioná-las ao banco.
