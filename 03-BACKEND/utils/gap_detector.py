def detect_gaps(line_items: dict, notes: dict, gaps_json: list) -> list:
    """
    Matches extracted statement line items to gaps using detection keywords.

    Args:
        line_items: {account_name: {amount, ...}, ...}
        notes: {raw: "text of notes", ...}
        gaps_json: list of all 58 gaps from gaps.json

    Returns:
        list: [
            {
                "gap_id": "1.1",
                "title": "...",
                "detected": True,
                "evidence": "Found X in statement",
                "severity": "HIGH",
                "line_items_affected": ["Current Assets", "Deferred Tax"]
            },
            ...
        ]
    """
    detected = []

    # Combine all line items + notes into searchable text
    searchable_text = " ".join([
        *line_items.keys(),
        notes.get('raw', '')
    ]).lower()

    for gap in gaps_json:
        gap_id = gap.get('gap_id')
        keywords = gap.get('detection_keywords', [])

        # Check if ANY keyword appears in the statement
        found_keywords = []
        for keyword in keywords:
            if keyword.lower() in searchable_text:
                found_keywords.append(keyword)

        if found_keywords:
            # Gap detected!
            detected.append({
                "gap_id": gap_id,
                "title": gap.get('title'),
                "detected": True,
                "keywords_found": found_keywords,
                "confidence": min(len(found_keywords) / len(keywords), 1.0),  # 0.0-1.0
                "evidence": f"Found keywords: {', '.join(found_keywords[:3])}",
                "severity": gap.get('risk', 'MEDIUM'),
                "mhms_treatment": gap.get('mhms_treatment', ''),
                "detection_rules": gap.get('detection_rules', [])
            })

    return detected
