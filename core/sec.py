import json
import os
import requests


def get_user_agent_string(first_name: str, last_name: str,
                          email: str) -> str:
    """
    Make string of personal info necessary for getting data from sec website.
    """

    return f'{first_name} {last_name} ({email})'

 
def get_company_identifiers(
        user_agent_string: str,
        save_path: str = './data/sec/companies.json'
        ):
    """
    Get information about which companies are filing at the SEC in the form
    of cik, ticker, name triplets.
    """

    url = "https://www.sec.gov/files/company_tickers.json"

    headers = {
        'User-Agent': user_agent_string
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        result_dict = response.json()
        print(f"Successfully retrieved data for {len(result_dict)} companies.")
        companies = []
        for value in result_dict.values():
            company_dict = {}
            company_dict['name'] = value['title']
            company_dict['ticker'] = value['ticker'].lower()
            company_dict['cik'] = str(value['cik_str']).zfill(10)
            companies.append(company_dict)

        if save_path is not None:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(companies, f, indent=4)
        
        return companies
    
    print(f"Failed to retrieve data. Status code: {response.status_code}")
    return None


def get_cik_from_ticker(ticker: str, companies: list[dict[str, str]]
                        ) -> str | None:
    """
    Retrieve the cik identifier given a ticker from a list of company info
    dictionaries.
    """

    for company in companies:
        if company['ticker'] == ticker:
            return company['cik']
    return None


def get_raw_data(user_agent_string: str, cik: str) -> dict | None:
    """
    Get the filings for a company identified by its cik.
    """

    headers = {
        'User-Agent': user_agent_string
    }
    url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 200:
        data = response.json()
        return data

    print(f"Error: {response.status_code}")
    return None


def get_tags(company_data: dict) -> dict[str, list[str]]:
    """
    Get the tags from the raw company filing data.
    """

    taxonomies = list(company_data['facts'].keys())
    all_tags = {}
    for taxonomy in taxonomies:
        all_tags[taxonomy] = list(company_data['facts'][taxonomy].keys())

    return all_tags


def make_fact(
        tag: str,
        value: int,
        unit: str,
        fiscal_year: int,
        fiscal_period: str,
        form_type: str,
        date_filed: str
) -> str:
    """
    Make a filing fact in the form of a full sentence from filing info.
    """

    clean_tag = ''.join(
        [' ' + char if char.isupper() else char for char in tag]
        ).strip()
    if fiscal_period == 'FY':
        fiscal_period = 'Full Year'
    formatted_value = f"{value:,}"
    fact = (
        f"The reported '{clean_tag}' in {fiscal_year} ({fiscal_period}) "
        f"filed in a {form_type} form on {date_filed} was {formatted_value} "
        f"{unit}."
    )
    return fact

def get_data_by_tag(company_data: dict, tag: str, taxonomy: str) -> dict:

    concept = {}
    concept['tag'] = tag
    concept['taxonomy'] = taxonomy
    concept['label'] = company_data['facts'][taxonomy][tag]['label']
    concept['description'] = company_data['facts'][taxonomy][tag]['description']
    concept['facts'] = []
    concept['filings'] = []
    for unit in company_data['facts'][taxonomy][tag]['units'].keys():
        for filing in company_data['facts'][taxonomy][tag]['units'][unit]:
            fact = make_fact(
                tag,
                filing['val'],
                unit,
                filing['fy'],
                filing['fp'],
                filing['form'],
                filing['filed']
            )
            concept['facts'].append(fact)
            concept['filings'].append({
                'unit': unit,
                'value': filing['val'],
                'fiscal_year': filing['fy'],
                'fiscal_period': filing['fp'],
                'form_type': filing['form'],
                'date_filed': filing['filed']
            })

    return concept

def get_all_data(company_data : dict, all_tags : dict) -> dict:
    facts = {}
    for taxonomy, tags_list in all_tags.items():
        for tag in tags_list:
            fact = get_data_by_tag(company_data, tag, taxonomy)
            facts[tag] = fact
    return facts


def get_all_data_for_ticker(
        ticker : str,
        save_dir : str = './data/sec/filings'):
    user_agent_string = get_user_agent_string(
        "Ingimar",
        "Tomasson",
        "ingitom99@gmail.com"
    )
    cik_map = get_cik_ticker_map(user_agent_string)
    cik = get_cik_from_ticker(ticker, cik_map)
    company_data = get_raw_data(user_agent_string, cik)
    all_tags = get_tags(company_data)
    all_data = get_all_data(company_data, all_tags)
    
    # Ensure the data directory and ticker subdirectory exist
    os.makedirs(f"./data/{ticker}", exist_ok=True)

    # Create the file path
    file_path = save_dir + f"/{ticker}.json"

    # Save the data to a JSON file
    with open(file_path, "w") as f:
        json.dump(all_data, f, indent=4)

    # Verify that the file was created
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Failed to create file: {file_path}")
    return None