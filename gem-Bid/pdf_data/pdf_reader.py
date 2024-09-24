import fitz  # PyMuPDF

# Open the PDF file
pdf_file = "/home/dhruvin/Web-Scrapping/gem-Bid/pdf_data/Pdf/GEM/2024/B/4817198/GeM-Bidding-6263304.pdf"
doc = fitz.open(pdf_file)

# Define the list to store URLs
url_list = []

# Define the file extensions to filter
file_extensions = ('.pdf', '.xlsx', '.csv', '.ods', '.txt')

for page_num in range(doc.page_count):
    page = doc.load_page(page_num)  # Load each page
    # Get all links on the page
    links = page.get_links()
    
    # Loop through all links
    for link in links:
        if 'uri' in link:
            uri = link['uri']  # Extract the URL of the link
            
            # Filter URLs that end with the specified file extensions
            if uri.endswith(file_extensions):
                rect = fitz.Rect(link['from'])  # Get the rectangle where the link appears
                
                # # Extract the text within the rectangle
                text_instances = page.get_text('dict', clip=rect)['blocks']
                
                # Loop through text instances in that area
                for block in text_instances:
                    for line in block.get('lines', []):
                        for span in line.get('spans', []):
                            # Append the URL to the list
                            url_list.append(uri)
                            url=set(url_list)
                            break  # Exit the loop after finding the link for this area

# Print the list of URLs
for id, url in enumerate(url, start=1):
    print(f"{id}. {url}")

doc.close()
