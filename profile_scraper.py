"""PROFILE SCAPER
This script scrapes the University of Waterloo website for faculty bios. 
Dependencies: requests, tqdm, bs4
"""

import os
import re
import json
import time

import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

def get_department_links(url: str, output_file: str = "") -> list:
    """ 
    Returns a list of links to each department homepage
    
    Parameters
    ----------
    url: URL of the faculty page listing all departments
    output_file: filepath to save department links found
    """
    
    # Load faculties overview page
    data = requests.get(url)
    soup = BeautifulSoup(data.text, 'html.parser')

    # Find department links, excluding links to anchors
    container = soup.select('h2:-soup-contains("Departments & Schools")')[0]
    container = container.parent.parent

    departments = container.select('a')
    departments = [a['href'] for a in departments if a['href'][:11] == 'https://uwa']

    # Save to file
    if output_file:
        with open(output_file, 'w') as f:
            f.write("\n".join(departments))

    return departments

def get_contacts(departments: list, output_file: str = "") -> list:
    """ 
    Returns a list of links to each department's contact page

    Parameters
    ----------
    departments: list of links to each department homepage
    output_file: filepath to save contact page links found
    """
    contacts = []

    # Usually, contact page at dept_link/contacts. 8 outliers fixed manually
    for link in tqdm(departments):
        res = requests.get(link + "contacts")
        if (res.status_code == 200):
            contacts.append(link + "contacts")
        else:
            print(link)
            continue

    # Save to file
    if output_file:
        with open(output_file, 'w') as f:
            f.write("\n".join(contacts))

    return contacts

def get_profiles(contacts: list, output_file: str = "") -> list:
    """ 
    Returns a list of links to faculty profile pages 
    
    Parameters
    ----------
    contacts: list of links to each department's contact page
    output_file: filepath to save profile page links found
    """

    profiles = []

    # Load contact pages
    for link in tqdm(contacts):
        res = requests.get(link)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Save relative and absolute links mentioning 'profile'
        links = soup.select('a[href*="profile"]')
        links = [a['href'] for a in links]

        links = [link + l if l[0] == '/' else l for l in links]
        profiles += links

    # Save to file
    if output_file:
        with open(output_file, 'w') as f:
            f.write("\n".join(profiles))

    return profiles

def get_content(profiles: list, output_file: str = "", start: int = 0, 
                end: int = -1) -> dict:
    """ 
    Saves raw text from profile bios to a JSON file 
    
    Parameters
    ----------
    profiles: list of links to each faculty profile page
    output_file: filepath to save profile page links found
    start: index of first profile to scrape
    end: index of last profile to scrape
    """

    # prep useful data for later
    bios = {}
    end = end if end != -1 else len(profiles)
    content_classes = [".node-uw-ct-person-profile", ".layout-ofis", 
                       ".card__node--profile", ".node--type-uw-ct-profile"]

    # Avoid processing all profiles at once (default). Server blocks requests
    for link in tqdm(profiles[start:end]):
        try:
            res = requests.get(link, timeout=5)

            # skip 404 pages
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')

                # Different faculty profiles vary in classes on bio content div.
                # Try each until one works.
                for c in content_classes:
                    content = soup.select(c)
                    if len(content):
                        
                        # Process text from all elements within content block
                        text = [c.get_text() for c in content[0].find_all(recursive=True)]
                        text = [re.sub(r'\s+', ' ', t) for t in text]
                        text = "\n".join(text)

                        # Save text under profile id
                        bios[link.split("/")[-1]] = text
                        break
        except Exception as e:
            print(e)  # Usually only timeout errors. Unimportant volume of data
            continue

    # Save to file
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(bios, f)

    return bios

def main():
    if not os.path.exists("data"):
        os.makedirs("data")

    # Get department links
    departments = get_department_links(
        "https://uwaterloo.ca/faculties-academics",
        "data/departments.txt"
    )

    # Get contact page links
    contacts = get_contacts(
        departments,
        "data/contacts.txt"
    )

    # Get profile page links
    profiles = get_profiles(
        contacts,
        "data/profiles.txt"
    )

    # Process 100 faculty pages at a time to reduce data loss from crashes
    master_bios = {}
    for i in range(0, len(profiles), 100):
        end = min(i+100, len(profiles))
        bios = get_content(profiles, f"data/bios{i}_{i+99}.json", i, end)
        master_bios.update(bios)
        time.sleep(5) # avoid server blocking requests

    # Save all bios to one file
    with open("data/bios.json", 'w') as f:
        json.dump(master_bios, f)

if __name__ == "__main__":
    main()