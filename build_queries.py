"""Queries files banata hai (tukde-tukde): har artist / mood ki alag file.
File ka naam: <genre>__<naam>.txt  -> genre se radio ka form bharta hai.
Har mahine (ya `python build_queries.py`) chalane par month/year naye ho jate hain."""
import datetime
import os
import re

import config

ROM_T = ["{a} romantic songs", "{a} love songs jukebox", "{a} new song {year}", "{a} {month} {year} new songs",
         "{a} superhit songs", "{a} best songs", "{a} top hits", "{a} romantic song video"]
BHOJ_T = ["{a} bhojpuri romantic song", "{a} bhojpuri love song new", "{a} bhojpuri song {year}",
          "{a} bhojpuri {month} {year} new gana", "{a} superhit bhojpuri gana", "{a} bhojpuri jukebox",
          "{a} bhojpuri new romantic video song"]
SAD_T = ["{a} sad songs", "{a} dard bhare gaane", "{a} bewafa song", "{a} broken heart songs jukebox",
         "{a} sad song {year}"]
BHOJ_SAD_T = ["{a} bhojpuri sad song", "{a} bhojpuri bewafai gana", "{a} bhojpuri dard bhara gana",
              "{a} bhojpuri sad {year}"]
DJ_T = ["{a} bhojpuri dj song", "{a} dj remix bhojpuri", "{a} bhojpuri dance song {year}"]
PUNJABI_T = ["{a} romantic punjabi songs", "{a} love songs", "{a} new punjabi song {year}", "{a} superhit songs"]

BHOJPURI = ["Pawan Singh", "Khesari Lal Yadav", "Pramod Premi Yadav", "Shilpi Raj", "Neelkamal Singh",
            "Samar Singh", "Ritesh Pandey", "Arvind Akela Kallu", "Dinesh Lal Yadav Nirahua",
            "Antra Singh Priyanka", "Khushboo Jain", "Alok Kumar", "Rakesh Mishra", "Awadhesh Premi Yadav",
            "Tuntun Yadav", "Ankush Raja", "Shivani Singh", "Kajal Raghwani", "Ashish Yadav", "Mohan Rathore"]
HINDI_ROM = ["Jubin Nautiyal", "Atif Aslam", "Darshan Raval", "Armaan Malik", "Shreya Ghoshal", "Neha Kakkar",
             "Sonu Nigam", "B Praak", "Vishal Mishra", "Mohit Chauhan", "Palak Muchhal", "Stebin Ben",
             "Tulsi Kumar", "Asees Kaur", "Papon"]
RETRO = ["Kumar Sanu", "Udit Narayan", "Alka Yagnik", "Lata Mangeshkar", "Mohammed Rafi", "Kishore Kumar",
         "Sadhana Sargam", "Abhijeet Bhattacharya", "Sonu Nigam 90s", "Shaan"]
PUNJABI = ["Diljit Dosanjh", "AP Dhillon", "Karan Aujla", "Jass Manak", "Ammy Virk", "Satinder Sartaaj",
           "Guri", "Gurnam Bhullar"]
SAD_HINDI = ["Arijit Singh", "Jubin Nautiyal", "Atif Aslam", "Darshan Raval", "B Praak", "Raj Barman"]
SAD_BHOJ = ["Pawan Singh", "Khesari Lal Yadav", "Pramod Premi Yadav", "Neelkamal Singh", "Samar Singh",
            "Ritesh Pandey", "Arvind Akela Kallu"]
DJ_BHOJ = ["Pawan Singh", "Khesari Lal Yadav", "Samar Singh", "Neelkamal Singh", "Pramod Premi Yadav",
           "Arvind Akela Kallu"]

