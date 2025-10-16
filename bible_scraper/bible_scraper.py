import argparse
import json
import os
import time
import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Any
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def normalize_quotes(text: str) -> str:
    """Normalize smart quotes to standard quotes."""
    text = re.sub(u'[\u201c\u201d\u201f]', '"', text)  # Smart double quotes
    text = re.sub(u'[\u2018\u2019\u201b]', "'", text)  # Smart single quotes
    return text

def parse_bible_reference(ref_text: str) -> List[Dict[str, str]]:
    """Parse bible references including ranges and multiple references."""
    refs = []
    # Split multiple references
    for ref in ref_text.split(','):
        ref = ref.strip()
        if not ref:
            continue
            
        # Handle ranges (e.g., "Habakkuk 1:3-Habakkuk 1:5" or "Habakkuk 1:3-5")
        if '-' in ref:
            start, end = ref.split('-')
            start = start.strip()
            end = end.strip()
            
            # Parse start reference
            parts = start.rsplit(' ', 1)
            if len(parts) != 2 or ':' not in parts[1]:
                continue
            book = parts[0]
            start_chapter, start_verse = parts[1].split(':')
            
            # Parse end reference
            if ' ' in end:  # Full reference ("Habakkuk 1:5")
                parts = end.rsplit(' ', 1)
                if len(parts) != 2 or ':' not in parts[1]:
                    continue
                end_chapter, end_verse = parts[1].split(':')
            else:  # Just chapter:verse ("5") or verse ("5")
                if ':' in end:
                    end_chapter, end_verse = end.split(':')
                else:
                    end_chapter = start_chapter
                    end_verse = end
            
            # Add all verses in the range
            if start_chapter == end_chapter:
                for v in range(int(start_verse), int(end_verse) + 1):
                    refs.append({
                        "book": book,
                        "chapter": start_chapter,
                        "verse": str(v)
                    })
            else:
                # For now, just add start and end verses if chapters differ
                refs.append({
                    "book": book,
                    "chapter": start_chapter,
                    "verse": start_verse
                })
                refs.append({
                    "book": book,
                    "chapter": end_chapter,
                    "verse": end_verse
                })
        else:
            # Single reference
            parts = ref.rsplit(' ', 1)
            if len(parts) != 2 or ':' not in parts[1]:
                continue
            book = parts[0]
            chapter, verse = parts[1].split(':')
            refs.append({
                "book": book,
                "chapter": chapter,
                "verse": verse
            })
    
    return refs

