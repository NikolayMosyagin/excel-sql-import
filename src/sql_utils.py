def quote_identifier(identifier: str) -> str:
    return f"[{identifier.replace(']', ']]')}]"