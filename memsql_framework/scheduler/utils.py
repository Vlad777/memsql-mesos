import itertools
import random

def get_resources(resources):
    try:
        cpus = next(rsc.scalar.value for rsc in resources if rsc.name == "cpus")
        mem = next(rsc.scalar.value for rsc in resources if rsc.name == "mem")
        disk = next(rsc.scalar.value for rsc in resources if rsc.name == "disk")
        port_ranges = list(range(port_range.begin, port_range.end + 1) for rsc in resources for port_range in rsc.ranges.range if rsc.name == "ports")
        ports = list(itertools.chain(*port_ranges))
        return cpus, mem, disk, ports
    except StopIteration:
        return 0, 0, 0, []

i = 0
left = [
    "happy", "jolly", "dreamy", "sad", "angry",
    "pensive", "focused", "sleepy", "grave", "distracted",
    "determined", "stoic", "stupefied", "sharp", "agitated",
    "cocky", "tender", "goofy", "furious", "desperate",
    "hopeful", "compassionate", "silly", "lonely", "condescending",
    "naughty", "kickass", "drunk", "boring", "nostalgic",
    "ecstatic", "insane", "cranky", "mad", "jovial",
    "sick", "hungry", "thirsty", "elegant", "backstabbing",
    "clever", "trusting", "loving", "suspicious", "berserk",
    "high", "romantic", "prickly", "evil"
]

right = [
    "lovelace", "franklin", "tesla", "einstein", "bohr",
    "davinci", "pasteur", "nobel", "curie", "darwin",
    "turing", "ritchie", "torvalds", "pike", "thompson",
    "wozniak", "galileo", "euclid", "newton", "fermat",
    "archimedes", "poincare", "heisenberg", "feynman", "hawking",
    "fermi", "pare", "mccarthy", "engelbart", "babbage",
    "albattani", "ptolemy", "bell", "wright", "lumiere",
    "morse", "mclean", "brown", "bardeen", "brattain",
    "shockley"
]

def generate_host():
    global i
    host = "%s_%s-%s.memsql" % (random.choice(left), random.choice(right), i)
    i += 1
    return host
