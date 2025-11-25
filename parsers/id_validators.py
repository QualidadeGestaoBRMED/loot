import re
import json
from enum import Enum
from typing import Optional

# --- 1. Definições ---

class DocType(Enum):
    CPF = "CPF"
    CNPJ = "CNPJ"  # <--- NOVO TIPO
    PASSPORT_BR = "PASSPORT_BR"
    PASSPORT_FOREIGN = "PASSPORT_FOREIGN"
    UNKNOWN = "UNKNOWN"

def clean_digits(value: str) -> str:
    if not value: return ""
    return re.sub(r'\D', '', str(value))

def clean_alphanumeric(value: str) -> str:
    if not value: return ""
    return re.sub(r'[^A-Za-z0-9]', '', str(value)).upper()

# --- 2. Validadores Específicos ---

def is_cpf_valid(cpf: str) -> bool:
    cpf_clean = clean_digits(cpf)
    if len(cpf_clean) != 11 or len(set(cpf_clean)) == 1:
        return False
    soma = sum(int(cpf_clean[i]) * (10 - i) for i in range(9))
    d1 = (soma * 10 % 11) % 10
    soma = sum(int(cpf_clean[i]) * (11 - i) for i in range(10))
    d2 = (soma * 10 % 11) % 10
    return d1 == int(cpf_clean[9]) and d2 == int(cpf_clean[10])

def is_cnpj_valid(cnpj: str) -> bool: # <--- NOVA FUNÇÃO
    """Valida CNPJ (14 dígitos) via Módulo 11."""
    cnpj_clean = clean_digits(cnpj)
    if len(cnpj_clean) != 14 or len(set(cnpj_clean)) == 1:
        return False

    def get_verifying_digit(sub_cnpj, weights):
        soma = sum(int(digit) * weight for digit, weight in zip(sub_cnpj, weights))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    # Pesos padrão do CNPJ
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    d1 = get_verifying_digit(cnpj_clean[:12], weights_1)
    d2 = get_verifying_digit(cnpj_clean[:13], weights_2)

    return d1 == int(cnpj_clean[12]) and d2 == int(cnpj_clean[13])

def is_passport_br_valid(value: str) -> bool:
    clean = clean_alphanumeric(value)
    return bool(re.match(r'^[A-Z]{2}\d{6}$', clean))

def is_generic_passport_valid(value: str) -> bool:
    clean = clean_alphanumeric(value)
    return bool(re.match(r'^[A-Z0-9]{6,15}$', clean))

# --- 3. O Detector (Funil) ---

def detect_doc_type(value: str) -> DocType:
    if not value: return DocType.UNKNOWN
    
    clean = clean_alphanumeric(value)
    digits_only = clean_digits(value)

    # Prioridade 1: Tamanho exato numérico (CPF ou CNPJ)
    if len(digits_only) == 11:
        return DocType.CPF
    
    if len(digits_only) == 14: # <--- DETECÇÃO CNPJ
        return DocType.CNPJ

    # Prioridade 2: Passaporte BR
    if is_passport_br_valid(clean):
        return DocType.PASSPORT_BR

    # Prioridade 3: Passaporte Gringo
    if is_generic_passport_valid(clean):
        return DocType.PASSPORT_FOREIGN

    return DocType.UNKNOWN

# --- 4. O Maestro (Processamento) ---

def process_document(value: str) -> dict:
    doc_type = detect_doc_type(value)
    
    result = {
        "original_input": value,
        "type": doc_type.value,
        "is_valid": False,
        "clean_value": None,
        "formatted": None
    }

    if doc_type == DocType.CPF:
        result["is_valid"] = is_cpf_valid(value)
        clean = clean_digits(value)
        result["clean_value"] = clean
        if result["is_valid"]:
            result["formatted"] = f"{clean[:3]}.{clean[3:6]}.{clean[6:9]}-{clean[9:]}"

    elif doc_type == DocType.CNPJ: # <--- TRATAMENTO CNPJ
        result["is_valid"] = is_cnpj_valid(value)
        clean = clean_digits(value)
        result["clean_value"] = clean
        if result["is_valid"]:
            # Formato: 12.345.678/0001-90
            result["formatted"] = f"{clean[:2]}.{clean[2:5]}.{clean[5:8]}/{clean[8:12]}-{clean[12:]}"

    elif doc_type == DocType.PASSPORT_BR:
        result["is_valid"] = True
        clean = clean_alphanumeric(value)
        result["clean_value"] = clean
        result["formatted"] = clean

    elif doc_type == DocType.PASSPORT_FOREIGN:
        result["is_valid"] = True
        clean = clean_alphanumeric(value)
        result["clean_value"] = clean
        result["formatted"] = clean
    
    return result

# --- 5. Teste ---
if __name__ == "__main__":
    testes = [
        "33.592.510/0001-54", # CNPJ da Microsoft Brasil (Válido)
        "12345678000199",     # CNPJ Formato válido, matemática inválida
        "AB123456",           # Passaporte BR
        "12345678909",        # CPF
    ]
    
    print(f"{'INPUT':<20} | {'JSON OUTPUT'}")
    print("-" * 80)
    
    for t in testes:
        resultado = process_document(t)
        print(json.dumps(resultado, ensure_ascii=False))