import json
from urllib import request
import pandas as pd
from pandas import json_normalize
import csv
import numpy as np
import scipy.stats as stats
from scipy.stats import multinomial
from scipy.stats import chisquare
import os
import urllib.parse

def fetch_raw_table_data(file_name):
    file_path = file_name
    url = "https://resultados.gob.ar/backend-difu/nomenclator/getNomenclator"

    if not os.path.exists(file_path):
        print("File not found. Fetching raw table data...")
        try:
            request.urlretrieve(url, file_path)
            print("Data fetched and saved to " +file_path+ " successfully.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
    else:
        print("File already exists.")

# Returns the list of tables with their index and code
def extract_tables(json_object):
    tables = []
    for index, table in enumerate(json_object['amb'][13]['ambitos']):
        if(table['l'] == 8) and table['co'].endswith('X'):
            tables.append({'index': index, 'numero_mesa': table['co']})
    
    print(f'Identified {len(tables)} tables to work on')
    return tables


def search_json(json_object, substring, path=None):
    if path is None:
        path = []
    if isinstance(json_object, dict):
        for key, value in json_object.items():
            new_path = path + [key]
            for result in search_json(value, substring, new_path):
                yield result
    elif isinstance(json_object, list):
        for index, value in enumerate(json_object):
            new_path = path + [index]
            for result in search_json(value, substring, new_path):
                yield result
    elif isinstance(json_object, str) and substring in json_object:
        # Here, you can customize how much context to provide, e.g., +-10 characters
        start = max(0, json_object.find(substring) - 10)
        end = min(len(json_object), start + len(substring) + 20)
        context = json_object[start:end]
        yield {'path': path, 'string': json_object, 'context': context, 'substring_location': json_object.find(substring)}



def get_table_data(table):
    print(f"${table['numero_mesa']} fetching data...")

    url = f"https://resultados.gob.ar/backend-difu/scope/data/getScopeData/{table['numero_mesa']}/1"
    
    try:
        with request.urlopen(url) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
            else:
                return f"Failed to fetch data, status code: {response.status}"
    except Exception as e:
        return f"An error occurred: {str(e)}"



def generate_url(json_data):
    try:
        # Extracting information from JSON
        eleccion_id = int(json_data['id']['eleccionId'])
        codigo = json_data['id']['idAmbito']['codigo']

        # Organizing fathers data by level for easy access
        fathers = {int(father['level']): father for father in json_data['fathers']}
        
        # Constructing the URL
        url_parts = [str(eleccion_id)]
        for level in sorted(fathers.keys()):
            name = fathers[level]['name'].replace(' ', '-').replace('---', '-')
            code = fathers[level]['codigo']
            url_parts.extend([code, urllib.parse.quote(name)])
        
        url_parts.append(codigo)
        url = "https://resultados.gob.ar/elecciones/" + "/".join(url_parts)
        
        return url
    
    except Exception as e:
        return f"An error occurred: {str(e)}"
preferences = {
    "132": 0.2383,  # JxC
    "134": 0.3668,  # UxP
    "135": 0.2998,  # LLA
    "136": 0.0273,  # FIT
    "133": 0.0678,  # Hacemos Nuestro Pais   
}

def chi_squared_test(votes, preferences):
    total_votes = sum(votes.values())
    expected_votes = {party: total_votes * pref for party, pref in preferences.items()}
    
    observed = list(votes.values())
    expected = list(expected_votes.values())
    
    chi2, p = stats.chisquare(f_obs=observed, f_exp=expected)
    
    return chi2, p

def update_last_processed_table(index):
    with open('last_processed_table.txt', 'w') as f:
        f.write(str(index))

def get_last_processed_table():
    try:
        with open('last_processed_table.txt', 'r') as f:
            return int(f.read())
    except FileNotFoundError:
        return -1  # Return -1 if the file does not exist
    
def write_to_csv(data, writer, fieldnames):
    row = {'numero_mesa': data['numero_mesa']}

    # Ubicacion
    for key, value in data['ubicacion'].items():
        row[key] = value['name']

    # Votes information
    total_votes = data['resultados']['afirmativos']
    winning_party = None
    max_votes = -1
    for party in data['resultados']['votes_per_party']:
        votes = party['votes']

        vote_percentage = (party['votes'] / total_votes) if total_votes != 0 else 0
        row[party['name']] = votes
        row[party['name']+' - %'] = "{:.4f}".format(vote_percentage)
        # Determine winning party
        if votes > max_votes:
            max_votes = votes
            winning_party = party['name']
    
    # Nulos, abstencion, etc...
    for key in ['nulos', 'abstencion', 'afirmativos', 'blancos', 'impugnados', 'votos_totales', 'census']:
        row[key] = data['resultados'][key]

    # Chi squared calculation
    affirmativos = data['resultados']['afirmativos']
    expected_votes = {code: affirmativos * pref for code, pref in preferences.items()}

    observed_votes = [party['votes'] for party in data['resultados']['votes_per_party'] if party['code'] in preferences]
    expected_votes_list = [expected_votes[party['code']] for party in data['resultados']['votes_per_party'] if party['code'] in preferences]

    chi2, p = stats.chisquare(f_obs=observed_votes, f_exp=expected_votes_list)

    row['Chi Squared'] = chi2
    row['P Value'] = p
    if p > 1e-10:
        row['Recommendation'] = "Normal"
    elif p > 1e-20:
        row['Recommendation'] = "Outlier Moderado"
    else:
        row['Recommendation'] = "Outlier Extremo"

    row['Ganador'] = winning_party
    writer.writerow(row)

def extract_location(data):
    result = {}
        # Extract fathers information
    fathers = data.get("fathers", [])
    for father in fathers:
        level = int(father["level"])
        if level == 1:
            result["Pais"] = {"name": "Argentina", "code": "1"}
        elif level == 2:
            result["Distrito"] = {"name": father["name"], "code": father["codigo"]}
        elif level == 4:
            result["Seccion"] = {"name": father["name"], "code": father["codigo"]}
        elif level == 5:
            result["Comuna_Municipio"] = {"name": father["name"], "code": father["codigo"]}
        elif level == 6:
            result["Circuito"] = {"name": father["name"], "code": father["codigo"]}
        elif level == 7:
            result["Local_de_Comicio"] = {"name": father["name"], "code": father["codigo"]}
        elif level == 8:
            result["Numero_de_Mesa"] = {"name": father["name"], "code": father["codigo"]}

    return result

def extract_votes(data):
    result = {}
    
    # Extract votes per party
    parties = data.get("partidos", [])
    result["votes_per_party"] = [
        {"votes": party["votos"], "name": party["name"], "code": party["code"]} for party in parties
    ]

    # Extract other required information
    result["nulos"] = data.get("nulos", 0)
    result["abstencion"] = data.get("abstencion", 0)
    result["afirmativos"] = data.get("afirmativos", 0)
    result['blancos'] = data.get("blancos", 0)
    result['impugnados'] = data.get("impugnados", 0)
    result['votos_totales'] = data.get("totalVotos", 0)
    result['census'] = data.get("census", 0)

    return result


def get_tables_to_process(file_name):
    with open(file_name) as f:
            data = json.load(f)

            tables = extract_tables(data)

            last_processed_table = get_last_processed_table()
            print(last_processed_table)
            if last_processed_table == len(tables) - 1:
                print("All tables have already been processed.")
                exit()


            if last_processed_table == -1:
                print("No tables have been processed yet.")
                to_process_tables = tables[0:]
            else:
                to_process_tables = tables[last_processed_table:]  # Change 100 to the number of tables you want to process

            print(f"{len(to_process_tables)} tables about to be process:")
            return to_process_tables, last_processed_table

def get_fieldnames():
    fieldnames = [
                'numero_mesa', 
                'Local_de_Comicio', 'Comuna_Municipio', 'Seccion', 'Circuito', 'Distrito', 'Pais',
                'UNION POR LA PATRIA', 'UNION POR LA PATRIA - %', 
                'LA LIBERTAD AVANZA','LA LIBERTAD AVANZA - %',
                'JUNTOS POR EL CAMBIO', 'JUNTOS POR EL CAMBIO - %', 
                'HACEMOS POR NUESTRO PAIS',  'HACEMOS POR NUESTRO PAIS - %',  
                'FRENTE DE IZQUIERDA Y DE TRABAJADORES - UNIDAD', 'FRENTE DE IZQUIERDA Y DE TRABAJADORES - UNIDAD - %',  # Add other parties as required
                'nulos', 'abstencion', 'afirmativos', 'blancos', 'impugnados', 'votos_totales', 'census',
                'Chi Squared', 'P Value',  'Ganador', 'Recommendation'
            ]   
    return fieldnames

def main():
    FILE_NAME="raw_table_data.json"
    OUTPUT="output.csv"

    # Call the function that gets the nomenclator data, used for getting the table codes
    # Stores it in FILE_NAME
    
    fetch_raw_table_data(FILE_NAME)
    
    # Get the tables of the elections (codes, ids) based on the last processed table
    to_process_tables, last_processed_table = get_tables_to_process(FILE_NAME)
    
    with open(OUTPUT, 'a', newline='', encoding='utf-8') as csvfile:
        
        fieldnames = get_fieldnames()
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if last_processed_table == -1:  # If no table has been processed, write the header
            print("Writing header...")
            writer.writeheader()

        for index, table in enumerate(to_process_tables, start=last_processed_table + 1):
            try: 
                result = get_table_data(table)
                table['resultados'] = extract_votes(result)
                table['ubicacion'] = extract_location(result)
                write_to_csv(table, writer, fieldnames)
                update_last_processed_table(index)
            except Exception as e:
                print(f"An error occurred while processing table {table['numero_mesa']}: {str(e)}")
                continue  # Skip to the next table


if __name__ == '__main__':
    main()


