"""Query concept extraction for graph-centric retrieval.

Tokenizes clinical queries, removes stop words, and matches tokens/bigrams
against graph node display names to identify relevant concepts.

Used by the ContextEngine to determine which graph nodes to traverse.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptMatch:
    """A matched concept from a user query.

    Attributes:
        term: The matched display name from the graph.
        resource_type_hint: Optional FHIR resource type (e.g. "Condition").
    """

    term: str
    resource_type_hint: str | None = None


# Common English stop words plus clinical filler words
STOP_WORDS: frozenset[str] = frozenset([
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "their", "his", "her", "its",
    "this", "that", "these", "those",
    "what", "which", "who", "whom", "how", "when", "where", "why",
    "and", "or", "but", "if", "then", "so", "because", "as", "while",
    "of", "in", "on", "at", "to", "for", "with", "by", "from", "about",
    "into", "through", "during", "before", "after", "between",
    "not", "no", "nor", "very", "just", "also", "than", "too",
    "all", "any", "some", "each", "every", "both",
    # Clinical filler
    "patient", "tell", "show", "give", "get", "find", "look",
    "please", "want", "know", "see", "check", "review",
    "recent", "latest", "last", "current",
])


def tokenize(query: str) -> list[str]:
    """Tokenize a query into lowercase alphanumeric tokens.

    Args:
        query: Raw user query string.

    Returns:
        List of lowercase tokens with punctuation stripped.
    """
    tokens: list[str] = []
    for word in query.lower().split():
        cleaned = "".join(ch for ch in word if ch.isalnum() or ch == "-")
        if cleaned:
            tokens.append(cleaned)
    return tokens


def remove_stop_words(tokens: list[str]) -> list[str]:
    """Remove stop words from token list.

    Args:
        tokens: List of lowercase tokens.

    Returns:
        Filtered list with stop words removed.
    """
    return [t for t in tokens if t not in STOP_WORDS]


def generate_bigrams(tokens: list[str]) -> list[str]:
    """Generate space-joined bigrams from a token list.

    Args:
        tokens: List of tokens (stop words already removed).

    Returns:
        List of "token1 token2" bigram strings.
    """
    return [f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)]


def extract_concepts(
    query: str,
    node_display_names: list[tuple[str, str | None]],
) -> list[ConceptMatch]:
    """Extract concepts from a query by matching against graph node names.

    Performs case-insensitive matching: checks whether query tokens and bigrams
    appear as substrings within node display names. Bigrams are checked first
    so multi-word clinical terms (e.g. "blood pressure") match before
    individual words.

    Args:
        query: The user's clinical query.
        node_display_names: List of (display_name, resource_type) tuples
            from graph nodes. resource_type may be None.

    Returns:
        Deduplicated list of ConceptMatch objects, bigram matches first.
    """
    if not query or not query.strip() or not node_display_names:
        return []

    tokens = tokenize(query)
    filtered = remove_stop_words(tokens)

    if not filtered:
        return []

    bigrams = generate_bigrams(filtered)

    # Build lowercase lookup: lowered_display -> (original_display, resource_type)
    display_lookup: dict[str, tuple[str, str | None]] = {}
    for display, rtype in node_display_names:
        if display:
            display_lookup[display.lower()] = (display, rtype)

    matched: dict[str, ConceptMatch] = {}  # keyed by lowered display name

    # Check bigrams first (higher specificity)
    for bigram in bigrams:
        for lower_display, (original, rtype) in display_lookup.items():
            if bigram in lower_display:
                if lower_display not in matched:
                    matched[lower_display] = ConceptMatch(
                        term=original, resource_type_hint=rtype
                    )

    # Check individual tokens
    for token in filtered:
        for lower_display, (original, rtype) in display_lookup.items():
            if token in lower_display:
                if lower_display not in matched:
                    matched[lower_display] = ConceptMatch(
                        term=original, resource_type_hint=rtype
                    )

    return list(matched.values())
