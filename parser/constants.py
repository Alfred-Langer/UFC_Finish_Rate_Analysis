# Fighters whose sex cannot be determined from their Tapology page or Combat Registry page.
# We have determined these manually and have hardcoded them here as a fallback.
# Keyed by tapology_id (int) → sex string ('M' or 'F').
SEX_OVERRIDES: dict[int, str] = {
    63947:  "M",  # Aleksander Doskalchuk
    173019: "M",  # Mashrabjon Ruziboev
}

SEX_OVERRIDES_BY_NAME: dict[str, str] = {
    "Matt Lindland % The Law" : "M",
}