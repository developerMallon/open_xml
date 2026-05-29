import sqlite3
import json
import os

DB_NAME = "nfe_database.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the SQLite database and creates the table and indexes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notas_fiscais (
            chave TEXT PRIMARY KEY,
            numero TEXT,
            serie TEXT,
            data_emissao TEXT,
            emitente_nome TEXT,
            emitente_cnpj TEXT,
            destinatario_nome TEXT,
            destinatario_cnpj TEXT,
            valor_total TEXT,
            chassi TEXT,
            dados_json TEXT
        )
    """)
    # Indexes for fast search/filtering
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chassi ON notas_fiscais (chassi)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_numero ON notas_fiscais (numero)")
    conn.commit()
    conn.close()

def chave_existe(chave):
    """Checks if an access key already exists in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM notas_fiscais WHERE chave = ?", (chave,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def salvar_nfe(data):
    """
    Saves a parsed NF-e dictionary to the SQLite database.
    Only saves if it is verified to be a vehicle.
    Checks for duplicates before inserting.
    """
    # 1. Verify if it is a vehicle (has veicProd with a chassi)
    chassi = ""
    is_vehicle = False
    for prod in data.get("products", []):
        if prod.get("veicProd") and prod["veicProd"].get("chassi"):
            chassi = prod["veicProd"]["chassi"]
            is_vehicle = True
            break
            
    if not is_vehicle:
        return False, "Ignorada (Nota Fiscal não é referente a Veículo)"

    chave = data["ide"]["chave"]
    
    # 2. Check for duplicate key
    if chave_existe(chave):
        return False, "Ignorada (Nota Fiscal com Chave de Acesso já cadastrada)"
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # Serialize the complete data dictionary into JSON
    dados_json = json.dumps(data, ensure_ascii=False)
    
    try:
        cursor.execute("""
            INSERT INTO notas_fiscais (
                chave, numero, serie, data_emissao, 
                emitente_nome, emitente_cnpj, 
                destinatario_nome, destinatario_cnpj, 
                valor_total, chassi, dados_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chave,
            data["ide"]["nNF"],
            data["ide"]["serie"],
            data["ide"]["dhEmi"],
            data["emit"].get("xNome", ""),
            data["emit"].get("CNPJ", "") or data["emit"].get("CPF", ""),
            data["dest"].get("xNome", ""),
            data["dest"].get("CNPJ", "") or data["dest"].get("CPF", ""),
            data["total"].get("vNF", "R$ 0,00"),
            chassi,
            dados_json
        ))
        conn.commit()
        return True, "Nota Fiscal de veículo importada com sucesso!"
    except Exception as e:
        return False, f"Erro ao inserir no banco: {str(e)}"
    finally:
        conn.close()

def listar_nfe(busca=None):
    """Lists saved notes, optionally filtering by search term."""
    conn = get_connection()
    cursor = conn.cursor()
    if busca:
        term = f"%{busca}%"
        cursor.execute("""
            SELECT chave, numero, serie, data_emissao, emitente_cnpj, emitente_nome, destinatario_cnpj, destinatario_nome, chassi, valor_total 
            FROM notas_fiscais 
            WHERE numero LIKE ? OR chassi LIKE ? OR emitente_nome LIKE ? OR destinatario_nome LIKE ?
            ORDER BY datetime(data_emissao) DESC;
        """, (term, term, term, term))
    else:
        cursor.execute("""
            SELECT chave, numero, serie, data_emissao, emitente_cnpj, emitente_nome, destinatario_cnpj, destinatario_nome, chassi, valor_total 
            FROM notas_fiscais 
            ORDER BY datetime(data_emissao) DESC;
        """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def carregar_nfe(chave):
    """Loads and deserializes the full parsed NF-e data dictionary using its access key."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT dados_json FROM notas_fiscais WHERE chave = ?", (chave,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row["dados_json"])
    return None

def excluir_nfe(chave):
    """Deletes a saved note from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notas_fiscais WHERE chave = ?", (chave,))
    conn.commit()
    conn.close()

# Initialize on import
init_db()
