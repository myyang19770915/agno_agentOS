try:
    from googlesearch import search
    print("Testing googlesearch...")
    results = []
    # Test simple search first
    for res in search("NVIDIA CES 2026", num_results=3, advanced=True):
        print(f"Title: {res.title}")
        print(f"URL: {res.url}")
        results.append(res)
    
    if not results:
        print("No results found.")
    else:
        print(f"Found {len(results)} results.")

except Exception as e:
    print(f"Error: {e}")
