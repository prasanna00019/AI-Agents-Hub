from config import Config
from extractor import AudioExtractor
import logging
import sys

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

print("Starting test")
c = Config()
c.start_time = "00:00"
c.end_time = "00:30"
c.verbose = True
ex = AudioExtractor(c)
out = ex.extract("https://youtu.be/00Q0G84kq3M?si=DcMwp-wihYtYBCGY")
print("Extracted:")
print(out)
