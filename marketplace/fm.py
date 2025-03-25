import json, requests as rq, os as sys_os
from pf import LoginWithCustomId as LWC, GetEntityToken as GET
T_C, S_K, C_T, I_L, M_I = 1, 0, 300, [], 3000

# Check if necessary packages are installed
def chk_pkg():
    p_m = {'requests': 'requests', 'colorama': 'colorama'}
    for m_n, p_n in p_m.items():
        try:
            __import__(m_n)
        except ModuleNotFoundError:
            print(f"Module '{m_n}' not found. Installing '{p_n}'...")
            try:
                print(f"Successfully installed '{p_n}'.")
            except Exception as e:
                print(f"Failed to install '{p_n}': {e}")

chk_pkg()

# Authentication function
def auth():
    rsp = LWC()
    if 'PlayFabId' in rsp:
        a_t = GET(rsp['PlayFabId'], 'master_player_account')
        print("Authentication successful.")
        return a_t
    else:
        print("Authentication failed.")
        return None

# Function to get items from PlayFab
def g_itm(a_t, s_k, c_t):
    u = "https://20ca2.playfabapi.com/Catalog/Search"
    h = {"x-entitytoken": a_t["EntityToken"], "Accept": "application/json"}
    b = {"filter": "(contentType eq 'PersonaDurable')", "orderBy": "creationDate DESC", "search": "Minecraft", "skip": s_k, "top": c_t}
    r = rq.post(u, json=b, headers=h)
    return r.json() if r.status_code == 200 else (print(f"API call failed: {r.text}"), {})[1]

# Function to get a specific item by UUID
def g_uuid(a_t, uuid):
    u = "https://20ca2.playfabapi.com/Catalog/Search"
    h = {"x-entitytoken": a_t["EntityToken"], "Accept": "application/json"}
    b = {"filter": f"(Id eq '{uuid}')", "top": 1, "skip": 0}
    r = rq.post(u, json=b, headers=h)
    return r.json() if r.status_code == 200 else (print(f"API call failed for UUID {uuid}: {r.text}"), {})[1]

# Function to process tags and fetch missing items
def process_tags_and_fetch_missing(a_t):
    tags_file = 'marketplace/tags.txt'
    data_file = 'marketplace/data.json'
    
    if not sys_os.path.exists(tags_file) or not sys_os.path.exists(data_file):
        print("Tags file or data.json not found. Skipping processing.")
        return

    # Read tag entries and descriptions from tags.txt
    with open(tags_file, 'r', encoding='utf-8') as f:
        tag_entries = {}
        for line in f:
            parts = line.strip().split('=')
            if len(parts) == 3:
                uuid, tag, description = parts
                tag_entries[uuid] = {"tag": tag, "description": description}

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    existing_items = {item.get("Id"): item for item in data.get("data", {}).get("Items", [])}

    # Process each UUID from tags.txt
    for uuid, tag_data in tag_entries.items():
        tag = tag_data["tag"]
        description = tag_data["description"]

        # Fetch the missing item for UUID if not already in existing_items
        if uuid not in existing_items:
            print(f"Fetching missing item for UUID: {uuid}")
            item_data = g_uuid(a_t, uuid.strip())
            if item_data and 'data' in item_data and 'Items' in item_data['data'] and item_data['data']['Items']:
                fetched_item = item_data['data']['Items'][0]
                existing_items[uuid] = fetched_item
                data["data"]["Items"].append(fetched_item)

        # Apply the tag and replace "§" in the description
        if uuid in existing_items:
            if "Tags" not in existing_items[uuid]:
                existing_items[uuid]["Tags"] = []
            if tag not in existing_items[uuid]["Tags"]:
                existing_items[uuid]["Tags"].append(tag)

            # Replace "§" in the Description with the custom description
            if "Description" in existing_items[uuid] and "NEUTRAL" in existing_items[uuid]["Description"]:
                if "§" in existing_items[uuid]["Description"]["NEUTRAL"]:
                    existing_items[uuid]["Description"]["NEUTRAL"] = description

    # Save the updated data back to the data.json
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print("Tags applied and missing UUIDs fetched successfully. Descriptions updated.")

# Main function to run the script
def main():
    # Delete data.json if it exists before proceeding
    data_file = 'marketplace/data.json'
    if sys_os.path.exists(data_file):
        print(f"Deleting existing {data_file}...")
        sys_os.remove(data_file)

    a_t = auth()
    if not a_t:
        return print("Exiting due to authentication failure.")

    global T_C, S_K, C_T, I_L
    f_d = g_itm(a_t, S_K, C_T)
    if f_d:
        print(json.dumps(f_d, ensure_ascii=False, indent=4))
        T_C = f_d.get('data', {}).get('Count', 0)
        print(f"Total items to fetch: {T_C}")
    if T_C > M_I:
        T_C = M_I
        print(f"Limiting the total number of items to fetch to {M_I}")
    while S_K < T_C:
        print(f"Fetching items {S_K} to {min(S_K + C_T, T_C)}")
        f_d = g_itm(a_t, S_K, C_T)
        if f_d:
            I_L.extend(f_d.get('data', {}).get('Items', []))
        S_K += C_T

    f_str = {"data": {"Count": T_C, "Items": I_L}}
    sys_os.makedirs('marketplace', exist_ok=True)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(f_str, f, ensure_ascii=False, indent=4)
    print(f"Fetched {len(I_L)} items and saved the full response to data.json")

    process_tags_and_fetch_missing(a_t)  # Fetch missing UUIDs and apply tags

if __name__ == "__main__":
    main()