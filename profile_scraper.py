import re
import json
import time
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

def get_department_links(url: str, output_file: str = "") -> list:
    """ Returns a list of links to each department """
    data = requests.get(url)
    soup = BeautifulSoup(data.text, 'html.parser')

    # Find department links, excluding links to anchors
    departments = soup.select('h2:-soup-contains("Departments & Schools")')
    departments = departments[0].parent.parent.select('a')
    departments = [a['href'] for a in departments if a['href'][:11] == 'https://uwa']

    # Save to file
    if output_file:
        with open(output_file, 'w') as f:
            f.write("\n".join(departments))

    return departments

def get_contacts(departments: list, output_file: str = "") -> list:
    """ Returns a list of contact page links """
    contacts = []

    # Most pages follow department/contacts. 8 outliers handled manually
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
    """ Returns a list of profile page links """

    profiles = []
    for link in tqdm(contacts):
        res = requests.get(link)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Handle relative vs absolute links mentioning 'profile'
        links = soup.select('a[href*="profile"]')
        links = [a['href'] for a in links]
        links = [link + l if l[0] == '/' else l for l in links]
        profiles += links

    # Save to file
    if output_file:
        with open(output_file, 'w') as f:
            f.write("\n".join(profiles))

    return profiles

def get_content(profiles: list, output_file: str = "", start: int = 0, end: int = -1) -> dict:
    """ Saves raw text from profile bios to a JSON file """

    # prep useful data for later
    bios = {}
    content_classes = [".node-uw-ct-person-profile", ".layout-ofis", 
                       ".card__node--profile", ".node--type-uw-ct-profile"]

    for link in tqdm(profiles[start:end if end != -1 else len(profiles)]):
        try:
            res = requests.get(link, timeout=5)

            # skip 404 pages
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')

                # Different profiles have different structure. Try until success.
                for c in content_classes:
                    content = soup.select(c)
                    if len(content):
                        
                        # Extract text from all tags within content block
                        text = [re.sub(r'\s+', ' ', c.get_text()) 
                                for c in content[0].find_all(recursive=True)]
                        text = "\n".join(text)
                        bios[link.split("/")[-1]] = text
                        break
        except Exception as e:
            print(e)
            continue

    # Save to file
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(bios, f)

    return bios
        
profiles = []
with open("data/profiles.txt", 'r') as f:
    profiles = f.read().split("\n")

master_bios = {}
for i in range(0, len(profiles), 100):
    end = min(i+100, len(profiles))
    bios = get_content(profiles, f"data/bios{i}_{i+99}.json", i, end)
    master_bios.update(bios)
    time.sleep(5) # seems like server is blocking requests halfway in

with open("data/bios.json", 'w') as f:
    json.dump(master_bios, f)