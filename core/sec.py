import json
import os
import requests


def make_user_agent_string(first_name: str, last_name: str,
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

    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 200:
        result_dict = response.json()
        
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

        print(f"Successfully retrieved data for {len(result_dict)} companies.")

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
            print(
                f"Successfully retrieved CIK: {company['cik']} for "
                f"ticker: {ticker}"
            )
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
        print("Successfully retrieved data for CIK: {cik}")
        return data

    print(f"Error: {response.status_code}")
    return None


def get_tags(company_data: dict) -> dict[str, list[str]]:
    """
    Get the filing concepts from the raw company filing data.
    """

    taxonomies = list(company_data['facts'].keys())
    tags = {}
    for taxonomy in taxonomies:
        tags[taxonomy] = list(company_data['facts'][taxonomy].keys())

    return tags


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

    concept = ''.join(
        [' ' + char if char.isupper() else char for char in tag]
        ).strip()
    if fiscal_period == 'FY':
        fiscal_period = 'Full Year'
    formatted_value = f"{value:,}"
    fact = (
        f"The reported '{concept}' in {fiscal_year} ({fiscal_period}) "
        f"filed in a {form_type} form on {date_filed} was {formatted_value} "
        f"{unit}."
    )
    return fact


def make_concept_info(company_data: dict, tag: str, taxonomy: str) -> dict:
    """
    Create a dict containing all the information filed about a concept.
    """

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


def make_concept_filings(company_data: dict, all_tags: dict) -> dict:
    """
    Create a dict containing all the filed information sorted by concept (tag).
    """

    concept_filings = {}
    for taxonomy, tags_list in all_tags.items():
        for tag in tags_list:
            concept = make_concept_info(company_data, tag, taxonomy)
            concept_filings[tag] = concept

    return concept_filings


def get_filings_from_ticker(
        ticker: str,
        first_name: str = "Ingimar",
        last_name: str = "Tomasson",
        email: str = "ingitom99@gmail.com",
        save_path: str = "./data/sec/filings"
) -> dict:
    """
    Get the filings for a company identified by its ticker.
    """

    user_agent_string = make_user_agent_string(first_name, last_name, email)
    companies = get_company_identifiers(user_agent_string)
    cik = get_cik_from_ticker(ticker, companies)
    if cik is None:
        raise ValueError(f"CIK not found for ticker: {ticker}")
    raw_data = get_raw_data(user_agent_string, cik)
    if raw_data is None:
        raise ValueError(f"Failed to retrieve raw data for CIK: {cik}")
    tags = get_tags(raw_data)
    concept_filings = make_concept_filings(raw_data, tags)

    os.makedirs(save_path, exist_ok=True)

    file_path = os.path.join(save_path, f"{ticker}.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(concept_filings, f, indent=4)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Failed to create file: {file_path}")

    return concept_filings
