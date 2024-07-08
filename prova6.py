import streamlit as st
import requests
import pandas as pd
import json
from beatifulsoup4 import BeautifulSoup
import fitz
import re
from concurrent.futures import ThreadPoolExecutor

# Cache the data fetching
@st.cache_data(show_spinner=False)
def fetch_data():
    url1 = "https://cir-reports.cir-safety.org/FetchCIRReports?&pagingcookie=%26lt%3Bcookie+page%3D%26quot%3B1%26quot%3B%26gt%3B%26lt%3Bpcpc_name+last%3D%26quot%3BPEG-50+Stearate%26quot%3B+first%3D%26quot%3B1%2C10-Decanediol%26quot%3B+%2F%26gt%3B%26lt%3Bpcpc_ingredientidname+last%3D%26quot%3BPEG-50+Stearate%26quot%3B+first%3D%26quot%3B1%2C10-Decanediol%26quot%3B+%2F%26gt%3B%26lt%3Bpcpc_cirrelatedingredientsid+last%3D%26quot%3B%7BC223037E-F278-416D-A287-2007B9671D0C%7D%26quot%3B+first%3D%26quot%3B%7B940AF697-52B5-4A3A-90A6-B9DB30EF4A7E%7D%26quot%3B+%2F%26gt%3B%26lt%3B%2Fcookie%26gt%3B&page=1"
    url2 = "https://cir-reports.cir-safety.org/FetchCIRReports?&pagingcookie=%26lt%3Bcookie+page%3D%26quot%3B1%26quot%3B%26gt%3B%26lt%3Bpcpc_name+last%3D%26quot%3BPEG-50+Stearate%26quot%3B+first%3D%26quot%3B1%2C10-Decanediol%26quot%3B+%2F%26gt%3B%26lt%3Bpcpc_ingredientidname+last%3D%26quot%3BPEG-50+Stearate%26quot%3B+first%3D%26quot%3B1%2C10-Decanediol%26quot%3B+%2F%26gt%3B%26lt%3Bpcpc_cirrelatedingredientsid+last%3D%26quot%3B%7BC223037E-F278-416D-A287-2007B9671D0C%7D%26quot%3B+first%3D%26quot%3B%7B940AF697-52B5-4A3A-90A6-B9DB30EF4A7E%7D%26quot%3B+%2F%26gt%3B%26lt%3B%2Fcookie%26gt%3B&page=2"
    
    with ThreadPoolExecutor() as executor:
        future1 = executor.submit(requests.get, url1)
        future2 = executor.submit(requests.get, url2)
        
        response1 = future1.result().text
        response2 = future2.result().text
    
    data1 = json.loads(response1)
    data2 = json.loads(response2)
    
    df1 = pd.DataFrame(data1["results"])
    df2 = pd.DataFrame(data2["results"])
    
    df = pd.concat([df1, df2], ignore_index=True)
    return df

@st.cache_data(show_spinner=False)
def get_pdf_link(ingredient_id):
    url = f"https://cir-reports.cir-safety.org/cir-ingredient-status-report/?id={ingredient_id}"
    response = requests.get(url).text
    soup = BeautifulSoup(response, "lxml")
    tab = soup.find("table")
    attach = tab.find("a")
    pidieffe = attach["href"]
    linktr = str(pidieffe).replace("../", "")
    pdf_link = "https://cir-reports.cir-safety.org/" + linktr
    return pdf_link

