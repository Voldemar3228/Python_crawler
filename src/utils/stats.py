def compute_page_stats(parsed_page: dict) -> dict:
    """Считает простую статистику для одной страницы"""
    return {
        "url": parsed_page["url"],
        "text_length": len(parsed_page["text"]),
        "num_links": len(parsed_page["links"]),
        "num_h1": len(parsed_page["headers"].get("h1", [])),
        "num_h2": len(parsed_page["headers"].get("h2", [])),
        "num_h3": len(parsed_page["headers"].get("h3", [])),
        "num_images": len(parsed_page["images"]),
        "num_lists": len(parsed_page["lists"].get("ul", [])) + len(parsed_page["lists"].get("ol", [])),
        "num_tables": len(parsed_page["tables"]),
    }

def compute_overall_stats(parsed_pages: list[dict]) -> dict:
    """Подсчёт общей статистики для всех страниц"""
    total_text = sum(len(p["text"]) for p in parsed_pages)
    total_links = sum(len(p["links"]) for p in parsed_pages)
    total_images = sum(len(p["images"]) for p in parsed_pages)
    return {
        "total_pages": len(parsed_pages),
        "total_text_length": total_text,
        "total_links": total_links,
        "total_images": total_images,
    }
