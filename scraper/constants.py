
#Events that we decided to skip due to them not following the 5 minute round format. 
# These events are typically from the early days of the UFC, (Pre UFC 21) when the rules were not yet standardized.
EXCLUDED_EVENTS = (
    "UFC 20: Battle for the Gold",
    "UFC 19: Ultimate Young Guns",
    "UFC 18: The Road to the Heavyweight Title",
    "UFC 17.5: Ultimate Brazil", #Alternate title to UFC Brazil: Ultimate Brazil
    "UFC Brazil: Ultimate Brazil",
    "UFC 17: Redemption",
    "UFC 16: Battle in the Bayou",
    "UFC 15.5: Ultimate Japan", #Alternate title to UFC Japan: Ultimate Japan
    "UFC Japan: Ultimate Japan",
    "UFC 15: Collision Course",
    "UFC 14: Showdown",
    "UFC 13: The Ultimate Force",
    "UFC 12: Judgement Day",
    "UFC 11.5: Ultimate Ultimate 1996", #Alternate title to UFC: The Ultimate Ultimate 2
    "UFC: The Ultimate Ultimate 2",
    "UFC 11: The Proving Ground",
    "UFC 10: The Tournament",
    "UFC 9: Motor City Madness",
    "UFC 8: David vs. Goliath",
    "UFC 7.5: Ultimate Ultimate 1995", #Alternate title to UFC: The Ultimate Ultimate
    "UFC: The Ultimate Ultimate",
    "UFC 7: The Brawl in Buffalo",
    "UFC 6: Clash of the Titans",
    "UFC 5: The Return of the Beast",
    "UFC 4: Revenge of the Warriors",
    "UFC 3: The American Dream",
    "UFC 2: No Way Out",
    "UFC 1: The Beginning",

    #These events are excluded because they were cancelled due to fighter injury or other issues.
    "UFC on ESPN: Overeem vs. Harris",
    "UFC 233: Cejudo vs. Dillashaw"
    "UFC Fight Night: Lamas vs. Penn",
    "UFC Fight Night: Hermansson vs. Weidman",
    "UFC 176: Aldo vs. Mendes 2",
)