class BibleScraper:
    def __init__(self, version: str, template_path: str):
        self.version = version
        self.base_url = "https://www.biblegateway.com/passage/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Load the template
        with open(template_path, 'r', encoding='utf-8') as f:
            self.template = json.load(f)
            
    def _get_version_info(self) -> Dict[str, str]:
        """Get information about the Bible version."""
        try:
            # Get the Genesis 1 page to find citation
            response = self.session.get(self.base_url, params={
                'search': 'Genesis 1',
                'version': self.version
            })
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if version exists by looking for error messages or version not found
            error_msg = soup.find('div', class_='error-msg')
            if error_msg or not soup.find('div', class_='passage-text'):
                raise ValueError(f"Bible version '{self.version}' does not exist or is not available")
            
            # Find version information and copyright notice
            copyright_div = soup.find('div', class_='publisher-info-bottom')
            copyright_text = ""
            name = self.version
            
            if copyright_div:
                # Get version name from the <strong><a> structure
                strong_tag = copyright_div.find('strong')
                if strong_tag:
                    a_tag = strong_tag.find('a')
                    if a_tag:
                        name = a_tag.get_text(strip=True)
                
                # Get copyright text from <p>
                p_element = copyright_div.find('p')
                if p_element:
                    copyright_text = p_element.get_text(strip=True)
            initials = self.version
            
            # Look for year in copyright notice first
            year = ""
            if copyright_text:
                year_match = re.search(r'\b(18\d{2}|19\d{2}|20\d{2})\b', copyright_text)
                if year_match:
                    year = year_match.group(1)
            
            # Get citation from copyright div
            citation = None
            if copyright_text:
                citation = copyright_text
            
            if not citation:
                # Construct citation
                citation = f"Scripture quotations taken from the {name}"
                if year:
                    citation += f" ({year})"
                citation += "."
            
            return {
                "name": name.strip(),
                "initials": initials.strip(),
                "version": year,
                "citation": citation
            }
            
        except requests.RequestException as e:
            logging.error(f"Error fetching version info: {str(e)}")
            raise ValueError(f"Failed to fetch Bible version '{self.version}': {str(e)}") from e

    def get_chapter_content(self, book: str, chapter: int) -> Dict[str, Any]:
        """Scrape a single chapter from Bible Gateway."""
        params = {
            'search': f"{book} {chapter}",
            'version': self.version
        }
        
        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Initialize verse tracking
            current_heading = None
            verse_updates = []
            
            # Get verses container
            passage_content = soup.find(class_='passage-content')
            if not passage_content:
                logging.error("Could not find passage-content")
                return []
                
            # Debug HTML structure
            #logging.debug(f"HTML structure:\n{passage_content.prettify()}")
            
            # Get verses container - try different class names
            verses_container = passage_content.find(class_='text-html') or passage_content
                
            # Find all footnotes and cross references for lookup
            footnotes = {}
            footnotes_div = soup.find('div', class_='footnotes')
            if footnotes_div:
                for fn in footnotes_div.find_all('li'):
                    fn_id = fn.get('id')
                    if fn_id and fn_id.startswith('fen-'):
                        text_span = fn.find('span', {'class': 'footnote-text'})
                        if text_span:
                                footnotes[fn_id] = text_span.get_text(strip=True)
            
            cross_refs = {}
            crossrefs_div = soup.find('div', class_='crossrefs')
            if crossrefs_div:
                for cr in crossrefs_div.find_all('li'):
                    cr_id = cr.get('id')
                    if cr_id and cr_id.startswith('cen-'):
                        ref_links = cr.find_all('a', {'class': 'crossref-link'})
                        refs = []
                        for link in ref_links:
                            bibleref = link.get('data-bibleref')
                            if bibleref:
                                refs.extend(parse_bible_reference(bibleref))
                        if refs:
                            cross_refs[cr_id] = refs
            
            # Process verses and headings
            # The .version-{version} div contains all verses in <p> tags, with <h3> for headings
            version_div = passage_content.find(class_=f'version-{self.version}')
            if not version_div:
                version_div = passage_content
            
            verse_updates = []
            current_heading = None

            previous_verse_num = None

            # Process all elements to collect verses and headings
            for element in version_div.find_all(['h3', 'p']):
                # Process headings
                if element.name == 'h3':
                    current_heading = element.get_text(strip=True)
                    continue

                # Process verse paragraphs
                if element.name == 'p':
                    # Find all verse spans within the paragraph
                    verse_spans = element.find_all(class_='text')
                    #logging.debug(f"Found {len(verse_spans)} verse spans in paragraph")
                    for verse_span in verse_spans:
                        append = False
                        #logging.debug(f"Verse span HTML: {verse_span.prettify()}")
                        # Process verse text and references
                        verse_text = ''
                        verse_footnotes = []
                        verse_cross_refs = []
                        
                        # Get verse number from versenum or chapternum
                        verse_num = None
                        verse_text = ''
                        
                        # Check for chapter number first (if present, this is verse 1)
                        chapternum = verse_span.find('span', class_='chapternum')
                        if chapternum:
                            verse_num = "1"
                        else:
                            versenum = verse_span.find('sup', class_='versenum')
                            if versenum:
                                verse_num = versenum.get_text(strip=True)
                            else:
                                verse_num = previous_verse_num  # Continue previous verse if no number
                                append = True
                        previous_verse_num = verse_num
                        
                        # Process footnotes and cross-references first
                        for sup in verse_span.find_all('sup', class_='footnote'):
                            fn_id = sup.get('data-fn')
                            if fn_id:
                                if fn_id.startswith('#'):
                                    # Remove the '#' prefix to match the element id
                                    fn_id = fn_id[1:]
                                # Find the footnote element directly
                                fn_element = soup.find('li', id=fn_id)
                                if fn_element:
                                    text_span = fn_element.find('span', class_='footnote-text')
                                    if text_span:
                                        fn_text = text_span.get_text(strip=False)
                                        # Normalize quotes in footnote text
                                        verse_footnotes.append(normalize_quotes(fn_text))
                        
                        # Process cross references
                        for sup in verse_span.find_all('sup', class_='crossreference'):
                            cr_id = sup.get('data-cr')
                            if cr_id:
                                if cr_id.startswith("#"):
                                    cr_id = cr_id[1:]
                                cr_element = soup.find('li', id=cr_id)
                                if cr_element:
                                    ref_links = cr_element.find_all('a', class_='crossref-link')
                                    for link in ref_links:
                                        bibleref = link.get('data-bibleref')
                                        if bibleref:
                                            refs = parse_bible_reference(bibleref)
                                            verse_cross_refs.extend(refs)
                                
                        # Now remove all excluded elements from original verse span, replacing with spaces
                        for element in verse_span.find_all(['span', 'sup']):
                            if (element.get('class') and 
                                any(c in ['crossreference', 'footnote', 'chapternum', 'versenum'] 
                                    for c in element.get('class', []))):
                                # Replace element with a space
                                element.replace_with(' ')
                        
                        # Get text and clean up spaces
                        verse_text = verse_span.get_text()  # Don't strip yet to preserve spaces
                        # Replace all whitespace sequences (including newlines, tabs) with a single space
                        verse_text = re.sub(r'\s+', ' ', verse_text)
                        # Normalize quotes
                        verse_text = normalize_quotes(verse_text)
                        # Now strip and ensure no leading/trailing spaces
                        verse_text = verse_text.strip()
                        
                        # Process cross references
                        for sup in verse_span.find_all('sup', class_='crossreference'):
                            cr_id = sup.get('data-cr')
                            #if cr_id and cr_id in cross_refs:
                            #    verse_cross_refs.extend(cross_refs[cr_id])
                        
                        # Clean up verse text
                        verse_text = verse_text.strip()
                        if not verse_text:
                            logging.warning(f"Empty verse text found for {book} {chapter}")
                            continue
                            
                        # Verify we got a verse number
                        if verse_num is None:
                            logging.error(f"No verse number found for text in {book} {chapter}: {verse_text}")
                            continue
                        
                        # Join multiple footnotes with a space, or None if no footnotes
                        footnote = '; '.join(verse_footnotes) if verse_footnotes else None
                        
                        if not append:
                            verse_updates.append({
                                "verse": verse_num,
                                "heading": current_heading,
                                "text": verse_text,
                                "footnote": footnote,
                                "cross_references": {
                                    "refers_to": verse_cross_refs,
                                    "refers_me": []
                                }
                            })
                        else:
                            verse_updates[-1]['text'] += ' ' + verse_text
                            if footnote:
                                verse_updates[-1]['footnote'] = (verse_updates[-1]['footnote'] + '; ' + footnote) if verse_updates[-1]['footnote'] else footnote
                            verse_updates[-1]['cross_references']['refers_to'].extend(verse_cross_refs)
                            if verse_updates[-1]['heading'] is None:
                                verse_updates[-1]['heading'] = current_heading
                        #logging.debug(f"Verse {verse_num}: {verse_text}")
                        current_heading = None  # Clear heading after using it
            
            return verse_updates
            
        except requests.RequestException as e:
            logging.error(f"Error fetching {book} {chapter}: {str(e)}")
            return []

    def process_reverse_references(self):
        """Process reverse references (refers_me) for all verses."""
        # First, build an index of all verses for faster lookup
        verse_index = {}
        for book in self.template["books"]:
            book_name = book["book"]
            for chapter in book["chapters"]:
                chapter_num = chapter["chapter"]
                for verse in chapter["verses"]:
                    verse_num = verse["verse"]
                    key = f"{book_name} {chapter_num}:{verse_num}"
                    verse_index[key] = verse

        # Process all refers_to to build refers_me
        for book in self.template["books"]:
            book_name = book["book"]
            for chapter in book["chapters"]:
                chapter_num = chapter["chapter"]
                for verse in chapter["verses"]:
                    verse_num = verse["verse"]
                    if not verse.get("cross_references"):
                        continue
                        
                    source_ref = {
                        "book": book_name,
                        "chapter": str(chapter_num),
                        "verse": str(verse_num)
                    }
                    
                    # Add this verse as refers_me to all verses it refers to
                    for ref in verse["cross_references"].get("refers_to", []):
                        target_key = f"{ref['book']} {ref['chapter']}:{ref['verse']}"
                        if target_key in verse_index:
                            target_verse = verse_index[target_key]
                            if not target_verse.get("cross_references"):
                                target_verse["cross_references"] = {"refers_to": [], "refers_me": []}
                            target_verse["cross_references"]["refers_me"].append(source_ref)

    def scrape_bible(self) -> Dict[str, Any]:
        """Scrape the entire Bible for the specified version."""
        # Get version information
        version_info = self._get_version_info()
        self.template.update(version_info)
        
        # Scrape each chapter
        for book in self.template["books"]:
            book_name = book["book"]
            logging.info(f"Processing {book_name}...")
            
            for chapter in book["chapters"]:
                chapter_num = chapter["chapter"]
                logging.debug(f"  Scraping {book_name} {chapter_num}...")
                
                # Get chapter content
                verse_updates = self.get_chapter_content(book_name, chapter_num)
                if verse_updates is None:
                    logging.error(f"No verse updates returned for {book_name} {chapter_num}")
                    verse_updates = []
                    
                # Update verses with scraped content
                for verse_update in verse_updates:
                    verse_num = verse_update.pop('verse')  # Remove verse number from update data
                    for verse in chapter["verses"]:
                        if str(verse["verse"]) == verse_num:
                            verse.update(verse_update)
                            break
                time.sleep(1)  # Be nice to the server

        # Process refers_me references
        logging.info("Processing reverse references...")
        self.process_reverse_references()
        
        return self.template

