import random
import os
import json
import time
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import shutil

# Ensure directories exist
os.makedirs("images", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Custom headers to mimic a browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://bulbapedia.bulbagarden.net/',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

ALL_POKEMON_VALUE = -1

# Create a session to persist cookies
session = requests.Session()
session.headers.update(headers)

def clean_text(text):
    """Clean text by removing extra whitespace, fixing quotes, and citation references."""
    if not text:
        return ""
    # Remove citation references like [1]
    text = re.sub(r'\[\d+\]', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Fix quotes
    text = text.replace("''", '"').replace("' ", "' ")
    return text

def clean_pokemon_name(name):
    """Clean Pokémon name by removing trailing underscores and standardizing format."""
    # Remove trailing underscores
    name = name.rstrip('_')
    # Convert to lowercase and replace spaces with hyphens
    return name.lower().replace(' ', '-')

def download_image(url, save_path):
    """Download an image from URL and save it to the specified path."""
    try:
        time.sleep(random.uniform(0.5, 1.5))  # Random delay to avoid rate limiting
        
        img_response = session.get(url, stream=True)
        if img_response.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                shutil.copyfileobj(img_response.raw, f)
            return True
        else:
            print(f"Failed to download image, status code: {img_response.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading image: {e}")
        return False

def extract_paragraphs_until_heading(soup, start_element):
    """Extract all paragraphs until the next heading."""
    paragraphs = []
    current = start_element.next_sibling
    
    while current and not current.name in ['h2', 'h3', 'h4']:
        if current.name == 'p' and current.text.strip():
            paragraphs.append(clean_text(current.text))
        current = current.next_sibling
    
    return "\n\n".join(paragraphs)

def extract_general_description(soup):
    """Extract the general description paragraphs from between the infobox and the TOC."""
    general_paragraphs = []
    
    # Find the infobox
    infobox = soup.select_one('table.roundy.infobox')
    if not infobox:
        infobox = soup.select_one('table.roundy')  # Try a more general selector
    
    # Find the table of contents
    toc = soup.select_one('div#toc')
    
    # If we found both elements
    if infobox and toc:
        # Get all elements between them
        elements = []
        current = infobox.next_sibling
        while current and current != toc:
            elements.append(current)
            current = current.next_sibling
        
        # Extract paragraphs from elements
        for element in elements:
            if element.name == 'p' and element.text.strip():
                general_paragraphs.append(clean_text(element.text))
    
    # If we didn't find the TOC, try to find the first heading after infobox
    elif infobox:
        # Get all elements until first heading
        elements = []
        current = infobox.next_sibling
        while current and not (current.name in ['h1', 'h2', 'h3']):
            elements.append(current)
            current = current.next_sibling
        
        # Extract paragraphs from elements
        for element in elements:
            if element.name == 'p' and element.text.strip():
                general_paragraphs.append(clean_text(element.text))
    
    # Fallback: just try to find the first paragraphs in the content area
    if not general_paragraphs:
        content_div = soup.select_one('#mw-content-text')
        if content_div:
            # Skip the infobox if present
            paragraphs = []
            for p in content_div.find_all('p', recursive=False):
                # Skip paragraphs inside tables or divs
                parent_table = p.find_parent('table')
                parent_div = p.find_parent('div', class_='toc')
                if not parent_table and not parent_div and p.text.strip():
                    paragraphs.append(p)
            
            # Use the first paragraphs as general description
            for p in paragraphs[:3]:
                if p.text.strip():
                    general_paragraphs.append(clean_text(p.text))
    
    return "\n\n".join(general_paragraphs)

def extract_pokemon_types(soup):
    """Extract the Pokémon's types, making sure to avoid hidden elements."""
    pokemon_types = []
    
    # Find the type section table
    type_section = soup.select_one('td:has(a[href="/wiki/Type"])')
    
    if type_section:
        # Get the main type table (first visible table inside)
        type_table = type_section.find_next('table', class_='roundy')
        
        if type_table:
            # Find all type links in visible rows/cells (not with display:none)
            visible_type_links = []
            
            # First approach: find direct links inside cells that don't have display:none in parent attributes
            for type_link in type_table.select('a[href^="/wiki/"][title$="(type)"]'):
                # Check if this link or any parent has display:none
                is_visible = True
                parent = type_link.parent
                while parent and parent != type_table:
                    if parent.has_attr('style') and 'display: none' in parent['style']:
                        is_visible = False
                        break
                    parent = parent.parent
                
                if is_visible and type_link.text.strip() and type_link.text.strip() != "Unknown":
                    visible_type_links.append(type_link)
            
            # Extract unique types from the visible links
            for link in visible_type_links:
                type_name = link.text.strip()
                if type_name and type_name not in pokemon_types:
                    pokemon_types.append(type_name)
    
    # If still no types found, try a more general approach with the first few type links
    if not pokemon_types:
        # Find all type links in the page and take the first 2 (most Pokémon have 1-2 types)
        type_links = soup.select('a[href^="/wiki/"][title$="(type)"]')
        for i, link in enumerate(type_links):
            if i < 2:  # Limit to first 2 types
                type_name = link.text.strip()
                if type_name and type_name not in pokemon_types and type_name != "Unknown":
                    pokemon_types.append(type_name)
    
    return pokemon_types

def scrape_pokemon_data(max_pokemon=100):
    """Scrape Pokemon data from Bulbapedia and return randomly selected ones with complete info."""
    # Base URL for Bulbapedia
    base_url = "https://bulbapedia.bulbagarden.net"
    
    # Get the list of Pokémon by National Pokédex number
    pokedex_url = f"{base_url}/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number"
    print(f"Fetching Pokédex page: {pokedex_url}")
    
    response = session.get(pokedex_url)
    if response.status_code != 200:
        print(f"Failed to get Pokédex page, status code: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all Pokémon links in the tables
    # Each Pokémon has a link in the format "/wiki/PokemonName_(Pokémon)"
    pokemon_links = []
    tables = soup.find_all('table', class_='roundy')
    
    for table in tables:
        # Find all Pokémon links using a more flexible pattern
        links = table.find_all('a', href=re.compile(r'/wiki/[^(]+\(Pok.+mon\)'))
        for link in links:
            # Skip duplicate links and make sure it's a Pokémon page
            if "wiki" in link['href'] and link not in pokemon_links:
                pokemon_links.append(link)
    
    # Create a list of unique Pokémon URLs
    pokemon_urls = []
    seen_hrefs = set()
    
    for link in pokemon_links:
        href = link['href']
        if href not in seen_hrefs:
            seen_hrefs.add(href)
            full_url = f"{base_url}{href}"
            pokemon_name = link.text.strip()
            pokemon_urls.append((full_url, pokemon_name))
    
    print(f"Found {len(pokemon_urls)} unique Pokémon")
    
    # Randomly select Pokémon
    if not max_pokemon == ALL_POKEMON_VALUE and len(pokemon_urls) > max_pokemon:
        pokemon_urls = random.sample(pokemon_urls, max_pokemon)
        print(f"Randomly selected {len(pokemon_urls)} Pokémon to process")
    else:
        print(f"Processing all {len(pokemon_urls)} Pokémon")
    
    valid_pokemon = []
    processed_count = 0
    
    # Process selected Pokémon
    for url, name in pokemon_urls:
        processed_count += 1
        print(f"Processing {processed_count}/{len(pokemon_urls)}: {name} - {url}")
        
        try:
            # Add a random delay between requests to avoid rate limiting
            time.sleep(random.uniform(2.0, 4.0))
            
            response = session.get(url)
            if response.status_code != 200:
                print(f"Failed to get {url}, status code: {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract clean Pokemon name from URL
            url_parts = url.split('/')
            page_name = url_parts[-1].split('(')[0]  # Get part before (Pokémon)
            pokemon_name = clean_pokemon_name(urllib.parse.unquote(page_name))
            
            # Create directory for this Pokémon's images
            pokemon_image_dir = f"images/{pokemon_name}"
            os.makedirs(pokemon_image_dir, exist_ok=True)
            
            # Extract Pokémon types using the improved function
            pokemon_types = extract_pokemon_types(soup)
            
            # Get general description - use the enhanced extraction method
            general_description = extract_general_description(soup)
            
            # Extract biology description
            biology_description = ""
            biology_heading = None
            
            # Find the Biology section
            for heading in soup.find_all(['h2', 'h3']):
                span = heading.find('span')
                if span and span.get('id') and span.get('id') in ['Biology', 'Physiology', 'Characteristics']:
                    biology_heading = heading
                    break
            
            # Extract all paragraphs in the Biology section
            if biology_heading:
                biology_description = extract_paragraphs_until_heading(soup, biology_heading)
            
            # If no biology section found, try to extract a substantial part of the page
            if not biology_description:
                content_paragraphs = soup.select('#mw-content-text > p')
                substantial_paragraphs = [p.text for p in content_paragraphs if len(p.text.strip()) > 100]
                if substantial_paragraphs:
                    biology_description = "\n\n".join([clean_text(p) for p in substantial_paragraphs])
            
            # Skip if we don't have enough information
            if not general_description and not biology_description:
                print(f"No valid description found for {name}, skipping")
                continue
            
            # Download main image
            main_img_url = None
            main_img_path = None
            
            # Try the main image in the infobox first
            infobox = soup.select_one('table.roundy')
            if infobox:
                img_tag = infobox.select_one('img')
                if img_tag and img_tag.get('src'):
                    main_img_url = img_tag['src']
                    if main_img_url.startswith('//'):
                        main_img_url = f"https:{main_img_url}"
                    elif not main_img_url.startswith('http'):
                        main_img_url = f"{base_url}{main_img_url}"
                    
                    main_img_path = f"{pokemon_image_dir}/main.png"
                    if download_image(main_img_url, main_img_path):
                        print(f"Downloaded main image for {name}")
            
            # If no main image found, try alternative methods
            if not main_img_url:
                for img_selector in [
                    'img.roundy',
                    'a.image img[alt*="artwork"]',
                    f'a.image img[alt*="{name}"]',
                    'a.image img'
                ]:
                    img_tag = soup.select_one(img_selector)
                    if img_tag and img_tag.get('src'):
                        main_img_url = img_tag['src']
                        if main_img_url.startswith('//'):
                            main_img_url = f"https:{main_img_url}"
                        elif not main_img_url.startswith('http'):
                            main_img_url = f"{base_url}{main_img_url}"
                        
                        main_img_path = f"{pokemon_image_dir}/main.png"
                        if download_image(main_img_url, main_img_path):
                            print(f"Downloaded main image for {name}")
                            break
            
            # Extract sprites from the Sprites section
            sprites = []
            sprites_section = None
            
            # Track sprite names to avoid duplicates
            sprite_name_counts = {}
            
            # Find the Sprites section
            for heading in soup.find_all(['h2', 'h3']):
                span = heading.find('span')
                if span and span.get('id') and 'Sprites' in span.get('id'):
                    sprites_section = heading
                    break
            
            # Extract sprite images if found
            if sprites_section:
                # Find the table containing sprites
                sprite_table = None
                current = sprites_section.next_sibling
                
                while current and not (current.name == 'h2' or current.name == 'h3'):
                    if current.name == 'table':
                        sprite_table = current
                        break
                    current = current.next_sibling
                
                # Process found sprite tables
                if sprite_table:
                    sprite_imgs = sprite_table.select('img')
                    for i, img in enumerate(sprite_imgs):
                        if img.get('src'):
                            sprite_url = img['src']
                            if sprite_url.startswith('//'):
                                sprite_url = f"https:{sprite_url}"
                            elif not sprite_url.startswith('http'):
                                sprite_url = f"{base_url}{sprite_url}"
                            
                            # Get a descriptive name for the sprite
                            alt_text = img.get('alt', f'sprite_{i+1}')
                            safe_name = re.sub(r'[^\w\-\.]', '_', alt_text)
                            
                            # If this name already exists, add a counter
                            if safe_name in sprite_name_counts:
                                sprite_name_counts[safe_name] += 1
                                safe_name = f"{safe_name}-{sprite_name_counts[safe_name]}"
                            else:
                                sprite_name_counts[safe_name] = 1
                            
                            sprite_path = f"{pokemon_image_dir}/{safe_name}.png"
                            
                            if download_image(sprite_url, sprite_path):
                                sprites.append({
                                    "url": sprite_url,
                                    "path": sprite_path,
                                    "description": alt_text
                                })
                                print(f"Downloaded sprite {i+1} for {name}")
            
            # Skip if we don't have any images
            if not main_img_path and not sprites:
                print(f"No images found for {name}, skipping")
                continue
            
            # Add to valid Pokemon list
            valid_pokemon.append({
                "name": pokemon_name,
                "display_name": name,
                "main_image_path": main_img_path,
                "sprites": sprites,
                "general_description": general_description,
                "biology_description": biology_description,
                "types": pokemon_types,
                "url": url
            })
            
            print(f"Added {name} - Types: {', '.join(pokemon_types)}")
            print(f"General Description: {general_description[:100]}...")
            
            # Save data after each successful Pokémon to avoid losing progress
            if len(valid_pokemon) % 5 == 0:
                temp_output_path = "data/pokemon_data_temp.json"
                with open(temp_output_path, "w", encoding="utf-8") as f:
                    json.dump(valid_pokemon, f, ensure_ascii=False, indent=2)
                print(f"Saved temporary data with {len(valid_pokemon)} Pokémon")
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
        
        # Print progress update
        if processed_count % 10 == 0:
            print(f"Progress: Processed {processed_count}/{len(pokemon_urls)}, found {len(valid_pokemon)} valid entries")
    
    return valid_pokemon

if __name__ == "__main__":
    pokemon_data = scrape_pokemon_data(max_pokemon=ALL_POKEMON_VALUE)
    
    # Save the data to JSON
    output_path = "data/pokemon_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pokemon_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nScraping complete! Found {len(pokemon_data)} valid Pokémon with images and descriptions.")
    print(f"Data saved to {output_path}") 