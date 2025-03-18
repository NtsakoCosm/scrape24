
import asyncio
import json
import re
import random
import datetime
from playwright.async_api import async_playwright,Page
from threading import Lock


dataBun = []
dataBunLock = Lock()
listingNums = set()

PROPERTY24_REGEX = re.compile(
    r"^https://(www\.)?property24\.com/for-sale/"
    r".+?/.+?/.+?/\d+/\d+/?(\?.*)?$",
    re.IGNORECASE
)
scraped_links = set()
scraped_linksLock = Lock()
def clean_text(text):
    # Split into lines and filter out unwanted lines like "View less"
    return [line.strip() for line in text.split('\n') if line.strip() and line.strip() != "View less"]

def group_data(tokens):
    grouped = {}
    i = 0
    current_category = None
    while i < len(tokens):
        token = tokens[i]
        # A category header is assumed to be any token that doesn't end with "km" and is not part of a pair.
        # If there's a following token that ends with "km", then this token is an item name.
        # Otherwise, we treat it as a new category header.
        if current_category is None or (i + 1 < len(tokens) and not tokens[i+1].endswith("km")):
            # New category header
            current_category = token
            if current_category not in grouped:
                grouped[current_category] = []
            i += 1
        else:
            # Otherwise, expect the current token and the next token to form an item (name, distance)
            if i + 1 < len(tokens) and tokens[i+1].endswith("km"):
                item = {"name": token, "distance": tokens[i+1]}
                grouped[current_category].append(item)
                i += 2
            else:
                # Fallback: treat token as a new category header if it doesn't follow the expected pattern
                current_category = token
                if current_category not in grouped:
                    grouped[current_category] = []
                i += 1
    return grouped

def clean_data_key(data):
    cleaned_data = []
    current_entry = {}

    for entry in data:
        if 'Bedrooms' in entry:  # New entry starts
            if current_entry:  # Append the previous entry if not empty
                cleaned_data.append(current_entry)
            current_entry = {}
        
        parts = entry.split('\n')
        for part in parts:
            if ':' in part:
                key, value = part.split(': ')
                current_entry[key.strip()] = value.strip()
            else:
                current_entry[part.strip()] = True
    
    # Append the last entry if not empty
    if current_entry:
        cleaned_data.append(current_entry)

    return cleaned_data

def clean_description(description):
    cleaned_description = description.replace('\n', ' ').strip()  # Replace '\n' with space and remove leading/trailing spaces
    if cleaned_description.endswith(' Read Less'):
        cleaned_description = cleaned_description[:-9].strip()  # Remove ' Read Less' from the end and strip leading/trailing spaces
    return cleaned_description
def clean_data(data):
    cleaned_data = {}
    keys = ['Province', 'City', 'Town',"ls"]
  
    values = [data[i] for i in range(len(data)) if data[i] not in ['|', '>', 'Property for Sale'] and data[i] != data[i-1]]
    for key, value in zip(keys, values):
        cleaned_data[key] = value
    return cleaned_data

async def scrapeListing(page:Page,start):
    global dataBun
    global dataBunLock
    listingData = {}
    url = page.url
    image_url =None
    address = None
    features = []
    properties = {}
    grouped= {}
    try:
        await page.click('.js_readMoreLinkText',timeout=500)
        descr =  await page.locator(".js_readMoreContainer").all_inner_texts()
        
    except :
        print("Read More, button not found or clickable.")
        descr =  await page.locator(".js_readMoreContainer").all_inner_texts()
    try: 
        headings= await page.query_selector_all(".collapsed")
        for i in headings:
            await i.click()
        
        
            
    except:
        pass
    try :
        #await asyncio.sleep(3)
        await page.locator("#P24_pointsOfInterest").scroll_into_view_if_needed(timeout=1000)
        pois = page.locator("#P24_pointsOfInterest").get_by_text("View more")
            
        # Check if elements exist
        if await pois.count() > 0:
            for i in range(await pois.count()):
                await pois.nth(0).click()
                await page.wait_for_load_state(state="load")
                
            
            
            point_of_interests= await page.locator("#P24_pointsOfInterest").all_inner_texts()
           
            for block in point_of_interests:
                cleaned = clean_text(block)
                grouped = group_data(cleaned)
    except :
        print("POIS ERROR")


    
    
        
    size =  await page.locator(".p24_size").all_inner_texts()
    
    try:
        keyfeatures = await page.locator(".p24_keyFeaturesContainer").all_inner_texts()
        if keyfeatures:
            keyfeatures = clean_data_key(keyfeatures)[0]
            for k,v in keyfeatures.items():
                if type(keyfeatures[k]) == bool:
                    features.append(k)
            
                else:
                    properties[k] = v
            
            features = features
        else:
            features =[]
    except :
        pass

    listingNo = await page.locator(".p24_propertyOverviewRow:nth-child(1) .p24_info").all_inner_texts()
    price = await page.locator(".p24_price").all_inner_texts()
    crumbs = await page.locator("#breadCrumbContainer li~ li+ li , #breadCrumbContainer li~ li+ li a").all_inner_texts()
    crumbs = clean_data(crumbs)
    element = await page.query_selector('div.js_lightboxImageWrapper.p24_galleryImageHolder.js_galleryImage.active')
    try:
        image_element = page.locator("div[class='js_lightboxImageWrapper p24_galleryImageHolder js_galleryImage active']")
        image_url = await image_element.get_attribute("data-image-url")
    except:
        pass
    
    try:
        address = await page.locator(".p24_addressPropOverview").inner_text(timeout=500)
    except:
        address = "None found"
    try:
        listingData["size"] = size[0]
    except:
        listingData["size"] = "None" 
    
    try:
        listingData["price"] = price[0]
    except:
        listingData["price"] = "None" 
    listingData["features"] = features
    try:
        listingData["description"]= clean_description(descr[0])
    except:
        listingData["description"]= "None Found"

    
    listingData["image_url"] =image_url
    listingData["pois"] = grouped
    listingData["address"] = address
    listingData["url"] =url
    listingData.update(properties)
    listingData.update(crumbs)
    listingData["ListingNo"] = listingNo[0] if listingNo != [] else "f"
   
    
    
    print(listingData)
    end = datetime.datetime.now()
    elapsed = end - start
    print(elapsed)
    
    with dataBunLock:
        if listingData["ListingNo"] not in listingNums:
            listingNums.add(listingData["ListingNo"])
            dataBun.append(listingData)
    print(len(dataBun))
    return listingData

