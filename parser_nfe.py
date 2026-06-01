import xml.etree.ElementTree as ET
from datetime import datetime
import re

def format_cnpj_cpf(val):
    if not val:
        return ""
    val = re.sub(r'\D', '', val)
    if len(val) == 14:
        return f"{val[:2]}.{val[2:5]}.{val[5:8]}/{val[8:12]}-{val[12:]}"
    elif len(val) == 11:
        return f"{val[:3]}.{val[3:6]}.{val[6:9]}-{val[9:]}"
    return val

def format_cep(val):
    if not val:
        return ""
    val = re.sub(r'\D', '', val)
    if len(val) == 8:
        return f"{val[:5]}-{val[5:]}"
    return val

def format_currency(val):
    if not val:
        return "R$ 0,00"
    try:
        float_val = float(val)
        return f"R$ {float_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except ValueError:
        return val

def format_date(val):
    if not val:
        return ""
    try:
        # Tenta parsear formato ISO (ex: 2026-05-27T17:16:53-03:00)
        # Remove timezone offset se houver
        clean_val = val.split('-')[0] if '-' in val and len(val.split('-')) > 3 else val
        if 'T' in val:
            dt_str = val.split('-03:00')[0] # Limpa timezone de Brasília comum
            dt_str = dt_str.split('-04:00')[0]
            dt_str = dt_str.split('-02:00')[0]
            dt_str = dt_str.split('Z')[0]
            dt = datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S")
            return dt.strftime("%d/%m/%Y %H:%M:%S")
        else:
            # Tenta yyyy-mm-dd
            dt = datetime.strptime(val[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
    except Exception:
        return val

def parse_nfe(xml_path):
    """
    Parses a Brazilian NF-e (Nota Fiscal Eletrônica) XML file and returns a structured dictionary.
    Handles namespaces dynamically to support files with or without namespace declarations.
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        raise ValueError(f"Erro ao analisar o arquivo XML: {e}")

    # Detect namespace
    ns_uri = ""
    if root.tag.startswith('{'):
        ns_uri = root.tag.split('}')[0].strip('{')
    
    # We will search with namespaces if detected, otherwise without
    ns = {'ns': ns_uri} if ns_uri else {}
    prefix = 'ns:' if ns_uri else ''

    # Helper to find elements and safe-get text
    def find_elem(parent, path):
        if parent is None:
            return None
        # Replace simple tags with namespace prefix in path
        if ns_uri:
            parts = path.split('/')
            ns_parts = [f"ns:{p}" if p and not p.startswith('ns:') else p for p in parts]
            path_with_ns = '/'.join(ns_parts)
            return parent.find(path_with_ns, ns)
        return parent.find(path)

    def get_text(parent, path, default=""):
        elem = find_elem(parent, path)
        if elem is not None and elem.text is not None:
            return elem.text.strip()
        return default

    # Find main information block (infNFe)
    # Could be directly under root or under NFe
    inf_nfe = root.find(f".//{prefix}infNFe", ns)
    if inf_nfe is None:
        raise ValueError("Tag <infNFe> não encontrada no XML. Este arquivo pode não ser uma Nota Fiscal Eletrônica válida.")

    # 1. Identificação da NF-e (ide)
    ide = find_elem(inf_nfe, "ide")
    nfe_id = inf_nfe.attrib.get('Id', '').replace('NFe', '')
    
    ide_data = {
        "nNF": get_text(ide, "nNF"),
        "serie": get_text(ide, "serie"),
        "dhEmi": format_date(get_text(ide, "dhEmi") or get_text(ide, "dEmi")),
        "natOp": get_text(ide, "natOp"),
        "mod": get_text(ide, "mod"),
        "tpNF": "Saída" if get_text(ide, "tpNF") == "1" else "Entrada" if get_text(ide, "tpNF") == "0" else get_text(ide, "tpNF"),
        "chave": nfe_id
    }

    # 2. Emitente (emit)
    emit = find_elem(inf_nfe, "emit")
    emit_data = {}
    if emit is not None:
        ender = find_elem(emit, "enderEmit")
        emit_data = {
            "CNPJ": format_cnpj_cpf(get_text(emit, "CNPJ")),
            "CPF": format_cnpj_cpf(get_text(emit, "CPF")),
            "xNome": get_text(emit, "xNome"),
            "xFant": get_text(emit, "xFant"),
            "IE": get_text(emit, "IE"),
            "logradouro": get_text(ender, "xLgr"),
            "numero": get_text(ender, "nro"),
            "complemento": get_text(ender, "xCpl"),
            "bairro": get_text(ender, "xBairro"),
            "municipio": get_text(ender, "xMun"),
            "uf": get_text(ender, "UF"),
            "cep": format_cep(get_text(ender, "CEP")),
            "telefone": get_text(ender, "fone")
        }

    # 3. Destinatário (dest)
    dest = find_elem(inf_nfe, "dest")
    dest_data = {}
    if dest is not None:
        ender = find_elem(dest, "enderDest")
        dest_data = {
            "CNPJ": format_cnpj_cpf(get_text(dest, "CNPJ")),
            "CPF": format_cnpj_cpf(get_text(dest, "CPF")),
            "xNome": get_text(dest, "xNome"),
            "IE": get_text(dest, "IE"),
            "logradouro": get_text(ender, "xLgr"),
            "numero": get_text(ender, "nro"),
            "complemento": get_text(ender, "xCpl"),
            "bairro": get_text(ender, "xBairro"),
            "municipio": get_text(ender, "xMun"),
            "uf": get_text(ender, "UF"),
            "cep": format_cep(get_text(ender, "CEP")),
            "telefone": get_text(ender, "fone")
        }

    # 4. Produtos (det)
    # Find all det elements
    det_elements = inf_nfe.findall(f".//{prefix}det", ns)
    products = []
    for det in det_elements:
        prod = find_elem(det, "prod")
        if prod is not None:
            n_item = det.attrib.get('nItem', '')
            
            # Extract basic product fields
            c_prod = get_text(prod, "cProd")
            x_prod = get_text(prod, "xProd")
            ncm = get_text(prod, "NCM")
            cfop = get_text(prod, "CFOP")
            u_com = get_text(prod, "uCom")
            q_com = get_text(prod, "qCom")
            v_un_com = get_text(prod, "vUnCom")
            v_prod = get_text(prod, "vProd")
            
            # Optional values
            v_desc = get_text(prod, "vDesc", "0.00")
            v_frete = get_text(prod, "vFrete", "0.00")
            v_seg = get_text(prod, "vSeg", "0.00")
            v_outro = get_text(prod, "vOutro", "0.00")

            # Vehicle info (<veicProd>)
            veic = find_elem(prod, "veicProd")
            veic_data = None
            if veic is not None:
                veic_data = {
                    "tpOp": get_text(veic, "tpOp"),
                    "importar_pasta_xml": get_text(veic, "chassi"),
                    "cCor": get_text(veic, "cCor"),
                    "xCor": get_text(veic, "xCor"),
                    "pot": get_text(veic, "pot"),
                    "cilin": get_text(veic, "cilin"),
                    "pesoL": get_text(veic, "pesoL"),
                    "pesoB": get_text(veic, "pesoB"),
                    "nSerie": get_text(veic, "nSerie"),
                    "tpComb": get_text(veic, "tpComb"),
                    "nMotor": get_text(veic, "nMotor"),
                    "CMT": get_text(veic, "CMT"),
                    "dist": get_text(veic, "dist"),
                    "anoMod": get_text(veic, "anoMod"),
                    "anoFab": get_text(veic, "anoFab"),
                    "tpPint": get_text(veic, "tpPint"),
                    "tpVeic": get_text(veic, "tpVeic"),
                    "espVeic": get_text(veic, "espVeic"),
                    "VIN": get_text(veic, "VIN"),
                    "condVeic": get_text(veic, "condVeic"),
                    "cMod": get_text(veic, "cMod"),
                    "cCorDENATRAN": get_text(veic, "cCorDENATRAN"),
                    "lota": get_text(veic, "lota"),
                    "tpRest": get_text(veic, "tpRest")
                }

            # Product additional info (<infAdProd>)
            inf_ad_prod = get_text(det, "infAdProd")

            products.append({
                "nItem": n_item,
                "cProd": c_prod,
                "xProd": x_prod,
                "ncm": ncm,
                "cfop": cfop,
                "uCom": u_com,
                "qCom": float(q_com) if q_com else 0.0,
                "vUnCom": float(v_un_com) if v_un_com else 0.0,
                "vProd": float(v_prod) if v_prod else 0.0,
                "vDesc": float(v_desc) if v_desc else 0.0,
                "vFrete": float(v_frete) if v_frete else 0.0,
                "vSeg": float(v_seg) if v_seg else 0.0,
                "vOutro": float(v_outro) if v_outro else 0.0,
                "infAdProd": inf_ad_prod,
                "veicProd": veic_data
            })

    # 5. Totais (total)
    total = find_elem(inf_nfe, "total")
    icms_tot = find_elem(total, "ICMSTot") if total is not None else None
    
    total_data = {}
    if icms_tot is not None:
        total_data = {
            "vBC": format_currency(get_text(icms_tot, "vBC")),
            "vICMS": format_currency(get_text(icms_tot, "vICMS")),
            "vBCST": format_currency(get_text(icms_tot, "vBCST")),
            "vST": format_currency(get_text(icms_tot, "vST")),
            "vProd": format_currency(get_text(icms_tot, "vProd")),
            "vFrete": format_currency(get_text(icms_tot, "vFrete")),
            "vSeg": format_currency(get_text(icms_tot, "vSeg")),
            "vDesc": format_currency(get_text(icms_tot, "vDesc")),
            "vII": format_currency(get_text(icms_tot, "vII")),
            "vIPI": format_currency(get_text(icms_tot, "vIPI")),
            "vPIS": format_currency(get_text(icms_tot, "vPIS")),
            "vCOFINS": format_currency(get_text(icms_tot, "vCOFINS")),
            "vOutro": format_currency(get_text(icms_tot, "vOutro")),
            "vNF": format_currency(get_text(icms_tot, "vNF"))
        }
    else:
        # Fallback if totals are not parsed properly or formatted differently
        total_data = {k: "R$ 0,00" for k in [
            "vBC", "vICMS", "vBCST", "vST", "vProd", "vFrete", "vSeg", 
            "vDesc", "vII", "vIPI", "vPIS", "vCOFINS", "vOutro", "vNF"
        ]}

    # 6. Informações Adicionais (infAdic)
    inf_adic = find_elem(inf_nfe, "infAdic")
    inf_adic_data = {
        "infAdFisco": get_text(inf_adic, "infAdFisco"),
        "infCpl": get_text(inf_adic, "infCpl")
    }

    return {
        "ide": ide_data,
        "emit": emit_data,
        "dest": dest_data,
        "products": products,
        "total": total_data,
        "infAdic": inf_adic_data
    }


def importar_pasta_xml(pasta_base="xml", callback_progresso=None):
    """
    Scans the 'xml' folder for .xml files (ignoring sub-folders like 'integrados'),
    parses each one, saves vehicles to the SQLite DB and moves every processed
    file to xml/integrados regardless of outcome.

    callback_progresso(msg: str) is called for each step if provided.

    Returns a dict: { total, importadas, ignoradas, erros, detalhes[] }
    """
    import os
    import shutil
    from db_nfe import salvar_nfe

    pasta_integrados = os.path.join(pasta_base, "integrados")
    os.makedirs(pasta_integrados, exist_ok=True)
    pasta_rejeitados = os.path.join(pasta_base, "rejeitados")
    os.makedirs(pasta_rejeitados, exist_ok=True)

    def log(msg):
        if callback_progresso:
            callback_progresso(msg)

    # Only scan files at the TOP level of pasta_base (not sub-folders)
    try:
        entries = os.listdir(pasta_base)
    except FileNotFoundError:
        return {"total": 0, "importadas": 0, "ignoradas": 0, "erros": 0,
                "detalhes": [f"Pasta '{pasta_base}' não encontrada."]}

    arquivos_xml = [
        os.path.join(pasta_base, f)
        for f in entries
        if f.lower().endswith(".xml") and os.path.isfile(os.path.join(pasta_base, f))
    ]

    total = len(arquivos_xml)
    importadas = 0
    ignoradas = 0
    erros = 0
    detalhes = []

    if total == 0:
        return {"total": 0, "importadas": 0, "ignoradas": 0, "erros": 0,
                "detalhes": ["Nenhum arquivo .xml encontrado na pasta 'xml'."]
                }

    log(f"Encontrados {total} arquivo(s) XML para processar...")

    for i, caminho in enumerate(arquivos_xml, 1):
        nome = os.path.basename(caminho)
        log(f"[{i}/{total}] Processando: {nome} ...")

        try:
            data = parse_nfe(caminho)
            sucesso, msg = salvar_nfe(data)

            if sucesso:
                importadas += 1
                detalhes.append(f"✅ {nome}: {msg}")
                log(f"   ✅ {msg}")
            else:
                ignoradas += 1
                detalhes.append(f"⚠️  {nome}: {msg}")
                log(f"   ⚠️  {msg}")

        except Exception as e:
            erros += 1
            detalhes.append(f"❌ {nome}: Erro - {str(e)}")
            log(f"   ❌ Erro: {e}")

        # Move file to integrados regardless of outcome
        destino_integrados = os.path.join(pasta_integrados, nome)
        # If file with same name already exists in integrados, append a counter
        base, ext = os.path.splitext(nome)
        counter = 1
        while os.path.exists(destino_integrados):
            destino_integrados = os.path.join(pasta_integrados, f"{base}_{counter}{ext}")
            counter += 1
        try:
            shutil.move(caminho, destino_integrados)
            log(f"   📁 Movido para: integrados/{os.path.basename(destino_integrados)}")
        except Exception as move_err:
            log(f"   ⚠️  Não foi possível mover o arquivo: {move_err}")

    log(f"\nConcluído! Importadas: {importadas} | Ignoradas: {ignoradas} | Erros: {erros}")

    return {
        "total": total,
        "importadas": importadas,
        "ignoradas": ignoradas,
        "erros": erros,
        "detalhes": detalhes
    }

