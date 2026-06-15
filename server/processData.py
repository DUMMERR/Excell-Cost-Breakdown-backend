
import re
import os
import sys
import pandas as pd
import json
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from cacheManagement import CacheManager

cache = CacheManager()

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

JSON_FILE_PATH = "./exchange_data/exchageRatesCached.json"

model = SentenceTransformer("all-MiniLM-L6-v2")

path = sys.argv[1] if len(sys.argv) > 1 else '.'


keywords = ["amount", "spend", "cost", "total"]
recipient_keywords = [ "vendor", "name", "merchant"]
keyword_embeddings = model.encode(keywords, convert_to_numpy=True)
recipient_embeddings = model.encode(recipient_keywords, convert_to_numpy=True)

ECB_RATES_CACHE = {}

def getCache():
    return cache.retrieveCache()

  
async def read_cached_data() -> dict | None:
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            if len(data) > 0:
                first_object = data[0]
                if isinstance(first_object, dict):
                    return first_object
                print("Warning: The first item in the list is not a dictionary.")
                return None
            print("Warning: The JSON list is empty.")
            return None
        if isinstance(data, dict):
            return data

        print("Warning: JSON root structure is neither a list nor a dictionary.")
        return None

    except FileNotFoundError:
        print(f"Error: The file {JSON_FILE_PATH} does not exist yet.")
        return None

    except json.JSONDecodeError:
        print("Warning: The JSON file was temporarily unreadable. Retrying soon...")
        return None
    
MASTER_CURRENCY_DECLARATIONS = {
    "EUR": ["EUR", "€"],
    "USD": ["USD", "US$", "$"],
    "JPY": ["JPY", "¥"],
    "CZK": ["CZK", "KČ", "Kč"],
    "DKK": ["DKK", "KR.", "KR"],
    "GBP": ["GBP", "£"],
    "HUF": ["HUF", "FT"],
    "PLN": ["PLN", "ZŁ", "ZL"],
    "RON": ["RON", "LEI", "LEU"],
    "SEK": ["SEK", "KR.", "KR"],
    "CHF": ["CHF", "FR."],
    "ISK": ["ISK", "KR.", "KR"],
    "NOK": ["NOK", "KR.", "KR"],
    "TRY": ["TRY", "₺"],
    "AUD": ["AUD", "AU$", "A$", "$"],
    "BRL": ["BRL", "R$"],
    "CAD": ["CAD", "CA$", "C$", "$"],
    "CNY": ["CNY", "RMB", "¥"],
    "HKD": ["HKD", "HK$", "$"],
    "IDR": ["IDR", "RP"],
    "ILS": ["ILS", "₪"],
    "INR": ["INR", "₹"],
    "KRW": ["KRW", "₩"],
    "MXN": ["MXN", "MX$", "$"],
    "MYR": ["MYR", "RM"],
    "NZD": ["NZD", "NZ$", "$"],
    "PHP": ["PHP", "₱"],
    "SGD": ["SGD", "S$", "$"],
    "THB": ["THB", "฿"],
    "ZAR": ["ZAR", "R"],
}


def spendAmountProcessing(row, spend_col, live_rates_json=ECB_RATES_CACHE):
    raw_spend = row[spend_col]
    if pd.isna(raw_spend):
        return None, "failed to extract (null)"
    if isinstance(raw_spend, str):
        cleaned_str = raw_spend.strip().replace(",", "")
        if cleaned_str == "":
            return None, "failed to extract (empty string)"
        try:
            cleaned_spend = float(cleaned_str)
        except ValueError:
            return None, "failed to extract (invalid string format)"
    else:
        cleaned_spend = float(raw_spend)
    if cleaned_spend < 0:
        return None, "failed to extract (negative value)"
    val_str = str(raw_spend).upper().strip()
    numeric_string = "".join(c for c in val_str if c.isdigit() or c in [".", "-"])
    try:
        if not numeric_string or numeric_string in [".", "-", ".-", "-."]:
            return None, "Invalid value"
        numeric_value = float(numeric_string)
    except ValueError:
        return None, "Invalid value"
    allowed_currencies = {
        currency: variants
        for currency, variants in MASTER_CURRENCY_DECLARATIONS.items()
        if currency in live_rates_json
    }
    row_text = " ".join(row.dropna().astype(str)).upper()
    if allowed_currencies:
        pattern = r"\b(" + "|".join(allowed_currencies.keys()) + r")\b"
        code_match = re.search(pattern, row_text)
        if code_match:
            return numeric_value, code_match.group(1)
    for currency, variants in allowed_currencies.items():
        for variant in variants:
            if variant.upper() in row_text:
                return numeric_value, currency
    return numeric_value, "No denomination was found"


def findSpendColumn(df):
    if df is None or df.empty:
        return None
    column_headers = list(df.columns)
    clean_headers = [str(h).strip() for h in column_headers]
    currency_symbols = re.compile(r'[\$\€\£\¥\₩\₽\₹\₪]')
    currency_codes = re.compile(
    r'(?<=[\d.,\s])(USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|HKD|NZD)\b', re.IGNORECASE)
    header_embeddings = model.encode(clean_headers, convert_to_numpy=True)
    similarity_matrix = cosine_similarity(header_embeddings, keyword_embeddings)
    scores = np.max(similarity_matrix, axis=1)
    for idx, col_name in enumerate(column_headers):
        header_has_currency = bool(currency_symbols.search(clean_headers[idx]) or currency_codes.search(clean_headers[idx]))
        if header_has_currency:
            scores[idx] += 0.25 
        column_data = df[col_name].dropna().head(20).astype(str).str.strip()
        if column_data.empty:
            continue
        currency_row_count = sum(bool(currency_symbols.search(row) or currency_codes.search(row)) for row in column_data)
        if currency_row_count / len(column_data) > 0.25:
            scores[idx] = 1.0
    best_match_idx = np.argmax(scores)
    if scores[best_match_idx] < 0.3:
        return None
    return column_headers[best_match_idx], best_match_idx