async def get_hovered_url(page, x, y):
    """Get the URL of the closest <a> element at the given viewport coordinates."""
    
    url = await page.evaluate("""
        ([x, y]) => {
            let elem = document.elementFromPoint(x, y);
            while (elem && elem.tagName !== 'A') {
                elem = elem.parentElement;
            }
            return elem ? elem.href : null;
        }
    """, [x, y])
    
    return url


async def scroll_and_scrape(page: Page, x=460, y=383, step=100, delay=0.1,start=datetime.datetime.now()):
    """
    Slowly scroll down the page while keeping the mouse at fixed (x, y) client coordinates.
    At each scroll step, check the link underneath the mouse. If a link is found
    and it matches the desired Property24 structure and hasn't been scraped yet,
    save the current scroll position, click the link, wait for the new page to load,
    scrape the listing, then return to the previous page at the saved scroll position with the mouse reset.
    
    :param page: The Playwright (or similar) page object.
    :param x: The fixed x-coordinate (client coordinate) for checking/clicking the link.
    :param y: The fixed y-coordinate (client coordinate) for checking/clicking the link.
    :param step: The number of pixels to scroll down each time.
    :param delay: The delay (in seconds) between scroll steps.
    :return: The data returned by scrapeListing, or None if no valid link is found.
    """
    global scraped_links
    while True:
        # Get current scroll position, viewport height, and total document height.
        scrollY = await page.evaluate("() => window.scrollY")
        innerHeight = await page.evaluate("() => window.innerHeight")
        scrollHeight = await page.evaluate("() => document.body.scrollHeight")
        
        # If we are near the bottom, break out of the loop.
        if scrollY + innerHeight >= scrollHeight:
            break
        
        # Get the URL at the current mouse (x, y) coordinates.
        url = await get_hovered_url(page, x, y)
        
        if url and PROPERTY24_REGEX.match(url):
            if url in scraped_links:
                pass
                #Continue on
            else:
                print(f"Valid new link found: {url}")
                with scraped_linksLock:
                    scraped_links.add(url)  # Mark this URL as scraped.
                
                # Save the current scroll position.
                previous_scroll = scrollY

                
                await page.mouse.click(x, y)
                await asyncio.sleep(0.5)
                if await page.locator("#DuplicateListingsModal > div > div").is_visible():
                    await page.mouse.click(555, 299)
                    await scrapeListing(page,start)
                    await page.go_back()
                    await page.mouse.click(166, 260)
                    continue

                # Call your scrapeListing function.
                listing_data = await scrapeListing(page,start)
                await page.go_back()
                
                
               
                await page.evaluate(f"() => window.scrollTo(0, {previous_scroll})")
                # Reset the mouse position.
                await page.mouse.move(x, y)
                
                return listing_data
        
        # Scroll down by the specified step.
        await page.evaluate(f"() => window.scrollBy(0, {step})")
        # Ensure the mouse stays at the fixed viewport coordinates.
        await page.mouse.move(x, y)
        # Wait briefly before the next scroll.
        await asyncio.sleep(delay)
    
    return None


async def main():
    one = random.randint(1, 2)
    two = random.randint(2, 4)
    three = random.randint(4, 6)
    four = random.randint(6, 8)
    five = random.randint(8, 10)
    six = random.randint(10, 12)
    
    async def run_context(url, context_name, rg =(1,32),headless=False):
        async with async_playwright() as p:
            
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context()
            page = await context.new_page()
  
            await page.set_viewport_size({"width": 1280,"height": 720})
            page.set_default_timeout(31536000)
            
            await page.goto(f"""{url}""")
            
            for ii in range(rg[0],rg[1]):
                for i in range(1,24):
                
                    await scroll_and_scrape(page)
            
                await page.goto(f"""https://www.property24.com/for-sale/advanced-search/results/p{ii+1}?sp=pid%3d1%2c{five}%2c{four}%2c{two}%2c{five}%2c{three}%2c2%2c{four}""")

               
                        
            
            await asyncio.sleep(60)
            
            
            
            
              
    num_scrapers = 1
    interval = 33
    # Generate URLs with page numbers increasing in intervals of 33
    pooled = [
        f"https://www.property24.com/for-sale/advanced-search/results/p{x}?sp=pid%3d1%2c{five}%2c{four}%2c{two}%2c{five}%2c{three}%2c2%2c{four}"
        for x in range(32, num_scrapers * interval, interval) 
    ]
    
    urls = [ 
        ( pooled[x],f"context_{x+1}",((x+(x*interval))+1,interval+(interval*x))) for x in range(0,len(pooled))

        ]
    
    tasks = [asyncio.create_task(run_context(*args)) for args in urls]
    await asyncio.gather(*tasks)
    with open("Property24Data.json", "w") as file:
        json.dump(dataBun, file, indent=4)
   
        
    


                
                
if __name__ == "__main__":
    asyncio.run(main())
    


