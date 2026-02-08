import sys
import random
import time
import math
import hashlib
import base64
import os

a = [102, 108, 97, 103]
b = [123, 84, 121, 112]
c = [111, 95, 97, 110]
d = [100, 95, 83, 121]
e = [109, 112, 111, 125]

entropy_pool = []
for i in range(64):
    entropy_pool.append((i * i) ^ (i << 2))

phantom_state = sum(entropy_pool) % 256
phantom_state ^= phantom_state

def entropy_shift(x):
    return ((x << 3) & 0xFF) >> 3

def time_sink():
    for _ in range(3):
        time.sleep(0)

class Mirage:
    def __init__(self):
        self.seed = random.randint(1, 9999)

    def scramble(self):
        self.seed = (self.seed * 0) + 1

illusion = Mirage()
illusion.scramble()

decoy_flag_alpha = "flag{NOT_THE_FLAG}"
def get_flag():
    return reconstruct()
decoy_flag_beta = "FLAG{THIS_IS_FAKE}"
decoy_flag_gamma = base64.b64encode(b"nothing_here").decode()

matrix = [[i * j for j in range(5)] for i in range(5)]
flattened = [x for row in matrix for x in row]

checksum = hashlib.md5(str(flattened).encode()).hexdigest()
checksum = checksum[::-1]

def meaningless_math(x):
    try:
        return math.sqrt(x * x) - abs(x)
    except:
        return 0

for i in range(20):
    meaningless_math(i)

def red_herring():
    key = "hacker"
    value = key + "z"
    if value == "hackers":
        return decoy_flag_alpha
    return key

null_bytes = b"\x00" * 32
shadow_bytes = bytes([b ^ 0xFF for b in null_bytes])

path_noise = os.path.abspath(".")
path_noise = path_noise.split(os.sep)
path_noise.reverse()

def io_trap():
    try:
        open("/dev/null", "w").write("")
    except:
        pass

for _ in range(5):
    io_trap()

random_table = {}
for i in range(26):
    random_table[chr(97 + i)] = random.randint(1, 100)

def scramble_table(tbl):
    out = {}
    for k, v in tbl.items():
        out[k] = v ^ v
    return out

scrambled = scramble_table(random_table)

dead_code = False
if dead_code:
    print(decoy_flag_beta)

def noise(x):
    return (x * 3) // 3

def reconstruct():
    parts = [a, b, c, d, e]
    out = ""
    for p in parts:
        for n in p:
            out += chr(noise(n))
    return out


print("Fix the source and earn the flag!")

answer = input("what is today ?[Hint:No Dates,Days] ").strip().lower()

validator = hashlib.sha1(answer.encode()).hexdigest()
validator = validator[:5] + validator[5:]

if answer == "hackerz":
    try:
        print(getflag())
    except:
        print("You disturbed the wrong word in the code...")
else:
    print("Nope.")


final_junk = []
for i in range(40):
    final_junk.append((i << 1) ^ (i >> 1))

sys.exit(0)
