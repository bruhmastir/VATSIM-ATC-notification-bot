SUPPORTED_AIRPORTS = ['OMAA', 'OMAB', 'OMAC', 'OMAD', 'OMAF', 'OMAG', 'OMAH', 'OMAJ', 'OMAL', 'OMAM', 'OMAQ', 'OMAR', 'OMAS', 'OMAZ', 'OMBY', 'OMDB', 'OMDM', 'OMDW', 'OMFJ', 'OMRK', 'OMRS', 'OMSJ', 'OMSN', 'OMUQ', 'OOBR', 'OOFD', 'OOFQ', 'OOGB', 'OOHA', 'OOIA', 'OOIZ', 'OOJA', 'OOKB', 'OOLK', 'OOMA', 'OOMS', 'OOMX', 'OOSA', 'OOSH', 'OOSQ', 'OOSR', 'OOTH', 'OOYB', 'OTBD', 'OTBH', 'OTBK', 'OTHH']

TIER_1_AIRPORTS = ['OMDB']

ATC_RATING_CONVERSIONS = {"CTR": "C1", "APP": "S3", "TWR": "S2", "GND": "S1", "DEL": "S1"}

PREFIX = "!"

DEV_PREFIX = "$"

COMMAND_ORDER = [
   "setrating",
   "register", 
   "optout", 
   "optin", 
   "setquiet", 
   "settraining", 
   "observe",
   "observehours", 
   "view", 
   "recommend", 
   "supportme", 
   "edit", 
   "remove", 
   "help", 
   "reportbug"
]