def main():
    parser = argparse.ArgumentParser(description="Scrape Bible Gateway for Bible text and references")
    parser.add_argument("version", help="Bible version abbreviation (e.g., ESV, NASB, NKJV)")
    parser.add_argument("template", help="Path to the template JSON file", nargs="?", default="./version_template.json")
    args = parser.parse_args()

    scraper = BibleScraper(args.version, args.template)
    try:
        bible_data = scraper.scrape_bible()

        output_path = f"./bibles/{args.version.upper()}.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(bible_data, f, ensure_ascii=False, indent=2)
    
        logging.info(f"Bible successfully scraped and saved to {output_path}")
    except Exception as e:
        logging.error(str(e))

if __name__ == "__main__":
    main()




# citation is in a special element at bottom of page, use Genesis 1 for citation, element with @publisher-info-bottom, citation is in the <p> element inside it
# if not found in translation name, use publication year in citation for version
# cross references have full addresses, and might list several, and might list ranges. Genesis 1:1, Habbakuk 1:1, Habbakuk 1:3-Habbakuk 1:5
# it is much easier than this llm thinks to parse references.
# footnotes and cross references are embedded in the verse text: 
# <sup class="crossreference" data-cr="<id of crossreference element>" , <sup class="footnote" data-fn="<id of footnote element>"
# those footnote and cross reference elements are li elements
# footnotes have a @footnote-text span inside them
# cross references have an @crossref-link element, and that element has a data-bibleref attribute with the reference text
# reference text is like this: Genesis 1:1, Habbakuk 1:1, Habbakuk 1:3-Habbakuk 1:5