def extract_text_from_pdf_url(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            pdf_data = response.content
            text_pages = []
            document = fitz.open(stream=pdf_data, filetype="pdf")
            for page_num in range(len(document)):
                try:
                    page = document.load_page(page_num)
                    page_text = page.get_text()
                    if page_text:
                        text_pages.append((page_text, page_num + 1))
                    else:
                        st.warning(f"Nessun testo trovato nella pagina {page_num + 1}")
                except Exception as e:
                    st.error(f"Errore durante l'estrazione del testo dalla pagina {page_num + 1}: {str(e)}")
            return text_pages
        else:
            st.error(f"Errore durante l'apertura del PDF. Codice di stato: {response.status_code}")
    except Exception as e:
        st.error(f"Errore generale durante l'operazione di estrazione del testo dal PDF: {str(e)}")

def extract_noael_and_ld50(text_pages):
    noael_pattern = re.compile(r'(.*?NOAEL.*?\d+\.?\d*\s*[a-zA-Z/]+.*?(\.|$))', re.IGNORECASE)
    ld50_pattern = re.compile(r'(.*?LD50.*?\d+\.?\d*\s*[a-zA-Z/]+.*?(\.|$))', re.IGNORECASE)
    
    noael_matches = []
    ld50_matches = []
    
    for text, page_num in text_pages:
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if re.search(noael_pattern, line):
                previous_line = lines[i - 1] if i > 0 else ""
                formatted_match = highlight_numbers(f"{previous_line}\n{line}")
                noael_matches.append((formatted_match, page_num))
            if re.search(ld50_pattern, line):
                previous_line = lines[i - 1] if i > 0 else ""
                formatted_match = highlight_numbers(f"{previous_line}\n{line}")
                ld50_matches.append((formatted_match, page_num))
    
    return noael_matches, ld50_matches

def highlight_numbers(text):
    text = re.sub(r'(\d+,\d+\.?\d*)', r'<b style="color:red;">\1</b>', text)
    
    highlight_words = ["rat", "NOAEL", "LD50", "rats", "rabbits", "ld50", "g/kg", "mg/kg/day", "mg/kg"]
    if highlight_words:
        pattern = r'\b(' + '|'.join(re.escape(word) for word in highlight_words) + r')\b'
        text = re.sub(pattern, r'<span style="background-color:yellow; color:black;">\1</span>', text)
    
    return text

def main():
    st.set_page_config(page_title="CIR Ingredient Report", layout="wide")
    
    st.title("CIR Ingredient Report")
    st.markdown("Benvenuti nell'applicazione per la consultazione dei report sugli ingredienti CIR. Seleziona un ingrediente per ottenere maggiori informazioni.")

    st.write("### Caricamento dati...")
    df = fetch_data()
    st.write("Dati caricati con successo!")
    
    ingredient = st.selectbox("Scrivi il nome dell'ingrediente", [""] + df["pcpc_ingredientname"].unique().tolist(), index=0)
    
    if ingredient:
        ingredient_row = df[df["pcpc_ingredientname"] == ingredient]
        
        if not ingredient_row.empty:
            ingredient_id = ingredient_row.iloc[0]["pcpc_ingredientid"]
            pdf_link = get_pdf_link(ingredient_id)
            
            st.write(f"Link al PDF: [Clicca qui per visualizzare il PDF]({pdf_link})")
            
            if st.button("Estrai testo dal PDF"):
                with st.spinner('Estrazione del testo in corso...'):
                    try:
                        text_pages = extract_text_from_pdf_url(pdf_link)
                        
                        noael_matches, ld50_matches = extract_noael_and_ld50(text_pages)
                        
                        if noael_matches:
                            st.write("### Valori NOAEL trovati:")
                            noael_df = pd.DataFrame(noael_matches, columns=["NOAEL value", "Page"])
                            st.write(noael_df.to_html(escape=False, index=False), unsafe_allow_html=True)
                        
                        if ld50_matches:
                            st.write("### Valori LD50 trovati:")
                            ld50_df = pd.DataFrame(ld50_matches, columns=["LD50 value", "Page"])
                            st.write(ld50_df.to_html(escape=False, index=False), unsafe_allow_html=True)
                        
                        if not noael_matches and not ld50_matches:
                            st.write("Nessun valore NOAEL o LD50 trovato.")
                        
                    except Exception as e:
                        st.error(f"ERRORE: {e}")
        else:
            st.warning("Ingrediente non trovato.")

if __name__ == "__main__":
    main()
