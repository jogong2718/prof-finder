"""PROFILE SCAPER
This script scrapes the University of Waterloo website for faculty bios. 
Dependencies: requests, tqdm, bs4
"""

# Standard library imports
import os
import re
import json
import time
import queue
import threading

# Custom library imports
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup


# Helper functions
def get_base(url: str) -> str:
    """ 
    Returns the base url of a given link 
    
    Parameters
    ----------
    url: link to a webpage
    """

    return "/".join(url.split("/")[:3])

def get_profiles(faculty_urls: list, output_file: str = "") -> list:
    """ 
    Returns a list of links to faculty member profiles 
    
    Parameters
    ----------
    faculty_urls: list of links to each faculty's home page
    output_file: filepath to save profile page links found
    """

    profiles = []

    # Load contact pages
    for link in tqdm(faculty_urls):
        res = requests.get(link)
        base = get_base(link)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Find links to faculty profiles
        links = soup.select('a.viewprofile')
        links = [a['href'] for a in links]

        # Add base url to relative links
        links = [base + l if l[0] == '/' else l for l in links]
        profiles += links

    # Save to file
    if output_file:
        with open(output_file, 'w') as f:
            f.write("\n".join(profiles))

    return profiles

def traverse_profiles(profiles: list, output_file: str = "", start: int = 0, 
                end: int = -1) -> dict:
    """ 
    Handles I/O for each profile page
    
    Parameters
    ----------
    profiles: list of links to each faculty profile page
    output_file: filepath to save profile page links found
    start: index of first profile to scrape
    end: index of last profile to scrape
    """

    # prep vars for later
    bios = []
    end = end if end != -1 else len(profiles)
    bios_queue = queue.Queue()
    threads = []
    batch_size = 10

    # Avoid processing all profiles at once. Server blocks requests
    for i in tqdm(range(start, end, batch_size)):
        end_i = min(i+batch_size, end)
        t = threading.Thread(
            target=process_profiles,
            args=(profiles, i, end_i, bios_queue)
        )
        threads.append(t)
        t.start()

    # Stop threads and retrieve data
    for t in threads:
        t.join()

    while not bios_queue.empty():
        bios.extend(bios_queue.get())

    # Save to file
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(bios, f)

    return bios

def process_profiles(profiles: list, start: int, end: int, 
                     bios_queue: queue.Queue) -> None:
    """ 
    Multithreaded task to process batch of profiles 
    
    Parameters
    ----------
    profiles: list of links to each faculty profile page
    start: index of first profile to scrape
    end: index of last profile to scrape
    bios_queue: where to store the extracted data
    """

    bios_in_current_thread = []
    for link in tqdm(profiles[start:end]):
        try:
            res = requests.get(link, timeout=5)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                soup.url = link
                data = fill_data(soup)
                bios_in_current_thread.append(data)
        except Exception as e:
            print(e)
            continue
    bios_queue.put(bios_in_current_thread)

def fill_data(profile_soup: BeautifulSoup) -> dict:
    """ Helper function for traverse_profiles to handle data extraction """

    # Prep vars
    data = {'profile': profile_soup.url, 'name': None, 'position': None, 
            'email': None, 'expertise': None, 'bio': None}
    selectors = {
        'name': 'h1.underlined',
        'position': 'p#generalDetails> :not(:last-child)',
        'email': 'a#email_address_1'
    }

    # Extract basic text data
    for key, selector in selectors.items():
        try:
            tmp = [x.get_text() for x in profile_soup.select(selector)]
            tmp = [re.sub(r'\s+', ' ', t) for t in tmp]
            data[key] = " ".join(tmp)
        except:
            data[key] = None

    # Extract areas of expertise
    container = profile_soup.select('h2:-soup-contains("Expert In")')[0].parent
    categories = container.select('a')
    data['expertise'] = [c.get_text() for c in categories]

    # Extract bio
    content_classes = [".node-uw-ct-person-profile", ".layout-ofis", 
                       ".card__node--profile", ".node--type-uw-ct-profile"]
    
    bio_link = profile_soup.select('a:-soup-contains("Faculty Page")')[0]

    try:
        bio = requests.get(bio_link['href'], timeout=5)

        if bio.status_code == 200:
            bio_soup = BeautifulSoup(bio.text, 'html.parser')
            # Different faculty profiles vary in classes on bio content div.
            # Try each until one works.
            for c in content_classes:
                content = bio_soup.select(c)
                if len(content):
                    
                    # Process text from all elements within content block
                    text = [c.get_text() for c in content[0].find_all(recursive=True)]
                    text = [re.sub(r'\s+', ' ', t) for t in text]
                    text = "\n".join(text)

                    # Save text under profile id
                    data['bio'] = text
                    break
    except Exception as e:
            print(e)  # Usually only timeout errors. Unimportant volume of data
    
    return data


def main(storage_folder: str):
    if not os.path.exists(storage_folder):
        os.makedirs(storage_folder)

    # Get profile page links
    faculty_urls = [
        "https://experts.uwaterloo.ca/faculties/Faculty%20of%20Arts",
        "https://experts.uwaterloo.ca/faculties/Faculty%20of%20Engineering",
        "https://experts.uwaterloo.ca/faculties/Faculty%20of%20Environment",
        "https://experts.uwaterloo.ca/faculties/Faculty%20of%20Health",
        "https://experts.uwaterloo.ca/faculties/Faculty%20of%20Mathematics",
        "https://experts.uwaterloo.ca/faculties/Faculty%20of%20Science",
        "https://experts.uwaterloo.ca/colleges/Conrad%20Grebel%20University%20College",
        "https://experts.uwaterloo.ca/colleges/Renison%20University%20College",
        "https://experts.uwaterloo.ca/colleges/St.%20Jerome's%20University",
        "https://experts.uwaterloo.ca/colleges/St.%20Paul's%20University%20College",
        "https://experts.uwaterloo.ca/colleges/United%20College"
    ]

    if os.path.exists(f"{storage_folder}/profiles.txt"):
        with open(f"{storage_folder}/profiles.txt", 'r') as f:
            profiles = f.read().split("\n")
    else:
        profiles = get_profiles(
            faculty_urls,
            f"{storage_folder}/profiles.txt"
        )
    
    # Process 100 profiles at a time to reduce data loss from crashes
    master_bios = []
    for i in range(0, len(profiles), 100):
        end = min(i+100, len(profiles))
        bios = traverse_profiles(profiles, f"{storage_folder}/bios{i}_{i+99}.json", i, end)
        master_bios += bios
        time.sleep(5) # avoid server blocking requests

    # Save all bios to one file
    with open(f"{storage_folder}/bios.json", 'w') as f:
        json.dump(master_bios, f)
    

if __name__ == "__main__":
    storage_folder = 'data_new'
    main(storage_folder)