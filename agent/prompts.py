"""System prompts used by the Pinterest poster agent."""

THUMBNAIL_SCORING_PROMPT = (
    "Score this {category} product image for e-commerce poster potential.\n"
    "Return JSON only, no markdown:\n"
    '{{\n'
    '  "score": <1-10>,\n'
    '  "reason": "<one concise sentence>",\n'
    '  "approve": <true if score >= 7>\n'
    '}}'
)

FULLRES_EXTRACTION_PROMPT = (
    "What is the main product image URL on this Pinterest pin page? "
    "Return only the URL, nothing else."
)

POSTER_GENERATION_PROMPT = (
    "Create a professional e-commerce poster for this product.\n"
    "Product name: {product_name}\n"
    "Price: {price}\n"
    "Tagline: {tagline}\n"
    "The poster should be clean, modern, and highlight the product."
)
