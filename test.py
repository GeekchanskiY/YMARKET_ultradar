import datetime
import time
import pause

for i in range(1, 100):
    print(i)
    if i % 10 == 0:
        print("A")
        pause.until(datetime.datetime.now() + datetime.timedelta(seconds=3))