# Full event name overrides — first match wins, then return immediately
EVENT_OVERRIDE_REPLACEMENTS = (
    # The original event was Blanchfield vs. Barber. However Barber suffered a seizure during her ring walk cancelling her bout
    # Due to this, Wikipedia changed the event title to Gamrot vs Klein. However Tapology kept the original title
    ("UFC on ESPN: Gamrot vs. Klein", "UFC Fight Night: Blanchfield vs. Barber"),

    # Rampage Jackson sometimes has his last name Jackson in the fight title and other times Rampage is in the title.
    # This is the one unique case where Tapology uses Jackson in the title while Wikipedia uses Rampage so we replace it.
    ("UFC 114: Rampage vs. Evans", "UFC 114: Jackson vs. Evans"),

    # Every other fighter that has "Saint" within their name has "St." in their fight titles. Benoit Saint-Denis is the
    # one exception to this rule, so we overwrite conversion of Saint -> St.
    ("UFC Fight Night: Moicano vs. Saint Denis", "UFC Fight Night: Moicano vs. Saint-Denis"),

    # Donald Cerrone sometimes has his last name Cerrone in the fight title and other times Cowboy is in the title.
    # These are the two unique cases where Tapology uses Cerrone in the title while Wikipedia uses Cowboy so we replace it.
    ("UFC 246: McGregor vs. Cowboy", "UFC 246: McGregor vs. Cerrone"),
    ("UFC Fight Night: Cowboy vs. Miller", "UFC Fight Night 45: Cerrone vs. Miller"),

    # Antonio Silva sometimes has his last name Silva in the fight title and other times Bigfoot is in the title.
    # These are the three unique cases where Tapology uses Bigfoot in the title instead of Silva
    ("UFC Fight Night: Bigfoot vs. Arlovski", "UFC Fight Night: Bigfoot vs. Arlovski 2"),
    ("UFC Fight Night: Bigfoot vs. Mir", "UFC Fight Night: Bigfoot vs Mir"),
    ("UFC Fight Night: Hunt vs. Bigfoot", "UFC Fight Night: Hunt vs Bigfoot"),


    #This is the only event on Tapology that uses Roman Numerals so we have to account for this specific case.
    #Also Cruz and Faber never fought each other in the UFC before this event, however they did fight against each other in the WEC
    #This is why there is a descrepencay between Wikipedia saying Cruz vs Faber 1 and Tapology saying Cruz vs Faber 2
    ("UFC 132: Cruz vs. Faber", "UFC 132: Cruz vs Faber II"),

    # Certain UFC events have alternative titles or slightly modified titles, we replace the title events from Wikipedia
    # to the titles of the events used within the Tapology website.
    ("UFC 75: Champion vs. Champion", "UFC 75: UFC 75"),
    ("UFC on FX: Johnson vs. McCall 2", "UFC on FX 3: Johnson vs. McCall"),
    ("UFC on ESPN: Vera vs. Cruz", "UFC Fight Night: Vera vs. Cruz"),
    ("UFC Fight Night 6.5", "UFC The Final Chapter: Ortiz vs Shamrock 3"),
    ("UFC Fight Night 6", "UFC Fight Night 6: Sanchez vs Parisyan"),
    ("UFC Ultimate Fight Night 5", "UFC Fight Night 5: Leben vs Silva"),

    # TUF Finale event name replacements: Wikipedia descriptive names -> Tapology numbered names
    ("The Ultimate Fighter: Heavy Hitters Finale", "The Ultimate Fighter 28 Finale"),
    ("The Ultimate Fighter: Undefeated Finale", "The Ultimate Fighter 27 Finale"),
    ("The Ultimate Fighter: A New World Champion Finale", "The Ultimate Fighter 26 Finale"),
    ("The Ultimate Fighter: Redemption Finale", "The Ultimate Fighter 25 Finale"),
    ("The Ultimate Fighter: Tournament of Champions Finale", "The Ultimate Fighter 24 Finale"),
    ("The Ultimate Fighter Latin America 3 Finale: dos Anjos vs. Ferguson", "UFC Fight Night 98: Dos Anjos vs. Ferguson"),
    ("The Ultimate Fighter: Team Joanna vs. Team Cláudia Finale", "The Ultimate Fighter 23 Finale"),
    ("The Ultimate Fighter: Team McGregor vs. Team Faber Finale", "The Ultimate Fighter 22 Finale"),
    ("The Ultimate Fighter Latin America 2 Finale: Magny vs. Gastelum", "UFC Fight Night 78: Magny vs. Gastelum"),
    ("The Ultimate Fighter: American Top Team vs. Blackzilians Finale", "The Ultimate Fighter 21 Finale"),
    ("The Ultimate Fighter: A Champion Will Be Crowned Finale", "The Ultimate Fighter 20 Finale"),
    ("The Ultimate Fighter: Team Edgar vs. Team Penn Finale", "The Ultimate Fighter 19 Finale"),
    ("The Ultimate Fighter Brazil 3 Finale: Miocic vs. Maldonado", "UFC Fight Night: Miocic vs. Maldonado"),
    ("The Ultimate Fighter Nations Finale: Bisping vs. Kennedy", "UFC Fight Night: Bisping vs. Kennedy"),
    ("The Ultimate Fighter China Finale: Kim vs. Hathaway", "UFC Fight Night: Kim vs. Hathaway"),
    ("The Ultimate Fighter: Team Rousey vs. Team Tate Finale", "The Ultimate Fighter 18 Finale"),
    ("The Ultimate Fighter: Team Jones vs. Team Sonnen Finale", "The Ultimate Fighter 17 Finale"),
    ("The Ultimate Fighter: Team Carwin vs. Team Nelson Finale", "The Ultimate Fighter 16 Finale"),
    ("The Ultimate Fighter: Live Finale", "The Ultimate Fighter 15 Finale"),
    ("The Ultimate Fighter: Team Bisping vs. Team Miller Finale", "The Ultimate Fighter 14 Finale"),
    ("The Ultimate Fighter: Team Lesnar vs. Team dos Santos Finale", "The Ultimate Fighter 13 Finale"),
    ("The Ultimate Fighter: Team GSP vs. Team Koscheck Finale", "The Ultimate Fighter 12 Finale"),
    ("The Ultimate Fighter: Team Liddell vs. Team Ortiz Finale", "The Ultimate Fighter 11 Finale"),
    ("The Ultimate Fighter: Heavyweights Finale", "The Ultimate Fighter 10 Finale"),
    ("The Ultimate Fighter: United States vs. United Kingdom Finale", "The Ultimate Fighter 9 Finale"),
    ("The Ultimate Fighter: Team Nogueira vs. Team Mir Finale", "The Ultimate Fighter 8 Finale"),
    ("The Ultimate Fighter: Team Rampage vs. Team Forrest Finale", "The Ultimate Fighter 7 Finale"),
    ("The Ultimate Fighter: Team Hughes vs. Team Serra Finale", "The Ultimate Fighter 6 Finale"),
    ("The Ultimate Fighter: Team Pulver vs. Team Penn Finale", "The Ultimate Fighter 5 Finale"),
    ("The Ultimate Fighter: The Comeback Finale", "The Ultimate Fighter 4 Finale"),
    ("The Ultimate Fighter: Team Ortiz vs. Team Shamrock Finale", "The Ultimate Fighter 3 Finale"),
    ("The Ultimate Fighter: Team Hughes vs. Team Franklin Finale", "The Ultimate Fighter 2 Finale"),
    ("The Ultimate Fighter: Team Couture vs. Team Liddell Finale", "The Ultimate Fighter 1 Finale"),
)

# Generic token replacements — all applied sequentially to handle fighter name oddities and roman numerals
EVENT_TOKEN_REPLACEMENTS = (
    # Handles oddities with particular Fighter Names between Wikipedia and Tapology
    ("du Plessis", "Du Plessis"),
    ("The Uprising", "Uprising"),
    ("The Korean Zombie", "Korean Zombie"),
    ("Ngannou", "N'gannou"),
    ("St-Pierre", "St. Pierre"),
    ("Saint", "St."),
    ("Rountree Jr.", "Rountree"),
    #("Cowboy", "Cerrone"),
    ("Bigfoot", "Silva"),

    # Converts Roman Numerals to decimal digits (Wikipedia uses Roman Numerals for some events and Tapology always uses Decimal)
    ("III", "3"),
    ("II", "2"),

    # Wikipedia labels the first few UFC Fight Night events as UFC Ultimate Fight Night X
    # Tapology instead just labels them as UFC Fight Night so we make the replacement
    ("UFC Ultimate Fight Night ", "UFC Fight Night "),    # Handles numbered cases ex. UFC Ultimate Fight Night X -> UFC Fight Night X
    ("UFC Ultimate Fight Night", "UFC Fight Night 1"),    # Exact match, no number
)



#WE DON'T INCLUDE ANY OF THE ULTIMATE FIGHTER EVENTS
#MAKE SURE TO MODIFY THE OBTAIN_UFC_EVENT_NAMES FUNCTION IN THE EVENTS SCRAPER TO ACCOUNT FOR THIS
#About 33 events are missing from the dataset due to this