ARIJIT_TITLES = [
    "Tum Hi Ho", "Channa Mereya", "Kesariya", "Apna Bana Le", "Tera Yaar Hoon Main", "Phir Bhi Tumko Chahunga",
    "Hamari Adhuri Kahani", "Raabta", "Pehle Bhi Main", "Ae Dil Hai Mushkil", "Muskurane", "Gerua", "Soch Na Sake",
    "Phir Kabhi", "Khairiyat", "Samjhawan", "Agar Tum Saath Ho", "Kalank title track", "Tujhe Kitna Chahne Lage",
    "Humdard", "Ve Kamleya", "Sanam Re", "Dilbaro", "O Maahi", "Shayad", "Laal Ishq", "Zaalima", "Mast Magan",
    "Bolna", "Janam Janam", "Hawayein", "Pal", "Rataan Lambiyan", "Heeriye", "Kabira", "Nashe Si Chadh Gayi",
]

MOODS = {
    "bhojpuri_romantic": ["bhojpuri romantic songs {year}", "bhojpuri love songs jukebox", "new bhojpuri gana {month} {year}",
                          "bhojpuri superhit romantic gana", "bhojpuri pyar bhare gaane", "bhojpuri shaadi geet romantic"],
    "bhojpuri_sad": ["bhojpuri sad song {year}", "bhojpuri bewafai gana jukebox", "bhojpuri dard bhare gaane"],
    "hindi_romantic": ["hindi romantic songs {year}", "new hindi love songs {month} {year}", "best romantic songs bollywood",
                       "romantic songs jukebox hindi", "love songs 2020s bollywood"],
    "hindi_sad": ["hindi sad songs {year}", "bollywood heart broken songs jukebox", "dard bhare gaane hindi"],
    "retro_romantic": ["90s romantic songs hindi", "old is gold romantic songs", "evergreen bollywood love songs",
                       "kumar sanu udit narayan alka yagnik hits"],
    "punjabi_romantic": ["punjabi romantic songs {year}", "punjabi love songs jukebox"],
    "party_dj": ["bhojpuri dj song {year}", "hindi dj dance songs {year}", "wedding dance songs hindi bhojpuri"],
}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _write(name, lines):
    os.makedirs(config.QUERIES_DIR, exist_ok=True)
    seen, out = set(), []
    for ln in lines:
        if ln not in seen:
            seen.add(ln)
            out.append(ln)
    with open(os.path.join(config.QUERIES_DIR, name), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def build(today=None):
    d = today or datetime.date.today()
    month, year = d.strftime("%B"), d.year
    specs = [
        ("bhojpuri_romantic", BHOJPURI, BHOJ_T),
        ("hindi_romantic", HINDI_ROM, ROM_T),
        ("arijit_singh", ["Arijit Singh"], ROM_T + ["{a} sad songs", "{a} live songs", "{a} duet songs"]),
        ("retro_romantic", RETRO, ROM_T),
        ("punjabi_romantic", PUNJABI, PUNJABI_T),
        ("hindi_sad", SAD_HINDI, SAD_T),
        ("bhojpuri_sad", SAD_BHOJ, BHOJ_SAD_T),
        ("party_dj", DJ_BHOJ, DJ_T),
    ]
    n = 0
    for genre, artists, templates in specs:
        for a in artists:
            qs = [t.format(a=a, month=month, year=year) for t in templates]
            _write(f"{genre}__{slug(a)}.txt", qs)
            n += 1
    for genre, qs in MOODS.items():
        _write(f"{genre}__mood.txt", [x.format(month=month, year=year) for x in qs])
        n += 1
    _write("arijit_singh__titles.txt", [f"{t} Arijit Singh" for t in ARIJIT_TITLES])
    return n + 1


def list_files():
    if not os.path.isdir(config.QUERIES_DIR):
        return []
    return sorted(f for f in os.listdir(config.QUERIES_DIR) if f.endswith(".txt"))


def load_queries():
    """[(genre, query)] - sab files se."""
    out = []
    for fn in list_files():
        genre = fn.split("__")[0]
        with open(os.path.join(config.QUERIES_DIR, fn), encoding="utf-8") as f:
            out += [(genre, ln.strip()) for ln in f if ln.strip()]
    return out


def genres():
    return sorted({fn.split("__")[0] for fn in list_files()})


if __name__ == "__main__":
    print(f"{build()} files bani, {len(load_queries())} queries")
