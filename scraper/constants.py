
#Events that we decided to replace due to them following a tournament format instead of the typical card format that is being used today.
EXCLUDED_EVENTS = (
    
    "UFC 23: Ultimate Japan 2",
    "UFC Fight Night: Lamas vs. Penn",
    "UFC Fight Night: Hermansson vs. Weidman",
    "UFC 20: Battle for the Gold",
    "UFC 19: Ultimate Young Guns",
    "UFC 18: The Road to the Heavyweight Title",
    "UFC Brazil: Ultimate Brazil",
    "UFC 17: Redemption",
    "UFC 16: Battle in the Bayou",
    "UFC Japan: Ultimate Japan",
    "UFC 15: Collision Course",
    "UFC 14: Showdown",
    "UFC 13: The Ultimate Force",
    "UFC 12: Judgement Day",
    "UFC: The Ultimate Ultimate 2",
    "UFC 11: The Proving Ground",
    "UFC 10: The Tournament",
    "UFC 9: Motor City Madness",
    "UFC 8: David vs. Goliath",
    "UFC: The Ultimate Ultimate",
    "UFC 7: The Brawl in Buffalo",
    "UFC 6: Clash of the Titans",
    "UFC 5: The Return of the Beast",
    "UFC 4: Revenge of the Warriors",
    "UFC 3: The American Dream",
    "UFC 2: No Way Out",
    "UFC 1: The Beginning",
)



#List of Tuples containing string replacements (Order matters: longer/more-specific patterns should precede shorter ones that)
EVENT_NAME_REPLACEMENTS = (
    #The original event was Blanchfield vs. Barber. However Barber suffered a seizure during her ring walk cancelling her bout
    #Due to this, Wikipedia changed the event title to Gamrot vs Klein. However Tapology kept the original title
    ("UFC on ESPN: Gamrot vs. Klein","UFC Fight Night: Blanchfield vs. Barber"),
    
    #Rampage Jackson sometimes has his last name Jackson in the fight title and other times Rampage is in the title.
    #This is the one unique case where Tapology uses Jackson in the title while Wikipedia uses Rampage so we replace it.
    ("UFC 114: Rampage vs. Evans", "UFC 114: Jackson vs. Evans"),

    #Certain UFC events have alternative titles or slightly modified titles, we replace the title events from Wikipedia
    # to the titles of the events used within the Tapology website. 
    ("UFC 75: Champion vs. Champion", "UFC 75"),
    ("UFC on FX: Johnson vs. McCall 2", "UFC on FX 3: Johnson vs. McCall"),
    ("UFC on ESPN: Vera vs. Cruz", "UFC Fight Night: Vera vs. Cruz"),
    ("UFC Fight Night 6.5",        "UFC The Final Chapter: Ortiz vs Shamrock 3"),
    #("UFC Brazil: Ultimate Brazil","UFC 17.5: Ultimate Brazil"),
    
    #Wikipedia labels the first few UFC Fight Night events as UFC Ultimate Fight Night X
    #Tapology instead just labels them as UFC Fight Night so we make the replacement
    ("UFC Ultimate Fight Night ",  "UFC Fight Night "),    # Handles numbered cases ex. UFC Ultimate Fight Night X-> UFC Fight Night X
    ("UFC Ultimate Fight Night",   "UFC Fight Night 1"),   # Exact match, no number
    
    ##Handles oddities with particular Fighter Names between Wikipedia and Tapology
    ("The Uprising","Uprising"),
    ("The Korean Zombie",          "Korean Zombie"),
    ("Ngannou",                    "N'gannou"),
    ("Saint",                      "St."),
    ("Rountree Jr.",               "Rountree"),
    ("Cowboy",                     "Cerrone"),
    ("Bigfoot",                    "Silva"),

    #Converts Roman Numerals to decimal digits (Wikipedia uses Roman Numerals for some events and Tapology always uses Decimal)
    ("III",                        "3"),
    ("II",                         "2"),
)


