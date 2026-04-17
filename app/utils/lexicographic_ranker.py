# Helper to generate and manage string-based fractional indexes
class LexicographicRanker:
    def increment(char: str) -> str:
        return chr(ord(char) + 1)

    def midpoint(str1: str | None, str2: str | None) -> str:
        # Default floors and ceilings if None
        if not str1:
            str1 = "`"  # Backtick, right before 'a'
        if not str2:
            str2 = "{"  # Brace, right after 'z'

        # If they are exactly the same, append 'm'
        if str1 == str2:
            return str1 + "m"

        pos = 0
        while True:
            char1 = str1[pos] if pos < len(str1) else "`"
            char2 = str2[pos] if pos < len(str2) else "{"

            # If there's a gap between characters, pick the middle
            if ord(char2) - ord(char1) > 1:
                mid_char = chr(ord(char1) + (ord(char2) - ord(char1)) // 2)
                return str1[:pos] + mid_char

            # If we've run out of the first string, append 'm' and return
            if pos >= len(str1) - 1:
                return str1 + "m"

            pos += 1

    # Generates simple sequential keys: a, b, c ... z, za, zb ...
    def initial_keys(count: int) -> list[str]:
        keys = []
        for i in range(count):
            prefix_length = i // 26
            char = chr(97 + (i % 26))
            keys.append("z" * prefix_length + char)
        return keys