def standardizeCompany(raw_name):
    if pd.isna(raw_name):
        return ""
    return str(raw_name).strip().upper()


def findVendorColumnByHeader(df, keyword_embeddings = recipient_embeddings):
    if df is None or df.empty:
        return None
    column_headers = list(df.columns)
    clean_headers = [str(h).strip() for h in column_headers]
    header_embeddings = model.encode(clean_headers, convert_to_numpy=True)
    similarity_matrix = cosine_similarity(header_embeddings, keyword_embeddings)
    scores = np.max(similarity_matrix, axis=1)
    best_match_idx = np.argmax(scores)
    if scores[best_match_idx] < 0.3:
        return None
    return column_headers[best_match_idx], best_match_idx


async def processExcellFile(file_object, user_currency):
    user_currency = str(user_currency).upper().strip()
    if getattr(cache, "Renew", True):
        global ECB_RATES_CACHE
        ECB_RATES_CACHE = getCache()
        cache.Renew = False

    try:
  
        if not ECB_RATES_CACHE or len(ECB_RATES_CACHE) <= 1:
            ECB_RATES_CACHE = getCache()
            print("attempt 1")
        if ECB_RATES_CACHE is None:
            ECB_RATES_CACHE = await read_cached_data()
            print("attempt 2")
        if ECB_RATES_CACHE is None:
            raise ValueError("The 'ecb' cache source could not be resolved.")
        ecb_rates = dict(ECB_RATES_CACHE)
    except Exception as error:
        return {
            "status": "error",
            "error": f"Cache Initialization Error: {str(error)}"
        }
    try:
        try:
            df = pd.read_excel(file_object, engine="calamine")
        except Exception:
            file_object.seek(0)
            df = pd.read_excel(file_object)
    except Exception as e:
        return {
            "status": "error",
            "error": "Internal Error: Could not read Excel file data structure.",
        }
    df = df.dropna(how='all', axis=1) 
    df = df.loc[:, ~df.columns.astype(str).str.startswith('Unnamed:')] 
    spend_result = findSpendColumn(df)
    if not spend_result:
        return {
            "status": "error",
            "error": "Internal Error: Spend or cost column could not be detected automatically."
        }
  
    spend_col, spend_idx = spend_result
    vendor_result = findVendorColumnByHeader(df, recipient_embeddings)
    if vendor_result and isinstance(vendor_result, tuple):
        company_col, company_idx = vendor_result
    else:
        company_col, company_idx = None, None
    if not company_col or company_col == spend_col:
        column_list = df.columns.to_list()
        remaining_cols = [c for c in column_list if c != spend_col]
        company_col = remaining_cols[0] if remaining_cols else spend_col

        
    summary_data = {}
    failed_rows = []
    if user_currency not in ecb_rates:
        ecb_rates[user_currency] = 1.0  

    for index, row in df.iterrows():
        excel_row_number = index + 2 
        
        try:
            raw_company = row.get(company_col)
            raw_spend = row.get(spend_col)
            if pd.isna(raw_company):
                failed_rows.append({
                    "row_number": excel_row_number, 
                    "reason": "Missing metadata fields."
                })
                continue

            company_name = standardizeCompany(raw_company)
            raw_amount, currency_code = spendAmountProcessing(row, spend_col, ecb_rates)
            current_currency_rate = ecb_rates.get(currency_code)
      
            if (raw_amount == 0.0 and str(raw_spend).strip() not in ["0", "0.0"]) or raw_amount is None or current_currency_rate is None:
                failed_rows.append({
                    "row_number": excel_row_number, 
                    "reason": currency_code
                })
                continue
          
            if not current_currency_rate and currency_code == user_currency:
                current_currency_rate = 1.0
            
            if not current_currency_rate:
                failed_rows.append({
                    "row_number": excel_row_number, 
                    "reason": f"Unsupported registry code: {currency_code}"
                })
                continue 
            normalized_eur_value = float(raw_amount) / float(current_currency_rate)
            data_key = (company_name, currency_code)
            summary_data[data_key] = summary_data.get(data_key, 0.0) + normalized_eur_value

        except Exception as row_error:
            failed_rows.append({
                "row_number": excel_row_number,
                "reason": f"Unexpected runtime error: {str(row_error)}"
            })

    flat_expense_list = [
        {"company": comp,"og-currency":curr, "normalized_value_eur": round(total_spend, 2)} 
        for (comp,curr), total_spend in summary_data.items()
    ]

    target_currencies = list(set([user_currency, "EUR", "USD"]))
    conversionMatrices = []

    for target in target_currencies:
        target_rate = ecb_rates.get(target, 1.0)
        conversionMatrices.append({
            "currency_code": target,
            "rate_against_eur": round(target_rate, 4),
            "is_user_default": target == user_currency
        })

    return {
        "status": "success" if not failed_rows else "partial_success",
        "exchange_rates": ecb_rates,
        "conversionMatrices": conversionMatrices, 
        "fileObjData": flat_expense_list,
        "failedRowCount": len(failed_rows),
        "failedRowDetails": failed_rows
    }

def returnPresentages():
    pass
